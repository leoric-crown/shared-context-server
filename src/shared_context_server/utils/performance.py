"""
Performance optimization system with connection pooling and monitoring.

Implements production-ready performance optimization including:
1. ConnectionPoolManager - aiosqlite connection pooling with optimized settings
2. Performance monitoring and metrics collection
3. Query optimization and background cleanup
4. Pool exhaustion monitoring and alerts

Built according to PRP-005: Phase 4 - Production Ready specification.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

# AsyncGenerator import moved to TYPE_CHECKING block for performance
if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
else:
    # Runtime fallback
    pass

import aiosqlite

from ..utils.llm_errors import create_system_error

logger = logging.getLogger(__name__)


# ============================================================================
# CONNECTION POOL MANAGER
# ============================================================================


class ConnectionPoolManager:
    """Production-ready connection pool manager with performance monitoring."""

    def __init__(self) -> None:
        self.pool: asyncio.Queue[aiosqlite.Connection] | None = None
        self.pool_size = 0
        self.min_size = 5
        self.max_size = 50
        self.database_url = ""
        self.connection_timeout = 30.0
        self.pool_lock = asyncio.Lock()

        # Performance metrics
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "peak_connections": 0,
            "total_queries": 0,
            "avg_query_time": 0.0,
            "slow_queries": 0,
            "pool_exhaustion_count": 0,
            "connection_errors": 0,
        }

        # Track connection creation times for debugging
        self.connection_creation_times: dict[int, float] = {}

        # Pool status tracking
        self.is_initialized = False
        self.is_shutting_down = False

    async def initialize_pool(
        self,
        database_url: str,
        min_size: int = 5,
        max_size: int = 50,
        connection_timeout: float = 30.0,
    ) -> None:
        """Initialize optimized connection pool."""

        async with self.pool_lock:
            if self.is_initialized:
                logger.warning("Connection pool already initialized")
                return

            self.database_url = database_url
            self.min_size = min_size
            self.max_size = max_size
            self.connection_timeout = connection_timeout

            # Create connection queue
            self.pool = asyncio.Queue(maxsize=max_size)

            # Pre-fill pool with minimum connections
            logger.info(f"Initializing connection pool with {min_size} connections")
            for _ in range(min_size):
                success = await self._try_create_pool_connection()
                if not success:
                    logger.warning(
                        "Failed to create initial pool connection, continuing with fewer connections"
                    )

            self.is_initialized = True
            logger.info(
                f"Connection pool initialized: {self.pool_size}/{max_size} connections"
            )

    async def _try_create_pool_connection(self) -> bool:
        """Try to create a connection and add it to the pool. Returns success status."""
        if self.pool is None:
            return False

        try:
            conn = await self._create_optimized_connection()
            await self.pool.put(conn)
            self.pool_size += 1
        except Exception:
            logger.exception("Failed to create initial pool connection")
            self.connection_stats["connection_errors"] += 1
            return False
        else:
            return True

    async def _create_optimized_connection(self) -> aiosqlite.Connection:
        """Create a new database connection with performance optimizations."""

        try:
            # Create connection with optimized settings
            conn = await aiosqlite.connect(
                self.database_url,
                timeout=self.connection_timeout,
                check_same_thread=False,
            )

            # Apply SQLite performance optimizations
            await self._optimize_connection(conn)

            # Track connection creation
            conn_id = id(conn)
            self.connection_creation_times[conn_id] = time.time()
            self.connection_stats["total_connections"] += 1

        except Exception:
            logger.exception("Failed to create database connection")
            self.connection_stats["connection_errors"] += 1
            raise
        else:
            return conn

    async def _optimize_connection(self, conn: aiosqlite.Connection) -> None:
        """Apply performance optimizations to a connection."""

        # Production-grade SQLite performance settings
        optimizations = [
            "PRAGMA journal_mode = WAL",  # Write-Ahead Logging for concurrency
            "PRAGMA synchronous = NORMAL",  # Balanced safety/performance
            "PRAGMA cache_size = -16000",  # 16MB cache per connection
            "PRAGMA temp_store = MEMORY",  # Use memory for temp tables
            "PRAGMA mmap_size = 268435456",  # 256MB memory mapping
            "PRAGMA busy_timeout = 10000",  # 10 second timeout
            "PRAGMA optimize",  # Query planner optimization
        ]

        # Apply optimizations and collect any errors
        failed_optimizations = []

        async def apply_pragma(pragma: str) -> tuple[str, str] | None:
            try:
                await conn.execute(pragma)
            except Exception as e:
                return (pragma, str(e))
            else:
                return None

        for pragma in optimizations:
            result = await apply_pragma(pragma)
            if result:
                failed_optimizations.append(result)

        # Log any failures after the loop
        for pragma, error in failed_optimizations:
            logger.warning(f"Failed to apply optimization '{pragma}': {error}")

    @asynccontextmanager
    async def get_connection(
        self, operation_name: str = "unknown"
    ) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get optimized database connection with metrics tracking."""

        if not self.is_initialized or self.pool is None:
            raise RuntimeError("Connection pool not initialized")

        if self.is_shutting_down:
            raise RuntimeError("Connection pool is shutting down")

        start_time = time.time()
        conn = None

        try:
            # Try to get connection from pool
            try:
                conn = await asyncio.wait_for(
                    self.pool.get(), timeout=self.connection_timeout
                )
            except asyncio.TimeoutError:
                # Pool exhausted - try to create new connection if under limit
                async with self.pool_lock:
                    if self.pool_size < self.max_size:
                        logger.info(
                            f"Pool exhausted, creating new connection (size: {self.pool_size}/{self.max_size})"
                        )
                        conn = await self._create_optimized_connection()
                        self.pool_size += 1
                    else:
                        self.connection_stats["pool_exhaustion_count"] += 1
                        logger.exception(
                            f"Connection pool exhausted: {self.max_size} connections in use"
                        )
                        raise RuntimeError("Connection pool exhausted") from None

            # Update metrics
            self.connection_stats["active_connections"] += 1
            if (
                self.connection_stats["active_connections"]
                > self.connection_stats["peak_connections"]
            ):
                self.connection_stats["peak_connections"] = self.connection_stats[
                    "active_connections"
                ]

            yield conn

        finally:
            if conn is not None:
                # Update performance metrics
                query_time = (time.time() - start_time) * 1000  # ms
                self.connection_stats["active_connections"] -= 1
                self.connection_stats["total_queries"] += 1

                # Update average query time
                current_avg = self.connection_stats["avg_query_time"]
                total_queries = self.connection_stats["total_queries"]
                self.connection_stats["avg_query_time"] = (
                    current_avg * (total_queries - 1) + query_time
                ) / total_queries

                # Track slow queries (>100ms threshold)
                if query_time > 100:
                    self.connection_stats["slow_queries"] += 1
                    logger.warning(
                        f"Slow query detected: {query_time:.1f}ms for {operation_name}"
                    )

                # Return connection to pool
                try:
                    if not self.is_shutting_down and self.pool is not None:
                        await self.pool.put(conn)
                except Exception as e:
                    logger.warning(f"Failed to return connection to pool: {e}")
                    # Connection lost, decrement pool size
                    self.pool_size -= 1

    async def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        operation_name: str = "execute_query",
    ) -> list[aiosqlite.Row]:
        """Execute query with connection pool and performance monitoring."""

        async with self.get_connection(operation_name) as conn:
            conn.row_factory = aiosqlite.Row  # Enable dict-like access
            cursor = await conn.execute(query, params)
            return list(await cursor.fetchall())

    async def execute_write(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        operation_name: str = "execute_write",
    ) -> int:
        """Execute write query with connection pool and auto-commit."""

        async with self.get_connection(operation_name) as conn:
            cursor = await conn.execute(query, params)
            await conn.commit()
            return cursor.lastrowid or cursor.rowcount

    async def execute_many(
        self,
        query: str,
        params_list: list[tuple[Any, ...]],
        operation_name: str = "execute_many",
    ) -> int:
        """Execute multiple queries in a single transaction."""

        async with self.get_connection(operation_name) as conn:
            cursor = await conn.executemany(query, params_list)
            await conn.commit()
            return cursor.rowcount

    def get_performance_stats(self) -> dict[str, Any]:
        """Get current performance statistics."""

        pool_stats = {
            "pool_size": self.pool_size,
            "available_connections": self.pool.qsize() if self.pool else 0,
            "active_connections": self.connection_stats["active_connections"],
            "max_pool_size": self.max_size,
            "pool_utilization": self.connection_stats["active_connections"]
            / self.max_size
            if self.max_size > 0
            else 0,
        }

        return {
            "connection_stats": self.connection_stats.copy(),
            "pool_stats": pool_stats,
            "performance_indicators": {
                "avg_query_time_ms": round(self.connection_stats["avg_query_time"], 2),
                "slow_query_ratio": (
                    self.connection_stats["slow_queries"]
                    / self.connection_stats["total_queries"]
                    if self.connection_stats["total_queries"] > 0
                    else 0
                ),
                "pool_utilization": pool_stats["pool_utilization"],
                "error_rate": (
                    self.connection_stats["connection_errors"]
                    / self.connection_stats["total_connections"]
                    if self.connection_stats["total_connections"] > 0
                    else 0
                ),
            },
            "health_status": self._get_health_status(),
        }

    def _get_health_status(self) -> str:
        """Get overall health status based on performance metrics."""

        stats = self.connection_stats

        # Check for critical issues
        if not self.is_initialized:
            return "not_initialized"

        if self.is_shutting_down:
            return "shutting_down"

        if stats["pool_exhaustion_count"] > 0:
            return "degraded"

        if stats["avg_query_time"] > 100:  # >100ms average
            return "slow"

        if (
            stats["connection_errors"] / max(stats["total_connections"], 1)
        ) > 0.1:  # >10% error rate
            return "unstable"

        return "healthy"

    async def cleanup_connections(self) -> None:
        """Clean up stale connections and optimize pool."""

        if not self.is_initialized or self.pool is None:
            return

        async with self.pool_lock:
            current_time = time.time()
            cleanup_count = 0

            # Check for old connections (>1 hour)
            old_connections = [
                conn_id
                for conn_id, creation_time in self.connection_creation_times.items()
                if current_time - creation_time > 3600
            ]

            # Close old connections and create fresh ones
            failed_refreshes = []

            async def refresh_connection() -> str | None:
                try:
                    if self.pool is not None and not self.pool.empty():
                        old_conn = await self.pool.get()
                        await old_conn.close()

                        # Create fresh connection
                        new_conn = await self._create_optimized_connection()
                        await self.pool.put(new_conn)
                except Exception as e:
                    return str(e)
                else:
                    return None

            for _ in old_connections:
                error = await refresh_connection()
                if error:
                    failed_refreshes.append(error)
                else:
                    cleanup_count += 1

            # Log any failures after the loop
            for error in failed_refreshes:
                logger.warning(f"Failed to refresh connection during cleanup: {error}")

            if cleanup_count > 0:
                logger.info(f"Refreshed {cleanup_count} connections during cleanup")

    async def shutdown_pool(self) -> None:
        """Gracefully shutdown the connection pool."""

        if not self.is_initialized:
            return

        logger.info("Shutting down connection pool...")
        self.is_shutting_down = True

        async with self.pool_lock:
            if self.pool:
                closed_count = 0
                close_errors = []

                # Close all pooled connections
                async def close_connection() -> str | None:
                    try:
                        if self.pool is not None:
                            conn = await self.pool.get()
                            await conn.close()
                    except Exception as e:
                        return str(e)
                    else:
                        return None

                while self.pool is not None and not self.pool.empty():
                    error = await close_connection()
                    if error:
                        close_errors.append(error)
                    else:
                        closed_count += 1

                # Log any closure errors after the loop
                for error in close_errors:
                    logger.warning(f"Error closing connection during shutdown: {error}")

                self.pool = None
                self.pool_size = 0
                logger.info(f"Closed {closed_count} pooled connections")

        self.is_initialized = False
        logger.info("Connection pool shutdown complete")

    async def reset_for_testing(self) -> None:
        """
        Reset connection pool state for testing environments.

        This method ensures clean state between tests by shutting down
        the pool and resetting all state variables.
        """
        try:
            if self.is_initialized and not self.is_shutting_down:
                await self.shutdown_pool()
        except Exception as e:
            logger.debug(f"Error during test reset shutdown: {e}")

        # Reset all state variables to initial values
        self.pool = None
        self.pool_size = 0
        self.database_url = ""
        self.is_initialized = False
        self.is_shutting_down = False

        # Reset performance metrics
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "peak_connections": 0,
            "total_queries": 0,
            "avg_query_time": 0.0,
            "slow_queries": 0,
            "pool_exhaustion_count": 0,
            "connection_errors": 0,
        }
        self.connection_creation_times.clear()


