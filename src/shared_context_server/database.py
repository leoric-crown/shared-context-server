"""
Unified database operations for Shared Context MCP Server.

This module provides a consolidated interface for all database operations,
schema management, and utilities. It uses SQLAlchemy as the single database
backend, eliminating dual-backend complexity while maintaining 100% backward
compatibility with all existing APIs.

Core functionality:
- Database connection management via SQLAlchemy
- Schema initialization and validation
- Query execution utilities (SELECT, INSERT, UPDATE, DELETE)
- UTC timestamp handling and validation
- Health checks and maintenance operations
- Agent memory and session management
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .database_manager import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseSchemaError,
    SQLAlchemyConnectionWrapper,
    adapt_datetime_iso,
    convert_datetime,
    get_sqlalchemy_manager,
)
from .database_manager import (
    get_db_connection as get_manager_connection,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


# Exception classes (backward compatibility)
__all__ = [
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseSchemaError",
    "adapt_datetime_iso",
    "convert_datetime",
    "get_db_connection",
    "initialize_database",
    "execute_query",
    "execute_update",
    "execute_insert",
    "get_schema_version",
    "validate_session_id",
    "validate_json_string",
    "health_check",
    "cleanup_expired_data",
    "utc_now",
    "utc_timestamp",
    "parse_utc_timestamp",
    # Private functions for backward compatibility
    "_raise_basic_query_error",
    "_raise_wal_mode_error",
    "_raise_journal_mode_check_error",
    "_raise_table_not_found_error",
    "_raise_no_schema_version_error",
    "_get_sqlalchemy_manager",
    "_is_testing_environment",
]


# Private error functions (preserved for backward compatibility)
def _raise_basic_query_error() -> None:
    """Raise a basic query error."""
    raise DatabaseError("Basic query failed")


def _raise_wal_mode_error(mode: str) -> None:
    """Raise WAL mode configuration error."""
    raise DatabaseSchemaError(f"Expected WAL mode, got {mode}")


def _raise_journal_mode_check_error(mode: str) -> None:
    """Raise journal mode check error."""
    raise DatabaseSchemaError(f"Journal mode check failed: {mode}")


def _raise_table_not_found_error(table: str) -> None:
    """Raise table not found error."""
    raise DatabaseSchemaError(f"Required table '{table}' not found")


def _raise_no_schema_version_error() -> None:
    """Raise no schema version error."""
    raise DatabaseSchemaError("No schema version found")


def _get_sqlalchemy_manager() -> Any:
    """Get SQLAlchemy manager (backward compatibility)."""
    return get_sqlalchemy_manager()


def _is_testing_environment() -> bool:
    """Check if running in testing environment."""
    import sys

    return bool(
        "pytest" in sys.modules
        or os.getenv("CI")
        or os.getenv("GITHUB_ACTIONS")
        or os.getenv("PYTEST_CURRENT_TEST")
    )


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
        # Handle datetime objects
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
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        elif "+" not in timestamp_str and "T" in timestamp_str:
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


# Database connection and initialization
@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[SQLAlchemyConnectionWrapper, None]:
    """
    Get database connection using SQLAlchemy backend.

    Provides a unified database connection interface that works identically
    to the previous dual-backend system but only uses SQLAlchemy.

    Yields:
        SQLAlchemyConnectionWrapper: Database connection with aiosqlite-compatible interface
    """
    async with get_manager_connection() as conn:
        yield conn


async def initialize_database() -> None:
    """
    Initialize database manager and schema.

    This function initializes the SQLAlchemy-based database backend,
    creates necessary tables, and validates the schema.
    """
    sqlalchemy_manager = get_sqlalchemy_manager()
    await sqlalchemy_manager.initialize()
    logger.info("Database initialization completed")


# Query execution utilities
async def execute_query(
    query: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    """
    Execute SELECT query and return results.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        List of result rows as dictionaries
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def execute_update(query: str, params: tuple[Any, ...] = ()) -> int:
    """
    Execute UPDATE/DELETE query.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Number of affected rows
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(query, params)
        await conn.commit()
        return int(cursor.rowcount)


async def execute_insert(query: str, params: tuple[Any, ...] = ()) -> int:
    """
    Execute INSERT query and return last row ID.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Last inserted row ID
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(query, params)
        await conn.commit()
        return cursor.lastrowid or 0


