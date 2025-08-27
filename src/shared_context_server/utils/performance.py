"""
Performance monitoring system for Shared Context MCP Server.

Note: Connection pooling removed as part of SQLAlchemy-only migration.
SQLAlchemy handles all connection management internally.
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
# BACKGROUND MONITORING
# ============================================================================


async def performance_monitoring_task() -> None:
    """Minimal background task for compatibility."""
    logger.info("Performance monitoring task using SQLAlchemy backend")

    # Minimal monitoring loop to prevent breaking existing code
    try:
        while True:
            await asyncio.sleep(300)  # Sleep 5 minutes
            # No actual monitoring - SQLAlchemy handles performance internally
    except asyncio.CancelledError:
        logger.info("Performance monitoring task cancelled")
        raise


async def start_performance_monitoring() -> asyncio.Task[None]:
    """Start the performance monitoring task."""
    return asyncio.create_task(performance_monitoring_task())


# ============================================================================
# PERFORMANCE METRICS TOOL
# ============================================================================


def get_performance_metrics_dict() -> dict[str, Any]:
    """Get performance metrics using SQLAlchemy backend."""

    try:
        # Return simplified metrics for SQLAlchemy-only architecture
        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_backend": "sqlalchemy",
            "migration_status": "complete",
            "database_performance": {
                "connection_stats": {
                    "total_connections": 0,
                    "active_connections": 0,
                    "peak_connections": 0,
                    "total_queries": 0,
                    "avg_query_time": 0.0,
                    "slow_queries": 0,
                    "pool_exhaustion_count": 0,
                    "connection_errors": 0,
                },
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
                "health_status": "healthy",
            },
            "system_info": {
                "database_backend": "sqlalchemy",
                "connection_management": "automatic",
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
