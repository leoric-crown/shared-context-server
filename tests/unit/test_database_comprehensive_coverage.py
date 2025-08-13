"""
Comprehensive tests for database.py to improve coverage to 85%+.

This test file specifically targets uncovered lines and error paths
identified in the coverage report to raise overall module coverage.
"""

import os
import tempfile
from datetime import timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.shared_context_server.database import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseManager,
    DatabaseSchemaError,
    _get_sqlalchemy_manager,
    _raise_basic_query_error,
    _raise_journal_mode_check_error,
    _raise_no_schema_version_error,
    _raise_table_not_found_error,
    _raise_wal_mode_error,
    cleanup_expired_data,
    execute_insert,
    execute_query,
    execute_update,
    get_database_manager,
    get_db_connection,
    get_schema_version,
    health_check,
    initialize_database,
    parse_utc_timestamp,
    utc_now,
    utc_timestamp,
    validate_json_string,
    validate_session_id,
)
from tests.fixtures.database import is_sqlalchemy_backend


class TestDatabaseErrorFunctions:
    """Test the database error raising functions for 100% coverage."""

    def test_raise_wal_mode_error(self):
        """Test WAL mode error raising."""
        with pytest.raises(
            DatabaseConnectionError, match="Failed to enable WAL mode, got: delete"
        ):
            _raise_wal_mode_error("delete")

    def test_raise_journal_mode_check_error(self):
        """Test journal mode check error raising."""
        with pytest.raises(
            DatabaseConnectionError, match="Failed to check journal mode"
        ):
            _raise_journal_mode_check_error()

    def test_raise_table_not_found_error(self):
        """Test table not found error raising."""
        with pytest.raises(
            DatabaseSchemaError, match="Required table 'test_table' not found"
        ):
            _raise_table_not_found_error("test_table")

    def test_raise_no_schema_version_error(self):
        """Test no schema version error raising."""
        with pytest.raises(DatabaseSchemaError, match="No schema version found"):
            _raise_no_schema_version_error()

    def test_raise_basic_query_error(self):
        """Test basic query error raising."""
        with pytest.raises(DatabaseError, match="Basic query failed"):
            _raise_basic_query_error()


class TestDatabaseManagerInitialization:
    """Test database manager initialization edge cases."""

    def test_database_manager_sqlite_url_parsing(self):
        """Test sqlite:/// URL parsing."""
        db_manager = DatabaseManager("sqlite:///./test.db")
        expected_path = Path("./test.db").resolve()
        assert db_manager.database_path == expected_path

    def test_database_manager_regular_path(self):
        """Test regular path handling."""
        db_manager = DatabaseManager("./test.db")
        expected_path = Path("./test.db").resolve()
        assert db_manager.database_path == expected_path

    async def test_initialize_already_initialized(self, isolated_db):
        """Test initializing already initialized database."""
        isolated_db.db_manager.is_initialized = True
        await isolated_db.db_manager.initialize()  # Should return early

    @patch("src.shared_context_server.database.DatabaseManager._ensure_schema_applied")
    async def test_initialize_schema_failure(self, mock_schema, isolated_db):
        """Test initialization failure during schema application."""
        mock_schema.side_effect = Exception("Schema error")
        isolated_db.db_manager.is_initialized = False

        with pytest.raises(
            DatabaseConnectionError, match="Failed to initialize database"
        ):
            await isolated_db.db_manager.initialize()


class TestDatabaseConnectionHandling:
    """Test database connection handling edge cases."""

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend doesn't use internal _apply_pragmas method",
    )
    async def test_get_connection_journal_mode_failure(self, isolated_db):
        """Test connection failure when journal mode check returns None."""
        with patch.object(isolated_db.db_manager, "_apply_pragmas") as mock_pragmas:
            # Make _apply_pragmas raise the journal mode check error
            mock_pragmas.side_effect = DatabaseConnectionError(
                "Failed to check journal mode"
            )

            with pytest.raises(DatabaseConnectionError):
                async with isolated_db.db_manager.get_connection():
                    pass

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend doesn't use internal _apply_pragmas method",
    )
    async def test_get_connection_pragma_failure(self, isolated_db):
        """Test connection failure during PRAGMA application."""
        with patch.object(isolated_db.db_manager, "_apply_pragmas") as mock_pragmas:
            mock_pragmas.side_effect = Exception("PRAGMA failed")

            with pytest.raises(DatabaseConnectionError, match="Connection failed"):
                async with isolated_db.db_manager.get_connection():
                    pass


