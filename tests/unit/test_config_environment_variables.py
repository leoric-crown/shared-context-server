"""
Comprehensive environment variable handling tests for config.py.

Tests missing required environment variable detection, invalid value handling,
type conversion and validation, and default value application to achieve 85%+ coverage.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shared_context_server.config import (
    DatabaseConfig,
    DevelopmentConfig,
    MCPServerConfig,
    OperationalConfig,
    SecurityConfig,
    SharedContextServerConfig,
    get_database_url,
    load_config,
    validate_required_env_vars,
)


class TestEnvironmentVariableDetection:
    """Test missing required environment variable detection."""

    def test_missing_api_key_detection(self):
        """Test detection of missing API_KEY environment variable."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(
                ValueError, match="Required environment variables are missing"
            ),
        ):
            validate_required_env_vars()

    def test_missing_api_key_in_security_config(self):
        """Test SecurityConfig fails when API_KEY is missing."""
        with pytest.raises(
            ValueError, match="API_KEY environment variable is required"
        ):
            SecurityConfig(api_key="")

    def test_api_key_present_validation_success(self):
        """Test successful validation when API_KEY is present."""
        with patch.dict(os.environ, {"API_KEY": "test-api-key"}, clear=True):
            # Should not raise any exception
            validate_required_env_vars()

            # Should create config successfully
            config = SecurityConfig(api_key="test-api-key")
            assert config.api_key == "test-api-key"

    def test_multiple_missing_variables_detection(self):
        """Test detection when multiple required variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_required_env_vars()

            error_message = str(exc_info.value)
            assert "Required environment variables are missing" in error_message
            assert "API_KEY" in error_message
            assert "Quick fix:" in error_message
            assert "openssl rand -base64 32" in error_message

    def test_helpful_error_message_format(self):
        """Test that missing variable error messages are helpful and actionable."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_required_env_vars()

            error_message = str(exc_info.value)
            # Check for helpful formatting
            assert "❌" in error_message
            assert "Missing variables:" in error_message
            assert "Quick fix:" in error_message
            assert "Copy .env.example to .env" in error_message
            assert "Example .env content:" in error_message


class TestInvalidEnvironmentVariableHandling:
    """Test invalid environment variable value handling."""

    def test_invalid_database_timeout_values(self):
        """Test handling of invalid database timeout values."""
        # Test negative timeout
        with pytest.raises(
            ValueError, match="Timeout must be between 1 and 300 seconds"
        ):
            DatabaseConfig(database_timeout=-1)

        # Test zero timeout
        with pytest.raises(
            ValueError, match="Timeout must be between 1 and 300 seconds"
        ):
            DatabaseConfig(database_timeout=0)

        # Test timeout too high
        with pytest.raises(
            ValueError, match="Timeout must be between 1 and 300 seconds"
        ):
            DatabaseConfig(database_timeout=301)

    def test_invalid_database_busy_timeout_values(self):
        """Test handling of invalid database busy timeout values."""
        # Test negative busy timeout
        with pytest.raises(
            ValueError, match="Timeout must be between 1 and 300 seconds"
        ):
            DatabaseConfig(database_busy_timeout=-1)

        # Test zero busy timeout
        with pytest.raises(
            ValueError, match="Timeout must be between 1 and 300 seconds"
        ):
            DatabaseConfig(database_busy_timeout=0)

        # Test busy timeout too high
        with pytest.raises(
            ValueError, match="Timeout must be between 1 and 300 seconds"
        ):
            DatabaseConfig(database_busy_timeout=301)

    def test_invalid_max_connections_values(self):
        """Test handling of invalid max connections values."""
        # Test zero connections
        with pytest.raises(
            ValueError, match="Max connections must be between 1 and 100"
        ):
            DatabaseConfig(database_max_connections=0)

        # Test negative connections
        with pytest.raises(
            ValueError, match="Max connections must be between 1 and 100"
        ):
            DatabaseConfig(database_max_connections=-1)

        # Test too many connections
        with pytest.raises(
            ValueError, match="Max connections must be between 1 and 100"
        ):
            DatabaseConfig(database_max_connections=101)

    def test_invalid_http_port_values(self):
        """Test handling of invalid HTTP port values."""
        # Test port too low
        with pytest.raises(
            ValueError, match="HTTP port must be between 1024 and 65535"
        ):
            MCPServerConfig(http_port=1023)

        # Test port too high
        with pytest.raises(
            ValueError, match="HTTP port must be between 1024 and 65535"
        ):
            MCPServerConfig(http_port=65536)

        # Test negative port
        with pytest.raises(
            ValueError, match="HTTP port must be between 1024 and 65535"
        ):
            MCPServerConfig(http_port=-1)

    def test_invalid_api_key_production_detection(self):
        """Test detection of invalid API key in production environment."""
        # Test that SharedContextServerConfig validates API key in production
        from pydantic import ValidationError

        from shared_context_server.config import (
            DevelopmentConfig,
            SharedContextServerConfig,
        )

        with pytest.raises(
            ValidationError, match="Default API_KEY detected in production"
        ):
            SharedContextServerConfig(
                security=SecurityConfig(
                    api_key="your-secure-api-key-replace-this-in-production"
                ),
                development=DevelopmentConfig(environment="production"),
            )

    def test_invalid_cors_origins_handling(self):
        """Test handling of various CORS origins formats."""
        # Test empty CORS origins
        config = SecurityConfig(api_key="test-key", cors_origins="")
        assert config.cors_origins == [""]

        # Test single origin
        config = SecurityConfig(api_key="test-key", cors_origins="https://example.com")
        assert config.cors_origins == ["https://example.com"]

        # Test multiple origins with spaces
        config = SecurityConfig(
            api_key="test-key",
            cors_origins="http://localhost:3000, https://example.com , http://127.0.0.1",
        )
        assert config.cors_origins == [
            "http://localhost:3000",
            "https://example.com",
            "http://127.0.0.1",
        ]


