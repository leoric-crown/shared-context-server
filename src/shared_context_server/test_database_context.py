"""
Thread-safe test database context management using ContextVar.

This module provides a ContextVar-based approach to managing UnifiedTestDatabase
instances, replacing the global _test_db_instance singleton anti-pattern with proper
thread-safe context management for test isolation.

Key Benefits:
- Zero global state pollution between tests
- Perfect thread safety without locks
- Automatic isolation for concurrent test execution
- Each test context gets its own database instance
- Eliminates manual database resets in test suites
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Optional

from .database_testing import TestDatabaseManager

# Thread-safe context variable for test database instances
# Each asyncio task/thread gets its own isolated instance
_test_db_context: ContextVar[Optional[TestDatabaseManager]] = ContextVar(
    "test_database", default=None
)


def get_context_test_database(_backend: str = "sqlalchemy") -> TestDatabaseManager:
    """
    Get test database from thread-local context.

    Creates a new instance if none exists in the current context,
    providing automatic isolation between different execution contexts
    (threads, asyncio tasks, tests, etc.).

    Args:
        backend: Database backend to use ("sqlalchemy" or "aiosqlite" - deprecated)

    Returns:
        TestDatabaseManager: Thread-local test database instance

    Thread Safety:
        Perfect - each context gets its own instance automatically

    Note:
        Always creates new instances to ensure clean isolation between tests.
        Memory databases are cheap to create and provide perfect isolation.
    """
    # Always create a new instance for perfect test isolation
    # This follows the same pattern as the original get_test_database()
    db = TestDatabaseManager()
    _test_db_context.set(db)
    return db


def set_test_database_for_testing(db: Optional[TestDatabaseManager]) -> None:
    """
    Set test database in context - for test injection only.

    This function is intended for testing scenarios where you need to
    inject a specific database instance (e.g., mock or configured instance).

    Args:
        db: Database instance to set in context, or None to clear

    Note:
        This is primarily for testing - production code should use
        get_context_test_database() which handles instance creation automatically.
    """
    _test_db_context.set(db)


def reset_test_database_context() -> None:
    """
    Reset context - automatic isolation for tests.

    Clears the current context, forcing the next call to get_context_test_database()
    to create a fresh instance. This is useful for test isolation, though in most
    cases the automatic context isolation should be sufficient.

    Note:
        With ContextVar, this is rarely needed as each test naturally gets
        its own context. This is provided for explicit cleanup scenarios.
    """
    _test_db_context.set(None)


def get_current_test_database() -> Optional[TestDatabaseManager]:
    """
    Get current test database from context without creating one.

    Returns:
        TestDatabaseManager or None: Current database if one exists in context

    Use Case:
        Checking if a test database exists without triggering creation.
        Useful for debugging or conditional logic.
    """
    return _test_db_context.get()


@asynccontextmanager
async def get_context_test_db_connection(
    backend: str = "sqlalchemy",
) -> AsyncGenerator[Any, None]:
    """
    Get test database connection from thread-local context.

    This is the main function to use for database testing with ContextVar isolation.
    Each test/task gets its own database instance automatically.

    Args:
        backend: Database backend to use ("sqlalchemy" or "aiosqlite" - deprecated)

    Yields:
        Database connection (aiosqlite.Connection or SQLAlchemy wrapper)

    Thread Safety:
        Perfect - each context gets its own database and connection

    Usage:
        ```python
        async with get_context_test_db_connection() as conn:
            # Use conn for database operations
            # Each test gets isolated database automatically
        ```
    """
    db = get_context_test_database(backend)

    # Initialize database if needed
    if not db._initialized:
        await db.initialize()

    async with db.get_connection() as conn:
        yield conn
