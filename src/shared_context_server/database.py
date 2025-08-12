"""
Unified database connection management for Shared Context MCP Server.

This module addresses critical issues identified in consultant review:
- Enables foreign keys on every connection
- Applies optimized PRAGMA settings consistently
- Provides unified connection factory with proper lifecycle
- Handles UTC timestamp operations correctly
- Includes connection pooling support for concurrent agents
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# Optimized PRAGMA settings based on consultant recommendations
# Reduced mmap_size from 30GB to 256MB for production safety
_SQLITE_PRAGMAS = [
    "PRAGMA foreign_keys = ON;",  # Critical: Enable foreign key constraints
    "PRAGMA journal_mode = WAL;",  # Write-Ahead Logging for concurrency
    "PRAGMA synchronous = NORMAL;",  # Balance performance and safety
    "PRAGMA cache_size = -8000;",  # 8MB cache per connection
    "PRAGMA temp_store = MEMORY;",  # Use memory for temporary tables
    "PRAGMA mmap_size = 268435456;",  # 256MB memory mapping (was 30GB)
    "PRAGMA busy_timeout = 5000;",  # 5 second timeout for busy database
    "PRAGMA optimize;",  # Enable query optimizer
]


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""

    pass


class DatabaseSchemaError(DatabaseError):
    """Exception raised when database schema is invalid."""

    pass


def _raise_wal_mode_error(journal_mode: str) -> None:
    """Raise a WAL mode configuration error."""
    raise DatabaseConnectionError(f"Failed to enable WAL mode, got: {journal_mode}")


def _raise_journal_mode_check_error() -> None:
    """Raise a journal mode check error."""
    raise DatabaseConnectionError("Failed to check journal mode")


def _raise_table_not_found_error(table: str) -> None:
    """Raise a table not found error."""
    raise DatabaseSchemaError(f"Required table '{table}' not found")


def _raise_no_schema_version_error() -> None:
    """Raise a no schema version error."""
    raise DatabaseSchemaError("No schema version found")


def _raise_basic_query_error() -> None:
    """Raise a basic query error."""
    raise DatabaseError("Basic query failed")


class DatabaseManager:
    """
    Unified database connection manager with optimized settings.

    Provides consistent PRAGMA application, connection pooling support,
    and proper UTC timestamp handling for multi-agent operations.
    """

    def __init__(self, database_path: str):
        """
        Initialize database manager.

        Args:
            database_path: Path to SQLite database file or sqlite:/// URL
        """
        # Handle sqlite:/// URLs by extracting the file path
        if database_path.startswith("sqlite:///"):
            actual_path = database_path[10:]  # Remove "sqlite:///" prefix
        else:
            actual_path = database_path

        self.database_path = Path(actual_path).resolve()
        self.is_initialized = False
        self._connection_count = 0

    async def initialize(self) -> None:
        """
        Initialize database with schema and validation.

        Raises:
            DatabaseConnectionError: If connection fails
            DatabaseSchemaError: If schema is invalid
        """
        if self.is_initialized:
            return

        # Ensure database directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Test connection and apply schema if needed
        try:
            async with self.get_connection() as conn:
                await self._ensure_schema_applied(conn)
                await self._validate_schema(conn)

            self.is_initialized = True
            logger.info(f"Database initialized successfully: {self.database_path}")

        except Exception as e:
            raise DatabaseConnectionError(f"Failed to initialize database: {e}") from e

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Get database connection with optimized settings applied.

        Yields:
            aiosqlite.Connection: Database connection with PRAGMAs applied

        Raises:
            DatabaseConnectionError: If connection fails
        """
        conn = None
        try:
            # Connect to database
            conn = await aiosqlite.connect(
                str(self.database_path),
                isolation_level=None,  # Autocommit mode for WAL
                timeout=30.0,  # 30 second connection timeout
                check_same_thread=False,
            )

            # Configure datetime adapters for Python 3.12+ compatibility
            import datetime as dt
            import sqlite3

            def adapt_datetime_iso(val: dt.datetime) -> str:
                """Adapt datetime to ISO format string."""
                return val.isoformat()

            def convert_datetime(val: bytes) -> dt.datetime:
                """Convert ISO format string to datetime."""
                return dt.datetime.fromisoformat(val.decode())

            sqlite3.register_adapter(dt.datetime, adapt_datetime_iso)
            sqlite3.register_converter("datetime", convert_datetime)
            sqlite3.register_converter("DATETIME", convert_datetime)
            sqlite3.register_converter("timestamp", convert_datetime)
            sqlite3.register_converter("TIMESTAMP", convert_datetime)

            # Apply optimized PRAGMA settings
            await self._apply_pragmas(conn)

            # Explicit WAL mode assertion to fail fast
            cursor = await conn.execute("PRAGMA journal_mode;")
            row = await cursor.fetchone()
            if row is None:
                _raise_journal_mode_check_error()
            assert row is not None
            journal_mode = row[0].lower()
            if journal_mode != "wal":
                _raise_wal_mode_error(journal_mode)

            # Track connection count for monitoring
            self._connection_count += 1

            yield conn

        except Exception as e:
            logger.exception("Database connection failed")
            raise DatabaseConnectionError(f"Connection failed: {e}") from e

        finally:
            if conn:
                await conn.close()
                self._connection_count = max(0, self._connection_count - 1)

    async def _apply_pragmas(self, conn: aiosqlite.Connection) -> None:
        """
        Apply optimized PRAGMA settings to connection.

        Args:
            conn: Database connection
        """
        try:
            for pragma in _SQLITE_PRAGMAS:
                await conn.execute(pragma)

            # Explicit WAL mode assertion to fail fast
            cursor = await conn.execute("PRAGMA journal_mode;")
            row = await cursor.fetchone()
            if row is None:
                _raise_journal_mode_check_error()
            assert row is not None
            journal_mode = row[0].lower()
            if journal_mode != "wal":
                _raise_wal_mode_error(journal_mode)

        except Exception as e:
            logger.exception("Failed to apply PRAGMA settings")
            raise DatabaseConnectionError(f"PRAGMA application failed: {e}") from e

    def _load_schema_file(self) -> str:
        """
        Load database schema file from multiple possible locations.

        Tries to find database.sql in:
        1. Project root (development environment)
        2. Package installation directory (pip installed)
        3. Site-packages root (wheel installation)

        Returns:
            Schema file contents as string

        Raises:
            DatabaseSchemaError: If schema file not found in any location
        """
        current_file = Path(__file__).resolve()

        # Location 1: Project root (development)
        project_root = current_file.parent.parent.parent
        schema_paths = [
            project_root / "database.sql",
            # Location 2: Package directory (installed package)
            current_file.parent / "database.sql",
            # Location 3: Site-packages root (wheel installation)
            Path(current_file.parts[0]).joinpath(*current_file.parts[1:-3])
            / "database.sql",
        ]

        # Additional location: Check based on Python path
        try:
            import sys

            schema_paths.extend(
                [
                    Path(site_pkg) / "database.sql"
                    for site_pkg in sys.path
                    if "site-packages" in site_pkg
                ]
            )
        except Exception:
            pass  # Ignore if we can't detect site-packages

        for schema_path in schema_paths:
            if schema_path.exists():
                logger.info(f"Loading schema from: {schema_path}")
                with open(schema_path) as f:
                    return f.read()

        # If we get here, schema file not found anywhere
        tried_paths = "\n".join(str(p) for p in schema_paths)
        raise DatabaseSchemaError(
            f"Schema file not found in any of the following locations:\n{tried_paths}"
        )

    def _raise_schema_not_found_error(self, schema_path: Path) -> None:
        """Raise a schema not found error."""
        raise DatabaseSchemaError(f"Schema file not found: {schema_path}")

    async def _ensure_schema_applied(self, conn: aiosqlite.Connection) -> None:
        """
        Ensure database schema is applied.

        Args:
            conn: Database connection
        """
        try:
            # Check if schema_version table exists
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='schema_version'
            """
            )

            if not await cursor.fetchone():
                # Schema not applied, read and execute schema file
                # Try multiple possible locations for schema file
                schema_content = self._load_schema_file()

                # Execute schema (split by semicolon for multiple statements)
                await conn.executescript(schema_content)
                logger.info("Database schema applied successfully")

        except Exception as e:
            logger.exception("Schema application failed")
            raise DatabaseSchemaError(f"Failed to apply schema: {e}") from e

    async def _validate_schema(self, conn: aiosqlite.Connection) -> None:
        """
        Validate database schema is correct.

        Args:
            conn: Database connection

        Raises:
            DatabaseSchemaError: If schema validation fails
        """
        try:
            # Check required tables exist
            required_tables = [
                "sessions",
                "messages",
                "agent_memory",
                "audit_log",
                "schema_version",
                "secure_tokens",  # PRP-006: Secure token authentication
            ]

            for table in required_tables:
                cursor = await conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=?
                """,
                    (table,),
                )

                if not await cursor.fetchone():
                    _raise_table_not_found_error(table)

            # Validate PRAGMA settings applied correctly
            await self._validate_pragmas(conn)

            # Check schema version
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            row = await cursor.fetchone()
            if row is None:
                _raise_no_schema_version_error()
            assert row is not None
            version = row[0]

            if version != 3:
                logger.warning(f"Unexpected schema version: {version}, expected: 3")

            logger.info("Database schema validation successful")

        except Exception as e:
            logger.exception("Schema validation failed")
            raise DatabaseSchemaError(f"Schema validation failed: {e}") from e

    async def _validate_pragmas(self, conn: aiosqlite.Connection) -> None:
        """
        Validate PRAGMA settings are applied correctly.

        Args:
            conn: Database connection
        """
        # Check critical PRAGMA settings
        pragma_checks = [
            ("journal_mode", "wal"),
            ("foreign_keys", "1"),
            ("synchronous", "1"),  # NORMAL = 1
        ]

        for pragma, expected in pragma_checks:
            cursor = await conn.execute(f"PRAGMA {pragma};")
            result = await cursor.fetchone()

            if result and str(result[0]).lower() != str(expected).lower():
                logger.warning(f"PRAGMA {pragma} = {result[0]}, expected {expected}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get database manager statistics.

        Returns:
            Dict with current statistics
        """
        return {
            "database_path": str(self.database_path),
            "is_initialized": self.is_initialized,
            "connection_count": self._connection_count,
            "database_exists": self.database_path.exists(),
            "database_size_mb": (
                self.database_path.stat().st_size / 1024 / 1024
                if self.database_path.exists()
                else 0
            ),
        }


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """
    Get global database manager instance.

    Returns:
        DatabaseManager: Global database manager

    Raises:
        DatabaseError: If database manager not initialized
    """
    global _db_manager

    if _db_manager is None:
        # Import here to avoid circular dependency
        from .config import get_database_config

        try:
            db_config = get_database_config()
            _db_manager = DatabaseManager(db_config.database_path)
        except Exception:
            # Fallback to environment variable for backward compatibility
            database_path = os.getenv("DATABASE_PATH", "./chat_history.db")
            _db_manager = DatabaseManager(database_path)
            logger.warning("Using fallback database path configuration")

    return _db_manager


async def initialize_database() -> None:
    """
    Initialize global database manager.

    Should be called during application startup.
    """
    db_manager = get_database_manager()
    await db_manager.initialize()


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Get database connection using global database manager.

    Yields:
        aiosqlite.Connection: Database connection with optimized settings
    """
    db_manager = get_database_manager()

    if not db_manager.is_initialized:
        await db_manager.initialize()

    async with db_manager.get_connection() as conn:
        yield conn


# Utility functions for common operations
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
        conn.row_factory = aiosqlite.Row  # Enable dict-like access
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def execute_update(query: str, params: tuple[Any, ...] = ()) -> int:
    """
    Execute UPDATE/INSERT/DELETE query.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Number of affected rows
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute(query, params)
        await conn.commit()
        return cursor.rowcount


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


# UTC timestamp utilities
def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    """Get current UTC timestamp as ISO string."""
    return utc_now().isoformat()


def parse_utc_timestamp(timestamp_str: str) -> datetime:
    """
    Parse UTC timestamp string to datetime.

    Args:
        timestamp_str: ISO timestamp string

    Returns:
        UTC datetime object
    """
    try:
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
            f"Invalid timestamp format: {timestamp_str}, error: {e}"
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
        db_manager = get_database_manager()

        if not db_manager.is_initialized:
            await db_manager.initialize()

        # Test basic connectivity
        async with get_db_connection() as conn:
            cursor = await conn.execute("SELECT 1")
            result = await cursor.fetchone()

            if result is None or result[0] != 1:
                _raise_basic_query_error()

        # Get statistics
        stats = db_manager.get_stats()

        return {
            "status": "healthy",
            "database_initialized": stats["is_initialized"],
            "database_exists": stats["database_exists"],
            "database_size_mb": stats["database_size_mb"],
            "connection_count": stats["connection_count"],
            "timestamp": utc_timestamp(),
        }

    except Exception as e:
        logger.exception("Database health check failed")
        return {"status": "unhealthy", "error": str(e), "timestamp": utc_timestamp()}


# Migration utilities (for future schema changes)
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
            return result[0] if result and result[0] is not None else 0

    except Exception:
        return 0  # Schema version table doesn't exist


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