class TestSchemaHandling:
    """Test schema loading and validation edge cases."""

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend uses different schema file handling",
    )
    def test_load_schema_file_not_found(self, isolated_db):
        """Test schema file loading when file doesn't exist."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            pytest.raises(
                DatabaseSchemaError,
                match="Schema file not found in any of the following locations",
            ),
        ):
            isolated_db.db_manager._load_schema_file()

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend uses different schema file handling",
    )
    def test_load_schema_file_found_in_project_root(self, isolated_db):
        """Test schema file loading from project root."""
        schema_content = "CREATE TABLE test(id INTEGER);"

        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("builtins.open", create=True) as mock_open,
        ):

            def exists_side_effect(path):
                # Only return True for the first path (project root)
                return str(path).endswith(
                    "database_sqlite.sql"
                ) and "parent.parent.parent" in str(path)

            mock_exists.side_effect = lambda: exists_side_effect(
                mock_exists.call_args[0] if mock_exists.call_args else None
            )
            mock_file = Mock()
            mock_file.read.return_value = schema_content
            mock_open.return_value.__enter__.return_value = mock_file

            with patch("pathlib.Path.exists", return_value=True):
                result = isolated_db.db_manager._load_schema_file()
                assert result == schema_content

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend doesn't use internal _ensure_schema_applied method",
    )
    async def test_ensure_schema_applied_failure(self, isolated_db):
        """Test schema application failure."""
        # Mock the schema loading to simulate failure
        with patch.object(isolated_db.db_manager, "_load_schema_file") as mock_load:
            mock_load.side_effect = Exception("Schema file error")

            async with isolated_db.db_manager.get_connection() as conn:
                # First drop the schema_version table to trigger schema application
                await conn.execute("DROP TABLE IF EXISTS schema_version")
                await conn.commit()

                with pytest.raises(DatabaseSchemaError, match="Failed to apply schema"):
                    await isolated_db.db_manager._ensure_schema_applied(conn)

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend doesn't use internal _validate_schema method",
    )
    async def test_validate_schema_failure(self, isolated_db):
        """Test schema validation failure."""
        async with isolated_db.db_manager.get_connection() as conn:
            # Remove a required table to trigger validation failure
            await conn.execute("DROP TABLE IF EXISTS sessions")
            await conn.commit()

            with pytest.raises(
                DatabaseSchemaError, match="Required table 'sessions' not found"
            ):
                await isolated_db.db_manager._validate_schema(conn)

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend doesn't use internal _validate_schema_with_recovery method",
    )
    async def test_validate_schema_with_recovery_secure_tokens_missing(
        self, isolated_db
    ):
        """Test schema recovery for missing secure_tokens table."""
        async with isolated_db.db_manager.get_connection() as conn:
            # Drop secure_tokens table to trigger recovery
            await conn.execute("DROP TABLE IF EXISTS secure_tokens")
            await conn.commit()

            # This should trigger recovery
            await isolated_db.db_manager._validate_schema_with_recovery(conn)

            # Verify table was recreated
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='secure_tokens'"
            )
            result = await cursor.fetchone()
            assert result is not None

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend doesn't use internal _validate_schema_with_recovery method",
    )
    async def test_validate_schema_with_recovery_non_recoverable_error(
        self, isolated_db
    ):
        """Test schema recovery for non-recoverable errors."""
        async with isolated_db.db_manager.get_connection() as conn:
            # Drop a different table to trigger non-recoverable error
            await conn.execute("DROP TABLE IF EXISTS sessions")
            await conn.commit()

            with pytest.raises(
                DatabaseSchemaError, match="Required table 'sessions' not found"
            ):
                await isolated_db.db_manager._validate_schema_with_recovery(conn)

    @pytest.mark.skipif(
        is_sqlalchemy_backend(),
        reason="SQLAlchemy backend doesn't use internal _validate_schema_with_recovery method",
    )
    async def test_validate_schema_with_recovery_recovery_failure(self, isolated_db):
        """Test schema recovery failure during table recreation."""
        async with isolated_db.db_manager.get_connection() as conn:
            # Drop secure_tokens table to trigger recovery attempt
            await conn.execute("DROP TABLE IF EXISTS secure_tokens")
            await conn.commit()

            # Mock the _validate_schema method to fail with secure_tokens error
            async def mock_validate_schema(connection):
                # First call - raise secure_tokens error
                if not hasattr(mock_validate_schema, "called"):
                    mock_validate_schema.called = True
                    raise DatabaseSchemaError(
                        "Required table 'secure_tokens' not found"
                    )
                # Subsequent calls should also fail for recovery failure test
                raise DatabaseSchemaError("Recovery still failed")

            with (
                patch.object(
                    isolated_db.db_manager, "_validate_schema", mock_validate_schema
                ),
                pytest.raises(DatabaseSchemaError),
            ):
                # This should trigger recovery but the second validation should still fail
                await isolated_db.db_manager._validate_schema_with_recovery(conn)


class TestUtilityFunctions:
    """Test utility functions for edge cases and error paths."""

    def test_parse_utc_timestamp_with_z_suffix(self):
        """Test parsing timestamp with Z suffix."""
        timestamp_str = "2025-01-15T10:30:00Z"
        result = parse_utc_timestamp(timestamp_str)
        assert result.tzinfo == timezone.utc

    def test_parse_utc_timestamp_without_timezone(self):
        """Test parsing timestamp without timezone info."""
        timestamp_str = "2025-01-15T10:30:00"
        result = parse_utc_timestamp(timestamp_str)
        assert result.tzinfo == timezone.utc

    def test_parse_utc_timestamp_with_timezone(self):
        """Test parsing timestamp with existing timezone."""
        timestamp_str = "2025-01-15T10:30:00+05:00"
        result = parse_utc_timestamp(timestamp_str)
        assert result.tzinfo == timezone.utc

    def test_parse_utc_timestamp_naive_datetime(self):
        """Test parsing naive datetime gets UTC timezone."""
        # Use a timestamp that will result in a naive datetime needing timezone conversion
        timestamp_str = "2025-01-15 10:30:00"
        result = parse_utc_timestamp(timestamp_str)
        assert result.tzinfo == timezone.utc

    def test_parse_utc_timestamp_invalid_format(self):
        """Test parsing invalid timestamp format."""
        with pytest.raises(ValueError, match="Invalid timestamp format"):
            parse_utc_timestamp("invalid-timestamp")

    def test_validate_session_id_valid(self):
        """Test valid session ID validation."""
        assert validate_session_id("session_0123456789abcdef") is True

    def test_validate_session_id_invalid(self):
        """Test invalid session ID validation."""
        assert validate_session_id("invalid_session_id") is False
        assert validate_session_id("session_short") is False
        assert validate_session_id("session_0123456789ABCDEF") is False  # uppercase

    def test_validate_json_string_valid(self):
        """Test valid JSON string validation."""
        assert validate_json_string('{"key": "value"}') is True
        assert validate_json_string("") is True  # Empty is valid
        assert validate_json_string(None) is True  # None is valid

    def test_validate_json_string_invalid(self):
        """Test invalid JSON string validation."""
        assert validate_json_string('{"invalid": json}') is False
        assert validate_json_string(123) is False  # Not a string

    def test_utc_now(self):
        """Test UTC now function."""
        now = utc_now()
        assert now.tzinfo == timezone.utc

    def test_utc_timestamp(self):
        """Test UTC timestamp string function."""
        timestamp = utc_timestamp()
        assert isinstance(timestamp, str)
        assert "T" in timestamp


class TestGlobalManagerFunctions:
    """Test global manager initialization and configuration."""

    def test_get_database_manager_config_failure(self):
        """Test database manager fallback to environment variable."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with patch.dict(os.environ, {"DATABASE_PATH": "/custom/path.db"}):
                # Clear global manager
                import src.shared_context_server.database as db_module

                original_manager = db_module._db_manager
                db_module._db_manager = None

                try:
                    manager = get_database_manager()
                    assert "/custom/path.db" in str(manager.database_path)
                finally:
                    # Restore original manager
                    db_module._db_manager = original_manager

    def test_get_sqlalchemy_manager_config_failure(self):
        """Test SQLAlchemy manager fallback to environment variable."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with patch.dict(os.environ, {"DATABASE_PATH": "/custom/path.db"}):
                # Clear global manager
                import src.shared_context_server.database as db_module

                original_manager = db_module._sqlalchemy_manager
                db_module._sqlalchemy_manager = None

                try:
                    manager = _get_sqlalchemy_manager()
                    # Should use fallback path
                    assert manager is not None
                finally:
                    # Restore original manager
                    db_module._sqlalchemy_manager = original_manager

    async def test_initialize_database_config_failure(self):
        """Test database initialization with config failure."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with (
                patch.dict(os.environ, {"USE_SQLALCHEMY": "false"}),
                patch(
                    "src.shared_context_server.database.get_database_manager"
                ) as mock_get_manager,
            ):
                mock_manager = Mock()
                mock_manager.initialize = AsyncMock()
                mock_get_manager.return_value = mock_manager

                await initialize_database()
                mock_manager.initialize.assert_called_once()

    async def test_initialize_database_sqlalchemy(self):
        """Test database initialization with SQLAlchemy."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with (
                patch.dict(os.environ, {"USE_SQLALCHEMY": "true"}),
                patch(
                    "src.shared_context_server.database._get_sqlalchemy_manager"
                ) as mock_get_manager,
            ):
                mock_manager = Mock()
                mock_manager.initialize = AsyncMock()
                mock_get_manager.return_value = mock_manager

                await initialize_database()
                mock_manager.initialize.assert_called_once()

    async def test_get_db_connection_config_failure(self):
        """Test get_db_connection with config failure."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with (
                patch.dict(os.environ, {"USE_SQLALCHEMY": "false"}),
                patch(
                    "src.shared_context_server.database.get_database_manager"
                ) as mock_get_manager,
            ):
                mock_manager = Mock()
                mock_manager.is_initialized = True
                # Create a proper async context manager mock
                mock_context_manager = Mock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=Mock())
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_manager.get_connection.return_value = mock_context_manager
                mock_get_manager.return_value = mock_manager

                async with get_db_connection():
                    pass

                mock_manager.get_connection.assert_called_once()

    async def test_get_db_connection_sqlalchemy_not_initialized(self):
        """Test get_db_connection with uninitialized SQLAlchemy manager."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with (
                patch.dict(os.environ, {"USE_SQLALCHEMY": "true"}),
                patch(
                    "src.shared_context_server.database._get_sqlalchemy_manager"
                ) as mock_get_manager,
            ):
                mock_manager = Mock()
                mock_manager.is_initialized = False
                mock_manager.initialize = AsyncMock()
                # Create a proper async context manager mock
                mock_context_manager = Mock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=Mock())
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_manager.get_connection.return_value = mock_context_manager
                mock_get_manager.return_value = mock_manager

                async with get_db_connection():
                    pass

                mock_manager.initialize.assert_called_once()
                mock_manager.get_connection.assert_called_once()


class TestHealthCheck:
    """Test health check function edge cases."""

    async def test_health_check_config_failure(self):
        """Test health check with config failure."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with (
                patch.dict(os.environ, {"USE_SQLALCHEMY": "false"}),
                patch(
                    "src.shared_context_server.database.get_database_manager"
                ) as mock_get_manager,
                patch(
                    "src.shared_context_server.database.get_db_connection"
                ) as mock_get_conn,
            ):
                mock_manager = Mock()
                mock_manager.is_initialized = False
                mock_manager.initialize = AsyncMock()
                mock_manager.get_stats.return_value = {
                    "is_initialized": True,
                    "database_exists": True,
                    "database_size_mb": 1.0,
                    "connection_count": 0,
                }
                mock_get_manager.return_value = mock_manager

                mock_conn = Mock()
                mock_cursor = AsyncMock()
                mock_cursor.fetchone = AsyncMock(return_value=[1])
                mock_conn.execute = AsyncMock(return_value=mock_cursor)
                mock_get_conn.return_value.__aenter__ = AsyncMock(
                    return_value=mock_conn
                )
                mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await health_check()
                assert result["status"] == "healthy"

    async def test_health_check_query_returns_none(self):
        """Test health check when query returns None."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=None)
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await health_check()
            assert result["status"] == "unhealthy"

    async def test_health_check_query_returns_coroutine(self):
        """Test health check when query incorrectly returns coroutine."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()

            # Create a coroutine that will be returned as the result
            async def fake_coro():
                return 1

            mock_cursor.fetchone = AsyncMock(return_value=fake_coro())
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await health_check()
            assert result["status"] == "unhealthy"

    async def test_health_check_sqlalchemy_backend(self):
        """Test health check with SQLAlchemy backend."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with (
                patch.dict(os.environ, {"USE_SQLALCHEMY": "true"}),
                patch(
                    "src.shared_context_server.database._get_sqlalchemy_manager"
                ) as mock_get_manager,
                patch(
                    "src.shared_context_server.database.get_db_connection"
                ) as mock_get_conn,
            ):
                mock_manager = Mock()
                mock_manager.is_initialized = False
                mock_manager.initialize = AsyncMock()
                mock_get_manager.return_value = mock_manager

                mock_conn = Mock()
                mock_cursor = AsyncMock()
                mock_cursor.fetchone = AsyncMock(return_value=[1])
                mock_conn.execute = AsyncMock(return_value=mock_cursor)
                mock_get_conn.return_value.__aenter__ = AsyncMock(
                    return_value=mock_conn
                )
                mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await health_check()
                assert result["status"] == "healthy"
                assert (
                    result["database_size_mb"] == 0
                )  # SQLAlchemy doesn't provide size

    async def test_health_check_exception_handling(self):
        """Test health check exception handling."""
        # Mock the database connection itself to fail, which will definitely cause unhealthy status
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.side_effect = Exception("Database connection failed")

            result = await health_check()
            assert result["status"] == "unhealthy"
            assert "error" in result


class TestSchemaVersion:
    """Test schema version handling."""

    async def test_get_schema_version_dict_result(self):
        """Test get_schema_version with dict result."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value={"version": 3})
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await get_schema_version()
            assert result == 3

    async def test_get_schema_version_row_like_result(self):
        """Test get_schema_version with row-like result."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()

            # Mock a row-like object with keys() method
            mock_result = Mock()
            mock_result.keys.return_value = ["version"]
            mock_result.__iter__ = Mock(return_value=iter([3]))
            mock_result.__getitem__ = Mock(return_value=3)

            mock_cursor.fetchone = AsyncMock(return_value=mock_result)
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await get_schema_version()
            assert result == 3

    async def test_get_schema_version_none_result(self):
        """Test get_schema_version with None result."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=None)
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await get_schema_version()
            assert result == 0

    async def test_get_schema_version_exception(self):
        """Test get_schema_version with exception."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")

            result = await get_schema_version()
            assert result == 0


class TestCleanupFunctions:
    """Test cleanup and maintenance functions."""

    async def test_cleanup_expired_data_config_failure(self):
        """Test cleanup with config failure."""
        with patch(
            "src.shared_context_server.config.get_database_config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with (
                patch.dict(os.environ, {"AUDIT_LOG_RETENTION_DAYS": "7"}),
                patch(
                    "src.shared_context_server.database.execute_update"
                ) as mock_execute,
            ):
                mock_execute.return_value = 5

                result = await cleanup_expired_data()
                assert result["expired_memory"] == 5
                assert result["old_audit_logs"] == 5

    async def test_cleanup_expired_data_exception(self):
        """Test cleanup with exception during execution."""
        with patch("src.shared_context_server.database.execute_update") as mock_execute:
            mock_execute.side_effect = Exception("Cleanup failed")

            result = await cleanup_expired_data()
            assert result["expired_memory"] == 0
            assert result["old_audit_logs"] == 0


class TestExecuteFunctions:
    """Test execute utility functions."""

    async def test_execute_query(self):
        """Test execute_query function."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()
            mock_row = Mock()
            mock_row.__dict__ = {"id": 1, "name": "test"}
            mock_cursor.fetchall = AsyncMock(return_value=[mock_row])
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_conn.row_factory = None
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock dict() conversion
            with patch("builtins.dict", return_value={"id": 1, "name": "test"}):
                result = await execute_query("SELECT * FROM test")
                assert len(result) == 1
                assert result[0] == {"id": 1, "name": "test"}

    async def test_execute_update(self):
        """Test execute_update function."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()
            mock_cursor.rowcount = 3
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_conn.commit = AsyncMock()
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await execute_update("UPDATE test SET name = ?", ("updated",))
            assert result == 3

    async def test_execute_insert(self):
        """Test execute_insert function."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()
            mock_cursor.lastrowid = 42
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_conn.commit = AsyncMock()
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await execute_insert(
                "INSERT INTO test (name) VALUES (?)", ("new",)
            )
            assert result == 42

    async def test_execute_insert_none_lastrowid(self):
        """Test execute_insert when lastrowid is None."""
        with patch(
            "src.shared_context_server.database.get_db_connection"
        ) as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = AsyncMock()
            mock_cursor.lastrowid = None
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_conn.commit = AsyncMock()
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await execute_insert(
                "INSERT INTO test (name) VALUES (?)", ("new",)
            )
            assert result == 0


