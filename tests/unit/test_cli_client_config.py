"""
Test coverage for CLI client configuration generation.

This module tests the client configuration generation functions for various
MCP clients including Claude, Cursor, VS Code, etc. Focus is on behavior-first
testing of configuration output and parameter handling.
"""

import sys
from unittest.mock import Mock, patch

import pytest

from shared_context_server.scripts.cli import (
    _extract_clipboard_content,
    _generate_claude_config,
    _generate_claude_desktop_config,
    _generate_codex_config,
    _generate_cursor_config,
    _generate_gemini_config,
    _generate_http_json_config,
    _generate_kiro_config,
    _generate_qwen_config,
    _generate_vscode_config,
    _generate_windsurf_config,
    _handle_clipboard,
    generate_client_config,
)


class TestCLIClientConfig:
    """Test CLI client configuration generation with behavior-first approach."""

    # =============================================================================
    # HTTP JSON CONFIG GENERATION
    # =============================================================================

    def test_generate_http_json_config_basic(self):
        """Test basic HTTP JSON configuration generation."""
        result = _generate_http_json_config(
            server_url="http://localhost:8000/mcp/", api_key="test_api_key"
        )

        assert '"url": "http://localhost:8000/mcp/"' in result
        assert '"X-API-Key": "test_api_key"' in result
        assert '"shared-context-server"' in result

    def test_generate_http_json_config_no_api_key(self):
        """Test HTTP JSON config with placeholder API key."""
        result = _generate_http_json_config(
            server_url="http://localhost:8000/mcp/", api_key="YOUR_API_KEY_HERE"
        )

        assert '"X-API-Key": "YOUR_API_KEY_HERE"' in result

    # =============================================================================
    # CLAUDE CONFIG GENERATION
    # =============================================================================

    def test_generate_claude_config_local_scope(self):
        """Test Claude configuration generation with local scope."""
        result = _generate_claude_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key", scope="local"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result
        assert "Scope: local" in result

    def test_generate_claude_config_user_scope(self):
        """Test Claude configuration generation with user scope."""
        result = _generate_claude_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key", scope="user"
        )

        assert "-s user" in result
        assert "shared-context-server" in result

    def test_generate_claude_config_project_scope(self):
        """Test Claude configuration generation with project scope."""
        result = _generate_claude_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key", scope="project"
        )

        assert "-s project" in result
        assert "shared-context-server" in result

    def test_generate_claude_config_dynamic_scope(self):
        """Test Claude configuration generation with dynamic scope."""
        result = _generate_claude_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key", scope="dynamic"
        )

        assert "-s dynamic" in result
        assert "shared-context-server" in result

    # =============================================================================
    # OTHER CLIENT CONFIGS
    # =============================================================================

    def test_generate_claude_desktop_config(self):
        """Test Claude Desktop configuration generation."""
        result = _generate_claude_desktop_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert '"shared-context-server"' in result
        assert '"http://localhost:8000/mcp/"' in result
        assert '"test_key"' in result
        assert "mcpServers" in result

    def test_generate_cursor_config(self):
        """Test Cursor configuration generation."""
        result = _generate_cursor_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_windsurf_config(self):
        """Test Windsurf configuration generation."""
        result = _generate_windsurf_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_vscode_config(self):
        """Test VS Code configuration generation."""
        result = _generate_vscode_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_gemini_config(self):
        """Test Gemini configuration generation."""
        result = _generate_gemini_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_codex_config(self):
        """Test Codex configuration generation."""
        result = _generate_codex_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_qwen_config(self):
        """Test Qwen configuration generation."""
        result = _generate_qwen_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_kiro_config(self):
        """Test Kiro configuration generation."""
        result = _generate_kiro_config(
            server_url="http://localhost:8000/mcp/", api_key="test_key"
        )

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    # =============================================================================
    # MAIN GENERATE_CLIENT_CONFIG FUNCTION
    # =============================================================================

    @patch("shared_context_server.scripts.cli.print")
    @patch("os.getenv")
    def test_generate_client_config_claude_with_api_key(self, mock_getenv, mock_print):
        """Test generate_client_config for Claude with API key from environment."""
        mock_getenv.return_value = "env_api_key"

        generate_client_config(
            client="claude",
            host="localhost",
            port=8000,
            scope="local",
            copy_behavior="no_copy",
        )

        # Verify os.getenv was called for API_KEY
        mock_getenv.assert_called_with("API_KEY", "")

        # Verify print was called with configuration
        assert mock_print.call_count > 0
        # Check that the printed content contains expected elements
        printed_content = "".join([str(call) for call in mock_print.call_args_list])
        assert "CLAUDE MCP Client Configuration" in printed_content

    @patch("shared_context_server.scripts.cli.print")
    @patch("os.getenv")
    def test_generate_client_config_no_api_key_in_env(self, mock_getenv, mock_print):
        """Test generate_client_config when no API key in environment."""
        mock_getenv.return_value = ""  # No API key in environment

        generate_client_config(
            client="claude-desktop",
            host="127.0.0.1",
            port=9000,
            scope="local",
            copy_behavior="no_copy",
        )

        # Should use placeholder
        printed_content = "".join([str(call) for call in mock_print.call_args_list])
        assert "YOUR_API_KEY_HERE" in printed_content

    @patch("shared_context_server.scripts.cli.print")
    @patch("os.getenv")
    def test_generate_client_config_scope_warning_for_non_claude(
        self, mock_getenv, mock_print
    ):
        """Test scope warning for non-Claude clients."""
        mock_getenv.return_value = "test_key"

        generate_client_config(
            client="cursor",
            host="localhost",
            port=8000,
            scope="user",  # Invalid for cursor
            copy_behavior="no_copy",
        )

        # Should print warning about scope
        printed_content = "".join([str(call) for call in mock_print.call_args_list])
        assert (
            "Warning: --scope/-s flag is only supported for Claude Code"
            in printed_content
        )

    @patch("shared_context_server.scripts.cli.print")
    @patch("os.getenv")
    def test_generate_client_config_no_scope_warning_for_claude(
        self, mock_getenv, mock_print
    ):
        """Test no scope warning for Claude clients."""
        mock_getenv.return_value = "test_key"

        generate_client_config(
            client="claude",
            host="localhost",
            port=8000,
            scope="user",
            copy_behavior="no_copy",
        )

        # Should NOT print warning about scope for Claude
        printed_content = "".join([str(call) for call in mock_print.call_args_list])
        assert "Warning: --scope/-s flag is only supported" not in printed_content

    def test_generate_client_config_unsupported_client(self):
        """Test generate_client_config with unsupported client type."""
        with pytest.raises(ValueError, match="Unsupported client type: unknown_client"):
            generate_client_config(
                client="unknown_client",
                host="localhost",
                port=8000,
                scope="local",
                copy_behavior="no_copy",
            )

    @patch("shared_context_server.scripts.cli.print")
    @patch("os.getenv")
    def test_generate_client_config_server_url_formation(self, mock_getenv, mock_print):
        """Test server URL formation with different hosts and ports."""
        mock_getenv.return_value = "test_key"

        generate_client_config(
            client="claude",
            host="192.168.1.100",
            port=3000,
            scope="local",
            copy_behavior="no_copy",
        )

        printed_content = "".join([str(call) for call in mock_print.call_args_list])
        assert "http://192.168.1.100:3000/mcp/" in printed_content

    @patch("shared_context_server.scripts.cli.print")
    @patch("os.getenv")
    def test_generate_client_config_all_supported_clients(
        self, mock_getenv, mock_print
    ):
        """Test generate_client_config for all supported client types."""
        mock_getenv.return_value = "test_key"

        supported_clients = [
            "claude",
            "claude-desktop",
            "cursor",
            "windsurf",
            "vscode",
            "gemini",
            "codex",
            "qwen",
            "kiro",
        ]

        for client in supported_clients:
            mock_print.reset_mock()

            generate_client_config(
                client=client,
                host="localhost",
                port=8000,
                scope="local",
                copy_behavior="no_copy",
            )

            # Each client should produce some configuration output
            assert mock_print.call_count > 0
            printed_content = "".join([str(call) for call in mock_print.call_args_list])
            assert "shared-context-server" in printed_content

    # =============================================================================
    # EDGE CASES AND VALIDATION
    # =============================================================================

    def test_config_generators_handle_empty_strings(self):
        """Test that config generators handle empty string inputs gracefully."""
        generators = [
            _generate_claude_config,
            _generate_claude_desktop_config,
            _generate_cursor_config,
            _generate_windsurf_config,
            _generate_vscode_config,
            _generate_gemini_config,
            _generate_codex_config,
            _generate_qwen_config,
            _generate_kiro_config,
        ]

        for generator in generators:
            if generator == _generate_claude_config:
                # Claude config needs scope parameter
                result = generator("", "", "local")
            else:
                result = generator("", "")

            # Should return a string without crashing
            assert isinstance(result, str)
            assert len(result) > 0

    def test_config_generators_handle_special_characters(self):
        """Test that config generators handle special characters in URLs and keys."""
        special_url = "http://test-server.com:8000/mcp/"
        special_key = "test_key_with-special.chars_123"

        generators = [
            _generate_claude_config,
            _generate_claude_desktop_config,
            _generate_cursor_config,
        ]

        for generator in generators:
            if generator == _generate_claude_config:
                result = generator(special_url, special_key, "local")
            else:
                result = generator(special_url, special_key)

            assert special_url in result
            assert special_key in result

    def test_http_json_config_structure(self):
        """Test that HTTP JSON config has proper JSON structure markers."""
        result = _generate_http_json_config("http://localhost:8000/mcp/", "test_key")

        # Should contain JSON structural elements
        assert "{" in result
        assert "}" in result
        assert ":" in result
        assert '"' in result

    def test_claude_config_scope_variations(self):
        """Test Claude config generation with all scope variations."""
        scopes = ["local", "user", "project", "dynamic"]

        for scope in scopes:
            result = _generate_claude_config(
                "http://localhost:8000/mcp/", "test_key", scope
            )

            # Each scope should produce different output
            assert scope in result.lower() or "scope" in result
            assert "shared-context-server" in result

    @patch("shared_context_server.scripts.cli.print")
    @patch("os.getenv")
    def test_generate_client_config_whitespace_api_key(self, mock_getenv, mock_print):
        """Test generate_client_config with whitespace in API key."""
        mock_getenv.return_value = "  test_key  "  # API key with whitespace

        generate_client_config(
            client="claude",
            host="localhost",
            port=8000,
            scope="local",
            copy_behavior="no_copy",
        )

        # Should strip whitespace and use the key
        printed_content = "".join([str(call) for call in mock_print.call_args_list])
        assert "test_key" in printed_content
        assert "  test_key  " not in printed_content

    # =============================================================================
    # CLIPBOARD UTILITIES
    # =============================================================================

    def test_extract_clipboard_content_basic(self):
        """Test basic clipboard content extraction."""
        formatted_text = """Configuration for Claude Code:

        claude mcp add shared-context-server

        Some additional text"""

        result = _extract_clipboard_content(formatted_text)
        # Should strip extra whitespace
        assert "claude mcp add shared-context-server" in result

    def test_extract_clipboard_content_multiline_json(self):
        """Test clipboard extraction with JSON configuration."""
        formatted_text = """Configuration:

        {
          "type": "http",
          "url": "http://localhost:8000/mcp/",
          "headers": {
            "X-API-Key": "test_key"
          }
        }"""

        result = _extract_clipboard_content(formatted_text)
        assert '"type": "http"' in result
        assert '"url": "http://localhost:8000/mcp/"' in result
        assert '"X-API-Key": "test_key"' in result

    def test_extract_clipboard_content_empty(self):
        """Test clipboard extraction with empty content."""
        result = _extract_clipboard_content("")
        assert result == ""

    def test_extract_clipboard_content_whitespace_only(self):
        """Test clipboard extraction with only whitespace."""
        result = _extract_clipboard_content("   \n\t   \n   ")
        assert result == ""

    def test_handle_clipboard_copy_success(self):
        """Test clipboard handling with successful copy."""

        # Create a mock Colors class with all required attributes
        class MockColors:
            GREEN = "\033[32m"
            YELLOW = "\033[33m"
            NC = "\033[0m"

        # Create a mock pyperclip module
        mock_pyperclip = Mock()
        mock_pyperclip.copy = Mock()

        # Mock sys.modules to include pyperclip before the import
        original_modules = sys.modules.copy()
        sys.modules["pyperclip"] = mock_pyperclip

        try:
            # Should not raise exception and should call copy
            _handle_clipboard("test content", "copy", MockColors)
            assert mock_pyperclip.copy.called, "pyperclip.copy should have been called"
        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)

    def test_handle_clipboard_copy_failure(self):
        """Test clipboard handling when copy fails."""

        class MockColors:
            GREEN = "\033[32m"
            YELLOW = "\033[33m"
            RED = "\033[31m"
            NC = "\033[0m"

        # Create a mock pyperclip module with failing copy
        mock_pyperclip = Mock()
        mock_pyperclip.copy = Mock(side_effect=Exception("Clipboard not available"))

        # Mock sys.modules to include pyperclip before the import
        original_modules = sys.modules.copy()
        sys.modules["pyperclip"] = mock_pyperclip

        try:
            # Should handle failure gracefully (no exception)
            _handle_clipboard("test content", "copy", MockColors)
            assert mock_pyperclip.copy.called, "pyperclip.copy should have been called"
        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)

    @patch("builtins.input")
    def test_handle_clipboard_prompt_yes(self, mock_input):
        """Test clipboard handling with prompt accepting."""
        mock_input.return_value = "y"

        class MockColors:
            YELLOW = "\033[33m"
            GREEN = "\033[32m"
            NC = "\033[0m"

        # Create a mock pyperclip module
        mock_pyperclip = Mock()
        mock_pyperclip.copy = Mock()

        # Mock sys.modules to include pyperclip before the import
        original_modules = sys.modules.copy()
        sys.modules["pyperclip"] = mock_pyperclip

        try:
            _handle_clipboard("test content", "prompt", MockColors)
            assert mock_input.called, "input should have been called for prompt"
            assert mock_pyperclip.copy.called, "pyperclip.copy should have been called"
        finally:
            # Restore original modules
            sys.modules.clear()
            sys.modules.update(original_modules)

    @patch("builtins.input")
    @patch("subprocess.run")
    def test_handle_clipboard_prompt_no(self, mock_run, mock_input):
        """Test clipboard handling with prompt declining."""
        mock_input.return_value = "n"

        class MockColors:
            YELLOW = "\033[33m"
            NC = "\033[0m"

        _handle_clipboard("test content", "prompt", MockColors)
        assert mock_input.called
        assert not mock_run.called

    def test_handle_clipboard_no_copy(self):
        """Test clipboard handling with no_copy behavior."""

        class MockColors:
            pass

        # Should do nothing (no exception)
        _handle_clipboard("test content", "no_copy", MockColors)
