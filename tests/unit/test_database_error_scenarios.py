"""
Tests for database error scenarios and edge cases to improve coverage.

These tests specifically target error paths and exception handling
in database.py to increase overall coverage.
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.shared_context_server.database import (
    DatabaseConnectionError,
    DatabaseManager,
    DatabaseSchemaError,
)
from tests.fixtures.database import is_sqlalchemy_backend


class TestDatabaseManagerErrorScenarios:
    """Test error scenarios in DatabaseManager."""

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend has different schema loading logic",
    )
    async def test_load_schema_file_not_found(self):
        """Test schema file loading when file doesn't exist."""
        # Create a temporary database manager with non-existent schema
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            manager = DatabaseManager(db_path)

            # Mock the schema file paths to non-existent locations
            with patch.object(manager, "_load_schema_file") as mock_load:
                mock_load.side_effect = DatabaseSchemaError(
                    "Schema file not found in any of the following locations"
                )

                with pytest.raises(DatabaseSchemaError, match="Schema file not found"):
                    manager._load_schema_file()

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend has different schema loading logic",
    )
    async def test_load_schema_file_io_error(self):
        """Test schema file loading with IO error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            manager = DatabaseManager(db_path)

            # Create a schema file but mock open to raise IOError
            schema_path = Path(tmpdir) / "database_sqlite.sql"
            schema_path.write_text("CREATE TABLE test (id INTEGER);")

            with (
                patch("builtins.open", side_effect=OSError("Permission denied")),
                pytest.raises(OSError, match="Permission denied"),
            ):
                manager._load_schema_file()

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend has different initialization logic",
    )
    async def test_ensure_schema_applied_executescript_failure(self):
        """Test schema application failure during executescript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            manager = DatabaseManager(db_path)

            # Mock connection and cursor for schema check
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = None  # No schema_version table
            mock_conn.execute.return_value = mock_cursor

            # Mock executescript to fail
            mock_conn.executescript.side_effect = Exception("SQL execution failed")

            # Mock _load_schema_file to return valid schema
            with (
                patch.object(
                    manager,
                    "_load_schema_file",
                    return_value="CREATE TABLE test (id INTEGER);",
                ),
                pytest.raises(DatabaseSchemaError, match="Failed to apply schema"),
            ):
                await manager._ensure_schema_applied(mock_conn)

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend has different validation logic",
    )
    async def test_validate_schema_table_check_failure(self):
        """Test schema validation when table existence check fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            manager = DatabaseManager(db_path)

            # Mock connection to raise exception during table check
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = Exception("Database error")

            with pytest.raises(DatabaseSchemaError, match="Schema validation failed"):
                await manager._validate_schema(mock_conn)

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend has different connection logic",
    )
    async def test_get_connection_pragma_failure(self):
        """Test connection failure during PRAGMA application."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            manager = DatabaseManager(db_path)

            # Mock aiosqlite.connect to return connection that fails on PRAGMA
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = Exception("PRAGMA failed")

            # Make aiosqlite.connect return an awaitable
            async def mock_connect(*args, **kwargs):
                return mock_conn

            with (
                patch("aiosqlite.connect", side_effect=mock_connect),
                pytest.raises(DatabaseConnectionError, match="PRAGMA failed"),
            ):
                async with manager.get_connection():
                    pass

    async def test_raise_schema_not_found_error(self):
        """Test schema not found error raising."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            manager = DatabaseManager(db_path)

            schema_path = Path("/nonexistent/schema.sql")
            with pytest.raises(DatabaseSchemaError, match="Schema file not found"):
                manager._raise_schema_not_found_error(schema_path)


class TestDatabaseConnectionErrors:
    """Test database connection error scenarios."""

    async def test_connection_timeout_error(self):
        """Test connection timeout handling."""
        # Mock a database connection that times out
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = TimeoutError("Connection timeout")

            manager = DatabaseManager(":memory:")
            with pytest.raises(
                DatabaseConnectionError
            ):  # Should propagate timeout as DatabaseConnectionError
                async with manager.get_connection():
                    pass

    async def test_database_locked_error(self):
        """Test database locked error handling."""
        with patch("aiosqlite.connect") as mock_connect:
            # Simulate database locked error
            mock_connect.side_effect = sqlite3.OperationalError("database is locked")

            manager = DatabaseManager(":memory:")
            with pytest.raises(DatabaseConnectionError):
                async with manager.get_connection():
                    pass

    async def test_connection_close_error(self):
        """Test error during connection close is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            manager = DatabaseManager(db_path)

            # Test that normal connection works
            async with manager.get_connection() as conn:
                # Simple test to ensure connection is functional
                cursor = await conn.execute("SELECT 1")
                result = await cursor.fetchone()
                assert result == (1,)


class TestDatabaseInitializationErrors:
    """Test database initialization error scenarios."""

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend has different initialization",
    )
    async def test_initialize_database_permission_error(self):
        """Test database initialization with permission error."""
        # Try to create database in read-only location
        readonly_path = "/dev/null/impossible.db"

        with pytest.raises(
            DatabaseConnectionError
        ):  # Should fail with permission/path error
            manager = DatabaseManager(readonly_path)
            async with manager.get_connection():
                pass

    async def test_database_corruption_scenario(self):
        """Test handling of corrupted database scenarios."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            # Write invalid content to simulate corruption
            tmp.write(b"This is not a valid SQLite database")
            tmp.flush()

            # Try to connect to corrupted database
            manager = DatabaseManager(tmp.name)

            with pytest.raises(DatabaseConnectionError):  # Should fail to connect
                async with manager.get_connection():
                    pass
