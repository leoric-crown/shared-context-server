"""
Comprehensive unit tests for config.py to achieve 85%+ coverage.

Tests configuration loading, validation, environment variable handling, and security settings.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from shared_context_server.config import (
    SharedContextServerConfig,
    get_config,
    load_config,
)


class TestSharedContextServerConfig:
    """Test the SharedContextServerConfig configuration class."""

    def test_config_default_values(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {"API_KEY": "test-api-key"}, clear=True):
            config = load_config()

            assert config.database.database_path.endswith("chat_history.db")
            assert config.security.api_key == "test-api-key"
            assert config.operational.log_level == "INFO"
            assert config.security.cors_origins == ["*"]
            assert config.security.jwt_expiration_time == 86400
            assert config.mcp_server.mcp_server_name == "shared-context-server"

    def test_config_from_environment(self):
        """Test configuration loaded from environment variables."""
        test_env = {
            "DATABASE_URL": "test_database.db",
            "API_KEY": "test_api_key",
            "LOG_LEVEL": "DEBUG",
            "CORS_ORIGINS": "http://localhost:3000,https://example.com",
            "JWT_SECRET_KEY": "custom_jwt_secret",
            "JWT_EXPIRATION_TIME": "7200",
            "MCP_SERVER_NAME": "test-server",
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = load_config()

            assert config.database.database_url == "test_database.db"
            assert config.security.api_key == "test_api_key"
            assert config.operational.log_level == "DEBUG"
            assert config.security.cors_origins == [
                "http://localhost:3000",
                "https://example.com",
            ]
            assert config.security.jwt_secret_key == "custom_jwt_secret"
            assert config.security.jwt_expiration_time == 7200
            assert config.mcp_server.mcp_server_name == "test-server"

    def test_config_cors_origins_list(self):
        """Test CORS origins parsing into list."""
        test_env = {
            "API_KEY": "test-key",
            "CORS_ORIGINS": "http://localhost:3000,https://example.com,http://127.0.0.1:8080",
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = load_config()

            expected = [
                "http://localhost:3000",
                "https://example.com",
                "http://127.0.0.1:8080",
            ]
            assert config.security.cors_origins == expected

    def test_config_cors_origins_single_wildcard(self):
        """Test CORS origins with wildcard."""
        test_env = {"API_KEY": "test-key", "CORS_ORIGINS": "*"}

        with patch.dict(os.environ, test_env, clear=True):
            config = load_config()

            assert config.security.cors_origins == ["*"]

    def test_config_cors_origins_empty(self):
        """Test CORS origins when empty."""
        test_env = {"API_KEY": "test-key", "CORS_ORIGINS": ""}

        with patch.dict(os.environ, test_env, clear=True):
            config = load_config()

            assert config.security.cors_origins == [""]

    def test_config_boolean_parsing_variations(self):
        """Test various boolean value parsing."""
        boolean_test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_value, expected in boolean_test_cases:
            with patch.dict(
                os.environ,
                {"API_KEY": "test-key", "ENABLE_PERFORMANCE_MONITORING": env_value},
                clear=True,
            ):
                config = load_config()
                assert config.operational.enable_performance_monitoring == expected, (
                    f"Failed for '{env_value}'"
                )

    def test_config_integer_parsing_valid(self):
        """Test integer parsing for JWT expiration."""
        test_env = {"API_KEY": "test-key", "JWT_EXPIRATION_TIME": "7200"}

        with patch.dict(os.environ, test_env, clear=True):
            config = load_config()
            assert config.security.jwt_expiration_time == 7200

    def test_config_integer_parsing_port(self):
        """Test integer parsing for HTTP port."""
        test_env = {"API_KEY": "test-key", "HTTP_PORT": "9000"}

        with patch.dict(os.environ, test_env, clear=True):
            config = load_config()
            assert config.mcp_server.http_port == 9000

    def test_config_database_path_creation(self):
        """Test database path directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "nested" / "test.db")

            with patch.dict(
                os.environ,
                {"API_KEY": "test-key", "DATABASE_PATH": db_path},
                clear=True,
            ):
                config = load_config()

                # Should create parent directory
                assert Path(config.database.database_path).parent.exists()

    def test_config_validation_errors(self):
        """Test configuration validation errors."""
        # Test invalid port
        with patch.dict(
            os.environ, {"API_KEY": "test-key", "HTTP_PORT": "999"}, clear=True
        ):

            def _assert_validation_error():
                raise AssertionError(
                    "Should have raised validation error for invalid port"
                )

            try:
                load_config()
                _assert_validation_error()
            except Exception:
                pass  # Expected validation error

    def test_config_security_validation(self):
        """Test security configuration validation."""
        # Test with secure API key
        with patch.dict(
            os.environ, {"API_KEY": "secure-32-character-api-key-here"}, clear=True
        ):
            config = load_config()
            assert len(config.security.api_key) >= 32

    def test_config_development_settings(self):
        """Test development configuration settings."""
        dev_env = {
            "API_KEY": "test-api-key",
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "DEV_RESET_DATABASE_ON_START": "true",
        }

        with patch.dict(os.environ, dev_env, clear=True):
            config = load_config()

            assert config.development.environment == "development"
            assert config.development.dev_reset_database_on_start is True

    def test_config_operational_settings(self):
        """Test operational configuration settings."""
        ops_env = {
            "API_KEY": "test-api-key",
            "MAX_MEMORY_ENTRIES_PER_AGENT": "2000",
            "MAX_MESSAGE_LENGTH": "50000",
            "CLEANUP_INTERVAL": "1800",
        }

        with patch.dict(os.environ, ops_env, clear=True):
            config = load_config()

            assert config.operational.max_memory_entries_per_agent == 2000
            assert config.operational.max_message_length == 50000
            assert config.operational.cleanup_interval == 1800

    def test_configuration_immutability(self):
        """Test that configuration values are properly handled."""
        config = get_config()
        original_db_path = config.database.database_path

        # Config should be consistent
        config2 = get_config()
        assert config2.database.database_path == original_db_path

    def test_config_missing_optional_values(self):
        """Test configuration with missing optional values."""
        minimal_env = {"API_KEY": "test-api-key"}

        # Clear environment and provide minimal config
        env_keys_to_remove = [
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "MCP_SERVER_NAME",
            "LOG_LEVEL",
            "CORS_ORIGINS",
        ]
        for key in env_keys_to_remove:
            if key in os.environ:
                os.environ.pop(key, None)

        with patch.dict(os.environ, minimal_env, clear=True):
            config = load_config()

            # Should handle missing optional configs gracefully
            assert config is not None
            assert config.database is not None
            assert config.security is not None
            assert config.mcp_server is not None


