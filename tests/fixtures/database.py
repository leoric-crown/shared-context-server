"""
Modern database testing fixtures with reduced mocking and better isolation.

This module provides improved database testing infrastructure that:
1. Uses real database connections instead of excessive mocking
2. Provides proper test isolation through clean database state
3. Supports both aiosqlite and SQLAlchemy backends seamlessly
4. Implements proper cleanup to prevent state leakage between tests
"""

import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.shared_context_server.database import DatabaseManager


class DatabaseTestManager:
    """
    Manages database testing with proper isolation and cleanup.

    This class provides a unified interface for testing both aiosqlite
    and SQLAlchemy backends with proper state management.
    """

    def __init__(self, backend: str = "auto"):
        self.backend = backend
        self.temp_db_path: str | None = None
        self.db_manager: DatabaseManager | None = None
        self._original_managers: dict[str, Any] = {}

    async def setup(self) -> None:
        """Initialize test database with proper backend detection."""
        # Create temporary database in system tmp directory

        # Create temp file and get just the filename
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_full_path = f.name

        # Use full temp path for both backends
        self.temp_db_path = temp_full_path
        self._full_temp_path = temp_full_path

        # Determine backend
        if self.backend == "auto":
            use_sqlalchemy = os.getenv("USE_SQLALCHEMY", "false").lower() == "true"
            self.backend = "sqlalchemy" if use_sqlalchemy else "aiosqlite"

        # Create appropriate database manager
        if self.backend == "sqlalchemy":
            # Import SQLAlchemy manager for SQLAlchemy mode
            from src.shared_context_server.database_sqlalchemy import (
                SimpleSQLAlchemyManager,
            )

            database_url = f"sqlite+aiosqlite:///{self.temp_db_path}"
            self.db_manager = SimpleSQLAlchemyManager(database_url)
        else:
            # Use regular DatabaseManager for aiosqlite mode
            database_url = f"sqlite:///{self.temp_db_path}"
            self.db_manager = DatabaseManager(database_url)

        await self.db_manager.initialize()

        # Store original global managers for restoration
        self._store_original_managers()

        # Set global managers to use test database
        self._patch_global_managers()

    def _store_original_managers(self) -> None:
        """Store original global database managers."""
        try:
            import src.shared_context_server.database as db_module

            self._original_managers = {
                "db_manager": getattr(db_module, "_db_manager", None),
                "sqlalchemy_manager": getattr(db_module, "_sqlalchemy_manager", None),
            }
        except ImportError:
            pass

    def _patch_global_managers(self) -> None:
        """Patch global managers to use test database."""
        try:
            import src.shared_context_server.database as db_module

            if self.backend == "sqlalchemy":
                # For SQLAlchemy mode
                db_module._sqlalchemy_manager = self.db_manager
                db_module._db_manager = None
            else:
                # For aiosqlite mode
                db_module._db_manager = self.db_manager
                db_module._sqlalchemy_manager = None

        except ImportError:
            pass

    def _restore_global_managers(self) -> None:
        """Restore original global managers."""
        try:
            import src.shared_context_server.database as db_module

            db_module._db_manager = self._original_managers.get("db_manager")
            db_module._sqlalchemy_manager = self._original_managers.get(
                "sqlalchemy_manager"
            )

        except ImportError:
            pass

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics for testing compatibility."""
        if not self.db_manager:
            return {"connection_count": 0, "is_initialized": False}

        # Provide basic stats for compatibility with tests
        return {
            "connection_count": 0,  # Test connections are contextual, not pooled
            "is_initialized": True,
            "backend": self.backend,
        }

    async def cleanup(self) -> None:
        """Clean up test database and restore state."""
        # Restore global managers first
        self._restore_global_managers()

        # Close database manager
        if self.db_manager:
            # Proper cleanup for different backends
            if hasattr(self.db_manager, "close"):
                await self.db_manager.close()
            self.db_manager = None

        # Remove temporary database file using full path
        if (
            hasattr(self, "_full_temp_path")
            and self._full_temp_path
            and Path(self._full_temp_path).exists()
        ):
            import contextlib

            with contextlib.suppress(OSError):
                Path(self._full_temp_path).unlink()
        self.temp_db_path = None
        self._full_temp_path = None

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection for testing."""
        if not self.db_manager:
            raise RuntimeError("Database manager not initialized")
        async with self.db_manager.get_connection() as conn:
            yield conn


