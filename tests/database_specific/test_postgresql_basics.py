"""
PostgreSQL-specific database tests.

Tests PostgreSQL dialect differences, connection handling, and schema features
that are unique to PostgreSQL (SERIAL, JSONB, TIMESTAMPTZ, etc.).
"""

import os
from unittest.mock import patch

import pytest

from shared_context_server.database_sqlalchemy import SimpleSQLAlchemyManager


class TestPostgreSQLBasics:
    """Test PostgreSQL-specific database functionality."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_url_detection(self, mock_create_engine):
        """Test PostgreSQL URL detection in SimpleSQLAlchemyManager."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        assert manager.db_type == "postgresql"
        assert manager.database_url == url

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_engine_config(self, mock_create_engine):
        """Test PostgreSQL-specific engine configuration."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        config = manager._get_engine_config()

        # Check PostgreSQL-specific settings
        assert config["pool_size"] == 20
        assert config["max_overflow"] == 30
        assert config["pool_recycle"] == 3600
        assert config["pool_pre_ping"] is True

        # Check connection args
        connect_args = config["connect_args"]
        assert connect_args["prepared_statement_cache_size"] == 500
        assert connect_args["server_settings"]["jit"] == "off"
        assert (
            connect_args["server_settings"]["application_name"] == "shared_context_mcp"
        )

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_schema_file_path(self, mock_create_engine):
        """Test PostgreSQL schema file path resolution."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_path = manager._get_schema_file_path()

        assert schema_path.name == "database_postgresql.sql"
        assert schema_path.exists()

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_postgresql_schema_loading(self, mock_create_engine):
        """Test loading of PostgreSQL schema file."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        schema_content = await manager._load_schema_file()

        # Check for PostgreSQL-specific elements
        assert "SERIAL PRIMARY KEY" in schema_content
        assert "BIGSERIAL PRIMARY KEY" in schema_content
        assert "JSONB" in schema_content
        assert "TIMESTAMPTZ" in schema_content
        assert "CREATE OR REPLACE FUNCTION update_updated_at_column()" in schema_content
        assert "EXECUTE FUNCTION update_updated_at_column()" in schema_content

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_function_block_detection(self, mock_create_engine):
        """Test detection of PostgreSQL function blocks during schema parsing."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Test function block detection
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

    def test_postgresql_query_translation(self):
        """Test that PostgreSQL doesn't need query translation."""
        from unittest.mock import MagicMock

        from shared_context_server.database_sqlalchemy import (
            SQLAlchemyConnectionWrapper,
        )

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

    @patch.dict(
        os.environ,
        {
            "TEST_POSTGRESQL_URL": "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
        },
    )
    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_postgresql_connection_integration(self, mock_create_engine):
        """Integration test for PostgreSQL connection with mocked engine."""
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

        url = os.environ["TEST_POSTGRESQL_URL"]
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Mock the manager's get_connection method to return our wrapper
        from shared_context_server.database_sqlalchemy import (
            SQLAlchemyConnectionWrapper,
        )

        wrapper = SQLAlchemyConnectionWrapper(mock_engine, mock_conn, "postgresql")

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
            "TEST_POSTGRESQL_URL": "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
        },
    )
    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_postgresql_schema_initialization(self, mock_create_engine):
        """Integration test for PostgreSQL schema initialization with mocked engine."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock the engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock schema query results for sessions table
        sessions_columns = [
            {"column_name": "id", "data_type": "bigint"},
            {"column_name": "purpose", "data_type": "character varying"},
            {"column_name": "metadata", "data_type": "jsonb"},  # PostgreSQL uses JSONB
        ]

        mock_cursor.fetchall = AsyncMock(return_value=sessions_columns)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        url = os.environ["TEST_POSTGRESQL_URL"]
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Mock initialization to be successful
        with patch.object(manager, "initialize", new_callable=AsyncMock) as mock_init:
            mock_init.return_value = None

            # Mock get_connection to return our wrapper
            from shared_context_server.database_sqlalchemy import (
                SQLAlchemyConnectionWrapper,
            )

            wrapper = SQLAlchemyConnectionWrapper(mock_engine, mock_conn, "postgresql")
            wrapper.execute = AsyncMock(return_value=mock_cursor)

            with patch.object(manager, "get_connection") as mock_get_conn:
                mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=wrapper)
                mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=None)

                # Initialize database (should create all tables and functions)
                await manager.initialize()

                # Test that key tables exist
                async with manager.get_connection() as conn:
                    # Check sessions table exists and has correct structure
                    cursor = await conn.execute("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = 'sessions'
                        ORDER BY ordinal_position
                    """)
                    columns = await cursor.fetchall()

                    column_names = [row["column_name"] for row in columns]
                    assert "id" in column_names
                    assert "purpose" in column_names
                    assert "metadata" in column_names

                    # Check that metadata column is JSONB
                    metadata_column = next(
                        (col for col in columns if col["column_name"] == "metadata"),
                        None,
                    )
                    assert metadata_column is not None
                    assert "jsonb" in metadata_column["data_type"].lower()

    def test_postgresql_unsupported_url_formats(self):
        """Test that unsupported PostgreSQL URL formats raise appropriate errors."""
        # Test psycopg2 URL (not supported)
        with pytest.raises(ValueError, match="Unsupported database URL"):
            SimpleSQLAlchemyManager("postgresql://user:pass@localhost:5432/testdb")

        # Test wrong dialect
        with pytest.raises(ValueError, match="Unsupported database URL"):
            SimpleSQLAlchemyManager(
                "postgresql+psycopg2://user:pass@localhost:5432/testdb"
            )

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    @pytest.mark.asyncio
    async def test_postgresql_schema_file_not_found_handling(self, mock_create_engine):
        """Test graceful handling when PostgreSQL schema file is missing."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Mock the schema file path to point to non-existent file
        original_path = manager._get_schema_file_path()
        nonexistent_path = original_path.parent / "nonexistent.sql"

        with (
            patch.object(
                manager, "_get_schema_file_path", return_value=nonexistent_path
            ),
            pytest.raises(FileNotFoundError, match="Schema file not found"),
        ):
            await manager._load_schema_file()


class TestPostgreSQLPerformance:
    """Test PostgreSQL-specific performance features."""

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_jsonb_optimizations(self, mock_create_engine):
        """Test that PostgreSQL schema includes JSONB optimizations."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        # Verify schema contains JSONB-specific indexes
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

    @patch("shared_context_server.database_sqlalchemy.create_async_engine")
    def test_postgresql_connection_pooling_config(self, mock_create_engine):
        """Test PostgreSQL connection pooling is properly configured."""
        from unittest.mock import MagicMock

        mock_create_engine.return_value = MagicMock()

        url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
        manager = SimpleSQLAlchemyManager(database_url=url)

        config = manager._get_engine_config()

        # PostgreSQL should have higher pool settings than SQLite
        assert config["pool_size"] == 20  # Higher than default
        assert config["max_overflow"] == 30  # Allows for burst connections
        assert (
            config["connect_args"]["prepared_statement_cache_size"] == 500
        )  # Performance optimization
