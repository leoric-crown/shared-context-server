"""
Simplified backend switching tests using unified database testing infrastructure.

This demonstrates how the new approach eliminates complexity while providing
comprehensive backend compatibility testing.
"""

import pytest

from shared_context_server.database_testing import (
    get_test_db_connection,
)
from tests.conftest import patch_database_connection

pytestmark = pytest.mark.asyncio


class TestSimplifiedBackendSwitching:
    """Test simplified database backend switching."""

    async def test_aiosqlite_backend_basic_operations(self):
        """Test basic operations with aiosqlite backend."""
        async with get_test_db_connection("aiosqlite") as conn:
            # Test basic CRUD operations
            await conn.execute("DROP TABLE IF EXISTS test_aiosqlite")
            await conn.execute("""
                CREATE TABLE test_aiosqlite (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    value INTEGER
                )
            """)

            # Insert test data
            await conn.execute(
                "INSERT INTO test_aiosqlite (name, value) VALUES (?, ?)",
                ("test_item", 42),
            )
            await conn.commit()

            # Query and verify
            cursor = await conn.execute(
                "SELECT name, value FROM test_aiosqlite WHERE id = 1"
            )
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "test_item"
            assert row[1] == 42

    async def test_sqlalchemy_backend_basic_operations(self):
        """Test basic operations with SQLAlchemy backend."""
        async with get_test_db_connection("sqlalchemy") as conn:
            # Test basic CRUD operations
            await conn.execute("DROP TABLE IF EXISTS test_sqlalchemy")
            await conn.execute("""
                CREATE TABLE test_sqlalchemy (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    value INTEGER
                )
            """)

            # Insert test data
            await conn.execute(
                "INSERT INTO test_sqlalchemy (name, value) VALUES (?, ?)",
                ("test_item", 42),
            )
            await conn.commit()

            # Query and verify
            cursor = await conn.execute(
                "SELECT name, value FROM test_sqlalchemy WHERE id = 1"
            )
            row = await cursor.fetchone()
            assert row is not None

            # Handle different row formats
            if hasattr(row, "keys"):
                # SQLAlchemy wrapper provides dict-like access
                assert row["name"] == "test_item"
                assert row["value"] == 42
            else:
                # Tuple access
                assert row[0] == "test_item"
                assert row[1] == 42

    async def test_backend_switching_with_patching(self, test_db_manager):
        """Test that the patch system works with both backends."""
        # Test aiosqlite backend
        with patch_database_connection(test_db_manager, backend="aiosqlite"):
            from shared_context_server.database import get_db_connection

            async with get_db_connection() as conn:
                await conn.execute(
                    "CREATE TABLE test_patch_aio (id INTEGER, data TEXT)"
                )
                await conn.execute("INSERT INTO test_patch_aio VALUES (1, 'aiosqlite')")
                await conn.commit()

                cursor = await conn.execute(
                    "SELECT data FROM test_patch_aio WHERE id = 1"
                )
                row = await cursor.fetchone()
                assert row[0] == "aiosqlite"

        # Test SQLAlchemy backend
        with patch_database_connection(test_db_manager, backend="sqlalchemy"):
            from shared_context_server.database import get_db_connection

            async with get_db_connection() as conn:
                await conn.execute(
                    "CREATE TABLE test_patch_sql (id INTEGER, data TEXT)"
                )
                await conn.execute(
                    "INSERT INTO test_patch_sql VALUES (1, 'sqlalchemy')"
                )
                await conn.commit()

                cursor = await conn.execute(
                    "SELECT data FROM test_patch_sql WHERE id = 1"
                )
                row = await cursor.fetchone()

                # Handle different row formats
                if hasattr(row, "keys"):
                    assert row["data"] == "sqlalchemy"
                else:
                    assert row[0] == "sqlalchemy"

    async def test_concurrent_backend_usage(self):
        """Test that different backends can be used concurrently without interference."""
        # Run operations on both backends in parallel
        import asyncio

        async def test_aiosqlite():
            async with get_test_db_connection("aiosqlite") as conn:
                await conn.execute(
                    "CREATE TABLE concurrent_aio (id INTEGER, backend TEXT)"
                )
                await conn.execute("INSERT INTO concurrent_aio VALUES (1, 'aiosqlite')")
                await conn.commit()

                cursor = await conn.execute(
                    "SELECT backend FROM concurrent_aio WHERE id = 1"
                )
                row = await cursor.fetchone()
                return row[0]

        async def test_sqlalchemy():
            async with get_test_db_connection("sqlalchemy") as conn:
                await conn.execute(
                    "CREATE TABLE concurrent_sql (id INTEGER, backend TEXT)"
                )
                await conn.execute(
                    "INSERT INTO concurrent_sql VALUES (1, 'sqlalchemy')"
                )
                await conn.commit()

                cursor = await conn.execute(
                    "SELECT backend FROM concurrent_sql WHERE id = 1"
                )
                row = await cursor.fetchone()
                if hasattr(row, "keys"):
                    return row["backend"]
                return row[0]

        # Run both tests concurrently
        aio_result, sql_result = await asyncio.gather(
            test_aiosqlite(), test_sqlalchemy()
        )

        assert aio_result == "aiosqlite"
        assert sql_result == "sqlalchemy"

    async def test_schema_consistency_across_backends(self):
        """Test that schema operations work consistently across backends."""
        schema_sql = """
        CREATE TABLE schema_test (
            id INTEGER PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data JSON,
            status TEXT CHECK (status IN ('active', 'inactive'))
        )
        """

        # Test schema creation with aiosqlite
        async with get_test_db_connection("aiosqlite") as conn:
            await conn.execute(schema_sql)
            await conn.execute(
                "INSERT INTO schema_test (data, status) VALUES (?, ?)",
                ('{"test": true}', "active"),
            )
            await conn.commit()

            cursor = await conn.execute("SELECT COUNT(*) FROM schema_test")
            count = await cursor.fetchone()
            assert count[0] == 1

        # Test schema creation with SQLAlchemy
        async with get_test_db_connection("sqlalchemy") as conn:
            await conn.execute(schema_sql)
            await conn.execute(
                "INSERT INTO schema_test (data, status) VALUES (?, ?)",
                ('{"test": true}', "active"),
            )
            await conn.commit()

            cursor = await conn.execute("SELECT COUNT(*) FROM schema_test")
            count = await cursor.fetchone()
            if hasattr(count, "keys"):
                assert list(count.values())[0] == 1
            else:
                assert count[0] == 1


