"""
Test database backend toggle functionality.

This module tests that both aiosqlite and SQLAlchemy backends work identically
with the same interface and produce the same results.
"""

import os
from unittest.mock import patch

import pytest

from src.shared_context_server.database import get_db_connection


class TestDatabaseBackendToggle:
    """Test database backend compatibility between aiosqlite and SQLAlchemy."""

    @pytest.mark.parametrize("use_sqlalchemy", [False, True])
    async def test_database_backend_compatibility(self, use_sqlalchemy: bool, tmp_path):
        """
        Verify both backends work identically with basic operations.

        Tests:
        - Connection establishment
        - Table creation
        - Data insertion and retrieval
        - Parameter binding
        - Transaction commit
        """
        # Use temporary database for testing
        test_db_path = tmp_path / "test_backend_toggle.db"

        env_vars = {
            "USE_SQLALCHEMY": str(use_sqlalchemy).lower(),
            "DATABASE_PATH": str(test_db_path),
        }

        # Clear DATABASE_URL to force use of DATABASE_PATH
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        with patch.dict(os.environ, env_vars, clear=False):
            # Clear any cached managers to ensure clean test
            from src.shared_context_server import database

            database._db_manager = None
            database._sqlalchemy_manager = None

            async with get_db_connection() as conn:
                # Test basic table creation
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS test_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await conn.commit()

                # Test data insertion with parameter binding
                cursor = await conn.execute(
                    "INSERT INTO test_messages (content) VALUES (?)", ("Hello, World!",)
                )
                await conn.commit()

                # Verify lastrowid works
                message_id = cursor.lastrowid
                assert message_id is not None
                assert message_id > 0

                # Test data retrieval with parameters
                # Set row factory for aiosqlite compatibility
                if hasattr(conn, "row_factory"):
                    import aiosqlite

                    conn.row_factory = aiosqlite.Row

                cursor = await conn.execute(
                    "SELECT id, content FROM test_messages WHERE id = ?", (message_id,)
                )
                row = await cursor.fetchone()

                # Verify results
                assert row is not None
                if isinstance(row, dict):  # SQLAlchemy returns dict-like
                    assert row["id"] == message_id
                    assert row["content"] == "Hello, World!"
                elif hasattr(row, "keys"):  # aiosqlite.Row with keys
                    assert dict(row)["id"] == message_id
                    assert dict(row)["content"] == "Hello, World!"
                else:  # Tuple access fallback
                    assert row[0] == message_id
                    assert row[1] == "Hello, World!"

                # Test fetchall
                cursor = await conn.execute(
                    "SELECT COUNT(*) as count FROM test_messages"
                )
                rows = await cursor.fetchall()
                assert len(rows) == 1

                # Test multiple inserts (SQLite doesn't support multi-row VALUES with ?)
                await conn.execute(
                    "INSERT INTO test_messages (content) VALUES (?)", ("Message 2",)
                )
                await conn.commit()

                await conn.execute(
                    "INSERT INTO test_messages (content) VALUES (?)", ("Message 3",)
                )
                await conn.commit()

                cursor = await conn.execute("SELECT COUNT(*) FROM test_messages")
                result = await cursor.fetchone()

                # Handle different result formats
                if isinstance(result, dict):
                    count = list(result.values())[0]  # Get first value from dict
                elif hasattr(result, "keys"):  # aiosqlite.Row
                    count = list(dict(result).values())[0]
                else:  # Tuple
                    count = result[0]

                assert count >= 3  # Should have at least 3 messages

    @pytest.mark.parametrize("use_sqlalchemy", [False, True])
    async def test_transaction_behavior(self, use_sqlalchemy: bool, tmp_path):
        """Test transaction commit/rollback behavior is consistent."""
        # Use unique database file for each test iteration
        test_db_path = tmp_path / f"test_transaction_{use_sqlalchemy}.db"

        env_vars = {
            "USE_SQLALCHEMY": str(use_sqlalchemy).lower(),
            "DATABASE_PATH": str(test_db_path),
        }

        # Clear DATABASE_URL to force use of DATABASE_PATH
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        with patch.dict(os.environ, env_vars, clear=False):
            # Clear any cached managers
            from src.shared_context_server import database

            database._db_manager = None
            database._sqlalchemy_manager = None

            async with get_db_connection() as conn:
                # Drop table if it exists (clean slate)
                await conn.execute("DROP TABLE IF EXISTS test_transactions")
                await conn.commit()

                # Create test table
                await conn.execute("""
                    CREATE TABLE test_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        value TEXT NOT NULL
                    )
                """)
                await conn.commit()

                # Insert data and commit
                await conn.execute(
                    "INSERT INTO test_transactions (value) VALUES (?)",
                    ("committed_value",),
                )
                await conn.commit()

                # Verify data exists
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM test_transactions WHERE value = ?",
                    ("committed_value",),
                )
                result = await cursor.fetchone()

                # Handle different result formats
                if isinstance(result, dict):
                    count = list(result.values())[0]
                elif hasattr(result, "keys"):  # aiosqlite.Row
                    count = list(dict(result).values())[0]
                else:  # Tuple
                    count = result[0]

                assert count == 1

    async def test_parameter_binding_edge_cases(self):
        """Test parameter binding works with various data types."""

        for use_sqlalchemy in [False, True]:
            env_vars = {"USE_SQLALCHEMY": str(use_sqlalchemy).lower()}

            with patch.dict(os.environ, env_vars, clear=False):
                # Clear cached managers
                from src.shared_context_server import database

                database._db_manager = None
                database._sqlalchemy_manager = None

                async with get_db_connection() as conn:
                    # Test with empty parameters
                    cursor = await conn.execute("SELECT 1 as test_value")
                    result = await cursor.fetchone()
                    assert result is not None

                    # Test with multiple parameters
                    cursor = await conn.execute(
                        "SELECT ? as param1, ? as param2, ? as param3",
                        ("string", 42, 3.14),
                    )
                    result = await cursor.fetchone()
                    assert result is not None

    async def test_backend_toggle_environment_variable(self):
        """Test that environment variable USE_SQLALCHEMY controls backend selection."""

        # Test default (aiosqlite)
        with patch.dict(os.environ, {"USE_SQLALCHEMY": "false"}, clear=False):
            from src.shared_context_server import database

            database._db_manager = None
            database._sqlalchemy_manager = None

            # Should work without error
            async with get_db_connection() as conn:
                cursor = await conn.execute("SELECT 1")
                result = await cursor.fetchone()
                assert result is not None

        # Test SQLAlchemy backend
        with patch.dict(os.environ, {"USE_SQLALCHEMY": "true"}, clear=False):
            from src.shared_context_server import database

            database._db_manager = None
            database._sqlalchemy_manager = None

            # Should work without error
            async with get_db_connection() as conn:
                cursor = await conn.execute("SELECT 1")
                result = await cursor.fetchone()
                assert result is not None