@pytest.fixture(scope="function")
async def isolated_db() -> AsyncGenerator[DatabaseTestManager, None]:
    """
    Provide an isolated database for each test function.

    This fixture:
    - Creates a fresh database for each test
    - Automatically detects the backend (aiosqlite vs SQLAlchemy)
    - Patches global state to use the test database
    - Ensures proper cleanup and state restoration

    Yields:
        DatabaseTestManager: Isolated database manager for testing
    """
    db_test_manager = DatabaseTestManager()

    try:
        await db_test_manager.setup()
        yield db_test_manager
    finally:
        await db_test_manager.cleanup()


@pytest.fixture(scope="function")
async def db_connection(isolated_db: DatabaseTestManager):
    """
    Provide a database connection using the isolated database.

    Args:
        isolated_db: The isolated database manager

    Yields:
        Database connection for direct SQL operations
    """
    async with isolated_db.get_connection() as conn:
        yield conn


@pytest.fixture(scope="function")
async def seeded_db(isolated_db: DatabaseTestManager) -> DatabaseTestManager:
    """
    Provide an isolated database pre-populated with test data.

    Args:
        isolated_db: The isolated database manager

    Returns:
        DatabaseTestManager: Database with seeded test data
    """
    async with isolated_db.get_connection() as conn:
        # Create test sessions
        await conn.execute(
            """
            INSERT INTO sessions (id, purpose, created_by, metadata)
            VALUES (?, ?, ?, ?)
            """,
            ("session_test_001", "Test session 1", "test_agent", '{"test": true}'),
        )

        await conn.execute(
            """
            INSERT INTO sessions (id, purpose, created_by, metadata)
            VALUES (?, ?, ?, ?)
            """,
            ("session_test_002", "Test session 2", "another_agent", '{"test": true}'),
        )

        # Create test messages
        test_messages = [
            (
                "session_test_001",
                "test_agent",
                "agent",
                "Public test message",
                "public",
                None,
                None,
            ),
            (
                "session_test_001",
                "test_agent",
                "agent",
                "Private test message",
                "private",
                None,
                None,
            ),
            (
                "session_test_002",
                "another_agent",
                "agent",
                "Another session message",
                "public",
                None,
                None,
            ),
        ]

        for msg_data in test_messages:
            await conn.execute(
                """
                INSERT INTO messages (session_id, sender, sender_type, content, visibility, metadata, parent_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                msg_data,
            )

        # Create test agent memory
        await conn.execute(
            """
            INSERT INTO agent_memory (agent_id, session_id, key, value, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("test_agent", "session_test_001", "test_key", '{"test": "data"}', None),
        )

        await conn.commit()

    return isolated_db


def patch_database_for_test(db_manager: DatabaseTestManager):
    """
    Create a context manager that patches database functions to use test database.

    This replaces the heavy mocking patterns with real database connections
    while ensuring tests use the isolated test database.

    Args:
        db_manager: The test database manager to use

    Returns:
        Context manager for patching database access
    """

    @asynccontextmanager
    async def mock_get_db_connection():
        async with db_manager.get_connection() as conn:
            yield conn

    # Create patches for all common database import patterns
    patches = []

    # Core database module patches
    patches.append(
        patch(
            "src.shared_context_server.database.get_db_connection",
            mock_get_db_connection,
        )
    )

    # Server module no longer has get_db_connection after modularization
    # Tool modules have their own patches

    # Tool module patches
    patches.extend(
        [
            patch(
                "shared_context_server.session_tools.get_db_connection",
                mock_get_db_connection,
            ),
            patch(
                "shared_context_server.memory_tools.get_db_connection",
                mock_get_db_connection,
            ),
            patch(
                "shared_context_server.search_tools.get_db_connection",
                mock_get_db_connection,
            ),
            patch(
                "shared_context_server.admin_tools.get_db_connection",
                mock_get_db_connection,
            ),
        ]
    )

    # Auth module patches
    patches.append(
        patch("shared_context_server.auth.get_db_connection", mock_get_db_connection)
    )

    from contextlib import ExitStack

    class DatabasePatcher:
        """Context manager that applies all database patches."""

        def __enter__(self):
            self.stack = ExitStack()
            for patch_obj in patches:
                self.stack.enter_context(patch_obj)
            return self

        def __exit__(self, *args):
            self.stack.__exit__(*args)

    return DatabasePatcher()


@pytest.fixture(scope="function")
async def patched_db_connection(isolated_db: DatabaseTestManager):
    """
    Provide database connection with all imports patched to use test database.

    This fixture combines isolated database with comprehensive patching,
    replacing the need for extensive mocking in individual tests.

    Args:
        isolated_db: The isolated database manager

    Yields:
        Database connection with all imports patched
    """
    with patch_database_for_test(isolated_db):
        async with isolated_db.get_connection() as conn:
            yield conn


# Utility functions for common test patterns


async def create_test_session(
    conn, session_id: str = "test_session", agent_id: str = "test_agent"
) -> str:
    """
    Create a test session in the database.

    Args:
        conn: Database connection
        session_id: Session ID to create
        agent_id: Agent that creates the session

    Returns:
        The created session ID
    """
    await conn.execute(
        """
        INSERT INTO sessions (id, purpose, created_by)
        VALUES (?, ?, ?)
        """,
        (session_id, f"Test session {session_id}", agent_id),
    )
    await conn.commit()
    return session_id


async def create_test_message(
    conn,
    session_id: str,
    content: str = "Test message",
    sender: str = "test_agent",
    visibility: str = "public",
) -> int:
    """
    Create a test message in the database.

    Args:
        conn: Database connection
        session_id: Session to add message to
        content: Message content
        sender: Message sender
        visibility: Message visibility

    Returns:
        The created message ID
    """
    cursor = await conn.execute(
        """
        INSERT INTO messages (session_id, sender, sender_type, content, visibility)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, sender, "agent", content, visibility),
    )
    await conn.commit()
    return cursor.lastrowid


async def create_test_memory(
    conn,
    agent_id: str = "test_agent",
    key: str = "test_key",
    value: str = '{"test": true}',
    session_id: str | None = None,
) -> None:
    """
    Create test agent memory in the database.

    Args:
        conn: Database connection
        agent_id: Agent ID
        key: Memory key
        value: Memory value (JSON string)
        session_id: Optional session scope
    """
    await conn.execute(
        """
        INSERT INTO agent_memory (agent_id, session_id, key, value)
        VALUES (?, ?, ?, ?)
        """,
        (agent_id, session_id, key, value),
    )
    await conn.commit()


async def assert_table_count(conn, table_name: str, expected_count: int) -> None:
    """
    Assert that a table has the expected number of rows.

    Args:
        conn: Database connection
        table_name: Name of table to check
        expected_count: Expected row count
    """
    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table_name}")
    actual_count = (await cursor.fetchone())[0]
    assert actual_count == expected_count, (
        f"Expected {expected_count} rows in {table_name}, got {actual_count}"
    )


async def assert_session_exists(conn, session_id: str) -> None:
    """
    Assert that a session exists in the database.

    Args:
        conn: Database connection
        session_id: Session ID to check
    """
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE id = ?", (session_id,)
    )
    count = (await cursor.fetchone())[0]
    assert count == 1, f"Session {session_id} not found"


async def assert_message_exists(conn, session_id: str, content: str) -> None:
    """
    Assert that a message exists in the database.

    Args:
        conn: Database connection
        session_id: Session ID to check
        content: Message content to check
    """
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ? AND content = ?",
        (session_id, content),
    )
    count = (await cursor.fetchone())[0]
    assert count == 1, f"Message '{content}' not found in session {session_id}"


def is_sqlalchemy_backend() -> bool:
    """
    Check if tests are running with SQLAlchemy backend.

    Returns:
        True if USE_SQLALCHEMY=true, False otherwise
    """
    return os.getenv("USE_SQLALCHEMY", "false").lower() == "true"


def is_aiosqlite_backend() -> bool:
    """
    Check if tests are running with aiosqlite backend.

    Returns:
        True if USE_SQLALCHEMY=false or not set, False otherwise
    """
    return not is_sqlalchemy_backend()
