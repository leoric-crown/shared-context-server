"""
PostgreSQL unit tests that don't require actual PostgreSQL drivers.

These tests focus on URL detection, configuration, and functionality
without requiring asyncpg to be installed.
"""

from unittest.mock import MagicMock, patch

from shared_context_server.database_sqlalchemy import (
    SimpleSQLAlchemyManager,
    SQLAlchemyConnectionWrapper,
)


class TestPostgreSQLUnitTests:
    """Unit tests for PostgreSQL functionality without database drivers."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_url_detection_mocked(self, mock_create_engine):
        """Test PostgreSQL URL detection without requiring asyncpg driver."""
        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        assert manager.db_type == "postgresql"
        assert manager.database_url == url

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_engine_config_mocked(self, mock_create_engine):
        """Test PostgreSQL engine configuration without requiring asyncpg driver."""
        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        SimpleSQLAlchemyManager(database_url=url)

        # Verify the engine was called with the right config
        assert mock_create_engine.called
        call_args = mock_create_engine.call_args
        config = call_args[1]  # kwargs

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
    def test_postgresql_schema_file_path_mocked(self, mock_create_engine):
        """Test PostgreSQL schema file path resolution without requiring asyncpg."""
        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()

        assert schema_path.name == "database_postgresql.sql"
        assert schema_path.exists()

    def test_postgresql_query_translation_unchanged(self):
        """Test that PostgreSQL queries are not modified (no column translation needed)."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "postgresql")

        # PostgreSQL should not modify agent_memory.key queries
        original_query = "SELECT * FROM agent_memory WHERE agent_memory.key = ?"
        converted_query, params = wrapper._convert_params(original_query, ("test_key",))

        assert "agent_memory.key" in converted_query
        assert "key_name" not in converted_query
        assert (
            converted_query
            == "SELECT * FROM agent_memory WHERE agent_memory.key = :param1"
        )
        assert params == {"param1": "test_key"}

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_function_block_detection_mocked(self, mock_create_engine):
        """Test PostgreSQL function block detection without requiring asyncpg."""
        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Test PostgreSQL function block detection
        function_lines = [
            "CREATE OR REPLACE FUNCTION update_updated_at_column()",
            "RETURNS TRIGGER AS $$",
            "BEGIN",
        ]
        assert manager._is_inside_function_block(function_lines) is True

        # Test complete function
        complete_function = [
            "CREATE OR REPLACE FUNCTION update_updated_at_column()",
            "RETURNS TRIGGER AS $$",
            "BEGIN",
            "    NEW.updated_at = CURRENT_TIMESTAMP;",
            "    RETURN NEW;",
            "END;",
            "$$ LANGUAGE plpgsql;",
        ]
        assert manager._is_inside_function_block(complete_function) is False

    def test_postgresql_parameter_binding(self):
        """Test PostgreSQL parameter binding functionality."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "postgresql")

        test_cases = [
            (
                "SELECT * FROM sessions WHERE id = ?",
                ("session1",),
                "SELECT * FROM sessions WHERE id = :param1",
                {"param1": "session1"},
            ),
            (
                "INSERT INTO messages (session_id, sender, content) VALUES (?, ?, ?)",
                ("session1", "agent1", "hello"),
                "INSERT INTO messages (session_id, sender, content) VALUES (:param1, :param2, :param3)",
                {"param1": "session1", "param2": "agent1", "param3": "hello"},
            ),
            (
                "UPDATE agent_memory SET value = ? WHERE agent_memory.key = ?",
                ("new_value", "test_key"),
                "UPDATE agent_memory SET value = :param1 WHERE agent_memory.key = :param2",
                {"param1": "new_value", "param2": "test_key"},
            ),
        ]

        for original_query, params_tuple, expected_query, expected_params in test_cases:
            converted_query, actual_params = wrapper._convert_params(
                original_query, params_tuple
            )
            assert converted_query == expected_query
            assert actual_params == expected_params

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_schema_content_validation_mocked(self, mock_create_engine):
        """Test that PostgreSQL schema file contains expected PostgreSQL-specific elements."""
        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()
        schema_content = schema_path.read_text()

        # Check for PostgreSQL-specific elements
        assert "SERIAL PRIMARY KEY" in schema_content
        assert "BIGSERIAL PRIMARY KEY" in schema_content
        assert "JSONB" in schema_content
        assert "TIMESTAMPTZ" in schema_content
        assert "CREATE OR REPLACE FUNCTION update_updated_at_column()" in schema_content
        assert "EXECUTE FUNCTION update_updated_at_column()" in schema_content

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_jsonb_optimizations_mocked(self, mock_create_engine):
        """Test that PostgreSQL schema includes JSONB-specific optimizations."""
        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()
        schema_content = schema_path.read_text()

        # Check for GIN indexes on JSONB columns (PostgreSQL-specific)
        assert (
            "CREATE INDEX idx_messages_metadata_gin ON messages USING GIN (metadata)"
            in schema_content
        )
        assert (
            "CREATE INDEX idx_sessions_metadata_gin ON sessions USING GIN (metadata)"
            in schema_content
        )
        assert (
            "CREATE INDEX idx_agent_memory_metadata_gin ON agent_memory USING GIN (metadata)"
            in schema_content
        )
        assert (
            "CREATE INDEX idx_audit_log_metadata_gin ON audit_log USING GIN (metadata)"
            in schema_content
        )

    def test_postgresql_no_reserved_keyword_issues(self):
        """Test that PostgreSQL doesn't have reserved keyword translation issues."""
        engine = MagicMock()
        conn = MagicMock()
        wrapper = SQLAlchemyConnectionWrapper(engine, conn, "postgresql")

        # PostgreSQL allows 'key' as a column name, so no translation should occur
        queries_that_should_not_change = [
            "SELECT * FROM agent_memory WHERE key = ?",
            "INSERT INTO agent_memory (agent_id, session_id, key, value) VALUES (?, ?, ?, ?)",
            "UPDATE agent_memory SET value = ? WHERE key = ?",
            "DELETE FROM agent_memory WHERE agent_id = ? AND key = ?",
        ]

        for query in queries_that_should_not_change:
            converted_query, _ = wrapper._convert_params(query, ("test_value",))
            # Should only have parameter substitution, no column name changes
            assert "key_name" not in converted_query
            assert "key" in converted_query  # Original column name should remain
