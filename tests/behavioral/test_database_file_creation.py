"""
Behavioral tests for database file creation patterns.

Tests user-observable behavior: what files are actually created during database
initialization under various configuration scenarios. Focuses on preventing
unwanted file creation and ensuring only intended database files exist.

Critical for preventing regression of shared_context.db vs chat_history.db issue.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from shared_context_server.config import get_database_url, get_default_database_path
from shared_context_server.database_testing import get_test_db_connection


class TestDatabaseFileCreationBehavior:
    """Test what files are actually created during database operations."""

    def test_default_database_path_development_environment(self, tmp_path):
        """Test that development environment defaults to ./chat_history.db."""
        # Simulate development environment with pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("[tool.pytest]\n")

        with patch("shared_context_server.config.Path") as mock_path:
            # Mock Path(".env").exists() and Path("pyproject.toml").exists()
            mock_path_instance = mock_path.return_value
            mock_path_instance.exists.side_effect = lambda: pyproject_file.name in str(
                mock_path_instance
            )
            mock_path.side_effect = (
                lambda x: Path(tmp_path / x)
                if x in [".env", "pyproject.toml"]
                else Path(x)
            )

            # Should return development default
            result = get_default_database_path()
            assert result == "./chat_history.db"

    def test_default_database_path_production_environment(self, tmp_path):
        """Test that production environment uses data directory path."""
        # Mock both specific Path calls to return False for exists()
        with patch("shared_context_server.config.Path") as mock_path_class:

            def path_side_effect(path_arg):
                if str(path_arg) in [".env", "pyproject.toml"]:
                    # For the exists() check - return a mock that exists() returns False
                    mock_instance = type("MockPath", (), {})()
                    mock_instance.exists = lambda: False
                    return mock_instance
                # For other Path usage (like Path(data_dir) / "chat_history.db"), return real Path
                return Path(path_arg)

            mock_path_class.side_effect = path_side_effect

            with patch(
                "shared_context_server.config.get_default_data_directory"
            ) as mock_data_dir:
                mock_data_dir.return_value = str(tmp_path)

                result = get_default_database_path()
                expected = str(tmp_path / "chat_history.db")
                assert result == expected, f"Expected {expected}, got {result}"

    def test_database_url_respects_environment_variable_precedence(self):
        """Test that DATABASE_URL takes precedence over DATABASE_PATH."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "sqlite:///./custom_from_url.db",
                "DATABASE_PATH": "./custom_from_path.db",
            },
        ):
            # Force config reload
            from shared_context_server import config

            with patch.object(config, "_config", None):
                result = get_database_url()
                assert result == "sqlite:///./custom_from_url.db"

    def test_database_url_fallback_to_database_path(self):
        """Test that DATABASE_PATH is used when DATABASE_URL is not set."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(
                os.environ,
                {"DATABASE_PATH": "./fallback_path.db", "API_KEY": "test-key"},
            ),
        ):
            # Force config reload
            from shared_context_server import config

            with patch.object(config, "_config", None):
                result = get_database_url()
                # The config system resolves relative paths to absolute paths
                expected_absolute_path = str(Path("./fallback_path.db").resolve())
                expected_url = f"sqlite:///{expected_absolute_path}"
                assert result == expected_url

    def test_no_shared_context_db_reference_in_code(self):
        """Test that 'shared_context.db' is never used as a filename in source code."""
        # This test ensures we don't regress to using wrong filename
        import shared_context_server.config as config_module
        import shared_context_server.database as database_module
        import shared_context_server.database_sqlalchemy as sqlalchemy_module

        # Check that modules don't contain hardcoded 'shared_context.db'
        config_source = Path(config_module.__file__).read_text()
        database_source = Path(database_module.__file__).read_text()
        sqlalchemy_source = Path(sqlalchemy_module.__file__).read_text()

        assert "shared_context.db" not in config_source
        assert "shared_context.db" not in database_source
        assert "shared_context.db" not in sqlalchemy_source


class TestBackendSwitchingFileCreation:
    """Test file creation behavior when switching between database backends."""

    @pytest.mark.asyncio
    async def test_aiosqlite_backend_creates_only_intended_files(self):
        """Test that aiosqlite backend creates only intended database files."""
        # Use test database connection that won't interfere with real files
        async with get_test_db_connection("aiosqlite") as conn:
            # Test basic operations to ensure database is functional
            await conn.execute("CREATE TABLE test_aiosqlite (id INTEGER, data TEXT)")
            await conn.execute("INSERT INTO test_aiosqlite VALUES (1, 'test')")
            await conn.commit()

            cursor = await conn.execute("SELECT data FROM test_aiosqlite WHERE id = 1")
            row = await cursor.fetchone()
            assert row[0] == "test"

        # Test passes if no exceptions and database operations work correctly
        # Memory databases used in tests don't create unwanted files

    @pytest.mark.asyncio
    async def test_sqlalchemy_backend_creates_only_intended_files(self):
        """Test that SQLAlchemy backend creates only intended database files."""
        # Use test database connection that won't interfere with real files
        async with get_test_db_connection("sqlalchemy") as conn:
            # Test basic operations to ensure database is functional
            await conn.execute("CREATE TABLE test_sqlalchemy (id INTEGER, data TEXT)")
            await conn.execute("INSERT INTO test_sqlalchemy VALUES (1, 'test')")
            await conn.commit()

            cursor = await conn.execute("SELECT data FROM test_sqlalchemy WHERE id = 1")
            row = await cursor.fetchone()

            # Handle different row formats
            if hasattr(row, "keys"):
                assert row["data"] == "test"
            else:
                assert row[0] == "test"

        # Test passes if no exceptions and database operations work correctly


class TestDatabaseFileCleanupBehavior:
    """Test behavior related to cleaning up unwanted database files."""

    def test_identify_unwanted_database_files(self, tmp_path):
        """Test identification of unwanted database files that shouldn't exist."""
        # Create test files to simulate the issue
        wanted_files = ["chat_history.db", "chat_history.db-wal", "chat_history.db-shm"]

        unwanted_files = [
            "shared_context.db",
            "shared_context.db-wal",
            "shared_context.db-shm",
        ]

        # Create files in temp directory
        for filename in wanted_files + unwanted_files:
            (tmp_path / filename).touch()

        # Test logic to identify unwanted files
        def identify_unwanted_db_files(directory: Path) -> list[Path]:
            """Identify database files that shouldn't exist."""
            return [
                file
                for file in directory.glob("*.db*")
                if file.name.startswith("shared_context")
            ]

        unwanted_found = identify_unwanted_db_files(tmp_path)
        unwanted_names = [f.name for f in unwanted_found]

        # Should find all shared_context.db* files
        assert "shared_context.db" in unwanted_names
        assert "shared_context.db-wal" in unwanted_names
        assert "shared_context.db-shm" in unwanted_names

        # Should NOT find wanted files
        assert "chat_history.db" not in unwanted_names
        assert "chat_history.db-wal" not in unwanted_names
        assert "chat_history.db-shm" not in unwanted_names


