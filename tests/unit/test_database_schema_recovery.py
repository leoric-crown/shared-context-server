"""
Comprehensive tests for database schema recovery and error handling.

This test module focuses on improving coverage for database connection management,
schema recovery, and error handling paths that weren't covered in basic tests.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from shared_context_server.database import (
    DatabaseConnectionError,
    DatabaseManager,
    DatabaseSchemaError,
    _raise_basic_query_error,
    _raise_journal_mode_check_error,
    _raise_no_schema_version_error,
    _raise_table_not_found_error,
    _raise_wal_mode_error,
    cleanup_expired_data,
    health_check,
)


class TestDatabaseErrorHandling:
    """Test database error handling functions."""

    def test_database_error_functions(self):
        """Test database error raising functions."""
        # Test WAL mode error
        with pytest.raises(
            DatabaseConnectionError, match="Failed to enable WAL mode, got: delete"
        ):
            _raise_wal_mode_error("delete")

        # Test journal mode check error
        with pytest.raises(
            DatabaseConnectionError, match="Failed to check journal mode"
        ):
            _raise_journal_mode_check_error()

        # Test table not found error
        with pytest.raises(
            DatabaseSchemaError, match="Required table 'test_table' not found"
        ):
            _raise_table_not_found_error("test_table")

        # Test no schema version error
        with pytest.raises(DatabaseSchemaError, match="No schema version found"):
            _raise_no_schema_version_error()

        # Test basic query error
        with pytest.raises(Exception, match="Basic query failed"):
            _raise_basic_query_error()


class TestDatabaseManagerSchemaRecovery:
    """Test DatabaseManager schema recovery functionality."""

    async def test_validate_schema_with_recovery_secure_tokens_missing(self):
        """Test schema recovery when secure_tokens table is missing."""
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create database manager
            db_manager = DatabaseManager(temp_db_path)

            # Initialize the database first to create the connection
            await db_manager.initialize()

            # Mock the validate_schema to fail first, then succeed
            call_count = 0

            async def mock_validate_schema(conn):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call fails with secure_tokens missing
                    raise DatabaseSchemaError(
                        "Required table 'secure_tokens' not found"
                    )
                # Second call after recovery should succeed
                pass

            with (
                patch.object(
                    db_manager, "_validate_schema", side_effect=mock_validate_schema
                ),
                patch.object(db_manager, "_ensure_schema_applied", return_value=None),
            ):
                # This should trigger recovery and succeed
                async with db_manager.get_connection() as conn:
                    await db_manager._validate_schema_with_recovery(conn)

                # Should have called validate_schema twice (fail, then succeed)
                assert call_count == 2

        finally:
            # Clean up temporary database
            Path(temp_db_path).unlink(missing_ok=True)

    async def test_validate_schema_with_recovery_other_error(self):
        """Test schema recovery with non-secure_tokens error."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            db_manager = DatabaseManager(temp_db_path)
            await db_manager.initialize()

            # Mock validate_schema to fail with different error
            async def mock_validate_schema(conn):
                raise DatabaseSchemaError(
                    "Different error not related to secure_tokens"
                )

            with (
                patch.object(
                    db_manager, "_validate_schema", side_effect=mock_validate_schema
                ),
                patch.object(db_manager, "_ensure_schema_applied", return_value=None),
                pytest.raises(
                    DatabaseConnectionError,
                    match="Connection failed: Different error not related to secure_tokens",
                ),
            ):
                # This should re-raise the original error since it's not secure_tokens related
                # But it gets wrapped in ConnectionError when get_connection catches it
                async with db_manager.get_connection() as conn:
                    await db_manager._validate_schema_with_recovery(conn)

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    async def test_validate_schema_with_recovery_recovery_fails(self):
        """Test schema recovery when recovery itself fails."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            db_manager = DatabaseManager(temp_db_path)

            # Mock validate_schema to always fail with secure_tokens error
            async def mock_validate_schema(conn):
                raise DatabaseSchemaError("Required table 'secure_tokens' not found")

            # Mock connection execute to fail during recovery
            with (
                patch.object(
                    db_manager, "_validate_schema", side_effect=mock_validate_schema
                ),
                patch.object(db_manager, "_ensure_schema_applied", return_value=None),
            ):
                async with db_manager.get_connection() as conn:
                    # Mock conn.execute to fail during recovery
                    conn.execute = AsyncMock(side_effect=Exception("Recovery failed"))

                    with pytest.raises(
                        DatabaseSchemaError, match="Schema recovery failed"
                    ):
                        await db_manager._validate_schema_with_recovery(conn)

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    async def test_database_manager_invalid_path(self):
        """Test DatabaseManager with invalid database path."""
        # Test with a path that uses invalid characters for filesystem
        import platform

        if platform.system() == "Windows":
            invalid_path = (
                "C:\\\\con\\invalid\\path\\database.db"  # CON is reserved on Windows
            )
        else:
            invalid_path = (
                "/dev/null/impossible/database.db"  # Can't create dir inside /dev/null
            )

        db_manager = DatabaseManager(invalid_path)

        # This should raise an error during initialization
        # The actual error could be NotADirectoryError, PermissionError, or wrapped DatabaseConnectionError
        with pytest.raises(
            (DatabaseConnectionError, NotADirectoryError, PermissionError)
        ):
            await db_manager.initialize()

    def test_database_manager_sqlite_url_parsing(self):
        """Test DatabaseManager with sqlite:/// URL parsing."""
        # Test sqlite URL parsing
        db_manager = DatabaseManager("sqlite:///./test_database.db")
        assert str(db_manager.database_path).endswith("test_database.db")

        # Test regular path
        db_manager2 = DatabaseManager("./another_test.db")
        assert str(db_manager2.database_path).endswith("another_test.db")

    @patch("shared_context_server.database.aiosqlite.connect")
    async def test_get_connection_wal_mode_failure(self, mock_connect):
        """Test database connection when WAL mode setting fails."""
        # Mock connection that fails WAL mode check
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = ("delete",)  # Not WAL mode
        mock_conn.execute.return_value = mock_cursor

        # Make connect return the mock connection (not a coroutine)
        async def mock_connect_func(*args, **kwargs):
            return mock_conn

        mock_connect.side_effect = mock_connect_func

        db_manager = DatabaseManager("test.db")

        # Should raise error when WAL mode is not enabled
        with pytest.raises(
            DatabaseConnectionError,
            match="Connection failed: PRAGMA application failed: Failed to enable WAL mode, got: delete",
        ):
            async with db_manager.get_connection():
                pass

    @patch("shared_context_server.database.aiosqlite.connect")
    async def test_get_connection_journal_mode_check_failure(self, mock_connect):
        """Test database connection when journal mode check returns None."""
        # Mock connection that returns None for journal mode check
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor

        # Make connect return the mock connection (not a coroutine)
        async def mock_connect_func(*args, **kwargs):
            return mock_conn

        mock_connect.side_effect = mock_connect_func

        db_manager = DatabaseManager("test.db")

        # Should raise error when journal mode check fails
        with pytest.raises(
            DatabaseConnectionError,
            match="Connection failed: PRAGMA application failed: Failed to check journal mode",
        ):
            async with db_manager.get_connection():
                pass

    async def test_load_schema_file_not_found(self):
        """Test schema file loading when file is not found."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            db_manager = DatabaseManager(temp_db_path)

            # Mock Path.exists to always return False
            with (
                patch("shared_context_server.database.Path.exists", return_value=False),
                pytest.raises(
                    DatabaseSchemaError,
                    match="Schema file not found in any of the following locations",
                ),
            ):
                db_manager._load_schema_file()

        finally:
            Path(temp_db_path).unlink(missing_ok=True)

    async def test_health_check_success(self, isolated_db):
        """Test health_check function returns healthy status with working database."""
        result = await health_check()

        # Basic structure validation
        assert "status" in result
        assert "timestamp" in result
        assert result["status"] == "healthy"

        # Should include database status fields
        expected_fields = ["database_initialized", "database_exists"]
        for field in expected_fields:
            assert field in result

        # Database should be working in test environment
        assert result["database_initialized"] is True
        assert result["database_exists"] is True

    async def test_cleanup_expired_data_error(self, isolated_db):
        """Test cleanup_expired_data with database errors."""
        # Patch execute_update to fail to test error handling
        with patch(
            "shared_context_server.database.execute_update"
        ) as mock_execute_update:
            mock_execute_update.side_effect = Exception("Database update failed")

            # Should handle exception gracefully and return empty stats
            result = await cleanup_expired_data()

            assert result["expired_memory"] == 0
            assert result["old_audit_logs"] == 0


class TestDatabaseConnectionEdgeCases:
    """Test database connection edge cases and error scenarios."""

    @patch("shared_context_server.database.aiosqlite.connect")
    async def test_connection_timeout_error(self, mock_connect):
        """Test database connection with timeout error."""

        # Mock connection to raise timeout error
        async def failing_connect(*args, **kwargs):
            raise ConnectionError("Connection timeout")

        mock_connect.side_effect = failing_connect

        db_manager = DatabaseManager("test.db")

        with pytest.raises(DatabaseConnectionError, match="Connection failed"):
            async with db_manager.get_connection():
                pass

    async def test_health_check_basic_query_failure(self, isolated_db):
        """Test health_check when basic query fails."""
        # Use real database but patch get_db_connection to return a broken connection
        with patch("shared_context_server.database.get_db_connection") as mock_get_db:
            # Mock database connection that fails basic query
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = None  # Returns None instead of (1,)
            mock_conn.execute.return_value = mock_cursor
            mock_get_db.return_value.__aenter__.return_value = mock_conn

            result = await health_check()

            assert result["status"] == "unhealthy"
            assert "Basic query failed" in result["error"]

    async def test_database_manager_connection_counting(self, isolated_db):
        """Test database manager connection counting."""
        db_manager = isolated_db.db_manager

        # Check initial connection count
        initial_stats = db_manager.get_stats()
        assert initial_stats["connection_count"] == 0

        # Open a connection and verify count increases
        async with db_manager.get_connection():
            stats_during = db_manager.get_stats()
            assert stats_during["connection_count"] == 1

        # After closing, count should decrease
        final_stats = db_manager.get_stats()
        assert final_stats["connection_count"] == 0

    def test_database_manager_stats(self, isolated_db):
        """Test database manager statistics collection."""
        db_manager = isolated_db.db_manager
        stats = db_manager.get_stats()

        assert "database_path" in stats
        assert "is_initialized" in stats
        assert "connection_count" in stats
        assert "database_exists" in stats
        assert "database_size_mb" in stats
        assert stats["database_exists"] is True
        assert stats["database_size_mb"] >= 0  # May be 0 for in-memory or small DBs

    def test_database_manager_stats_nonexistent_file(self):
        """Test database manager statistics for nonexistent database."""
        nonexistent_path = "/tmp/nonexistent_database.db"
        db_manager = DatabaseManager(nonexistent_path)
        stats = db_manager.get_stats()

        assert stats["database_exists"] is False
        assert stats["database_size_mb"] == 0
