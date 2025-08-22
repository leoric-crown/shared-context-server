"""
Database connection management for Shared Context MCP Server.

This module handles:
- SQLite connection setup and optimization
- PRAGMA settings application
- Connection lifecycle management
- DatabaseManager class implementation
- Global manager instances

Extracted from database.py for better maintainability while preserving
all existing functionality and public interfaces.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime as dt
from datetime import timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


def _raise_table_not_found_error(table: str) -> None:
    """Raise a table not found error."""
    raise DatabaseSchemaError(f"Required table '{table}' not found")


def _raise_no_schema_version_error() -> None:
    """Raise a no schema version error."""
    raise DatabaseSchemaError("No schema version found")


def adapt_datetime_iso(val: dt) -> str:
    """Adapt datetime to ISO format string to avoid deprecation warnings."""
    return val.isoformat()


def convert_datetime(val: bytes) -> dt:
    """Convert ISO format string or Unix timestamp to datetime."""
    decoded_val = val.decode()

    # Handle Unix timestamp format (like '1755135988.48165')
    try:
        # Try to parse as float (Unix timestamp)
        timestamp = float(decoded_val)
        return dt.fromtimestamp(timestamp, timezone.utc)
    except ValueError:
        pass

    # Handle ISO format string
    try:
        return dt.fromisoformat(decoded_val)
    except ValueError:
        # Fallback: try to parse as UTC timestamp if it ends with Z
        if decoded_val.endswith("Z"):
            return dt.fromisoformat(decoded_val[:-1] + "+00:00")
        raise


# Register our explicit adapters to replace the deprecated defaults
sqlite3.register_adapter(dt, adapt_datetime_iso)
sqlite3.register_converter("datetime", convert_datetime)
sqlite3.register_converter("DATETIME", convert_datetime)
sqlite3.register_converter("timestamp", convert_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)


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


def _is_testing_environment() -> bool:
    """
    Check if running in testing environment.

    Returns True if pytest is running or testing environment variables are present.
    """
    # Check for pytest
    if "pytest" in sys.modules:
        return True

    # Check for testing environment variables
    return bool(
        os.getenv("CI")
        or os.getenv("GITHUB_ACTIONS")
        or os.getenv("PYTEST_CURRENT_TEST")
    )


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

    def _raise_schema_not_found_error(self, schema_path: Path) -> None:
        """Raise a schema not found error."""
        raise DatabaseSchemaError(f"Schema file not found: {schema_path}")

    async def initialize(self) -> None:
        """
        Initialize database with schema and validation.

        Raises:
            DatabaseConnectionError: If connection fails
            DatabaseSchemaError: If schema is invalid
        """
        if self.is_initialized:
            return

        # Schema functions moved here to avoid circular dependency

        # Ensure database directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Test connection and apply schema if needed
        try:
            async with self.get_connection() as conn:
                await self._ensure_schema_applied(conn)
                await self._validate_schema_with_recovery(conn)

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
            # Connect to database with explicit settings to avoid Python 3.12+ deprecation warnings
            conn = await aiosqlite.connect(
                str(self.database_path),
                isolation_level=None,  # Autocommit mode for WAL
                timeout=30.0,  # 30 second connection timeout
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
                | sqlite3.PARSE_COLNAMES,  # Enable our custom adapters
            )

            # Apply optimized PRAGMA settings
            await self._apply_pragmas(conn)

            # Explicit WAL mode assertion to fail fast
            cursor = await conn.execute("PRAGMA journal_mode;")
            row = await cursor.fetchone()
            if row is None:
                _raise_journal_mode_check_error()
            assert row is not None
            journal_mode = row[0].lower()

            if _is_testing_environment():
                # In testing environments, accept any journal mode (including memory databases)
                acceptable_modes = {"wal", "memory", "delete", "truncate", "persist"}
                if journal_mode not in acceptable_modes:
                    _raise_wal_mode_error(journal_mode)
                elif journal_mode != "wal":
                    logger.debug(
                        f"Using journal_mode={journal_mode} instead of WAL "
                        f"(testing environment detected)"
                    )
            else:
                # In production, require WAL mode
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

            if _is_testing_environment():
                # In testing environments, accept any journal mode (including memory databases)
                acceptable_modes = {"wal", "memory", "delete", "truncate", "persist"}
                if journal_mode not in acceptable_modes:
                    _raise_wal_mode_error(journal_mode)
                elif journal_mode != "wal":
                    logger.debug(
                        f"Using journal_mode={journal_mode} instead of WAL "
                        f"(testing environment detected)"
                    )
            else:
                # In production, require WAL mode
                if journal_mode != "wal":
                    _raise_wal_mode_error(journal_mode)

        except Exception as e:
            logger.exception("Failed to apply PRAGMA settings")
            raise DatabaseConnectionError(f"PRAGMA application failed: {e}") from e

    def _load_schema_file(self) -> str:
        """
        Load database schema file from multiple possible locations.

        Tries to find database_sqlite.sql in:
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
            project_root / "database_sqlite.sql",
            # Location 2: Package directory (installed package)
            current_file.parent / "database_sqlite.sql",
            # Location 3: Site-packages root (wheel installation)
            Path(current_file.parts[0]).joinpath(*current_file.parts[1:-3])
            / "database_sqlite.sql",
        ]

        # Additional location: Check based on Python path
        try:
            import sys

            schema_paths.extend(
                [
                    Path(site_pkg) / "database_sqlite.sql"
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

    async def _validate_schema_with_recovery(self, conn: aiosqlite.Connection) -> None:
        """
        Validate database schema with automatic recovery for missing tables.

        This method attempts to fix schema issues by recreating missing tables,
        which can happen during parallel test execution or interrupted initialization.

        Args:
            conn: Database connection

        Raises:
            DatabaseSchemaError: If schema validation or recovery fails
        """
        try:
            # First try normal validation
            await self._validate_schema(conn)
            return
        except DatabaseSchemaError as e:
            # If validation fails, check if it's due to missing tables
            error_msg = str(e)
            if "secure_tokens" in error_msg and "not found" in error_msg:
                logger.warning("secure_tokens table missing, attempting recovery...")
                try:
                    # Recreate the secure_tokens table specifically
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS secure_tokens (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            token_id TEXT UNIQUE NOT NULL,
                            encrypted_jwt BLOB NOT NULL,
                            agent_id TEXT NOT NULL,
                            expires_at TIMESTAMP NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                            -- Ensure data consistency for concurrent access
                            CONSTRAINT secure_tokens_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),
                            CONSTRAINT secure_tokens_token_id_not_empty CHECK (length(trim(token_id)) > 0)
                        )
                    """)

                    # Create indexes
                    await conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_token_id ON secure_tokens(token_id)"
                    )
                    await conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_agent_expires ON secure_tokens(agent_id, expires_at)"
                    )
                    await conn.execute(
                        "CREATE INDEX IF NOT EXISTS idx_expires_cleanup ON secure_tokens(expires_at)"
                    )

                    # Update schema version if needed
                    await conn.execute("""
                        INSERT OR REPLACE INTO schema_version (version, description)
                        VALUES (3, 'PRP-006: Added secure_tokens table with Fernet encryption for JWT hiding (recovered)')
                    """)

                    await conn.commit()
                    logger.info("Successfully recovered secure_tokens table")

                    # Try validation again
                    await self._validate_schema(conn)
                    return
                except Exception as recovery_error:
                    logger.exception("Failed to recover secure_tokens table")
                    raise DatabaseSchemaError(
                        f"Schema recovery failed: {recovery_error}"
                    ) from recovery_error
            else:
                # Re-raise original error if it's not the secure_tokens issue
                raise

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


# ContextVar-based database managers for perfect thread isolation
# Replaces global singleton pattern with thread-local context variables
_db_manager_context: ContextVar[DatabaseManager | None] = ContextVar(
    "database_manager_context", default=None
)
_sqlalchemy_manager_context: ContextVar[Any | None] = ContextVar(
    "sqlalchemy_manager_context", default=None
)


def get_database_manager() -> DatabaseManager:
    """
    Get thread-local database manager instance with automatic isolation.

    Uses ContextVar for perfect thread safety and automatic test isolation.
    Each thread/context gets its own database manager instance.

    Returns:
        DatabaseManager: Thread-local database manager

    Raises:
        DatabaseError: If database manager cannot be initialized
    """
    manager = _db_manager_context.get()

    if manager is None:
        # Import here to avoid circular dependency
        from .config import get_database_config

        try:
            db_config = get_database_config()
            manager = DatabaseManager(db_config.database_path)
        except Exception:
            # Fallback to environment variable for backward compatibility
            database_path = os.getenv("DATABASE_PATH", "./chat_history.db")
            manager = DatabaseManager(database_path)
            logger.warning("Using fallback database path configuration")

        _db_manager_context.set(manager)

    return manager


def _get_sqlalchemy_manager() -> Any:
    """Get thread-local SQLAlchemy manager instance with automatic isolation."""
    manager = _sqlalchemy_manager_context.get()

    if manager is None:
        from .config import get_database_config
        from .database_sqlalchemy import SimpleSQLAlchemyManager

        try:
            db_config = get_database_config()

            # Determine database URL for SQLAlchemy
            if db_config.database_url:
                database_url = db_config.database_url
            else:
                # Convert database_path to SQLAlchemy URL
                database_url = f"sqlite+aiosqlite:///{db_config.database_path}"

            manager = SimpleSQLAlchemyManager(database_url)

        except Exception:
            # Fallback to environment variables
            database_url = os.getenv("DATABASE_URL") or ""
            if database_url:
                # Convert sqlite:// to sqlite+aiosqlite:// if needed
                if database_url.startswith("sqlite://"):
                    database_url = database_url.replace(
                        "sqlite://", "sqlite+aiosqlite://", 1
                    )
                manager = SimpleSQLAlchemyManager(database_url)
            else:
                # Fallback to database path
                database_path = os.getenv("DATABASE_PATH", "./chat_history.db")
                database_url = f"sqlite+aiosqlite:///{database_path}"
                manager = SimpleSQLAlchemyManager(database_url)
            logger.warning("Using fallback SQLAlchemy database configuration")

        _sqlalchemy_manager_context.set(manager)

    return manager


def reset_database_context() -> None:
    """
    Reset database context - automatic isolation for tests.

    Clears both aiosqlite and SQLAlchemy manager contexts, forcing the next call
    to get_database_manager() or _get_sqlalchemy_manager() to create fresh instances.

    This is useful for test isolation, though in most cases the automatic context
    isolation should be sufficient.
    """
    _db_manager_context.set(None)
    _sqlalchemy_manager_context.set(None)


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Get database connection using thread-local database manager.

    Automatically routes to either aiosqlite or SQLAlchemy backend based on configuration.
    Uses ContextVar for perfect thread isolation and automatic test cleanup.

    Yields:
        Connection: Database connection with optimized settings (aiosqlite.Connection or SQLAlchemyConnectionWrapper)
    """
    # Import here to avoid circular dependency
    from .config import get_database_config

    try:
        db_config = get_database_config()
        use_sqlalchemy = db_config.use_sqlalchemy
    except Exception:
        # Fallback to environment variable
        use_sqlalchemy = os.getenv("USE_SQLALCHEMY", "false").lower() == "true"

    if use_sqlalchemy:
        # Use SQLAlchemy backend
        sqlalchemy_manager = _get_sqlalchemy_manager()

        async with sqlalchemy_manager.get_connection() as conn:
            yield conn
    else:
        # Use aiosqlite backend (current default)
        db_manager = get_database_manager()

        async with db_manager.get_connection() as conn:
            yield conn
