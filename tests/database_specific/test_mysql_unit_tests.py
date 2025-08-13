"""
MySQL unit tests that don't require actual MySQL drivers.

These tests focus on URL detection, configuration, and query translation
without requiring aiomysql to be installed.
"""

from unittest.mock import MagicMock, patch

from shared_context_server.database_sqlalchemy import (
    SimpleSQLAlchemyManager,
    SQLAlchemyConnectionWrapper,
)


class TestMySQLUnitTests:
    """Unit tests for MySQL functionality without database drivers."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_url_detection_mocked(self, mock_create_engine):
        """Test MySQL URL detection without requiring aiomysql driver."""
        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        assert manager.db_type == "mysql"
        assert manager.database_url == url

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_engine_config_mocked(self, mock_create_engine):
        """Test MySQL engine configuration without requiring aiomysql driver."""
        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        SimpleSQLAlchemyManager(database_url=url)

        # Verify the engine was called with the right config
        assert mock_create_engine.called
        call_args = mock_create_engine.call_args
        config = call_args[1]  # kwargs

        assert config["pool_size"] == 10
        assert config["max_overflow"] == 20
        assert config["pool_recycle"] == 3600
        assert config["pool_pre_ping"] is True

        connect_args = config["connect_args"]
        assert connect_args["charset"] == "utf8mb4"
        assert connect_args["autocommit"] is False
        assert connect_args["init_command"] == "SET sql_mode='STRICT_TRANS_TABLES'"

    def test_mysql_key_column_translation_unit(self):
        """Test MySQL column name translation without database drivers."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Test INSERT with key column
        query = "INSERT INTO agent_memory (agent_id, session_id, key, value) VALUES (?, ?, ?, ?)"
        converted_query, params = wrapper._convert_params(
            query, ("agent1", "session1", "test_key", "test_value")
        )

        assert "key_name" in converted_query
        assert " key," not in converted_query
        assert (
            converted_query
            == "INSERT INTO agent_memory (agent_id, session_id, key_name, value) VALUES (:param1, :param2, :param3, :param4)"
        )
        assert params == {
            "param1": "agent1",
            "param2": "session1",
            "param3": "test_key",
            "param4": "test_value",
        }

    def test_mysql_key_column_translation_where_clause(self):
        """Test MySQL key column translation in WHERE clauses."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Test SELECT with WHERE clause
        query = "SELECT * FROM agent_memory WHERE key = ?"
        converted_query, params = wrapper._convert_params(query, ("test_key",))

        assert "key_name" in converted_query
        assert " key " not in converted_query
        assert converted_query == "SELECT * FROM agent_memory WHERE key_name = :param1"
        assert params == {"param1": "test_key"}

    def test_mysql_key_column_translation_update(self):
        """Test MySQL key column translation in UPDATE statements."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Test UPDATE with key in WHERE clause
        query = "UPDATE agent_memory SET value = ? WHERE key = ?"
        converted_query, params = wrapper._convert_params(
            query, ("new_value", "test_key")
        )

        assert "key_name" in converted_query
        assert " key " not in converted_query
        assert (
            converted_query
            == "UPDATE agent_memory SET value = :param1 WHERE key_name = :param2"
        )
        assert params == {"param1": "new_value", "param2": "test_key"}

    def test_mysql_key_translation_with_table_prefix(self):
        """Test MySQL key translation with explicit table prefix."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Test with explicit table prefix
        query = "SELECT * FROM agent_memory WHERE agent_memory.key = ?"
        converted_query, params = wrapper._convert_params(query, ("test_key",))

        assert "agent_memory.key_name" in converted_query
        assert "agent_memory.key " not in converted_query
        assert (
            converted_query
            == "SELECT * FROM agent_memory WHERE agent_memory.key_name = :param1"
        )
        assert params == {"param1": "test_key"}

    def test_mysql_non_agent_memory_queries_unchanged(self):
        """Test that non-agent_memory queries are not affected by key translation."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Test queries that should not be modified
        test_queries = [
            (
                "SELECT * FROM sessions WHERE id = ?",
                "SELECT * FROM sessions WHERE id = :param1",
            ),
            (
                "INSERT INTO messages (session_id, sender, content) VALUES (?, ?, ?)",
                "INSERT INTO messages (session_id, sender, content) VALUES (:param1, :param2, :param3)",
            ),
            (
                "SELECT key FROM some_other_table WHERE id = ?",
                "SELECT key FROM some_other_table WHERE id = :param1",
            ),  # Different table, should not change
        ]

        for original_query, expected_query in test_queries:
            converted_query, _ = wrapper._convert_params(
                original_query, ("test_value",)
            )
            assert converted_query == expected_query

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_schema_file_path_mocked(self, mock_create_engine):
        """Test MySQL schema file path resolution without requiring aiomysql."""
        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()

        assert schema_path.name == "database_mysql.sql"
        assert schema_path.exists()

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_mysql_function_block_detection_mocked(self, mock_create_engine):
        """Test MySQL procedure/function block detection without requiring aiomysql."""
        mock_create_engine.return_value = MagicMock()

        url = "mysql+aiomysql://user:pass@localhost:3306/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        # MySQL doesn't use complex stored procedures in our schema,
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

    def test_mysql_complex_query_translation(self):
        """Test complex MySQL query translation scenarios."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "mysql")

        # Complex query with multiple key references
        query = """
        UPDATE agent_memory
        SET value = ?
        WHERE agent_id = ?
        AND agent_memory.key = ?
        AND session_id IS NOT NULL
        """

        converted_query, params = wrapper._convert_params(
            query, ("new_value", "agent1", "test_key")
        )

        # Should translate both key references
        assert "key_name" in converted_query
        assert "agent_memory.key_name" in converted_query
        assert " key " not in converted_query
        assert params == {
            "param1": "new_value",
            "param2": "agent1",
            "param3": "test_key",
        }