# ============================================================================
# GLOBAL POOL INSTANCE
# ============================================================================


# Global connection pool manager instance
db_pool: ConnectionPoolManager = ConnectionPoolManager()


# ============================================================================
# BACKGROUND MONITORING
# ============================================================================


async def performance_monitoring_task() -> None:
    """Background task for performance monitoring and optimization."""

    logger.info("Starting performance monitoring task")

    try:
        while True:
            try:
                # Monitor pool health every 30 seconds
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                logger.info("Performance monitoring task cancelled")
                break

            try:
                if not db_pool.is_initialized:
                    continue

                stats = db_pool.get_performance_stats()
                health_status = stats["health_status"]

                # Log performance warnings
                if health_status == "degraded":
                    logger.warning(
                        "Database pool performance degraded - pool exhaustion detected"
                    )

                elif health_status == "slow":
                    avg_time = stats["performance_indicators"]["avg_query_time_ms"]
                    logger.warning(
                        f"Database queries running slowly: {avg_time:.1f}ms average"
                    )

                elif health_status == "unstable":
                    error_rate = stats["performance_indicators"]["error_rate"]
                    logger.warning(f"High connection error rate: {error_rate:.1%}")

                # Perform connection cleanup every 5 minutes
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    await db_pool.cleanup_connections()

            except Exception:
                logger.exception("Performance monitoring task failed")
                await asyncio.sleep(60)  # Longer wait on error

    except asyncio.CancelledError:
        logger.info("Performance monitoring task cancelled")
        raise  # Re-raise to properly handle cancellation
    except Exception:
        logger.exception("Performance monitoring task encountered unexpected error")