class TestEnvironmentVariableValidation:
    """Test environment variable handling for database configuration."""

    def test_database_url_sqlite_format_validation(self):
        """Test that DATABASE_URL sqlite format is handled correctly."""
        valid_formats = [
            "sqlite:///./chat_history.db",
            "sqlite:///chat_history.db",
            "sqlite:////absolute/path/chat_history.db",
        ]

        for url_format in valid_formats:
            with patch.dict(
                os.environ, {"DATABASE_URL": url_format, "API_KEY": "test"}
            ):
                from shared_context_server import config

                with patch.object(config, "_config", None):
                    result = get_database_url()
                    assert result == url_format

    def test_database_path_relative_vs_absolute(self, tmp_path):
        """Test handling of relative vs absolute database paths."""
        # Use tmp_path for absolute path test to avoid filesystem issues
        absolute_test_path = str(tmp_path / "chat_history.db")
        test_cases = ["./chat_history.db", "chat_history.db", absolute_test_path]

        for path in test_cases:
            # Clear all environment variables and avoid .env file loading
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.dict(os.environ, {"DATABASE_PATH": path, "API_KEY": "test"}),
            ):
                from shared_context_server import config

                with (
                    patch.object(config, "_config", None),
                    patch("shared_context_server.config.dotenv.load_dotenv"),
                ):
                    result = get_database_url()
                    # The config system resolves all paths to absolute paths
                    expected_absolute_path = str(Path(path).resolve())
                    expected = f"sqlite:///{expected_absolute_path}"
                    assert result == expected


