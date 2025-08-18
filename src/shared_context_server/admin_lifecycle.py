"""
Administration Lifecycle Management for Shared Context MCP Server.

Provides server lifecycle management and performance monitoring:
- get_performance_metrics: Comprehensive performance data for admin users
- Background memory cleanup tasks
- Server lifecycle management with startup/shutdown hooks
- Database connection pool management

Built for production monitoring with admin-level security controls.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from typing import Any

from fastmcp import Context  # noqa: TC002
from pydantic import Field

from .auth import validate_agent_context_or_error
from .core_server import mcp
from .database import get_db_connection, initialize_database
from .utils.llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    create_system_error,
)

logger = logging.getLogger(__name__)


# ============================================================================
# PERFORMANCE MONITORING TOOL
# ============================================================================


@mcp.tool(exclude_args=["ctx"])
async def get_performance_metrics(
    auth_token: str | None = Field(
        default=None, description="Optional JWT token for admin access"
    ),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Get comprehensive performance metrics for monitoring.
    Requires admin permission.
    """

    try:
        # Extract and validate agent context (with token validation error handling)
        agent_context = await validate_agent_context_or_error(ctx, auth_token)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]

        # Check permission for admin access
        if "admin" not in agent_context.get("permissions", []):
            return ERROR_MESSAGE_PATTERNS["admin_required"]()  # type: ignore[no-any-return,operator]

        # Get performance metrics from the performance module
        from .utils.performance import get_performance_metrics_dict

        metrics = get_performance_metrics_dict()

        # Add requesting agent info
        if metrics.get("success"):
            metrics["requesting_agent"] = agent_id
            metrics["request_timestamp"] = datetime.now(timezone.utc).isoformat()

        return metrics

    except Exception:
        logger.exception("Failed to get performance metrics")
        return create_system_error(
            "get_performance_metrics", "performance_monitoring", temporary=True
        )


# ============================================================================
# BACKGROUND TASK MANAGEMENT
# ============================================================================


async def _perform_memory_cleanup() -> None:
    """Perform a single memory cleanup operation."""
    try:
        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            cursor = await conn.execute(
                """
                DELETE FROM agent_memory
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """,
                (current_timestamp,),
            )

            deleted_count = cursor.rowcount
            await conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired memory entries")

    except Exception:
        logger.exception("Memory cleanup failed")


async def cleanup_expired_memory_task() -> None:
    """Lightweight TTL sweeper for expired memory entries."""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        await _perform_memory_cleanup()


# ============================================================================
# SERVER LIFECYCLE MANAGEMENT
# ============================================================================


@asynccontextmanager
async def lifespan() -> Any:
    """FastMCP server lifespan management."""

    # Startup
    print("Initializing Shared Context MCP Server...")

    # Use unified connection management from Phase 0
    # Initialize database schema
    await initialize_database()

    # Phase 4: Initialize performance optimization system
    from .utils.caching import start_cache_maintenance
    from .utils.performance import db_pool, start_performance_monitoring

    try:
        # Initialize connection pool
        database_url = os.getenv("DATABASE_URL", "chat_history.db")
        await db_pool.initialize_pool(database_url, min_size=5, max_size=50)
        print("Database connection pool initialized")

    except Exception:
        logger.exception("Failed to initialize connection pool")
        print("Warning: Running without connection pooling")

    # Start background tasks
    cleanup_tasks = []
    try:
        # Phase 4: Start performance monitoring
        perf_task = await start_performance_monitoring()
        cleanup_tasks.append(perf_task)

        # Phase 4: Start cache maintenance
        cache_task = await start_cache_maintenance()
        cleanup_tasks.append(cache_task)

        # Import subscription cleanup from resources module
        from .admin_resources import cleanup_subscriptions_task

        # Start subscription cleanup task
        cleanup_task = asyncio.create_task(cleanup_subscriptions_task())
        cleanup_tasks.append(cleanup_task)

        # Start memory cleanup task
        memory_task = asyncio.create_task(cleanup_expired_memory_task())
        cleanup_tasks.append(memory_task)

        print("Background tasks started (performance, cache, cleanup)")
    except Exception as e:
        logger.warning(f"Could not start background tasks: {e}")

    print("Server ready with Phase 4 production features!")

    yield

    # Shutdown
    print("Shutting down...")

    # Phase 4: Shutdown performance system
    try:
        await db_pool.shutdown_pool()
        print("Connection pool shutdown complete")
    except Exception as e:
        logger.warning(f"Error shutting down connection pool: {e}")

    # Cancel background tasks
    for task in cleanup_tasks:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    # Connection cleanup handled by get_db_connection context manager
    print("Shutdown complete")


# ============================================================================
# SERVER MANAGEMENT FUNCTIONS
# ============================================================================


async def shutdown_server() -> None:
    """Shutdown the server gracefully."""
    logger.info("Server shutdown initiated")


# Set up server lifecycle hooks if FastMCP supports them
# Note: FastMCP lifecycle management varies by version - this may need adjustment
try:
    if hasattr(mcp, "on_startup"):
        mcp.on_startup(initialize_database)
    if hasattr(mcp, "lifespan"):
        mcp.lifespan = lifespan
except Exception as e:
    logger.warning(f"Could not set lifecycle hooks: {e}")
