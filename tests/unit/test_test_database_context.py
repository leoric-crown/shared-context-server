"""
Unit tests for thread-safe test database context management.

These tests validate the ContextVar-based approach to managing
UnifiedTestDatabase instances for test isolation, ensuring proper
thread safety and automatic cleanup.
"""

import asyncio
import threading
from unittest.mock import MagicMock

import pytest

from shared_context_server.database_testing import UnifiedTestDatabase
from shared_context_server.test_database_context import (
    get_context_test_database,
    get_context_test_db_connection,
    get_current_test_database,
    reset_test_database_context,
    set_test_database_for_testing,
)


class TestDatabaseContext:
    """Test ContextVar-based test database management."""

    def test_get_context_test_database_creates_instance(self):
        """Test that get_context_test_database creates new instance."""
        reset_test_database_context()

        db = get_context_test_database()

        assert db is not None
        assert isinstance(db, UnifiedTestDatabase)
        assert db.backend == "aiosqlite"  # Default backend

    def test_get_context_test_database_with_backend(self):
        """Test creating database with specific backend."""
        reset_test_database_context()

        db = get_context_test_database("sqlalchemy")

        assert db is not None
        assert isinstance(db, UnifiedTestDatabase)
        assert db.backend == "sqlalchemy"

    def test_get_context_test_database_always_creates_new(self):
        """Test that get_context_test_database always creates new instances."""
        reset_test_database_context()

        # Unlike other contexts, test databases should always be new
        # for perfect test isolation
        db1 = get_context_test_database()
        db2 = get_context_test_database()

        assert db1 is not db2  # Always different instances

    def test_set_test_database_for_testing(self):
        """Test setting custom database instance for testing."""
        reset_test_database_context()

        mock_db = MagicMock(spec=UnifiedTestDatabase)
        set_test_database_for_testing(mock_db)

        # Since get_context_test_database always creates new instances,
        # we need to check current context instead
        current = get_current_test_database()
        assert current is mock_db

    def test_set_test_database_for_testing_none(self):
        """Test setting None clears the context."""
        reset_test_database_context()

        # Set a mock database
        mock_db = MagicMock(spec=UnifiedTestDatabase)
        set_test_database_for_testing(mock_db)
        assert get_current_test_database() is mock_db

        # Clear it
        set_test_database_for_testing(None)
        assert get_current_test_database() is None

    def test_reset_test_database_context(self):
        """Test that reset clears the context."""
        # Set a mock database
        mock_db = MagicMock(spec=UnifiedTestDatabase)
        set_test_database_for_testing(mock_db)
        assert get_current_test_database() is mock_db

        # Reset context
        reset_test_database_context()
        assert get_current_test_database() is None

    def test_get_current_test_database_none(self):
        """Test getting current database when none exists."""
        reset_test_database_context()

        current = get_current_test_database()
        assert current is None

    def test_get_current_test_database_exists(self):
        """Test getting current database when one exists."""
        reset_test_database_context()

        mock_db = MagicMock(spec=UnifiedTestDatabase)
        set_test_database_for_testing(mock_db)

        current = get_current_test_database()
        assert current is mock_db

    def test_thread_isolation(self):
        """Test that different threads get different database instances."""
        results = {}
        db_objects = {}  # Keep references to prevent garbage collection

        def create_db_in_thread(thread_id: int):
            """Create database in separate thread."""
            reset_test_database_context()
            db = get_context_test_database()
            results[thread_id] = id(db)  # Store object ID
            db_objects[thread_id] = db  # Keep reference to prevent GC

        # Create databases in separate threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_db_in_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Each thread should have gotten a different database instance
        db_ids = list(results.values())
        assert len(set(db_ids)) == 3  # All different IDs

        # Verify the objects are actually different instances
        db_list = list(db_objects.values())
        assert db_list[0] is not db_list[1]
        assert db_list[1] is not db_list[2]
        assert db_list[0] is not db_list[2]

    @pytest.mark.asyncio
    async def test_async_task_isolation(self):
        """Test that different async tasks get different database instances."""
        results = {}
        db_objects = {}  # Keep references to prevent garbage collection

        async def create_db_in_task(task_id: int):
            """Create database in separate async task."""
            reset_test_database_context()
            db = get_context_test_database()
            results[task_id] = id(db)  # Store object ID
            db_objects[task_id] = db  # Keep reference to prevent GC

        # Create databases in separate async tasks
        tasks = []
        for i in range(3):
            task = asyncio.create_task(create_db_in_task(i))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Each task should have gotten a different database instance
        db_ids = list(results.values())
        assert len(set(db_ids)) == 3  # All different IDs

        # Verify the objects are actually different instances
        db_list = list(db_objects.values())
        assert db_list[0] is not db_list[1]
        assert db_list[1] is not db_list[2]
        assert db_list[0] is not db_list[2]

    def test_perfect_isolation_between_calls(self):
        """Test that each call gets isolated database instance."""
        reset_test_database_context()

        # Even within same context, each call should get new instance
        # This provides perfect test isolation
        db1 = get_context_test_database()
        db2 = get_context_test_database()
        db3 = get_context_test_database()

        # All should be different instances for perfect isolation
        assert db1 is not db2
        assert db2 is not db3
        assert db1 is not db3

    @pytest.mark.asyncio
    async def test_get_context_test_db_connection(self):
        """Test getting database connection from context."""
        reset_test_database_context()

        from unittest.mock import AsyncMock, patch

        # Mock the database to avoid actual initialization
        mock_db = MagicMock(spec=UnifiedTestDatabase)
        mock_db._aiosqlite_manager = None
        mock_db._sqlalchemy_manager = None
        mock_db.initialize = AsyncMock()  # Use AsyncMock for async method

        # Mock the context manager for get_connection
        mock_conn = MagicMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_connection.return_value = mock_context_manager

        # Patch get_context_test_database to return our mock
        with patch(
            "shared_context_server.test_database_context.get_context_test_database",
            return_value=mock_db,
        ):
            async with get_context_test_db_connection() as conn:
                assert conn is mock_conn
                mock_db.initialize.assert_called_once()

    def test_backend_isolation(self):
        """Test that different backends create different instances."""
        reset_test_database_context()

        db1 = get_context_test_database("aiosqlite")
        db2 = get_context_test_database("sqlalchemy")

        assert db1 is not db2
        assert db1.backend == "aiosqlite"
        assert db2.backend == "sqlalchemy"

    def test_test_injection_isolation(self):
        """Test that test injection doesn't affect other contexts."""
        reset_test_database_context()

        # Create mock database
        mock_db = MagicMock(spec=UnifiedTestDatabase)

        def thread_with_injection():
            """Thread that injects mock database."""
            set_test_database_for_testing(mock_db)
            current = get_current_test_database()
            assert current is mock_db

        def thread_without_injection():
            """Thread that uses normal database creation."""
            reset_test_database_context()
            db = get_context_test_database()
            assert db is not mock_db
            assert isinstance(db, UnifiedTestDatabase)

        # Run both threads
        thread1 = threading.Thread(target=thread_with_injection)
        thread2 = threading.Thread(target=thread_without_injection)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()