class TestEnvironmentVariableTypeConversion:
    """Test environment variable type conversion and validation."""

    def test_string_to_integer_conversion(self):
        """Test conversion of string environment variables to integers."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "DATABASE_TIMEOUT": "45",
                "DATABASE_BUSY_TIMEOUT": "10",
                "DATABASE_MAX_CONNECTIONS": "25",
                "HTTP_PORT": "8080",
            },
            clear=True,
        ):
            config = load_config()

            assert config.database.database_timeout == 45
            assert config.database.database_busy_timeout == 10
            assert config.database.database_max_connections == 25
            assert config.mcp_server.http_port == 8080

    def test_string_to_boolean_conversion(self):
        """Test conversion of string environment variables to booleans."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "DEBUG": "true",
                "ENABLE_PERFORMANCE_MONITORING": "false",
                "ENABLE_AUTOMATIC_CLEANUP": "True",
                "DEV_RESET_DATABASE_ON_START": "False",
            },
            clear=True,
        ):
            config = load_config()

            assert config.development.debug is True
            assert config.operational.enable_performance_monitoring is False
            assert config.operational.enable_automatic_cleanup is True
            assert config.development.dev_reset_database_on_start is False

    def test_string_to_enum_conversion(self):
        """Test conversion of string environment variables to enums."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "LOG_LEVEL": "WARNING",
                "DATABASE_LOG_LEVEL": "ERROR",
                "MCP_TRANSPORT": "http",
                "ENVIRONMENT": "testing",
            },
            clear=True,
        ):
            config = load_config()

            assert config.operational.log_level == "WARNING"
            assert config.operational.database_log_level == "ERROR"
            assert config.mcp_server.mcp_transport == "http"
            assert config.development.environment == "testing"

    def test_invalid_type_conversion_handling(self):
        """Test handling of invalid type conversions."""
        # Test invalid integer conversion
        with (
            patch.dict(
                os.environ,
                {"API_KEY": "test-key", "DATABASE_TIMEOUT": "invalid"},
                clear=True,
            ),
            pytest.raises(ValueError),
        ):
            load_config()

        # Test invalid boolean conversion (should use default)
        with (
            patch.dict(
                os.environ, {"API_KEY": "test-key", "DEBUG": "maybe"}, clear=True
            ),
            pytest.raises(ValueError),
        ):
            load_config()

    def test_path_resolution_and_validation(self):
        """Test path resolution and validation for database paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "subdir" / "test.db")

            with patch.dict(
                os.environ,
                {"API_KEY": "test-key", "DATABASE_PATH": db_path},
                clear=True,
            ):
                config = load_config()

                # Path should be resolved and directory created
                resolved_path = Path(config.database.database_path)
                assert resolved_path.is_absolute()
                assert resolved_path.parent.exists()
                assert str(resolved_path).endswith("test.db")


