"""
Example tests demonstrating improved testing patterns with reduced mocking.

This file showcases the new testing approach that:
1. Uses real database connections instead of excessive mocking
2. Provides proper test isolation through clean database state
3. Supports both aiosqlite and SQLAlchemy backends seamlessly
4. Implements proper cleanup to prevent state leakage between tests

These patterns replace overmocking with integration testing for better test fidelity.
"""

import sqlite3

import pytest

from src.shared_context_server.database import (
    execute_insert,
    execute_query,
)
from tests.fixtures.database import (
    DatabaseTestManager,
    assert_message_exists,
    assert_session_exists,
    assert_table_count,
    create_test_memory,
    create_test_message,
    create_test_session,
)


class TestImprovedDatabasePatterns:
    """Demonstrate improved database testing patterns."""

    @pytest.mark.asyncio
    async def test_direct_database_access(self, isolated_db: DatabaseTestManager):
        """Test using direct database connection for precise control."""
        async with isolated_db.get_connection() as conn:
            # Create test data directly
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by)
                VALUES ('direct_test', 'Direct access test', 'test_agent')
                """
            )
            await conn.commit()

            # Verify data was created
            cursor = await conn.execute(
                "SELECT purpose FROM sessions WHERE id = 'direct_test'"
            )
            result = await cursor.fetchone()
            assert result[0] == "Direct access test"

    @pytest.mark.asyncio
    async def test_global_functions_with_patching(self, patched_db_connection):
        """Test global database functions with proper patching."""
        # Test global functions work with isolated database
        session_data = await execute_insert(
            """
            INSERT INTO sessions (id, purpose, created_by)
            VALUES ('global_test', 'Global function test', 'test_agent')
            """
        )
        assert session_data is not None

        # Query the data back
        results = await execute_query(
            "SELECT purpose FROM sessions WHERE id = 'global_test'"
        )
        assert len(results) == 1
        assert results[0]["purpose"] == "Global function test"

    @pytest.mark.asyncio
    async def test_seeded_database(self, seeded_db: DatabaseTestManager):
        """Test using pre-populated database for complex scenarios."""
        async with seeded_db.get_connection() as conn:
            # Verify seeded data exists
            await assert_table_count(conn, "sessions", 2)
            await assert_table_count(conn, "messages", 3)
            await assert_table_count(conn, "agent_memory", 1)

            # Verify specific seeded content
            await assert_session_exists(conn, "session_test_001")
            await assert_message_exists(conn, "session_test_001", "Public test message")

    @pytest.mark.asyncio
    async def test_helper_functions(self, db_connection):
        """Test using helper functions for common test patterns."""
        # Use helper to create test data
        session_id = await create_test_session(
            db_connection, "helper_session", "helper_agent"
        )
        assert session_id == "helper_session"

        # Create test message using helper
        message_id = await create_test_message(
            db_connection, session_id, "Helper message", "helper_agent", "public"
        )
        assert message_id is not None

        # Create test memory using helper
        await create_test_memory(
            db_connection, "helper_agent", "helper_key", '{"helper": true}', session_id
        )

        # Verify all data was created
        await assert_session_exists(db_connection, session_id)
        await assert_message_exists(db_connection, session_id, "Helper message")

    @pytest.mark.asyncio
    async def test_cross_backend_compatibility(self, isolated_db: DatabaseTestManager):
        """Test that tests work regardless of backend (aiosqlite vs SQLAlchemy)."""
        # This test works the same way regardless of USE_SQLALCHEMY setting
        async with isolated_db.get_connection() as conn:
            # Create test data
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, metadata)
                VALUES ('backend_test', 'Backend compatibility', 'test_agent', '{"backend": "any"}')
                """
            )
            await conn.commit()

            # Test JSON handling (works with both backends)
            cursor = await conn.execute(
                "SELECT metadata FROM sessions WHERE id = 'backend_test'"
            )
            result = await cursor.fetchone()
            metadata_json = result[0]
            assert '"backend": "any"' in metadata_json

    @pytest.mark.asyncio
    async def test_no_state_leakage(self, isolated_db: DatabaseTestManager):
        """Test that demonstrates proper isolation between tests."""
        # Each test gets a completely fresh database
        async with isolated_db.get_connection() as conn:
            # This should always be empty
            await assert_table_count(conn, "sessions", 0)
            await assert_table_count(conn, "messages", 0)
            await assert_table_count(conn, "agent_memory", 0)

            # Add some data
            await create_test_session(conn, "isolation_test", "isolation_agent")
            await assert_table_count(conn, "sessions", 1)

        # The next test will get a fresh database with 0 sessions again


class TestReplacingOvermockingPatterns:
    """Examples of replacing overmocking with better patterns."""

    @pytest.mark.asyncio
    async def test_old_pattern_with_mocking(self, patched_db_connection):
        """
        Old pattern: Heavy mocking of database functions.

        This demonstrates the OLD way (don't do this anymore):
        - Mock every database call
        - Mock return values
        - Mock connection management
        - Results in fragile tests that break when implementation changes
        """
        # OLD PATTERN (replaced): from unittest.mock import patch, MagicMock
        # Complex mocking patterns were replaced with real database testing

        # NEW PATTERN: Use real database with proper isolation
        result = await execute_query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [row["name"] for row in result]
        assert "sessions" in table_names  # Real data, real constraints, real behavior

    @pytest.mark.asyncio
    async def test_new_pattern_integration(self, seeded_db: DatabaseTestManager):
        """
        New pattern: Integration testing with real database.

        Benefits:
        - Tests actual behavior, not mocked behavior
        - Catches real database constraint violations
        - Tests work as implementation evolves
        - Much more maintainable and reliable
        """
        # Test real database operations end-to-end
        async with seeded_db.get_connection() as conn:
            # Real foreign key constraints are enforced
            with pytest.raises((sqlite3.IntegrityError, RuntimeError)):
                await conn.execute(
                    """
                    INSERT INTO messages (session_id, sender, sender_type, content, visibility)
                    VALUES ('nonexistent_session', 'test', 'agent', 'test', 'public')
                    """
                )
                await conn.commit()

            # Real JSON validation constraints work
            with pytest.raises((sqlite3.IntegrityError, RuntimeError)):
                await conn.execute(
                    """
                    INSERT INTO sessions (id, purpose, created_by, metadata)
                    VALUES ('json_test', 'JSON test', 'agent', 'invalid json{')
                    """
                )
                await conn.commit()

    @pytest.mark.asyncio
    async def test_error_handling_patterns(self, isolated_db: DatabaseTestManager):
        """Test error handling with real database constraints."""
        async with isolated_db.get_connection() as conn:
            # Test unique constraint violation (real behavior)
            await create_test_session(conn, "unique_test", "agent1")

            # This should fail due to unique constraint
            with pytest.raises((sqlite3.IntegrityError, RuntimeError)):
                await create_test_session(conn, "unique_test", "agent2")  # Same ID

            # Verify first session still exists
            await assert_session_exists(conn, "unique_test")

            # Verify session count is still 1 (rollback worked)
            await assert_table_count(conn, "sessions", 1)
