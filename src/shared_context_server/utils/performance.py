"""
Performance optimization system with SQLAlchemy-based monitoring.

DEPRECATED: Aiosqlite connection pooling has been removed as part of PRP-024.
This module now provides performance monitoring only, using SQLAlchemy backend.

For database connections, use:
- database_manager.get_db_connection() for production
- database_testing.UnifiedTestDatabase for testing

Migration Note: ConnectionPoolManager class will raise RuntimeError when used.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ..utils.llm_errors import create_system_error

# Configure sqlite3 to avoid deprecated datetime adapter warnings in Python 3.12+
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_converter("TIMESTAMP", lambda b: datetime.fromisoformat(b.decode()))

logger = logging.getLogger(__name__)


# ============================================================================
# DEPRECATED CONNECTION POOL MANAGER
# ============================================================================


class ConnectionPoolManager:
    """DEPRECATED: Aiosqlite connection pool removed as part of PRP-024 flaky test stabilization.

    This class now raises RuntimeError when used to prevent dual-backend resource conflicts.

    Migration:
    - Use database_manager.get_db_connection() for production database access
    - Use database_testing.UnifiedTestDatabase for testing scenarios
    """

    def __init__(self) -> None:
        # Keep basic attributes for compatibility but don't initialize actual pools
        self.pool = None  # Compatibility attribute
        self.pool_size = 0
        self.min_size = 5
        self.max_size = 50
        self.database_url = ""
        self.connection_timeout = 30.0

        # Performance metrics (deprecated but kept for API compatibility)
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

        # Status tracking
        self.is_initialized = False
        self.is_shutting_down = False

    async def initialize_pool(
        self,
        database_url: str,
        min_size: int = 5,
        max_size: int = 50,
        connection_timeout: float = 30.0,
    ) -> None:
        """DEPRECATED: Aiosqlite connection pool removed.

        Raises:
            RuntimeError: Always raised to prevent dual-backend conflicts.
        """
        raise RuntimeError(
            "ConnectionPoolManager deprecated as part of PRP-024. "
            "Use database_manager.get_db_connection() for database access."
        )

    async def _try_create_pool_connection(self) -> bool:
        """DEPRECATED: Returns False to indicate deprecated status."""
        return False

    async def _create_optimized_connection(self) -> None:
        """DEPRECATED: Raises RuntimeError."""
        raise RuntimeError("Aiosqlite connection creation deprecated.")

    async def _optimize_connection(self, conn: Any) -> None:
        """DEPRECATED: No longer used."""
        pass

    async def get_connection(self, operation_name: str = "unknown") -> None:
        """DEPRECATED: Raises RuntimeError.

        Use database_manager.get_db_connection() instead.
        """
        raise RuntimeError(
            "ConnectionPoolManager.get_connection() deprecated. "
            "Use database_manager.get_db_connection() for database access."
        )

    async def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        operation_name: str = "execute_query",
    ) -> list[Any]:
        """DEPRECATED: Raises RuntimeError."""
        raise RuntimeError(
            "ConnectionPoolManager.execute_query() deprecated. "
            "Use database_manager.get_db_connection() for database access."
        )

    async def execute_write(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        operation_name: str = "execute_write",
    ) -> int:
        """DEPRECATED: Raises RuntimeError."""
        raise RuntimeError(
            "ConnectionPoolManager.execute_write() deprecated. "
            "Use database_manager.get_db_connection() for database access."
        )

    async def execute_many(
        self,
        query: str,
        params_list: list[tuple[Any, ...]],
        operation_name: str = "execute_many",
    ) -> int:
        """DEPRECATED: Raises RuntimeError."""
        raise RuntimeError(
            "ConnectionPoolManager.execute_many() deprecated. "
            "Use database_manager.get_db_connection() for database access."
        )

    def get_performance_stats(self) -> dict[str, Any]:
        """Get current performance statistics (DEPRECATED - returns empty stats)."""

        pool_stats = {
            "pool_size": self.pool_size,
            "available_connections": 0,  # No pool exists
            "active_connections": self.connection_stats["active_connections"],
            "max_pool_size": self.max_size,
            "pool_utilization": 0.0,  # No pool exists
        }

        return {
            "connection_stats": self.connection_stats.copy(),
            "pool_stats": pool_stats,
            "performance_indicators": {
                "avg_query_time_ms": 0.0,
                "slow_query_ratio": 0.0,
                "pool_utilization": 0.0,
                "error_rate": 0.0,
            },
            "health_status": "deprecated",
        }

    def _get_health_status(self) -> str:
        """DEPRECATED: Always returns 'deprecated' status."""
        return "deprecated"

    async def cleanup_connections(self) -> None:
        """DEPRECATED: No-op method."""
        pass

    async def shutdown_pool(self) -> None:
        """DEPRECATED: No-op method."""
        self.is_shutting_down = True

    async def reset_for_testing(self) -> None:
        """DEPRECATED: Reset stats only (no actual connections to close)."""
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


# ============================================================================
# DEPRECATED GLOBAL POOL INSTANCE
# ============================================================================


# Global connection pool manager instance (DEPRECATED - for API compatibility only)
db_pool: ConnectionPoolManager = ConnectionPoolManager()


# ============================================================================
# DEPRECATED BACKGROUND MONITORING
# ============================================================================


async def performance_monitoring_task() -> None:
    """DEPRECATED: Background task disabled as part of aiosqlite removal."""
    logger.info("Performance monitoring task disabled - using SQLAlchemy backend only")

    # Minimal monitoring loop to prevent breaking existing code
    try:
        while True:
            await asyncio.sleep(300)  # Sleep 5 minutes
            # No actual monitoring - just prevent task failure
    except asyncio.CancelledError:
        logger.info("Performance monitoring task cancelled")
        raise


async def start_performance_monitoring() -> asyncio.Task[None]:
    """Start the deprecated performance monitoring task."""
    return asyncio.create_task(performance_monitoring_task())


# ============================================================================
# SIMPLIFIED PERFORMANCE METRICS TOOL
# ============================================================================


def get_performance_metrics_dict() -> dict[str, Any]:
    """Get performance metrics (DEPRECATED - returns minimal SQLAlchemy-only stats)."""

    try:
        # Return simplified metrics indicating migration to SQLAlchemy
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_backend": "sqlalchemy",
            "migration_status": "aiosqlite_removed",
            "database_performance": {
                "connection_stats": db_pool.connection_stats.copy(),
                "pool_stats": {
                    "pool_size": 0,
                    "available_connections": 0,
                    "active_connections": 0,
                    "max_pool_size": 0,
                    "pool_utilization": 0.0,
                },
                "performance_indicators": {
                    "avg_query_time_ms": 0.0,
                    "slow_query_ratio": 0.0,
                    "pool_utilization": 0.0,
                    "error_rate": 0.0,
                },
                "health_status": "deprecated",
            },
            "system_info": {
                "pool_initialized": False,
                "pool_shutting_down": True,
                "database_backend": "sqlalchemy",
                "migration_complete": True,
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