# Schema management
async def get_schema_version() -> int:
    """
    Get current database schema version.

    Returns:
        Current schema version number
    """
    try:
        async with get_db_connection() as conn:
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            result = await cursor.fetchone()

            if result is None:
                return 0

            # Handle different result formats
            try:
                version = None
                if hasattr(result, "values") and callable(result.values):
                    version = list(result.values())[0]
                elif hasattr(result, "keys") and callable(
                    getattr(result, "keys", None)
                ):
                    try:
                        version = list(dict(result).values())[0]
                    except (TypeError, ValueError):
                        version = result[0]
                else:
                    version = result[0]

                return version if version is not None else 0
            except (KeyError, IndexError, TypeError):
                return 0

    except Exception:
        return 0


# Health checks and maintenance
async def health_check() -> dict[str, Any]:
    """
    Perform database health check.

    Returns:
        Dict with health check results
    """
    try:
        # Test basic connectivity
        async with get_db_connection() as conn:
            cursor = await conn.execute("SELECT 1")
            result = await cursor.fetchone()

            if result is None:
                _raise_basic_query_error()

            # Extract value from result
            assert result is not None  # for mypy
            try:
                value = None
                if hasattr(result, "__getitem__"):
                    with contextlib.suppress(IndexError, TypeError, KeyError):
                        value = result[0]

                if value is None and hasattr(result, "keys"):
                    try:
                        result_dict = dict(result)
                        if result_dict:
                            value = next(iter(result_dict.values()))
                    except (TypeError, ValueError, AttributeError):
                        pass

                if value is None:
                    try:
                        result_list = list(result)
                        if result_list:
                            value = result_list[0]
                    except (TypeError, ValueError):
                        pass

                if value is None or value != 1:
                    _raise_basic_query_error()
            except (KeyError, IndexError, TypeError) as e:
                logger.warning(f"Unable to extract value from result {result}: {e}")
                _raise_basic_query_error()

        return {
            "status": "healthy",
            "database_initialized": True,
            "database_exists": True,
            "database_size_mb": 0,  # SQLAlchemy doesn't easily provide this
            "connection_count": 0,  # Managed internally
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

        # Clean old audit logs
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


# Legacy classes and functions for backward compatibility
class DatabaseManager:
    """Legacy DatabaseManager class for backward compatibility."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self.is_initialized = False
        self._connection_count = 0

    async def initialize(self) -> None:
        """Initialize database."""
        await initialize_database()
        self.is_initialized = True

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[SQLAlchemyConnectionWrapper, None]:
        """Get database connection."""
        async with get_db_connection() as conn:
            self._connection_count += 1
            try:
                yield conn
            finally:
                self._connection_count -= 1

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        from pathlib import Path

        db_path = Path(self.database_path)
        return {
            "database_path": str(self.database_path),
            "is_initialized": self.is_initialized,
            "connection_count": self._connection_count,
            "database_exists": db_path.exists(),
            "database_size_mb": (
                db_path.stat().st_size / 1024 / 1024 if db_path.exists() else 0
            ),
        }


def get_database_manager() -> DatabaseManager:
    """Get database manager (backward compatibility)."""
    # Import here to avoid circular dependency
    try:
        from .config import get_database_config

        db_config = get_database_config()
        return DatabaseManager(db_config.database_path)
    except Exception:
        database_path = os.getenv("DATABASE_PATH", "./chat_history.db")
        return DatabaseManager(database_path)
