"""
Database backend switching and feature flag tests.

Tests the ability to switch between different database backends and ensure
proper fallback behavior when USE_SQLALCHEMY feature flag is toggled.
"""

import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from shared_context_server.database import get_db_connection
from shared_context_server.database_sqlalchemy import SimpleSQLAlchemyManager


@contextmanager
def isolated_database_backend(use_sqlalchemy: bool, test_name: str = "test"):
    """Context manager that provides isolated database backend for testing."""
    import tempfile

    import shared_context_server.database as db_module

    # Store original state
    original_db_manager = getattr(db_module, "_db_manager", None)
    original_sqlalchemy_manager = getattr(db_module, "_sqlalchemy_manager", None)

    # Create a temporary database file for this test
    with tempfile.NamedTemporaryFile(
        suffix=f"_{test_name}.db", delete=False
    ) as temp_db:
        temp_db_path = temp_db.name

    try:
        # Clear global state
        db_module._db_manager = None
        db_module._sqlalchemy_manager = None

        # Set environment with isolated database path
        env_vars = {
            "USE_SQLALCHEMY": "true" if use_sqlalchemy else "false",
            "DATABASE_PATH": temp_db_path,
        }

        with patch.dict(os.environ, env_vars):
            yield
    finally:
        # Restore original state
        db_module._db_manager = original_db_manager
        db_module._sqlalchemy_manager = original_sqlalchemy_manager

        # Clean up temporary database file
        from contextlib import suppress
        from pathlib import Path

        with suppress(OSError):
            Path(temp_db_path).unlink()


@pytest.fixture
def clean_database_state():
    """Pytest fixture that ensures clean database state for each test."""
    import shared_context_server.database as db_module

    # Store original state
    original_db_manager = getattr(db_module, "_db_manager", None)
    original_sqlalchemy_manager = getattr(db_module, "_sqlalchemy_manager", None)

    # Clear state before test
    db_module._db_manager = None
    db_module._sqlalchemy_manager = None

    yield

    # Restore state after test
    db_module._db_manager = original_db_manager
    db_module._sqlalchemy_manager = original_sqlalchemy_manager


