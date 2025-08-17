#!/usr/bin/env python3
"""
Debug script to test FastMCP tool validation specifically.
This will help isolate if the issue is in FastMCP's handling of json_schema_extra.
"""

import asyncio
import json
from typing import Any

# Import FastMCP
from fastmcp import FastMCP
from pydantic import Field


async def test_fastmcp_validation():
    """Test FastMCP tool validation with metadata field."""

    # Create a test MCP server
    mcp = FastMCP("test-server")

    @mcp.tool()
    async def test_create_session_current(
        purpose: str = Field(description="Purpose or description of the session"),
        metadata: Any = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
            json_schema_extra={"anyOf": [{"type": "object"}, {"type": "null"}]},
        ),
    ) -> dict[str, Any]:
        """Test tool with current refactor implementation."""
        return {"purpose": purpose, "metadata": metadata}

    @mcp.tool()
    async def test_create_session_simple(
        purpose: str = Field(description="Purpose or description of the session"),
        metadata: Any = Field(
            default=None,
            description="Optional metadata for the session (simple Any field)",
            examples=[{"test": True, "version": 1}, None],
        ),
    ) -> dict[str, Any]:
        """Test tool with simple Any field."""
        return {"purpose": purpose, "metadata": metadata}

    @mcp.tool()
    async def test_create_session_dict_union(
        purpose: str = Field(description="Purpose or description of the session"),
        metadata: dict[str, Any] | None = Field(
            default=None,
            description="Optional metadata (dict union type)",
            examples=[{"test": True, "version": 1}, None],
        ),
    ) -> dict[str, Any]:
        """Test tool with dict union type."""
        return {"purpose": purpose, "metadata": metadata}

    # Test values
    test_cases = [
        {"purpose": "test", "metadata": {"test": "value"}},
        {"purpose": "test", "metadata": {"test": True, "version": 1}},
        {"purpose": "test", "metadata": None},
        {"purpose": "test", "metadata": {}},
    ]

    print("FASTMCP VALIDATION TESTING")
    print("=" * 60)

    # Get tool schemas to see what FastMCP generates
    for tool_name in [
        "test_create_session_current",
        "test_create_session_simple",
        "test_create_session_dict_union",
    ]:
        tool = mcp._tools[tool_name]
        schema = tool.get_json_schema()
        metadata_schema = (
            schema.get("inputSchema", {}).get("properties", {}).get("metadata", {})
        )
        print(f"\n{tool_name} metadata schema:")
        print(json.dumps(metadata_schema, indent=2))

    return mcp


async def main():
    """Run the FastMCP validation test."""
    await test_fastmcp_validation()


if __name__ == "__main__":
    asyncio.run(main())