class TestBackwardCompatibility:
    """Test backward compatibility with legacy test database pattern."""

    def test_legacy_get_test_database_import(self):
        """Test that legacy get_test_database import still works."""
        from shared_context_server.database_testing import get_test_database

        db = get_test_database()
        assert isinstance(db, UnifiedTestDatabase)

    def test_legacy_reset_test_database_is_noop(self):
        """Test that legacy reset function is no-op."""
        from shared_context_server.database_testing import (
            get_test_database,
            reset_test_database,
        )

        # Get database
        db1 = get_test_database()

        # Reset (should be no-op, but databases are always new anyway)
        reset_test_database()

        # Get another database - should be new instance (normal behavior)
        db2 = get_test_database()
        assert db1 is not db2  # Always different (expected behavior)

    @pytest.mark.asyncio
    async def test_legacy_get_test_db_connection(self):
        """Test that legacy get_test_db_connection still works."""
        # Mock to avoid actual database initialization
        from unittest.mock import AsyncMock, MagicMock, patch

        from shared_context_server.database_testing import get_test_db_connection

        mock_db = MagicMock(spec=UnifiedTestDatabase)
        mock_db._aiosqlite_manager = None
        mock_db._sqlalchemy_manager = None
        mock_db.initialize = AsyncMock()  # Use AsyncMock for async method

        # Mock the context manager for get_connection
        mock_conn = MagicMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_connection.return_value = mock_context_manager

        with patch(
            "shared_context_server.test_database_context.get_context_test_database",
            return_value=mock_db,
        ):
            async with get_test_db_connection() as conn:
                assert conn is mock_conn

    def test_legacy_and_new_api_consistency(self):
        """Test that legacy and new APIs create consistent databases."""
        from shared_context_server.database_testing import get_test_database

        reset_test_database_context()

        # Both should create UnifiedTestDatabase instances
        legacy_db = get_test_database()
        new_db = get_context_test_database()

        assert isinstance(legacy_db, UnifiedTestDatabase)
        assert isinstance(new_db, UnifiedTestDatabase)
        # Should be different instances (expected behavior)
        assert legacy_db is not new_db

    def test_backend_parameter_consistency(self):
        """Test that backend parameter works consistently across APIs."""
        from shared_context_server.database_testing import get_test_database

        reset_test_database_context()

        # Test both backends with both APIs
        legacy_sqlite = get_test_database("aiosqlite")
        legacy_sqlalchemy = get_test_database("sqlalchemy")
        new_sqlite = get_context_test_database("aiosqlite")
        new_sqlalchemy = get_context_test_database("sqlalchemy")

        assert legacy_sqlite.backend == "aiosqlite"
        assert legacy_sqlalchemy.backend == "sqlalchemy"
        assert new_sqlite.backend == "aiosqlite"
        assert new_sqlalchemy.backend == "sqlalchemy"