async def start_performance_monitoring() -> asyncio.Task[None]:
    """Start the performance monitoring background task."""

    return asyncio.create_task(performance_monitoring_task())


# ============================================================================
# PERFORMANCE METRICS TOOL
# ============================================================================


def get_performance_metrics_dict() -> dict[str, Any]:
    """Get comprehensive performance metrics for monitoring and alerting."""

    if not db_pool.is_initialized:
        return {
            "success": False,
            "error": "Connection pool not initialized",
            "code": "POOL_NOT_INITIALIZED",
        }

    try:
        stats = db_pool.get_performance_stats()

        # Add timestamp and additional system info
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_performance": stats,
            "system_info": {
                "pool_initialized": db_pool.is_initialized,
                "pool_shutting_down": db_pool.is_shutting_down,
                "database_url": db_pool.database_url,
                "min_pool_size": db_pool.min_size,
                "max_pool_size": db_pool.max_size,
                "connection_timeout": db_pool.connection_timeout,
            },
            "performance_targets": {
                "target_avg_query_time": 50,  # ms
                "target_pool_utilization": 0.8,  # 80%
                "target_error_rate": 0.05,  # 5%
            },
        }

    except Exception:
        logger.exception("Failed to get performance metrics")
        return create_system_error(
            "get_performance_metrics", "performance_monitoring", temporary=True
        )