class TestDefaultValueApplication:
    """Test default value application when environment variables are missing."""

    def test_database_config_defaults(self):
        """Test database configuration default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = DatabaseConfig()

            assert config.database_path == str(Path("./chat_history.db").resolve())
            assert config.database_url is None
            assert config.database_timeout == 30
            assert config.database_busy_timeout == 5
            assert config.database_max_connections == 20
            assert config.database_min_connections == 2
            assert config.audit_log_retention_days == 30
            assert config.inactive_session_retention_days == 7

    def test_mcp_server_config_defaults(self):
        """Test MCP server configuration default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = MCPServerConfig()

            assert config.mcp_server_name == "shared-context-server"
            assert config.mcp_server_version == "1.0.0"
            assert config.mcp_transport == "stdio"
            assert config.http_host == "localhost"
            assert config.http_port == 23456

    def test_operational_config_defaults(self):
        """Test operational configuration default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = OperationalConfig()

            assert config.log_level == "INFO"
            assert (
                config.log_format
                == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            assert config.database_log_level == "INFO"
            assert config.enable_performance_monitoring is True
            assert config.performance_log_interval == 300
            assert config.max_memory_entries_per_agent == 1000
            assert config.max_memory_size_mb == 100
            assert config.max_message_length == 100000
            assert config.max_messages_per_session == 10000
            assert config.max_metadata_size_kb == 10
            assert config.enable_automatic_cleanup is True
            assert config.cleanup_interval == 3600

    def test_development_config_defaults(self):
        """Test development configuration default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = DevelopmentConfig()

            assert config.environment == "development"
            assert config.debug is False
            assert config.enable_debug_tools is False
            assert config.dev_reset_database_on_start is False
            assert config.dev_seed_test_data is False
            # Test database path uses smart detection now
            assert "test_chat_history.db" in config.test_database_path
            assert config.test_database_path.endswith("test_chat_history.db")

    def test_security_config_defaults_with_api_key(self):
        """Test security configuration default values when API key is provided."""
        with patch.dict(os.environ, {}, clear=True):
            config = SecurityConfig(api_key="test-api-key")

            assert config.api_key == "test-api-key"
            # jwt_secret_key might have a default value from environment
            assert config.jwt_expiration_time == 86400
            assert config.session_timeout == 3600
            assert config.max_sessions_per_agent == 50
            assert config.cors_origins == ["*"]
            # allowed_hosts is stored as string, not parsed like cors_origins
            assert config.allowed_hosts == "localhost,127.0.0.1"

    def test_main_config_default_initialization(self):
        """Test main configuration default section initialization."""
        with patch.dict(os.environ, {"API_KEY": "test-key"}, clear=True):
            config = SharedContextServerConfig()

            # All sections should be initialized with defaults
            assert config.database is not None
            assert config.mcp_server is not None
            assert config.security is not None
            assert config.operational is not None
            assert config.development is not None

            # Check that defaults are applied
            assert config.database.database_timeout == 30
            assert config.mcp_server.mcp_transport == "stdio"
            assert config.operational.log_level == "INFO"
            assert config.development.environment == "development"

    def test_partial_environment_override_with_defaults(self):
        """Test that partial environment variables override defaults correctly."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "DATABASE_TIMEOUT": "60",  # Override default
                "LOG_LEVEL": "DEBUG",  # Override default
                # Other values should use defaults
            },
            clear=True,
        ):
            config = load_config()

            # Overridden values
            assert config.database.database_timeout == 60
            assert config.operational.log_level == "DEBUG"

            # Default values should still be used
            assert config.database.database_busy_timeout == 5  # Default
            assert config.mcp_server.http_port == 23456  # Default
            assert config.operational.enable_performance_monitoring is True  # Default

    def test_database_url_fallback_behavior(self):
        """Test database URL fallback to database path when URL not provided."""
        with patch.dict(
            os.environ,
            {"API_KEY": "test-key", "DATABASE_PATH": "./custom.db"},
            clear=True,
        ):
            # Force reload to pick up new environment
            from shared_context_server.config import reload_config

            reload_config()
            url = get_database_url()

            # Should fallback to path-based URL
            assert url.startswith("sqlite:///")
            # The path might be resolved to absolute path, so just check it's a valid sqlite URL
            assert ".db" in url

        # Test with DATABASE_URL provided
        with patch.dict(
            os.environ,
            {"API_KEY": "test-key", "DATABASE_URL": "sqlite:///explicit.db"},
            clear=True,
        ):
            # Force reload to pick up new environment
            reload_config()
            url = get_database_url()

            # Should use explicit URL
            assert url == "sqlite:///explicit.db"


class TestEnvironmentVariableEdgeCases:
    """Test edge cases in environment variable handling."""

    def test_empty_string_environment_variables(self):
        """Test handling of empty string environment variables."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "MCP_SERVER_NAME": "",  # Empty string
                "CORS_ORIGINS": "",  # Empty string
            },
            clear=True,
        ):
            config = load_config()

            # Empty string should be preserved
            assert config.mcp_server.mcp_server_name == ""
            assert config.security.cors_origins == [""]

    def test_whitespace_environment_variables(self):
        """Test handling of whitespace-only environment variables."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "MCP_SERVER_NAME": "   ",  # Whitespace only
                "CORS_ORIGINS": " http://localhost:3000 , https://example.com ",  # With spaces
            },
            clear=True,
        ):
            config = load_config()

            # Whitespace should be preserved in server name
            assert config.mcp_server.mcp_server_name == "   "

            # CORS origins should be trimmed
            assert config.security.cors_origins == [
                "http://localhost:3000",
                "https://example.com",
            ]

    def test_special_characters_in_environment_variables(self):
        """Test handling of special characters in environment variables."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key-with-special-chars!@#$%^&*()",
                "MCP_SERVER_NAME": "server-with-unicode-🚀",
                "DATABASE_PATH": "./test-db-with-spaces and special chars.db",
            },
            clear=True,
        ):
            config = load_config()

            # Special characters should be preserved
            assert config.security.api_key == "test-key-with-special-chars!@#$%^&*()"
            assert config.mcp_server.mcp_server_name == "server-with-unicode-🚀"
            assert (
                "test-db-with-spaces and special chars.db"
                in config.database.database_path
            )

    def test_very_long_environment_variables(self):
        """Test handling of very long environment variable values."""
        long_api_key = "a" * 1000  # Very long API key
        long_server_name = "server-" + "x" * 500

        with patch.dict(
            os.environ,
            {
                "API_KEY": long_api_key,
                "MCP_SERVER_NAME": long_server_name,
            },
            clear=True,
        ):
            config = load_config()

            # Long values should be preserved
            assert config.security.api_key == long_api_key
            assert config.mcp_server.mcp_server_name == long_server_name
            assert len(config.security.api_key) == 1000
            assert len(config.mcp_server.mcp_server_name) == 507  # "server-" + 500 x's

    def test_numeric_string_edge_cases(self):
        """Test edge cases with numeric string conversions."""
        with patch.dict(
            os.environ,
            {
                "API_KEY": "test-key",
                "DATABASE_TIMEOUT": "1",  # Minimum valid value
                "DATABASE_MAX_CONNECTIONS": "100",  # Maximum valid value
                "HTTP_PORT": "1024",  # Minimum valid port
            },
            clear=True,
        ):
            config = load_config()

            # Edge case values should be accepted
            assert config.database.database_timeout == 1
            assert config.database.database_max_connections == 100
            assert config.mcp_server.http_port == 1024
