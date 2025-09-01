"""
Test coverage for startup validation utilities.

This module tests the startup validation functions including environment
validation, configuration loading, and development server setup validation.
Focus is on behavior-first testing with environment mocking.
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

from shared_context_server.scripts.dev import validate_environment


class TestStartupValidation:
    """Test startup validation behavior with focus on environment setup."""

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_success(self, mock_load_config, mock_logger):
        """Test successful environment validation."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "/tmp/test.db"
        mock_config.development.debug = True
        mock_config.development.dev_reset_database_on_start = False
        mock_load_config.return_value = mock_config

        # Mock Path.mkdir to avoid filesystem operations
        with patch.object(Path, "mkdir") as mock_mkdir:
            result = validate_environment()

        assert result is True
        mock_load_config.assert_called_once()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify logging calls
        expected_calls = [
            call("Validating development environment..."),
            call("✓ Configuration loaded successfully"),
            call("✓ API_KEY is configured"),
            call(f"✓ Database path accessible: {Path('/tmp/test.db')}"),
            call("✓ Debug mode enabled"),
            call("Environment validation completed successfully"),
        ]
        mock_logger.info.assert_has_calls(expected_calls)

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_missing_api_key(self, mock_load_config, mock_logger):
        """Test environment validation with missing API key."""
        # Mock configuration with missing API key
        mock_config = MagicMock()
        mock_config.security.api_key = None
        mock_config.database.database_path = "/tmp/test.db"
        mock_load_config.return_value = mock_config

        result = validate_environment()

        assert result is False
        mock_logger.error.assert_called_once_with("✗ API_KEY not set")

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_empty_api_key(self, mock_load_config, mock_logger):
        """Test environment validation with empty API key."""
        # Mock configuration with empty API key
        mock_config = MagicMock()
        mock_config.security.api_key = ""
        mock_config.database.database_path = "/tmp/test.db"
        mock_load_config.return_value = mock_config

        result = validate_environment()

        assert result is False
        mock_logger.error.assert_called_once_with("✗ API_KEY not set")

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_database_reset_warning(
        self, mock_load_config, mock_logger
    ):
        """Test warning when database reset on start is enabled."""
        # Mock configuration with database reset enabled
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "/tmp/test.db"
        mock_config.development.debug = False
        mock_config.development.dev_reset_database_on_start = True
        mock_load_config.return_value = mock_config

        with patch.object(Path, "mkdir"):
            result = validate_environment()

        assert result is True
        mock_logger.warning.assert_called_once_with(
            "⚠ Database reset on start is enabled"
        )

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_config_load_exception(
        self, mock_load_config, mock_logger
    ):
        """Test environment validation when config loading fails."""
        mock_load_config.side_effect = ValueError("Config loading failed")

        result = validate_environment()

        assert result is False
        mock_logger.exception.assert_called_once_with("✗ Environment validation failed")

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_path_creation_exception(
        self, mock_load_config, mock_logger
    ):
        """Test environment validation when database path creation fails."""
        # Mock configuration
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "/invalid/path/test.db"
        mock_load_config.return_value = mock_config

        # Mock Path.mkdir to raise an exception
        with patch.object(
            Path, "mkdir", side_effect=PermissionError("Permission denied")
        ):
            result = validate_environment()

        assert result is False
        mock_logger.exception.assert_called_once_with("✗ Environment validation failed")

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_debug_mode_disabled(
        self, mock_load_config, mock_logger
    ):
        """Test environment validation when debug mode is disabled."""
        # Mock configuration with debug disabled
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "/tmp/test.db"
        mock_config.development.debug = False
        mock_config.development.dev_reset_database_on_start = False
        mock_load_config.return_value = mock_config

        with patch.object(Path, "mkdir"):
            result = validate_environment()

        assert result is True
        # Should not log debug mode enabled message
        debug_calls = [
            call
            for call in mock_logger.info.call_args_list
            if "Debug mode enabled" in str(call)
        ]
        assert len(debug_calls) == 0

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_path_relative(self, mock_load_config, mock_logger):
        """Test environment validation with relative database path."""
        # Mock configuration with relative path
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "data/test.db"
        mock_config.development.debug = False
        mock_config.development.dev_reset_database_on_start = False
        mock_load_config.return_value = mock_config

        with patch.object(Path, "mkdir") as mock_mkdir:
            result = validate_environment()

        assert result is True
        # Path should be created for parent directory
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_all_options_enabled(
        self, mock_load_config, mock_logger
    ):
        """Test environment validation with all development options enabled."""
        # Mock configuration with all development features
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "/tmp/test.db"
        mock_config.development.debug = True
        mock_config.development.dev_reset_database_on_start = True
        mock_load_config.return_value = mock_config

        with patch.object(Path, "mkdir"):
            result = validate_environment()

        assert result is True

        # Should log both debug and reset warnings
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]

        assert any("Debug mode enabled" in call for call in info_calls)
        assert any(
            "Database reset on start is enabled" in call for call in warning_calls
        )

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_generic_exception(
        self, mock_load_config, mock_logger
    ):
        """Test environment validation with generic exception during validation."""
        # Mock configuration that passes initial checks
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "/tmp/test.db"
        mock_load_config.return_value = mock_config

        # Mock Path to raise unexpected exception
        with patch(
            "shared_context_server.scripts.dev.Path",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = validate_environment()

        assert result is False
        mock_logger.exception.assert_called_once_with("✗ Environment validation failed")

    def test_validate_environment_import_available(self):
        """Test that validate_environment can be imported successfully."""
        from shared_context_server.scripts.dev import (
            validate_environment as imported_func,
        )

        assert imported_func is not None
        assert callable(imported_func)

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_logging_order(self, mock_load_config, mock_logger):
        """Test that logging messages appear in correct order."""
        mock_config = MagicMock()
        mock_config.security.api_key = "test_api_key"
        mock_config.database.database_path = "/tmp/test.db"
        mock_config.development.debug = True
        mock_config.development.dev_reset_database_on_start = False
        mock_load_config.return_value = mock_config

        with patch.object(Path, "mkdir"):
            result = validate_environment()

        assert result is True

        # Check that initial validation message comes first
        first_call = mock_logger.info.call_args_list[0]
        assert "Validating development environment..." in str(first_call)

        # Check that completion message comes last
        last_call = mock_logger.info.call_args_list[-1]
        assert "Environment validation completed successfully" in str(last_call)

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_whitespace_api_key(
        self, mock_load_config, mock_logger
    ):
        """Test environment validation with whitespace-only API key."""
        mock_config = MagicMock()
        mock_config.security.api_key = "   "  # Whitespace only
        mock_config.database.database_path = "/tmp/test.db"
        mock_config.development.debug = False
        mock_config.development.dev_reset_database_on_start = False
        mock_load_config.return_value = mock_config

        with patch.object(Path, "mkdir"):
            result = validate_environment()

        # Whitespace-only is truthy, so validation should pass
        assert result is True
        mock_logger.info.assert_any_call("✓ API_KEY is configured")

    @patch("shared_context_server.scripts.dev.logger")
    @patch("shared_context_server.scripts.dev.load_config")
    def test_validate_environment_boolean_checks(self, mock_load_config, mock_logger):
        """Test boolean evaluation of development flags."""
        mock_config = MagicMock()
        mock_config.security.api_key = "test_key"
        mock_config.database.database_path = "/tmp/test.db"

        # Test falsy values for boolean flags
        mock_config.development.debug = 0  # Falsy but not False
        mock_config.development.dev_reset_database_on_start = ""  # Falsy string
        mock_load_config.return_value = mock_config

        with patch.object(Path, "mkdir"):
            result = validate_environment()

        assert result is True

        # Should not log messages for falsy values
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]

        assert not any("Debug mode enabled" in call for call in info_calls)
        assert not any(
            "Database reset on start is enabled" in call for call in warning_calls
        )
