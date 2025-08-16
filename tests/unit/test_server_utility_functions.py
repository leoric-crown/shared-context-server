"""
Test coverage for server utility functions and error paths.

This module focuses on testing the smaller utility functions in server.py
that are currently uncovered, aiming to improve overall test coverage.
"""

from unittest.mock import MagicMock, patch

import pytest

from shared_context_server.server import (
    _generate_agent_type_field_description,
    _generate_authenticate_agent_docstring,
    _raise_session_not_found_error,
    _raise_unauthorized_access_error,
)


class TestServerUtilityFunctions:
    """Test utility functions and error handling in server.py."""

    def test_raise_session_not_found_error(self):
        """Test session not found error raising."""
        with pytest.raises(ValueError, match="Session test-session not found"):
            _raise_session_not_found_error("test-session")

    def test_raise_unauthorized_access_error(self):
        """Test unauthorized access error raising."""
        with pytest.raises(
            ValueError, match="Unauthorized access to agent memory for test-agent"
        ):
            _raise_unauthorized_access_error("test-agent")

    def test_generate_agent_type_field_description_success(self):
        """Test successful generation of agent type field description."""
        mock_config = MagicMock()
        mock_config.agent_type_permissions = {
            "admin": ["read", "write", "admin"],
            "claude": ["read", "write"],
            "gemini": ["read", "write"],
            "generic": ["read"],
        }

        with patch(
            "shared_context_server.config.get_agent_permissions_config",
            return_value=mock_config,
        ):
            result = _generate_agent_type_field_description()

            assert "Agent type - determines base permissions" in result
            assert "admin" in result
            assert "claude" in result or "gemini" in result

    def test_generate_agent_type_field_description_multiple_admin_types(self):
        """Test description generation with multiple admin types."""
        mock_config = MagicMock()
        mock_config.agent_type_permissions = {
            "admin": ["read", "write", "admin"],
            "system": ["read", "write", "admin"],
            "claude": ["read", "write"],
        }

        with patch(
            "shared_context_server.config.get_agent_permissions_config",
            return_value=mock_config,
        ):
            result = _generate_agent_type_field_description()

            assert "admin" in result and "system" in result
            assert " or " in result

    def test_generate_agent_type_field_description_no_admin_types(self):
        """Test description generation with no admin types."""
        mock_config = MagicMock()
        mock_config.agent_type_permissions = {
            "claude": ["read", "write"],
            "generic": ["read"],
        }

        with patch(
            "shared_context_server.config.get_agent_permissions_config",
            return_value=mock_config,
        ):
            result = _generate_agent_type_field_description()

            assert "No admin types configured" in result

    def test_generate_agent_type_field_description_no_key_types(self):
        """Test description generation with no standard key types."""
        mock_config = MagicMock()
        mock_config.agent_type_permissions = {
            "admin": ["read", "write", "admin"],
            "custom": ["read", "write"],
        }

        with patch(
            "shared_context_server.config.get_agent_permissions_config",
            return_value=mock_config,
        ):
            result = _generate_agent_type_field_description()

            assert "standard agents" in result

    def test_generate_agent_type_field_description_config_exception(self):
        """Test fallback when config loading fails."""
        with patch(
            "shared_context_server.config.get_agent_permissions_config",
            side_effect=Exception("Config error"),
        ):
            result = _generate_agent_type_field_description()

            # Should return fallback description
            assert "Agent type - determines base permissions" in result
            assert "admin" in result
            assert "claude" in result

    def test_generate_authenticate_agent_docstring_success(self):
        """Test successful generation of authenticate agent docstring."""
        mock_config = MagicMock()
        mock_config.generate_agent_types_docstring.return_value = (
            "**Agent Types:**\n- admin: Full access"
        )

        with patch(
            "shared_context_server.config.get_agent_permissions_config",
            return_value=mock_config,
        ):
            result = _generate_authenticate_agent_docstring()

            assert "Generate JWT token for agent authentication" in result
            assert "Agent Types:" in result
            assert "admin: Full access" in result

    def test_generate_authenticate_agent_docstring_config_exception(self):
        """Test fallback when config loading fails for docstring."""
        with patch(
            "shared_context_server.config.get_agent_permissions_config",
            side_effect=Exception("Config error"),
        ):
            result = _generate_authenticate_agent_docstring()

            # Should return fallback docstring
            assert "Generate JWT token for agent authentication" in result
            assert "validates the MCP client's API key" in result