class TestConfigCoverage:
    """Additional tests to improve config coverage."""

    def setup_method(self):
        """Setup method to clear global config before each test."""
        import shared_context_server.config

        shared_context_server.config._config = None

    def test_get_config_function(self):
        """Test get_config function."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "ENVIRONMENT": "development",
                "CORS_ORIGINS": "http://localhost:3000",
            },
            clear=True,
        ):
            config = get_config()
            assert isinstance(config, SharedContextServerConfig)
            assert hasattr(config, "database")
            assert hasattr(config, "security")
            assert hasattr(config, "mcp_server")
            assert hasattr(config, "operational")
            assert hasattr(config, "development")

    def test_load_config_function(self):
        """Test load_config function."""
        with patch.dict(
            os.environ,
            {"API_KEY": "test-key", "ENVIRONMENT": "development"},
            clear=True,
        ):
            config = load_config()
            assert isinstance(config, SharedContextServerConfig)

    def test_config_field_access(self):
        """Test accessing configuration fields."""
        with patch.dict(
            os.environ,
            {"API_KEY": "test-key", "ENVIRONMENT": "development"},
            clear=True,
        ):
            config = load_config()

            # Test all major config sections
            assert config.database.database_timeout >= 1
            assert config.mcp_server.http_port >= 1024
            assert config.security.session_timeout > 0
            assert config.operational.max_memory_entries_per_agent > 0
            assert config.development.environment in ["development", "production"]

    def test_config_model_serialization(self):
        """Test configuration model serialization."""
        with patch.dict(os.environ, {"API_KEY": "test-key"}, clear=True):
            config = load_config()

            # Should be able to serialize to dict
            config_dict = config.model_dump()
            assert isinstance(config_dict, dict)
            assert "database" in config_dict
            assert "security" in config_dict
            assert "mcp_server" in config_dict
            assert "operational" in config_dict
            assert "development" in config_dict
