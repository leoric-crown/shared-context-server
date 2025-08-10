"""
Testing utilities for FastMCP-based shared context server.

Provides helper functions to properly test FastMCP decorated functions
by handling Field default value extraction.
"""

import inspect
from typing import Any

from pydantic.fields import FieldInfo


def extract_field_defaults(fastmcp_tool) -> dict[str, Any]:
    """
    Extract actual default values from a FastMCP tool function.

    FastMCP decorated functions have FieldInfo objects as defaults,
    but we need the actual default values for testing.

    Args:
        fastmcp_tool: A FastMCP FunctionTool object

    Returns:
        Dict mapping parameter names to their actual default values
    """
    defaults = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for name, param in sig.parameters.items():
        if name == "ctx":  # Skip context parameter
            continue

        if isinstance(param.default, FieldInfo):
            # Extract the actual default from FieldInfo
            defaults[name] = param.default.default
        elif param.default is not inspect.Parameter.empty:
            defaults[name] = param.default

    return defaults


async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """
    Call a FastMCP tool function with proper default handling.

    This helper automatically extracts Field defaults and merges them
    with provided kwargs to avoid FieldInfo object issues.

    Args:
        fastmcp_tool: A FastMCP FunctionTool object
        ctx: Mock context object
        **kwargs: Arguments to pass to the function

    Returns:
        Result of the function call
    """
    # Get the actual defaults
    defaults = extract_field_defaults(fastmcp_tool)

    # Merge defaults with provided kwargs (kwargs override defaults)
    call_args = {**defaults, **kwargs}

    # Call the function with context as first parameter
    return await fastmcp_tool.fn(ctx, **call_args)


class MockContext:
    """Standard mock context for FastMCP testing."""

    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        self.agent_id = agent_id


# Example usage patterns for common tools:

# Use call_fastmcp_tool(tool_function, ctx, **kwargs) to call any MCP tool
# - create_session: purpose="Test session"
# - add_message: session_id, content, visibility
# - set_memory: key, value, session_id (optional)
# - search_context: session_id, query
