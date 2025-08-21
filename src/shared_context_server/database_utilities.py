"""
Database utilities and helper functions for Shared Context MCP Server.

This module handles:
- UTC timestamp utilities
- Validation functions (session_id, JSON)
- Health check functionality
- Data cleanup operations
- Error handling utilities

Extracted from database.py for better maintainability while preserving
all existing functionality and public interfaces.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from .database_connection import (
    DatabaseError,
    _get_sqlalchemy_manager,
    get_database_manager,
    get_db_connection,
)
from .database_operations import execute_update

logger = logging.getLogger(__name__)


def _raise_basic_query_error() -> None:
    """Raise a basic query error."""
    raise DatabaseError("Basic query failed")


# UTC timestamp utilities
def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    """Get current UTC timestamp as ISO string."""
    return utc_now().isoformat()


def parse_utc_timestamp(timestamp_input: str | datetime) -> datetime:
    """
    Parse UTC timestamp string or datetime object to datetime.

    Args:
        timestamp_input: ISO timestamp string or datetime object

    Returns:
        UTC datetime object
    """
    try:
        # Handle datetime objects (from datetime adapters)
        if isinstance(timestamp_input, datetime):
            dt = timestamp_input
            # Convert to UTC if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt

        # Handle string inputs
        timestamp_str = timestamp_input
        # Handle both with and without timezone info
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        elif "+" not in timestamp_str and "T" in timestamp_str:
            # Add UTC timezone if missing
            timestamp_str += "+00:00"

        dt = datetime.fromisoformat(timestamp_str)

        # Convert to UTC if not already
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

    except ValueError as e:
        raise ValueError(
            f"Invalid timestamp format: {timestamp_input}, error: {e}"
        ) from e
    else:
        return dt


# Validation utilities
def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.

    Args:
        session_id: Session ID to validate

    Returns:
        True if valid format
    """
    import re

    return bool(re.match(r"^session_[a-f0-9]{16}$", session_id))


def validate_json_string(json_str: str) -> bool:
    """
    Validate JSON string can be parsed.

    Args:
        json_str: JSON string to validate

    Returns:
        True if valid JSON
    """
    if not json_str:
        return True  # NULL/empty is valid

    try:
        json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return False
    else:
        return True


# Health check utilities
async def health_check() -> dict[str, Any]:
    """
    Perform database health check.

    Returns:
        Dict with health check results
    """
    try:
        # Check which backend we're using for proper initialization
        try:
            from .config import get_database_config

            db_config = get_database_config()
            use_sqlalchemy = db_config.use_sqlalchemy
        except Exception:
            use_sqlalchemy = os.getenv("USE_SQLALCHEMY", "false").lower() == "true"

        # Initialize the appropriate database backend
        if use_sqlalchemy:
            sqlalchemy_manager = _get_sqlalchemy_manager()
            if not sqlalchemy_manager.is_initialized:
                await sqlalchemy_manager.initialize()
        else:
            db_manager = get_database_manager()
            if not db_manager.is_initialized:
                await db_manager.initialize()

        # Test basic connectivity
        async with get_db_connection() as conn:
            cursor = await conn.execute("SELECT 1")
            result = await cursor.fetchone()

            # Handle different result formats (dict vs tuple)
            if result is None:
                _raise_basic_query_error()

            # Type narrowing: result is not None at this point
            assert result is not None

            # Extract value from result (handle different database row formats)
            try:
                value = None
                # Handle Row objects with both tuple and dict-like access
                if hasattr(result, "__getitem__"):
                    # Try tuple-style access first (most common)
                    with contextlib.suppress(IndexError, TypeError, KeyError):
                        value = result[0]

                if value is None:
                    # For Row objects that support dict-like access
                    try:
                        if hasattr(result, "keys") and callable(
                            getattr(result, "keys", None)
                        ):
                            # Convert to dict if possible
                            result_dict = dict(result)
                            if result_dict:
                                value = next(iter(result_dict.values()))
                    except (TypeError, ValueError, AttributeError):
                        pass

                if value is None:
                    # Last resort: try converting to list
                    try:
                        result_list = list(result)
                        if result_list:
                            value = result_list[0]
                    except (TypeError, ValueError):
                        pass

                # Check if we successfully extracted a value
                if value is None or value != 1:
                    _raise_basic_query_error()
            except (KeyError, IndexError, TypeError) as e:
                # If we can't extract a value, consider it a query failure
                logger.warning(f"Unable to extract value from result {result}: {e}")
                _raise_basic_query_error()

        # Get statistics from the actual backend being used
        if use_sqlalchemy:
            sqlalchemy_manager = _get_sqlalchemy_manager()
            return {
                "status": "healthy",
                "database_initialized": sqlalchemy_manager.is_initialized,
                "database_exists": True,  # If we got here, it exists
                "database_size_mb": 0,  # SQLAlchemy doesn't easily provide this
                "connection_count": 0,  # SQLAlchemy manages this internally
                "timestamp": utc_timestamp(),
            }
        db_manager = get_database_manager()
        stats = db_manager.get_stats()
        return {
            "status": "healthy",
            "database_initialized": stats[
                "is_initialized"
            ],  # Correct key for aiosqlite
            "database_exists": stats["database_exists"],
            "database_size_mb": stats["database_size_mb"],
            "connection_count": stats["connection_count"],
            "timestamp": utc_timestamp(),
        }

    except Exception as e:
        logger.exception("Database health check failed")
        return {"status": "unhealthy", "error": str(e), "timestamp": utc_timestamp()}


async def cleanup_expired_data() -> dict[str, int]:
    """
    Clean up expired data from database.

    Returns:
        Dict with cleanup statistics
    """
    stats = {"expired_memory": 0, "old_audit_logs": 0}

    try:
        # Clean expired agent memory
        expired_memory = await execute_update(
            """
            DELETE FROM agent_memory
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """,
            (utc_now().timestamp(),),
        )

        stats["expired_memory"] = expired_memory

        # Clean old audit logs (configurable retention period)
        try:
            from .config import get_database_config

            audit_retention_days = get_database_config().audit_log_retention_days
        except Exception:
            audit_retention_days = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "30"))

        cutoff_date = utc_now().timestamp() - (audit_retention_days * 24 * 3600)
        old_audit_logs = await execute_update(
            """
            DELETE FROM audit_log
            WHERE timestamp < ?
        """,
            (datetime.fromtimestamp(cutoff_date, timezone.utc).isoformat(),),
        )

        stats["old_audit_logs"] = old_audit_logs

        logger.info(f"Database cleanup completed: {stats}")

    except Exception:
        logger.exception("Database cleanup failed")

    return stats
