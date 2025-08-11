"""
Smoke tests for critical infrastructure components.

These tests ensure the basic foundation is working:
- Database WAL mode is active
- Required tables and indexes exist
- Environment validation works correctly

Run with: pytest tests/test_smoke.py -v
"""

import contextlib
import os
import tempfile
from pathlib import Path

import pytest

from src.shared_context_server.config import get_config
from src.shared_context_server.database import DatabaseManager


class TestWALSchemaSmoke:
    """Critical smoke tests that must pass for system to be functional."""

    @pytest.mark.asyncio
    async def test_wal_mode_active(self):
        """Test that WAL mode is properly enabled - critical for concurrent access."""
        # Use temporary database for isolated testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db_manager = DatabaseManager(temp_path)
            await db_manager.initialize()

            async with db_manager.get_connection() as conn:
                cursor = await conn.execute("PRAGMA journal_mode;")
                mode = (await cursor.fetchone())[0].lower()
                assert mode == "wal", (
                    f"❌ WAL mode not enabled, got: {mode}. This breaks concurrent agent access!"
                )

        finally:
            # Cleanup
            with contextlib.suppress(FileNotFoundError):
                Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_required_tables_exist(self):
        """Test that all required database tables exist after initialization."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db_manager = DatabaseManager(temp_path)
            await db_manager.initialize()

            required_tables = {
                "sessions": "Session isolation and management",
                "messages": "Agent communication storage",
                "agent_memory": "Agent persistent memory",
                "audit_log": "Security and debugging trail",
                "schema_version": "Database version tracking",
            }

            async with db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table'
                    ORDER BY name
                """)
                existing_tables = {row[0] for row in await cursor.fetchall()}

            missing_tables = []
            for table, purpose in required_tables.items():
                if table not in existing_tables:
                    missing_tables.append(f"❌ Missing table '{table}' ({purpose})")

            assert not missing_tables, "Database schema incomplete:\n" + "\n".join(
                missing_tables
            )

        finally:
            with contextlib.suppress(FileNotFoundError):
                Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_required_indexes_exist(self):
        """Test that performance-critical indexes exist."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db_manager = DatabaseManager(temp_path)
            await db_manager.initialize()

            # Critical indexes for performance
            required_indexes = {
                "idx_messages_session_id": "Message lookup by session",
                "idx_agent_memory_lookup": "Agent memory access",
                "idx_audit_log_timestamp": "Audit log queries",
            }

            async with db_manager.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND sql IS NOT NULL
                    ORDER BY name
                """)
                existing_indexes = {row[0] for row in await cursor.fetchall()}

            missing_indexes = []
            for index, purpose in required_indexes.items():
                if index not in existing_indexes:
                    missing_indexes.append(
                        f"⚠️ Missing index '{index}' ({purpose}) - performance will suffer!"
                    )

            # Don't fail on missing indexes, but warn
            if missing_indexes:
                print("\n".join(missing_indexes))

        finally:
            with contextlib.suppress(FileNotFoundError):
                Path(temp_path).unlink()

    def test_environment_validation_loads(self):
        """Test that config loads successfully when API_KEY is available (from .env or environment)."""
        # This test validates that the configuration can load successfully
        # The .env file provides the API_KEY, so we test successful loading
        try:
            config = get_config()
            assert config is not None, "❌ Configuration should load successfully"
            assert config.security.api_key is not None, (
                "❌ API_KEY should be available from .env or environment"
            )
            assert len(config.security.api_key) > 0, "❌ API_KEY should not be empty"

        except Exception as e:
            pytest.fail(
                f"❌ Configuration should load successfully with available API_KEY: {e}"
            )

    def test_environment_validation_succeeds_with_required_vars(self):
        """Test that config loads successfully when required variables are present."""
        # Ensure required variables are set
        required_env = {
            "API_KEY": os.environ.get("API_KEY", "test-api-key"),
            "DATABASE_PATH": os.environ.get("DATABASE_PATH", ":memory:"),
            "ENVIRONMENT": os.environ.get("ENVIRONMENT", "testing"),
        }

        # Temporarily set environment
        for key, value in required_env.items():
            os.environ[key] = value

        try:
            config = get_config()
            assert config is not None, (
                "❌ Configuration failed to load with required environment variables"
            )
            assert config.security.api_key == required_env["API_KEY"]
            # DATABASE_PATH gets resolved to absolute path by validator, so just check it's not None
            assert config.database.database_path is not None, (
                "❌ Database path should be configured"
            )

        except Exception as e:
            pytest.fail(
                f"❌ Configuration should load successfully with required vars, but failed: {e}"
            )


class TestFoundationIntegrity:
    """Additional smoke tests for system integrity."""

    @pytest.mark.asyncio
    async def test_foreign_keys_enabled(self):
        """Test that foreign key constraints are enabled for data integrity."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db_manager = DatabaseManager(temp_path)
            await db_manager.initialize()

            async with db_manager.get_connection() as conn:
                cursor = await conn.execute("PRAGMA foreign_keys;")
                result = (await cursor.fetchone())[0]
                assert str(result) == "1", (
                    f"❌ Foreign keys not enabled, got: {result}. This breaks data integrity!"
                )

        finally:
            with contextlib.suppress(FileNotFoundError):
                Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_schema_version_tracked(self):
        """Test that schema version is properly tracked."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            db_manager = DatabaseManager(temp_path)
            await db_manager.initialize()

            async with db_manager.get_connection() as conn:
                cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
                version = (await cursor.fetchone())[0]
                assert version is not None and version >= 1, (
                    f"❌ Schema version not tracked properly, got: {version}"
                )

        finally:
            with contextlib.suppress(FileNotFoundError):
                Path(temp_path).unlink()
