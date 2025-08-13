"""
Core multi-database functionality tests.

Tests the essential functionality of the multi-database support without
requiring actual database drivers or complex setup.
"""

from unittest.mock import MagicMock, patch

import pytest

from shared_context_server.database_sqlalchemy import (
    SimpleSQLAlchemyManager,
    SQLAlchemyConnectionWrapper,
)

pytestmark = pytest.mark.sqlalchemy


class TestMultiDatabaseCore:
    """Test core multi-database functionality."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_sqlite_url_detection_and_config(self, mock_create_engine):
        """Test SQLite URL detection and configuration."""
        mock_create_engine.return_value = MagicMock()

        manager = SimpleSQLAlchemyManager("sqlite+aiosqlite:///./test.db")

        assert manager.db_type == "sqlite"

        # Verify config is correct for SQLite
        config = manager._get_engine_config()
        assert config["pool_pre_ping"] is True
        assert config["pool_recycle"] == 3600
        assert "pool_size" not in config  # SQLite doesn't use traditional pools

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_url_detection_and_config(self, mock_create_engine):
        """Test PostgreSQL URL detection and configuration."""
        mock_create_engine.return_value = MagicMock()

        manager = SimpleSQLAlchemyManager(
            "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        )

        assert manager.db_type == "postgresql"

        # Verify PostgreSQL-specific config
        config = manager._get_engine_config()
        assert config["pool_size"] == 20
        assert config["max_overflow"] == 30
        assert config["pool_recycle"] == 3600
        assert config["pool_pre_ping"] is True

        connect_args = config["connect_args"]
        assert connect_args["prepared_statement_cache_size"] == 500
        assert connect_args["server_settings"]["jit"] == "off"
        assert (
            connect_args["server_settings"]["application_name"] == "shared_context_mcp"
        )

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_url_detection_and_config(self, mock_create_engine):
        """Test MySQL URL detection and configuration."""
        mock_create_engine.return_value = MagicMock()

        manager = SimpleSQLAlchemyManager(
            "mysql+aiomysql://user:pass@localhost:3306/testdb"
        )

        assert manager.db_type == "mysql"

        # Verify MySQL-specific config
        config = manager._get_engine_config()
        assert config["pool_size"] == 10
        assert config["max_overflow"] == 20
        assert config["pool_recycle"] == 3600  # Important for MySQL timeout
        assert config["pool_pre_ping"] is True

        connect_args = config["connect_args"]
        assert connect_args["charset"] == "utf8mb4"
        assert connect_args["autocommit"] is False
        assert connect_args["init_command"] == "SET sql_mode='STRICT_TRANS_TABLES'"

    def test_mysql_query_translation(self):
        """Test MySQL query translation for key column."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Test INSERT query translation
        query = "INSERT INTO agent_memory (agent_id, session_id, key, value) VALUES (?, ?, ?, ?)"
        params = ("agent1", "session1", "test_key", "test_value")

        converted_query, named_params = wrapper._convert_params(query, params)

        # Should translate 'key' to 'key_name' for MySQL
        assert "key_name" in converted_query
        assert " key," not in converted_query
        assert named_params == {
            "param1": "agent1",
            "param2": "session1",
            "param3": "test_key",
            "param4": "test_value",
        }

    def test_postgresql_query_no_translation(self):
        """Test PostgreSQL queries are not modified."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "postgresql")

        # PostgreSQL should not modify queries
        query = "SELECT * FROM agent_memory WHERE key = ?"
        params = ("test_key",)

        converted_query, named_params = wrapper._convert_params(query, params)

        # Should only change ? to named parameters, no column changes
        assert "key" in converted_query
        assert "key_name" not in converted_query
        assert converted_query == "SELECT * FROM agent_memory WHERE key = :param1"
        assert named_params == {"param1": "test_key"}

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_schema_file_selection(self, mock_create_engine):
        """Test that correct schema files are selected."""
        mock_create_engine.return_value = MagicMock()

        # SQLite
        sqlite_manager = SimpleSQLAlchemyManager("sqlite+aiosqlite:///./test.db")
        assert sqlite_manager._get_schema_file_path().name == "database_sqlite.sql"

        # PostgreSQL
        pg_manager = SimpleSQLAlchemyManager(
            "postgresql+asyncpg://user:pass@localhost:5432/db"
        )
        assert pg_manager._get_schema_file_path().name == "database_postgresql.sql"

        # MySQL
        mysql_manager = SimpleSQLAlchemyManager(
            "mysql+aiomysql://user:pass@localhost:3306/db"
        )
        assert mysql_manager._get_schema_file_path().name == "database_mysql.sql"

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_schema_files_exist(self, mock_create_engine):
        """Test that required schema files exist."""
        mock_create_engine.return_value = MagicMock()

        # All database types should have their schema files
        for url, expected_file in [
            ("sqlite+aiosqlite:///./test.db", "database_sqlite.sql"),
            (
                "postgresql+asyncpg://user:pass@localhost:5432/db",
                "database_postgresql.sql",
            ),
            ("mysql+aiomysql://user:pass@localhost:3306/db", "database_mysql.sql"),
        ]:
            manager = SimpleSQLAlchemyManager(url)
            schema_path = manager._get_schema_file_path()
            assert schema_path.exists(), f"Schema file {expected_file} does not exist"

    def test_case_insensitive_url_detection(self):
        """Test that URL detection is case insensitive."""
        with patch(
            "shared_context_server.database_sqlalchemy.create_async_engine"
        ) as mock_create_engine:
            mock_create_engine.return_value = MagicMock()

            # Test various case combinations
            test_cases = [
                ("SQLITE+AIOSQLITE:///./test.db", "sqlite"),
                ("PostgreSQL+AsyncPG://user:pass@localhost:5432/db", "postgresql"),
                ("MySQL+AIOMYSQL://user:pass@localhost:3306/db", "mysql"),
                ("sqlite+AIOSQLITE:///./test.db", "sqlite"),  # Mixed case
            ]

            for url, expected_type in test_cases:
                manager = SimpleSQLAlchemyManager(url)
                assert manager.db_type == expected_type

    def test_unsupported_database_types(self):
        """Test that unsupported database types raise appropriate errors."""
        unsupported_urls = [
            "oracle://user:pass@localhost:1521/db",
            "mssql://user:pass@localhost:1433/db",
            "sqlite:///:memory:",  # Wrong driver
            "postgresql://user:pass@localhost:5432/db",  # Wrong driver
            "mysql://user:pass@localhost:3306/db",  # Wrong driver
            "invalid_format",
            "",
        ]

        with patch("shared_context_server.database_sqlalchemy.create_async_engine"):
            for url in unsupported_urls:
                with pytest.raises(ValueError, match="Unsupported database URL"):
                    SimpleSQLAlchemyManager(url)

    def test_parameter_binding_consistency(self):
        """Test that parameter binding works consistently across databases."""
        test_queries = [
            ("SELECT * FROM sessions WHERE id = ?", ("session1",)),
            (
                "INSERT INTO messages (session_id, sender, content) VALUES (?, ?, ?)",
                ("session1", "agent1", "hello"),
            ),
            (
                "UPDATE sessions SET purpose = ? WHERE id = ?",
                ("new_purpose", "session1"),
            ),
        ]

        for db_type in ["sqlite", "postgresql", "mysql"]:
            engine = MagicMock()
            conn = MagicMock()
            wrapper = SQLAlchemyConnectionWrapper(engine, conn, db_type)

            for query, params in test_queries:
                converted_query, named_params = wrapper._convert_params(query, params)

                # All should convert to named parameters
                assert "?" not in converted_query
                assert ":param1" in converted_query
                assert len(named_params) == len(params)

                # Verify parameter values are correct
                for i, param_value in enumerate(params):
                    assert named_params[f"param{i + 1}"] == param_value


class TestSchemaContent:
    """Test schema file content validation."""

    def test_postgresql_schema_content(self):
        """Test PostgreSQL schema contains expected elements."""
        from pathlib import Path

        current_dir = Path(__file__).parent.parent
        schema_path = current_dir / "database_postgresql.sql"

        assert schema_path.exists(), "PostgreSQL schema file should exist"

        content = schema_path.read_text()

        # Check PostgreSQL-specific elements
        assert "SERIAL PRIMARY KEY" in content
        assert "BIGSERIAL PRIMARY KEY" in content
        assert "JSONB" in content
        assert "TIMESTAMPTZ" in content
        assert "CREATE OR REPLACE FUNCTION" in content
        assert "USING GIN" in content  # JSONB indexes

    def test_mysql_schema_content(self):
        """Test MySQL schema contains expected elements."""
        from pathlib import Path

        current_dir = Path(__file__).parent.parent
        schema_path = current_dir / "database_mysql.sql"

        assert schema_path.exists(), "MySQL schema file should exist"

        content = schema_path.read_text()

        # Check MySQL-specific elements
        assert "AUTO_INCREMENT PRIMARY KEY" in content
        assert "ENGINE=InnoDB" in content
        assert "DEFAULT CHARSET=utf8mb4" in content
        assert "COLLATE=utf8mb4_unicode_ci" in content
        assert "JSON" in content
        assert "key_name" in content  # MySQL uses key_name instead of key
        assert "ENUM(" in content

    def test_schema_version_consistency(self):
        """Test that all schema files reference the same version."""
        from pathlib import Path

        current_dir = Path(__file__).parent.parent

        # Read all schema files
        sqlite_schema = (current_dir / "database_sqlite.sql").read_text()
        pg_schema = (current_dir / "database_postgresql.sql").read_text()
        mysql_schema = (current_dir / "database_mysql.sql").read_text()

        # All should reference schema version 3 (consistent with current system)
        for schema_content, db_type in [
            (sqlite_schema, "SQLite"),
            (pg_schema, "PostgreSQL"),
            (mysql_schema, "MySQL"),
        ]:
            assert "schema_version" in schema_content, (
                f"{db_type} schema should have version table"
            )
            # Each schema should insert/update version 3
            assert "VALUES (3," in schema_content, (
                f"{db_type} schema should reference version 3"
            )