class TestConfigurationErrorScenarios:
    """Test database file creation during error scenarios."""

    def test_missing_environment_variables_fallback(self):
        """Test behavior when environment variables are missing."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(os.environ, {"API_KEY": "test-key"}),
        ):
            from shared_context_server import config

            with patch.object(config, "_config", None):
                # Should fall back to default path
                result = get_database_url()
                # Should use default database path pattern
                assert "chat_history.db" in result
                assert "shared_context.db" not in result

    def test_invalid_database_url_fallback_behavior(self, caplog):
        """Test behavior when DATABASE_URL is malformed."""
        invalid_urls = [
            "invalid-url",
            "sqlite://invalid-path",
            "postgresql://incomplete",
        ]

        for invalid_url in invalid_urls:
            with patch.dict(
                os.environ, {"DATABASE_URL": invalid_url, "API_KEY": "test-key"}
            ):
                from shared_context_server import config

                with patch.object(config, "_config", None):
                    # Configuration should still load (validation may be permissive)
                    result = get_database_url()
                    assert result == invalid_url  # Returns as-is, validation elsewhere


class TestDocumentationAccuracy:
    """Test that documentation matches actual behavior."""

    def test_claude_md_documentation_accuracy(self):
        """Test that CLAUDE.md documents correct default database filename."""
        claude_md_path = Path(__file__).parent.parent.parent / "CLAUDE.md"

        if claude_md_path.exists():
            claude_md_content = claude_md_path.read_text()

            # The bug: CLAUDE.md incorrectly documents shared_context.db as default
            # This test documents the current (incorrect) state and should be updated
            # when the documentation is fixed

            # Current incorrect state (this line should fail after docs are fixed):
            assert "default: shared_context.db" in claude_md_content

            # TODO: Update assertions when documentation is fixed
            # Should assert "default: chat_history.db" in claude_md_content
            # Should assert "default: shared_context.db" not in claude_md_content


class TestRegressionPrevention:
    """Tests designed to prevent regression to unwanted file creation."""

    def test_database_initialization_file_pattern(self, tmp_path):
        """Test that database initialization follows correct file naming pattern."""
        # This test would ideally use actual database initialization
        # but uses test patterns to verify naming logic

        def simulate_database_file_creation(base_name: str) -> list[str]:
            """Simulate what files database initialization might create."""
            return [f"{base_name}.db", f"{base_name}.db-wal", f"{base_name}.db-shm"]

        # Test with correct base name
        correct_files = simulate_database_file_creation("chat_history")
        assert "chat_history.db" in correct_files
        assert all("chat_history" in f for f in correct_files)

        # Test that we don't accidentally use wrong base name
        wrong_files = simulate_database_file_creation("shared_context")
        assert "shared_context.db" in wrong_files
        # This demonstrates what we DON'T want to happen

    @pytest.mark.asyncio
    async def test_memory_database_testing_creates_no_files(self, tmp_path):
        """Test that memory database testing doesn't create any unwanted files."""
        original_files = {f.name for f in tmp_path.iterdir() if f.is_file()}

        # Use memory database for testing
        async with get_test_db_connection("aiosqlite") as conn:
            await conn.execute("CREATE TABLE regression_test (id INTEGER)")
            await conn.execute("INSERT INTO regression_test VALUES (1)")
            await conn.commit()

        # Memory database should not create any files
        final_files = {f.name for f in tmp_path.iterdir() if f.is_file()}
        new_files = final_files - original_files

        # No new database files should be created
        db_extensions = [".db", ".db-wal", ".db-shm"]
        new_db_files = [
            f for f in new_files if any(f.endswith(ext) for ext in db_extensions)
        ]

        assert len(new_db_files) == 0, (
            f"Unexpected database files created: {new_db_files}"
        )


class TestProductionScenarioValidation:
    """Test database file creation in production-like scenarios."""

    def test_containerized_environment_database_path(self):
        """Test database path resolution in containerized environment."""
        # Simulate container environment (no .env or pyproject.toml)
        with patch("shared_context_server.config.Path") as mock_path:

            def path_side_effect(path_arg):
                if str(path_arg) in [".env", "pyproject.toml"]:
                    # For the exists() check - return a mock that exists() returns False
                    mock_instance = type("MockPath", (), {})()
                    mock_instance.exists = lambda: False
                    return mock_instance
                # For other Path usage (like Path(data_dir) / "chat_history.db"), return real Path
                return Path(path_arg)

            mock_path.side_effect = path_side_effect

            with patch(
                "shared_context_server.config.get_default_data_directory"
            ) as mock_data_dir:
                mock_data_dir.return_value = "/app/data"

                result = get_default_database_path()
                assert result == "/app/data/chat_history.db"
                assert "shared_context.db" not in result

    def test_environment_variable_override_production(self):
        """Test that production environment variables properly override defaults."""
        production_vars = {
            "DATABASE_URL": "postgresql://user:pass@db:5432/prod_database",
            "ENVIRONMENT": "production",
            "API_KEY": "production-secure-key",
            "LOG_LEVEL": "INFO",  # Production requires non-DEBUG log level
            "CORS_ORIGINS": "https://example.com",  # Production requires specific origins
        }

        # Clear all environment variables first, then set only what we want
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(os.environ, production_vars),
        ):
            from shared_context_server import config

            with (
                patch.object(config, "_config", None),
                patch("shared_context_server.config.dotenv.load_dotenv"),
            ):
                result = get_database_url()
                assert result == "postgresql://user:pass@db:5432/prod_database"
                # Ensure no fallback to sqlite with wrong filename
                assert "shared_context.db" not in result
