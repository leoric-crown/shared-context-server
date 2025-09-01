"""
Test coverage for MCP authentication middleware whitelist behavior.

This module tests the selective authentication bypass for MCP Inspector CLI
compatibility, focusing on behavior-first testing of the whitelist logic
and authentication flow decisions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared_context_server.mcp_auth_middleware import MCPAuthenticationMiddleware


class TestMCPMiddlewareWhitelist:
    """Test MCP authentication middleware behavior with focus on whitelist logic."""

    def test_middleware_initialization(self):
        """Test middleware initialization and whitelisted methods setup."""
        middleware = MCPAuthenticationMiddleware()

        expected_methods = {
            "initialize",
            "tools/list",
            "resources/list",
            "resources/templates/list",
            "prompts/list",
            "ping",
        }

        assert expected_methods == middleware.WHITELISTED_METHODS

    @patch("shared_context_server.mcp_auth_middleware.logger")
    def test_initialization_logging(self, mock_logger):
        """Test that initialization logs the whitelisted methods."""
        MCPAuthenticationMiddleware()

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "MCPAuthenticationMiddleware initialized" in call_args
        assert "initialize" in call_args
        assert "tools/list" in call_args

    @pytest.mark.asyncio
    async def test_whitelisted_method_bypass_initialize(self):
        """Test that 'initialize' method bypasses authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "initialize"

        mock_call_next = AsyncMock(return_value="success")

        with patch("shared_context_server.mcp_auth_middleware.logger") as mock_logger:
            result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "success"
        mock_call_next.assert_called_once_with(mock_context)
        mock_logger.debug.assert_called_once_with(
            "Bypassing authentication for whitelisted method: initialize"
        )

    @pytest.mark.asyncio
    async def test_whitelisted_method_bypass_tools_list(self):
        """Test that 'tools/list' method bypasses authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "tools/list"

        mock_call_next = AsyncMock(return_value="tools_list_result")

        with patch("shared_context_server.mcp_auth_middleware.logger") as mock_logger:
            result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "tools_list_result"
        mock_call_next.assert_called_once_with(mock_context)
        mock_logger.debug.assert_called_once_with(
            "Bypassing authentication for whitelisted method: tools/list"
        )

    @pytest.mark.asyncio
    async def test_whitelisted_method_bypass_resources_list(self):
        """Test that 'resources/list' method bypasses authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "resources/list"

        mock_call_next = AsyncMock(return_value="resources_result")

        result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "resources_result"
        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_whitelisted_method_bypass_resources_templates_list(self):
        """Test that 'resources/templates/list' method bypasses authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "resources/templates/list"

        mock_call_next = AsyncMock(return_value="templates_result")

        result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "templates_result"
        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_whitelisted_method_bypass_prompts_list(self):
        """Test that 'prompts/list' method bypasses authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "prompts/list"

        mock_call_next = AsyncMock(return_value="prompts_result")

        result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "prompts_result"
        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_whitelisted_method_bypass_ping(self):
        """Test that 'ping' method bypasses authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "ping"

        mock_call_next = AsyncMock(return_value="pong")

        result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "pong"
        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_non_whitelisted_method_requires_auth(self):
        """Test that non-whitelisted methods proceed to normal authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "create_session"  # Custom tool, not whitelisted

        mock_call_next = AsyncMock(return_value="session_created")

        with patch("shared_context_server.mcp_auth_middleware.logger") as mock_logger:
            result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "session_created"
        mock_call_next.assert_called_once_with(mock_context)

        # Should log authentication required message
        mock_logger.debug.assert_called_once_with(
            "Authentication required for method: create_session"
        )

    @pytest.mark.asyncio
    async def test_custom_tool_method_requires_auth(self):
        """Test that custom tool methods require authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "add_message"  # Custom tool

        mock_call_next = AsyncMock(return_value="message_added")

        result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "message_added"
        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_case_sensitive_method_matching(self):
        """Test that method matching is case-sensitive."""
        middleware = MCPAuthenticationMiddleware()

        # Uppercase version should not be whitelisted
        mock_context = MagicMock()
        mock_context.method = "INITIALIZE"

        mock_call_next = AsyncMock(return_value="result")

        with patch("shared_context_server.mcp_auth_middleware.logger") as mock_logger:
            result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "result"
        mock_call_next.assert_called_once_with(mock_context)

        # Should log authentication required (not bypass) for case mismatch
        mock_logger.debug.assert_called_once_with(
            "Authentication required for method: INITIALIZE"
        )

    @pytest.mark.asyncio
    async def test_partial_method_name_no_bypass(self):
        """Test that partial method names don't trigger bypass."""
        middleware = MCPAuthenticationMiddleware()

        # Partial match should not be whitelisted
        mock_context = MagicMock()
        mock_context.method = "tools/list/extended"

        mock_call_next = AsyncMock(return_value="result")

        with patch("shared_context_server.mcp_auth_middleware.logger") as mock_logger:
            result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "result"
        mock_call_next.assert_called_once_with(mock_context)

        # Should log authentication required (not bypass) for partial match
        mock_logger.debug.assert_called_once_with(
            "Authentication required for method: tools/list/extended"
        )

    @pytest.mark.asyncio
    async def test_empty_method_name_requires_auth(self):
        """Test that empty method name requires authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = ""

        mock_call_next = AsyncMock(return_value="result")

        result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "result"
        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_none_method_name_requires_auth(self):
        """Test that None method name requires authentication."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = None

        mock_call_next = AsyncMock(return_value="result")

        result = await middleware.on_request(mock_context, mock_call_next)

        assert result == "result"
        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_exception_handling_in_call_next(self):
        """Test that exceptions from call_next are properly propagated."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "initialize"  # Whitelisted

        # Mock call_next to raise an exception
        mock_call_next = AsyncMock(side_effect=ValueError("Test exception"))

        with pytest.raises(ValueError, match="Test exception"):
            await middleware.on_request(mock_context, mock_call_next)

        mock_call_next.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_whitelisted_methods_immutable(self):
        """Test that WHITELISTED_METHODS cannot be modified after init."""
        middleware1 = MCPAuthenticationMiddleware()
        middleware2 = MCPAuthenticationMiddleware()

        original_methods = middleware1.WHITELISTED_METHODS.copy()

        # Verify both instances have same methods
        assert middleware1.WHITELISTED_METHODS == middleware2.WHITELISTED_METHODS
        assert original_methods == middleware1.WHITELISTED_METHODS

    @pytest.mark.asyncio
    async def test_context_object_passed_through_unchanged(self):
        """Test that context object is passed through to call_next unchanged."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "initialize"
        mock_context.custom_attribute = "test_value"

        def verify_context(ctx):
            # Verify context is passed through unchanged
            assert ctx is mock_context
            assert ctx.custom_attribute == "test_value"
            return "success"

        mock_call_next = AsyncMock(side_effect=verify_context)

        result = await middleware.on_request(mock_context, mock_call_next)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_multiple_whitelisted_calls_same_middleware(self):
        """Test that same middleware instance can handle multiple whitelisted calls."""
        middleware = MCPAuthenticationMiddleware()

        mock_call_next = AsyncMock(side_effect=lambda ctx: f"result_for_{ctx.method}")

        # Test multiple different whitelisted methods
        whitelisted_methods = ["initialize", "tools/list", "resources/list", "ping"]

        for method in whitelisted_methods:
            mock_context = MagicMock()
            mock_context.method = method

            result = await middleware.on_request(mock_context, mock_call_next)
            assert result == f"result_for_{method}"

        # Verify call_next was called for each method
        assert mock_call_next.call_count == len(whitelisted_methods)

    def test_whitelisted_methods_coverage(self):
        """Test that all expected MCP standard methods are whitelisted."""
        middleware = MCPAuthenticationMiddleware()

        # These are the core MCP discovery methods that should always be whitelisted
        required_methods = {
            "initialize",  # MCP handshake
            "tools/list",  # Tool discovery
            "resources/list",  # Resource discovery
            "prompts/list",  # Prompt discovery
            "ping",  # Health check
        }

        # Verify all required methods are present
        for method in required_methods:
            assert method in middleware.WHITELISTED_METHODS, (
                f"Required method '{method}' not whitelisted"
            )

    @pytest.mark.asyncio
    async def test_logging_level_debug(self):
        """Test that bypass logging uses debug level (not info/warning)."""
        middleware = MCPAuthenticationMiddleware()

        mock_context = MagicMock()
        mock_context.method = "tools/list"
        mock_call_next = AsyncMock(return_value="success")

        with patch("shared_context_server.mcp_auth_middleware.logger") as mock_logger:
            await middleware.on_request(mock_context, mock_call_next)

            # Should use debug level, not info/warning/error
            mock_logger.debug.assert_called_once()
            mock_logger.info.assert_not_called()
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()