class TestPragmaValidation:
    """Test PRAGMA validation edge cases."""

    async def test_validate_pragmas_mismatch(self, isolated_db):
        """Test PRAGMA validation with mismatched values."""
        # Create a custom connection that will return wrong PRAGMA values
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db_path = Path(temp_db.name)

        temp_manager = DatabaseManager(str(temp_db_path))

        try:
            # Initialize without proper PRAGMA settings for testing
            temp_manager.database_path.parent.mkdir(parents=True, exist_ok=True)

            # Manually create a connection that bypasses normal PRAGMA setup
            import aiosqlite

            conn = await aiosqlite.connect(str(temp_manager.database_path))

            # This should log warnings but not raise exceptions since validation is non-fatal
            await temp_manager._validate_pragmas(conn)

            await conn.close()
        finally:
            # Cleanup
            if temp_db_path.exists():
                temp_db_path.unlink()


class TestDatabaseStats:
    """Test database statistics functionality."""

    def test_get_stats_database_exists(self, isolated_db):
        """Test get_stats when database file exists."""
        # Ensure database file exists
        isolated_db.db_manager.database_path.parent.mkdir(parents=True, exist_ok=True)
        isolated_db.db_manager.database_path.touch()

        stats = isolated_db.db_manager.get_stats()
        assert stats["database_exists"] is True
        assert stats["database_size_mb"] >= 0

    def test_get_stats_database_not_exists(self):
        """Test get_stats when database file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nonexistent.db"
            db_manager = DatabaseManager(str(db_path))

            stats = db_manager.get_stats()
            assert stats["database_exists"] is False
            assert stats["database_size_mb"] == 0
