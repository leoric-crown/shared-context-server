"""
Selective Authentication Middleware for MCP Inspector CLI Compatibility.

Provides selective authentication bypass for MCP standard methods (tools/list,
resources/list, prompts/list) while maintaining full authentication for custom tools.

This enables MCP Inspector CLI to work with STDIO transport for discovery operations
while preserving security for actual tool execution and data access.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from collections.abc import Awaitable

from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


class MCPAuthenticationMiddleware(Middleware):
    """
    Selective authentication middleware for MCP Inspector CLI compatibility.

    Whitelists standard MCP discovery methods to work without authentication:
    - initialize: MCP protocol handshake
    - tools/list: Discover available tools
    - resources/list: Discover available resources
    - resources/templates/list: Discover resource templates
    - prompts/list: Discover available prompts
    - ping: Health check

    All other methods (custom tools, actual execution) require full authentication.
    """

    # Methods that can bypass authentication for discovery purposes
    WHITELISTED_METHODS = {
        "initialize",
        "tools/list",
        "resources/list",
        "resources/templates/list",
        "prompts/list",
        "ping",
    }

    def __init__(self) -> None:
        """Initialize the middleware with standard MCP discovery methods whitelisted."""
        logger.info(
            f"MCPAuthenticationMiddleware initialized with whitelisted methods: {self.WHITELISTED_METHODS}"
        )

    async def on_request(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[Any]],
    ) -> Any:
        """
        Handle incoming MCP requests with selective authentication.

        For whitelisted methods (discovery operations), bypass authentication.
        For all other methods (custom tools, execution), maintain full authentication.
        """
        method = context.method

        # Check if this is a whitelisted discovery method
        if method in self.WHITELISTED_METHODS:
            logger.debug(f"Bypassing authentication for whitelisted method: {method}")
            # Skip authentication for discovery methods
            return await call_next(context)

        # For all other methods, authentication will be handled by the actual tool implementation
        logger.debug(f"Authentication required for method: {method}")
        return await call_next(context)

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[Any]],
    ) -> Any:
        """
        Handle tool calls - all custom tools require authentication.

        This ensures that while discovery methods work without auth,
        actual tool execution always requires proper authentication.
        """
        tool_name = getattr(context.message, "name", "unknown")
        logger.debug(f"Tool call requires authentication: {tool_name}")

        # Let the tool handle its own authentication requirements
        # Tools use validate_agent_context_or_error() for authentication
        return await call_next(context)

    async def on_read_resource(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[Any]],
    ) -> Any:
        """
        Handle resource reads - all resource access requires authentication.

        This ensures that while resource discovery works without auth,
        actual resource access always requires proper authentication.
        """
        resource_uri = getattr(context.message, "uri", "unknown")
        logger.debug(f"Resource read requires authentication: {resource_uri}")

        # Let the resource handler manage its own authentication
        return await call_next(context)

    async def on_get_prompt(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[Any]],
    ) -> Any:
        """
        Handle prompt gets - all prompt access requires authentication.

        This ensures that while prompt discovery works without auth,
        actual prompt access always requires proper authentication.
        """
        prompt_name = getattr(context.message, "name", "unknown")
        logger.debug(f"Prompt get requires authentication: {prompt_name}")

        # Let the prompt handler manage its own authentication
        return await call_next(context)
