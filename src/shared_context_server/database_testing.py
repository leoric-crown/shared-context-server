"""
Simplified database testing infrastructure for shared context server.

This module provides a clean, simple database testing approach that eliminates
complexity around CI environment detection, WAL mode handling, and backend switching.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# Simplified PRAGMA settings for testing (no WAL mode complications)
_TEST_SQLITE_PRAGMAS = [
    "PRAGMA foreign_keys = ON;",  # Enable foreign key constraints
    "PRAGMA synchronous = NORMAL;",  # Balance performance and safety
    "PRAGMA cache_size = -2000;",  # 2MB cache (smaller for testing)
    "PRAGMA temp_store = MEMORY;",  # Use memory for temporary tables
]


class TestDatabaseManager:
    """
    Simplified database manager for testing that eliminates CI conditionals.

    Uses a shared temporary file to ensure schema persistence across connections.
    Memory databases create new instances for each connection, so we use temp files
    that get automatically cleaned up.
    """

    def __init__(self, database_url: str = "sqlite:///:memory:"):
        """
        Initialize test database manager.

        Args:
            database_url: Database URL (defaults to memory database)
        """
        import tempfile

        # Create a temporary file that will be automatically cleaned up
        # This ensures schema persistence across connections
        self._temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=True)  # noqa: SIM115
        self.database_path = self._temp_file.name

        self.is_initialized = False

    async def initialize(self) -> None:
        """Initialize database with schema."""
        if self.is_initialized:
            return

        # Apply schema to the memory database
        async with self.get_connection() as conn:
            await self._ensure_schema_applied(conn)

        self.is_initialized = True
        logger.info("Test database initialized successfully (memory)")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Get database connection with optimized settings applied.

        Yields:
            aiosqlite.Connection: Database connection with simplified settings
        """
        conn = None
        try:
            # Connect to in-memory database
            conn = await aiosqlite.connect(
                self.database_path,
                isolation_level=None,
                timeout=30.0,
                check_same_thread=False,
            )

            # Apply simplified PRAGMA settings (no WAL mode)
            for pragma in _TEST_SQLITE_PRAGMAS:
                await conn.execute(pragma)

            yield conn

        except Exception as e:
            logger.exception("Test database connection failed")
            raise RuntimeError(f"Test connection failed: {e}") from e

        finally:
            if conn:
                await conn.close()

    async def _ensure_schema_applied(self, conn: aiosqlite.Connection) -> None:
        """Ensure database schema is applied."""
        try:
            # Load and apply schema
            schema_content = self._load_schema_file()
            await conn.executescript(schema_content)
            logger.info("Test database schema applied successfully")

        except Exception as e:
            logger.exception("Test schema application failed")
            raise RuntimeError(f"Failed to apply test schema: {e}") from e

    def _load_schema_file(self) -> str:
        """Load database schema file."""
        from pathlib import Path

        # Find schema file (same logic as production but simplified)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        schema_path = project_root / "database_sqlite.sql"

        if schema_path.exists():
            with open(schema_path) as f:
                return f.read()

        # Fallback to package directory
        schema_path = current_file.parent / "database_sqlite.sql"
        if schema_path.exists():
            with open(schema_path) as f:
                return f.read()

        raise RuntimeError(f"Schema file not found: {schema_path}")


class UnifiedTestDatabase:
    """
    Unified database interface that works with both aiosqlite and SQLAlchemy backends.

    This provides a single interface for testing that eliminates backend switching complexity.
    """

    def __init__(self, backend: str = "aiosqlite"):
        """
        Initialize unified test database.

        Args:
            backend: Database backend to use ("aiosqlite" or "sqlalchemy")
        """
        self.backend = backend
        self._aiosqlite_manager: TestDatabaseManager | None = None
        self._sqlalchemy_manager: Any = None

    async def initialize(self) -> None:
        """Initialize the appropriate backend."""
        if self.backend == "aiosqlite":
            self._aiosqlite_manager = TestDatabaseManager()
            await self._aiosqlite_manager.initialize()
        elif self.backend == "sqlalchemy":
            # Import here to avoid circular dependencies
            from .database_sqlalchemy import SimpleSQLAlchemyManager

            self._sqlalchemy_manager = SimpleSQLAlchemyManager(
                "sqlite+aiosqlite:///:memory:"
            )
            await self._sqlalchemy_manager.initialize()
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get database connection from the appropriate backend."""
        if self.backend == "aiosqlite":
            if not self._aiosqlite_manager:
                raise RuntimeError("aiosqlite manager not initialized")
            async with self._aiosqlite_manager.get_connection() as conn:
                yield conn
        elif self.backend == "sqlalchemy":
            if not self._sqlalchemy_manager:
                raise RuntimeError("SQLAlchemy manager not initialized")
            async with self._sqlalchemy_manager.get_connection() as conn:
                yield conn
        else:
            raise RuntimeError(f"Backend not initialized: {self.backend}")


# LEGACY: Global test database singleton anti-pattern (DEPRECATED)
# Maintained for backward compatibility only
_test_db_instance: UnifiedTestDatabase | None = None


def get_test_database(backend: str = "aiosqlite") -> UnifiedTestDatabase:
    """
    DEPRECATED: Get test database (redirects to ContextVar implementation).

    This function is maintained for backward compatibility.
    New code should use get_context_test_database() from test_database_context.py
    which provides proper thread-safe ContextVar-based management.

    Args:
        backend: Database backend to use

    Returns:
        UnifiedTestDatabase: Thread-local test database instance
    """
    from .test_database_context import get_context_test_database

    return get_context_test_database(backend)


def reset_test_database() -> None:
    """
    DEPRECATED: No-op for backward compatibility.

    ContextVar provides automatic isolation, making manual resets unnecessary.
    This function is retained for backward compatibility but does nothing.
    """
    pass  # No-op - ContextVar provides automatic isolation


@asynccontextmanager
async def get_test_db_connection(
    backend: str = "aiosqlite",
) -> AsyncGenerator[Any, None]:
    """
    DEPRECATED: Get test database connection (redirects to ContextVar implementation).

    This function is maintained for backward compatibility.
    New code should use get_context_test_db_connection() from test_database_context.py
    which provides proper thread-safe ContextVar-based management.

    Args:
        backend: Database backend to use ("aiosqlite" or "sqlalchemy")

    Yields:
        Database connection (aiosqlite.Connection or SQLAlchemy wrapper)
    """
    from .test_database_context import get_context_test_db_connection

    async with get_context_test_db_connection(backend) as conn:
        yield conn
