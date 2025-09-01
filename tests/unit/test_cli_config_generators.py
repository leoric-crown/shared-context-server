"""
Test coverage for CLI configuration generator functions.

This module tests the individual config generation functions for MCP clients,
focusing on behavior-first testing of configuration output format and content.
These are utility functions with clear input/output behavior.
"""

from shared_context_server.scripts.cli import (
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
)


class TestCLIConfigGenerators:
    """Test CLI config generation utility functions with behavior-first approach."""

    # =============================================================================
    # HTTP JSON CONFIG GENERATION
    # =============================================================================

    def test_generate_http_json_config_contains_required_fields(self):
        """Test HTTP JSON config includes all required JSON structure elements."""
        result = _generate_http_json_config(
            server_url="http://localhost:8000/mcp/", api_key="test_api_key"
        )

        # Verify JSON structure markers and required fields
        assert "{" in result
        assert "}" in result
        assert '"shared-context-server"' in result
        assert '"url": "http://localhost:8000/mcp/"' in result
        assert '"X-API-Key": "test_api_key"' in result

    def test_generate_http_json_config_handles_different_urls(self):
        """Test HTTP JSON config works with various server URLs."""
        test_cases = [
            ("http://localhost:3000/mcp/", "key1"),
            ("https://remote-server.com:8080/mcp/", "key2"),
            ("http://192.168.1.100:9000/mcp/", "key3"),
        ]

        for url, key in test_cases:
            result = _generate_http_json_config(url, key)
            assert f'"url": "{url}"' in result
            assert f'"X-API-Key": "{key}"' in result

    def test_generate_http_json_config_escapes_special_characters(self):
        """Test HTTP JSON config handles special characters in API keys."""
        special_key = "api-key_with.special/chars&symbols"
        result = _generate_http_json_config("http://localhost:8000/mcp/", special_key)

        assert f'"X-API-Key": "{special_key}"' in result

    # =============================================================================
    # CLAUDE CONFIG GENERATION
    # =============================================================================

    def test_generate_claude_config_includes_scope_parameters(self):
        """Test Claude config includes correct scope flags."""
        test_scopes = ["local", "user", "project", "dynamic"]
        server_url = "http://localhost:8000/mcp/"
        api_key = "test_key"

        for scope in test_scopes:
            result = _generate_claude_config(server_url, api_key, scope)

            # Check for scope-specific content
            if scope != "local":
                assert f"-s {scope}" in result
            assert "shared-context-server" in result
            assert server_url in result
            assert api_key in result

    def test_generate_claude_config_handles_empty_parameters(self):
        """Test Claude config handles empty string parameters gracefully."""
        result = _generate_claude_config("", "", "local")

        # Should return a valid string without crashing
        assert isinstance(result, str)
        assert len(result) > 0
        assert "shared-context-server" in result

    # =============================================================================
    # CLIENT-SPECIFIC CONFIG GENERATION
    # =============================================================================

    def test_generate_claude_desktop_config_json_structure(self):
        """Test Claude Desktop config has proper JSON structure."""
        result = _generate_claude_desktop_config(
            "http://localhost:8000/mcp/", "test_key"
        )

        assert "mcpServers" in result
        assert '"shared-context-server"' in result
        assert '"http://localhost:8000/mcp/"' in result
        assert '"test_key"' in result
        assert "{" in result
        assert "}" in result

    def test_generate_cursor_config_contains_required_elements(self):
        """Test Cursor config includes necessary configuration elements."""
        result = _generate_cursor_config("http://localhost:8000/mcp/", "test_key")

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_windsurf_config_format(self):
        """Test Windsurf config generates proper format."""
        result = _generate_windsurf_config("http://localhost:8000/mcp/", "test_key")

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_vscode_config_structure(self):
        """Test VS Code config includes proper structure."""
        result = _generate_vscode_config("http://localhost:8000/mcp/", "test_key")

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_gemini_config_command_format(self):
        """Test Gemini config generates proper command format."""
        result = _generate_gemini_config("http://localhost:8000/mcp/", "test_key")

        assert "gemini mcp add" in result
        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    def test_generate_codex_config_includes_transport_info(self):
        """Test Codex config includes transport and authentication info."""
        result = _generate_codex_config("http://localhost:8000/mcp/", "test_key")

        assert "[mcp_servers.shared-context-server]" in result
        assert '"test_key"' in result
        assert "http://localhost:8000/mcp/" in result

    def test_generate_qwen_config_json_format(self):
        """Test Qwen config includes proper JSON format."""
        result = _generate_qwen_config("http://localhost:8000/mcp/", "test_key")

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result
        assert "{" in result
        assert "}" in result

    def test_generate_kiro_config_workspace_format(self):
        """Test Kiro config includes workspace configuration format."""
        result = _generate_kiro_config("http://localhost:8000/mcp/", "test_key")

        assert "shared-context-server" in result
        assert "http://localhost:8000/mcp/" in result
        assert "test_key" in result

    # =============================================================================
    # CROSS-CLIENT CONSISTENCY TESTS
    # =============================================================================

    def test_all_config_generators_handle_url_variations(self):
        """Test all config generators handle URL variations consistently."""
        test_urls = [
            "http://localhost:8000/mcp/",
            "https://example.com:3000/mcp/",
            "http://192.168.1.50:9090/mcp/",
        ]
        api_key = "consistent_test_key"

        generators = [
            _generate_claude_desktop_config,
            _generate_cursor_config,
            _generate_windsurf_config,
            _generate_vscode_config,
            _generate_gemini_config,
            _generate_codex_config,
            _generate_qwen_config,
            _generate_kiro_config,
        ]

        for url in test_urls:
            for generator in generators:
                result = generator(url, api_key)
                assert isinstance(result, str)
                assert len(result) > 0
                assert "shared-context-server" in result

    def test_all_config_generators_include_api_key(self):
        """Test all config generators properly include API key."""
        server_url = "http://localhost:8000/mcp/"
        test_keys = ["simple_key", "complex-key_123", "key.with.dots"]

        generators = [
            _generate_claude_desktop_config,
            _generate_cursor_config,
            _generate_windsurf_config,
            _generate_vscode_config,
            _generate_gemini_config,
            _generate_codex_config,
            _generate_qwen_config,
            _generate_kiro_config,
        ]

        for api_key in test_keys:
            for generator in generators:
                result = generator(server_url, api_key)
                assert api_key in result, (
                    f"API key '{api_key}' not found in {generator.__name__} output"
                )