class TestMemoryDatabaseAdvantages:
    """Test the advantages of memory-based database testing."""

    async def test_perfect_isolation(self):
        """Test that memory databases provide perfect isolation between instances."""
        # Test 1: Demonstrate that each get_test_db_connection() call creates isolated databases
        async with get_test_db_connection("aiosqlite") as conn1:
            await conn1.execute("CREATE TABLE isolation_test (id INTEGER, data TEXT)")
            await conn1.execute("INSERT INTO isolation_test VALUES (1, 'first')")
            await conn1.commit()

            # Verify data exists in this connection
            cursor = await conn1.execute(
                "SELECT COUNT(*) FROM isolation_test WHERE data = 'first'"
            )
            count = await cursor.fetchone()
            assert count[0] == 1

        # Test 2: New connection should NOT see the previous data (perfect isolation)
        async with get_test_db_connection("aiosqlite") as conn2:
            try:
                cursor = await conn2.execute("SELECT COUNT(*) FROM isolation_test")
                # If we get here, table exists (bad isolation)
                count = await cursor.fetchone()
                # This should not happen with proper isolation
                pytest.fail(f"Table should not exist, but found {count[0]} rows")
            except Exception:
                # Table doesn't exist - perfect isolation achieved
                pass

        # Test 3: Demonstrate that this is a feature, not a bug
        # This shows that each test gets a completely clean database
        async with get_test_db_connection("aiosqlite") as conn3:
            await conn3.execute("CREATE TABLE isolation_test (id INTEGER, data TEXT)")
            await conn3.execute("INSERT INTO isolation_test VALUES (2, 'second')")
            await conn3.commit()

            cursor = await conn3.execute("SELECT data FROM isolation_test WHERE id = 2")
            row = await cursor.fetchone()
            assert row[0] == "second"

            # Verify the first test's data is NOT here
            cursor = await conn3.execute(
                "SELECT COUNT(*) FROM isolation_test WHERE data = 'first'"
            )
            count = await cursor.fetchone()
            assert count[0] == 0  # No data from previous test

    async def test_no_cleanup_needed(self):
        """Test that memory databases require no cleanup."""
        # Create lots of data
        async with get_test_db_connection("aiosqlite") as conn:
            await conn.execute("CREATE TABLE cleanup_test (id INTEGER, data BLOB)")

            # Insert large amounts of data
            for i in range(100):
                large_data = b"x" * 1000  # 1KB per row
                await conn.execute(
                    "INSERT INTO cleanup_test VALUES (?, ?)", (i, large_data)
                )
            await conn.commit()

            # Verify data was created
            cursor = await conn.execute("SELECT COUNT(*) FROM cleanup_test")
            count = await cursor.fetchone()
            assert count[0] == 100

        # Connection is closed, memory is automatically freed
        # No temporary files to clean up, no WAL files, no journal files
        # This test demonstrates that memory databases are self-cleaning

    async def test_fast_execution(self):
        """Test that memory databases provide fast execution."""
        import time

        start_time = time.time()

        async with get_test_db_connection("aiosqlite") as conn:
            # Create table and insert data
            await conn.execute("CREATE TABLE speed_test (id INTEGER, data TEXT)")

            # Insert 1000 rows
            for i in range(1000):
                await conn.execute(
                    "INSERT INTO speed_test VALUES (?, ?)", (i, f"data_{i}")
                )
            await conn.commit()

            # Query all data
            cursor = await conn.execute("SELECT COUNT(*) FROM speed_test")
            count = await cursor.fetchone()
            assert count[0] == 1000

        end_time = time.time()
        execution_time = end_time - start_time

        # Memory databases should be very fast (< 1 second for 1000 rows)
        assert execution_time < 1.0, f"Memory database too slow: {execution_time:.2f}s"