class TestBackendSwitching:
    """Test database backend switching functionality."""

    @pytest.mark.asyncio
    async def test_feature_flag_rollback_to_aiosqlite(self, clean_database_state):
        """Test that USE_SQLALCHEMY=false rolls back to aiosqlite backend."""
        # Test with feature flag disabled - should use aiosqlite backend
        with isolated_database_backend(
            use_sqlalchemy=False, test_name="aiosqlite_test"
        ):
            async with get_db_connection() as conn:
                # Should be using aiosqlite backend
                assert hasattr(conn, "execute")
                assert hasattr(conn, "commit")

                # Test that it's not the SQLAlchemy wrapper
                from shared_context_server.database_sqlalchemy import (
                    SQLAlchemyConnectionWrapper,
                )

                assert not isinstance(conn, SQLAlchemyConnectionWrapper)

                # Test basic operation
                await conn.execute("DROP TABLE IF EXISTS test_table_aiosqlite")
                await conn.execute(
                    "CREATE TABLE test_table_aiosqlite (id INTEGER PRIMARY KEY, name TEXT)"
                )
                await conn.commit()

                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table_aiosqlite'"
                )
                row = await cursor.fetchone()
                assert row is not None
                assert row[0] == "test_table_aiosqlite"

    def test_database_url_parsing_sqlite(self):
        """Test database URL parsing for different SQLite formats."""
        # Test file path format
        manager = SimpleSQLAlchemyManager("sqlite+aiosqlite:///./test.db")
        assert manager.db_type == "sqlite"

        # Test absolute path format
        manager = SimpleSQLAlchemyManager("sqlite+aiosqlite:////tmp/test.db")
        assert manager.db_type == "sqlite"

        # Test memory database
        manager = SimpleSQLAlchemyManager("sqlite+aiosqlite:///:memory:")
        assert manager.db_type == "sqlite"

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_database_url_parsing_postgresql(self, mock_create_engine):
        """Test database URL parsing for PostgreSQL formats."""
        mock_create_engine.return_value = MagicMock()

        test_urls = [
            "postgresql+asyncpg://user:pass@localhost:5432/dbname",
            "postgresql+asyncpg://user@localhost/dbname",
            "postgresql+asyncpg://localhost/dbname",
            "postgresql+asyncpg:///dbname",
        ]

        for url in test_urls:
            manager = SimpleSQLAlchemyManager(url)
            assert manager.db_type == "postgresql"

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_database_url_parsing_mysql(self, mock_create_engine):
        """Test database URL parsing for MySQL formats."""
        mock_create_engine.return_value = MagicMock()

        test_urls = [
            "mysql+aiomysql://user:pass@localhost:3306/dbname",
            "mysql+aiomysql://user@localhost/dbname",
            "mysql+aiomysql://localhost/dbname",
        ]

        for url in test_urls:
            manager = SimpleSQLAlchemyManager(url)
            assert manager.db_type == "mysql"

    def test_unsupported_database_urls(self):
        """Test that unsupported database URLs raise appropriate errors."""
        unsupported_urls = [
            "oracle://user:pass@localhost:1521/dbname",
            "mssql://user:pass@localhost:1433/dbname",
            "sqlite:///:memory:",  # Wrong driver
            "postgresql://user:pass@localhost:5432/dbname",  # Wrong driver
            "mysql://user:pass@localhost:3306/dbname",  # Wrong driver
            "invalid_url",
        ]

        for url in unsupported_urls:
            with pytest.raises(ValueError, match="Unsupported database URL"):
                SimpleSQLAlchemyManager(url)

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_schema_file_selection_by_database_type(self, mock_create_engine):
        """Test that correct schema files are selected based on database type."""
        mock_create_engine.return_value = MagicMock()

        # Test SQLite
        sqlite_manager = SimpleSQLAlchemyManager("sqlite+aiosqlite:///./test.db")
        sqlite_schema_path = sqlite_manager._get_schema_file_path()
        assert sqlite_schema_path.name == "database_sqlite.sql"

        # Test PostgreSQL
        pg_manager = SimpleSQLAlchemyManager(
            "postgresql+asyncpg://user:pass@localhost:5432/db"
        )
        pg_schema_path = pg_manager._get_schema_file_path()
        assert pg_schema_path.name == "database_postgresql.sql"

        # Test MySQL
        mysql_manager = SimpleSQLAlchemyManager(
            "mysql+aiomysql://user:pass@localhost:3306/db"
        )
        mysql_schema_path = mysql_manager._get_schema_file_path()
        assert mysql_schema_path.name == "database_mysql.sql"

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_engine_configuration_per_database(self, mock_create_engine):
        """Test that each database type gets appropriate engine configuration."""
        mock_create_engine.return_value = MagicMock()

        # Test SQLite config
        sqlite_manager = SimpleSQLAlchemyManager("sqlite+aiosqlite:///./test.db")
        sqlite_config = sqlite_manager._get_engine_config()
        assert sqlite_config["pool_pre_ping"] is True
        assert (
            "pool_size" not in sqlite_config
        )  # SQLite doesn't use connection pools the same way

        # Test PostgreSQL config
        pg_manager = SimpleSQLAlchemyManager(
            "postgresql+asyncpg://user:pass@localhost:5432/db"
        )
        pg_config = pg_manager._get_engine_config()
        assert pg_config["pool_size"] == 20
        assert pg_config["max_overflow"] == 30
        assert "prepared_statement_cache_size" in pg_config["connect_args"]

        # Test MySQL config
        mysql_manager = SimpleSQLAlchemyManager(
            "mysql+aiomysql://user:pass@localhost:3306/db"
        )
        mysql_config = mysql_manager._get_engine_config()
        assert mysql_config["pool_size"] == 10
        assert (
            mysql_config["pool_recycle"] == 3600
        )  # Important for MySQL timeout handling
        assert mysql_config["connect_args"]["charset"] == "utf8mb4"

    @pytest.mark.asyncio
    async def test_graceful_backend_switching_during_operation(
        self, clean_database_state
    ):
        """Test graceful switching between backends without data loss."""
        # This test demonstrates that both backends can work on the same database
        # Use a shared temporary database for this specific test
        import tempfile

        import shared_context_server.database as db_module

        with tempfile.NamedTemporaryFile(
            suffix="_switching_test.db", delete=False
        ) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Start with aiosqlite backend
            db_module._db_manager = None
            db_module._sqlalchemy_manager = None

            env_vars = {"USE_SQLALCHEMY": "false", "DATABASE_PATH": temp_db_path}

            with patch.dict(os.environ, env_vars):
                async with get_db_connection() as conn:
                    # Create test data with aiosqlite
                    await conn.execute("DROP TABLE IF EXISTS test_switching")
                    await conn.execute("""
                        CREATE TABLE test_switching (
                            id INTEGER PRIMARY KEY,
                            data TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    await conn.execute(
                        "INSERT INTO test_switching (data) VALUES (?)",
                        ("aiosqlite_data",),
                    )
                    await conn.commit()

            # Switch to SQLAlchemy backend
            db_module._db_manager = None
            db_module._sqlalchemy_manager = None

            env_vars["USE_SQLALCHEMY"] = "true"

            with patch.dict(os.environ, env_vars):
                async with get_db_connection() as conn:
                    # Verify data exists and add more data with SQLAlchemy
                    cursor = await conn.execute(
                        "SELECT data FROM test_switching WHERE data = ?",
                        ("aiosqlite_data",),
                    )
                    row = await cursor.fetchone()
                    assert row is not None
                    # SQLAlchemy wrapper should provide dict access
                    if hasattr(row, "keys"):
                        assert row["data"] == "aiosqlite_data"
                    else:
                        assert row[0] == "aiosqlite_data"

                    # Add new data with SQLAlchemy backend
                    await conn.execute(
                        "INSERT INTO test_switching (data) VALUES (?)",
                        ("sqlalchemy_data",),
                    )
                    await conn.commit()

            # Switch back to aiosqlite backend
            db_module._db_manager = None
            db_module._sqlalchemy_manager = None

            env_vars["USE_SQLALCHEMY"] = "false"

            with patch.dict(os.environ, env_vars):
                async with get_db_connection() as conn:
                    # Verify both pieces of data exist
                    cursor = await conn.execute(
                        "SELECT COUNT(*) as count FROM test_switching"
                    )
                    row = await cursor.fetchone()
                    assert row[0] == 2  # Both records should exist

                    cursor = await conn.execute(
                        "SELECT data FROM test_switching ORDER BY id"
                    )
                    rows = await cursor.fetchall()
                    assert len(rows) == 2
                    assert rows[0][0] == "aiosqlite_data"
                    assert rows[1][0] == "sqlalchemy_data"

        finally:
            # Clean up temporary database file
            from contextlib import suppress
            from pathlib import Path

            with suppress(OSError):
                Path(temp_db_path).unlink()

    @pytest.mark.asyncio
    async def test_configuration_validation(self):
        """Test validation of database configuration parameters."""
        # Test that invalid configuration is caught early
        with pytest.raises(ValueError):
            SimpleSQLAlchemyManager("")  # Empty URL

        with pytest.raises(ValueError):
            SimpleSQLAlchemyManager("not_a_valid_url")  # Invalid format

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_database_type_detection_edge_cases(self, mock_create_engine):
        """Test database type detection with edge cases."""
        mock_create_engine.return_value = MagicMock()

        # Test case sensitivity
        manager = SimpleSQLAlchemyManager("SQLITE+AIOSQLITE:///./test.db")
        assert manager.db_type == "sqlite"  # Should be case-insensitive

        # Test URL with query parameters
        manager = SimpleSQLAlchemyManager(
            "postgresql+asyncpg://user:pass@localhost:5432/db?sslmode=require"
        )
        assert manager.db_type == "postgresql"

        # Test URL with special characters in password
        manager = SimpleSQLAlchemyManager(
            "mysql+aiomysql://user:p%40ssw%40rd@localhost:3306/db"
        )
        assert manager.db_type == "mysql"


class TestBackendCompatibility:
    """Test compatibility between different database backends."""

    @pytest.mark.asyncio
    async def test_parameter_binding_compatibility(self):
        """Test that parameter binding works consistently across backends."""
        test_cases = [
            ("SELECT * FROM test WHERE id = ?", ("test_id",)),
            (
                "INSERT INTO test (name, value) VALUES (?, ?)",
                ("test_name", "test_value"),
            ),
            ("UPDATE test SET value = ? WHERE name = ?", ("new_value", "test_name")),
            ("DELETE FROM test WHERE id = ? AND name = ?", ("test_id", "test_name")),
        ]

        for query, params in test_cases:
            from unittest.mock import MagicMock

            from shared_context_server.database_sqlalchemy import (
                SQLAlchemyConnectionWrapper,
            )

            wrapper = SQLAlchemyConnectionWrapper(MagicMock(), MagicMock(), "sqlite")
            converted_query, named_params = wrapper._convert_params(query, params)

            # Should have named parameters
            assert ":param1" in converted_query
            assert len(named_params) == len(params)
            assert all(f"param{i + 1}" in named_params for i in range(len(params)))

    def test_row_access_pattern_compatibility(self):
        """Test that row access patterns work consistently across backends."""
        from shared_context_server.database_sqlalchemy import CompatibleRow

        # Test data that would come from any database
        test_data = {"id": 1, "name": "test_name", "value": "test_value"}
        row = CompatibleRow(test_data)

        # Test all access patterns that existing code uses
        assert row[0] == 1  # Index access
        assert row["id"] == 1  # Key access
        assert row["name"] == "test_name"
        assert len(row) == 3
        assert "id" in row
        assert 0 in row

        # Test iteration
        values = list(row)
        assert values == [1, "test_name", "test_value"]

        # Test dict-like access
        assert list(row.keys()) == ["id", "name", "value"]
        assert list(row.values()) == [1, "test_name", "test_value"]
