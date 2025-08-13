"""
MySQL-specific database tests.

Tests MySQL dialect differences, connection handling, and schema features
that are unique to MySQL (AUTO_INCREMENT, JSON, ENUM, InnoDB, etc.).
"""

import os
from unittest.mock import patch

import pytest

from shared_context_server.database_sqlalchemy import SimpleSQLAlchemyManager


class TestMySQLBasics:
    """Test MySQL-specific database functionality."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_url_detection(self, mock_create_engine):
        """Test MySQL URL detection in SimpleSQLAlchemyManager."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        assert manager.db_type == "mysql"
        assert manager.database_url == url

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_engine_config(self, mock_create_engine):
        """Test MySQL-specific engine configuration."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        config = manager._get_engine_config()

        # Check MySQL-specific settings
        assert config["pool_size"] == 10
        assert config["max_overflow"] == 20
        assert config["pool_recycle"] == 3600  # Handle 8-hour timeout
        assert config["pool_pre_ping"] is True

        # Check MySQL connection args
        connect_args = config["connect_args"]
        assert connect_args["charset"] == "utf8mb4"
        assert connect_args["autocommit"] is False
        assert connect_args["init_command"] == "SET sql_mode='STRICT_TRANS_TABLES'"

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_schema_file_path(self, mock_create_engine):
        """Test MySQL schema file path resolution."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()

        assert schema_path.name == "database_mysql.sql"
        assert schema_path.exists()

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_mysql_schema_loading(self, mock_create_engine):
        """Test loading of MySQL schema file."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_content = await manager._load_schema_file()

        # Check for MySQL-specific elements
        assert "AUTO_INCREMENT PRIMARY KEY" in schema_content
        assert "BIGINT AUTO_INCREMENT PRIMARY KEY" in schema_content
        assert "ENGINE=InnoDB" in schema_content
        assert "DEFAULT CHARSET=utf8mb4" in schema_content
        assert "COLLATE=utf8mb4_unicode_ci" in schema_content
        assert "JSON" in schema_content
        assert "ENUM(" in schema_content
        assert "key_name" in schema_content  # MySQL uses key_name instead of key

    def test_mysql_key_column_translation(self):
        """Test MySQL column name translation (key -> key_name)."""
        from unittest.mock import MagicMock

        from shared_context_server.database_sqlalchemy import (
            SQLAlchemyConnectionWrapper,
        )

        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Test various key column translation scenarios
        test_cases = [
            (
                "SELECT * FROM agent_memory WHERE agent_memory.key = ?",
                "SELECT * FROM agent_memory WHERE agent_memory.key_name = :param1",
            ),
            (
                "INSERT INTO agent_memory (agent_id, session_id, key, value) VALUES (?, ?, ?, ?)",
                "INSERT INTO agent_memory (agent_id, session_id, key_name, value) VALUES (:param1, :param2, :param3, :param4)",
            ),
            (
                "UPDATE agent_memory SET value = ? WHERE key = ?",
                "UPDATE agent_memory SET value = :param1 WHERE key_name = :param2",
            ),
            (
                "DELETE FROM agent_memory WHERE agent_id = ? AND key = ?",
                "DELETE FROM agent_memory WHERE agent_id = :param1 AND key_name = :param2",
            ),
        ]

        for original, _expected in test_cases:
            converted_query, _ = wrapper._convert_params(original, ("test_value",))

            if "agent_memory" in original and "key" in original:
                assert "key_name" in converted_query
                assert (
                    "agent_memory.key " not in converted_query
                )  # Should be translated

    def test_mysql_query_without_agent_memory_unchanged(self):
        """Test that non-agent_memory queries are not affected by key translation."""
        from unittest.mock import MagicMock

        from shared_context_server.database_sqlalchemy import (
            SQLAlchemyConnectionWrapper,
        )

        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # These queries should not be modified
        test_queries = [
            (
                "SELECT * FROM sessions WHERE id = ?",
                ("test_value",),
                "SELECT * FROM sessions WHERE id = :param1",
            ),
            (
                "INSERT INTO messages (session_id, sender, content) VALUES (?, ?, ?)",
                ("session1", "user", "content"),
                "INSERT INTO messages (session_id, sender, content) VALUES (:param1, :param2, :param3)",
            ),
            (
                "SELECT key FROM some_other_table WHERE id = ?",
                ("test_value",),
                "SELECT key FROM some_other_table WHERE id = :param1",
            ),  # Different table
        ]

        for query, params, expected in test_queries:
            converted_query, _ = wrapper._convert_params(query, params)
            # Should only have parameter translation, no column name changes
            assert converted_query == expected

    @patch.dict(
        os.environ,
        {
            "TEST_MYSQL_URL": "mysql+aiomysql://test_user:test_pass@localhost:3306/test_db"
        },
    )
    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_mysql_connection_integration(self, mock_create_engine):
        """Integration test for MySQL connection with mocked engine."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock the engine and connection
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock connection and cursor behavior
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock row result with dict-like access
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=1)
        mock_row.get = MagicMock(return_value=1)
        mock_row.keys = MagicMock(return_value=["test_value"])

        mock_cursor.fetchone = AsyncMock(return_value=mock_row)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        # Mock the engine's connect method
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)

        url = os.environ["TEST_MYSQL_URL"]
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Mock the manager's get_connection method to return our wrapper
        from shared_context_server.database_sqlalchemy import (
            SQLAlchemyConnectionWrapper,
        )

        wrapper = SQLAlchemyConnectionWrapper(mock_engine, mock_conn, "mysql")

        # Mock connection wrapper methods
        wrapper.execute = AsyncMock(return_value=mock_cursor)

        # Test basic connection
        with patch.object(manager, "get_connection") as mock_get_conn:
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=wrapper)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

            async with manager.get_connection() as conn:
                cursor = await conn.execute("SELECT 1 as test_value")
                row = await cursor.fetchone()
                assert row["test_value"] == 1

    @patch.dict(
        os.environ,
        {
            "TEST_MYSQL_URL": "mysql+aiomysql://test_user:test_pass@localhost:3306/test_db"
        },
    )
    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_mysql_schema_initialization(self, mock_create_engine):
        """Integration test for MySQL schema initialization with mocked engine."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock the engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock schema query results for sessions table
        sessions_columns = [
            {"COLUMN_NAME": "id", "DATA_TYPE": "bigint", "COLUMN_TYPE": "bigint(20)"},
            {
                "COLUMN_NAME": "purpose",
                "DATA_TYPE": "varchar",
                "COLUMN_TYPE": "varchar(255)",
            },
            {"COLUMN_NAME": "metadata", "DATA_TYPE": "json", "COLUMN_TYPE": "json"},
        ]

        # Mock agent_memory columns
        agent_memory_columns = [
            {"COLUMN_NAME": "id"},
            {"COLUMN_NAME": "agent_id"},
            {"COLUMN_NAME": "key_name"},  # MySQL uses key_name instead of key
            {"COLUMN_NAME": "value"},
        ]

        # Set up mock to return different results based on query
        def mock_execute_side_effect(query):
            if "sessions" in query and "INFORMATION_SCHEMA.COLUMNS" in query:
                mock_cursor.fetchall = AsyncMock(return_value=sessions_columns)
            elif "agent_memory" in query and "INFORMATION_SCHEMA.COLUMNS" in query:
                mock_cursor.fetchall = AsyncMock(return_value=agent_memory_columns)
            return mock_cursor

        mock_conn.execute = AsyncMock(side_effect=mock_execute_side_effect)

        url = os.environ["TEST_MYSQL_URL"]
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Mock initialization to be successful
        with patch.object(manager, "initialize", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = None

            # Mock get_connection to return our wrapper
            from shared_context_server.database_sqlalchemy import (
                SQLAlchemyConnectionWrapper,
            )

            wrapper = SQLAlchemyConnectionWrapper(mock_engine, mock_conn, "mysql")
            wrapper.execute = AsyncMock(side_effect=mock_execute_side_effect)

            with patch.object(manager, "get_connection") as mock_get_conn:
                mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=wrapper)
                mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

                # Initialize database (should create all tables)
                await manager.initialize()

                # Test that key tables exist
                async with manager.get_connection() as conn:
                    # Check sessions table exists and has correct structure
                    cursor = await conn.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'sessions'
                        ORDER BY ORDINAL_POSITION
                    """)
                    columns = await cursor.fetchall()

                    column_names = [row["COLUMN_NAME"].lower() for row in columns]
                    assert "id" in column_names
                    assert "purpose" in column_names
                    assert "metadata" in column_names

                    # Check that metadata column is JSON
                    metadata_column = next(
                        (
                            col
                            for col in columns
                            if col["COLUMN_NAME"].lower() == "metadata"
                        ),
                        None,
                    )
                    assert metadata_column is not None
                    assert "json" in metadata_column["DATA_TYPE"].lower()

                    # Check that agent_memory table uses key_name
                    cursor = await conn.execute("""
                        SELECT COLUMN_NAME
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'agent_memory'
                    """)
                    memory_columns = await cursor.fetchall()
                    memory_column_names = [
                        row["COLUMN_NAME"].lower() for row in memory_columns
                    ]

                    assert "key_name" in memory_column_names
                    assert (
                        "key" not in memory_column_names
                    )  # Should not have 'key' column

    def test_mysql_unsupported_url_formats(self):
        """Test that unsupported MySQL URL formats raise appropriate errors."""
        # Test pymysql URL (not supported in this implementation)
        with pytest.raises(ValueError, match="Unsupported database URL"):
            SimpleSQLAlchemyManager("mysql://user:pass@localhost:3306/testdb")

        # Test wrong dialect
        with pytest.raises(ValueError, match="Unsupported database URL"):
            SimpleSQLAlchemyManager("mysql+pymysql://user:pass@localhost:3306/testdb")

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_mysql_charset_handling(self, mock_create_engine):
        """Test MySQL charset and collation settings."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_content = await manager._load_schema_file()

        # Check charset and collation settings
        assert "DEFAULT CHARSET=utf8mb4" in schema_content
        assert "COLLATE=utf8mb4_unicode_ci" in schema_content
        assert "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci" in schema_content


class TestMySQLPerformance:
    """Test MySQL-specific performance features."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_innodb_engine(self, mock_create_engine):
        """Test that MySQL schema uses InnoDB engine."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()
        schema_content = schema_path.read_text()

        # All tables should use InnoDB engine
        create_table_count = schema_content.count("CREATE TABLE")
        innodb_count = schema_content.count("ENGINE=InnoDB")

        assert (
            innodb_count >= create_table_count
        )  # At least one ENGINE=InnoDB per table

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_connection_pooling_config(self, mock_create_engine):
        """Test MySQL connection pooling configuration."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        config = manager._get_engine_config()

        # MySQL should have moderate pool settings (less than PostgreSQL)
        assert config["pool_size"] == 10
        assert config["max_overflow"] == 20
        assert config["pool_recycle"] == 3600  # Important for MySQL's 8-hour timeout

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_json_constraints(self, mock_create_engine):
        """Test that MySQL schema includes proper JSON validation."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()
        schema_content = schema_path.read_text()

        # Check for JSON validation constraints
        assert "JSON_VALID(metadata)" in schema_content
        assert "metadata JSON" in schema_content

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_enum_constraints(self, mock_create_engine):
        """Test that MySQL schema uses ENUM for visibility constraints."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()
        schema_content = schema_path.read_text()

        # Check for ENUM usage in visibility column
        assert "ENUM('public', 'private', 'agent_only', 'admin_only')" in schema_content

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_mysql_auto_increment_handling(self, mock_create_engine):
        """Test MySQL AUTO_INCREMENT primary key handling."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_content = await manager._load_schema_file()

        # Check for AUTO_INCREMENT on primary keys
        assert "BIGINT AUTO_INCREMENT PRIMARY KEY" in schema_content
        # Should not have SQLite-style AUTOINCREMENT
        assert "AUTOINCREMENT" not in schema_content


class TestMySQLCompatibility:
    """Test MySQL compatibility and edge cases."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_reserved_keyword_handling(self, mock_create_engine):
        """Test that MySQL reserved keywords are properly handled."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()
        schema_content = schema_path.read_text()

        # 'key' is reserved in MySQL, should use 'key_name'
        assert "key_name VARCHAR(255)" in schema_content
        assert " key VARCHAR(" not in schema_content  # Should not have 'key' column

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_mysql_function_block_detection(self, mock_create_engine):
        """Test MySQL procedure/function block detection."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        # MySQL doesn't use complex stored procedures in this schema
        # but test the detection logic anyway
        procedure_lines = [
            "CREATE PROCEDURE test_proc()",
            "BEGIN",
            "    SELECT 1;",
        ]
        assert manager._is_inside_function_block(procedure_lines) is True

        complete_procedure = [
            "CREATE PROCEDURE test_proc()",
            "BEGIN",
            "    SELECT 1;",
            "END",
        ]
        assert manager._is_inside_function_block(complete_procedure) is False
