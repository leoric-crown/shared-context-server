"""
Static MCP Resources for Shared Context Server.

Provides discoverable server capabilities and tool documentation through
MCP resource primitives, enabling client-side capability detection and
workflow automation.

Resources:
- server://info: Static server capabilities and metadata
- docs://tools: Comprehensive tool documentation with usage examples
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp.resources import Resource, TextResource
from pydantic import AnyUrl

from .core_server import mcp
from .tools import TOOL_REGISTRY


@mcp.resource("server://info/{_}")
async def get_server_info_resource(_: str = "default", ctx: Any = None) -> Resource:  # noqa: ARG001
    """
    Static server information and capabilities discovery.

    Provides essential server metadata for client capability detection
    and integration planning.
    """

    server_info = {
        "server_info": {
            "name": "shared-context-server",
            "version": "1.1.1",
            "description": "Multi-agent collaboration server with memory persistence",
            "capabilities": ["tools", "resources", "prompts", "resource_templates"],
            "mcp_version": "2024-11-05",
            "fastmcp_patterns": True,
        },
        "tools": {
            "count": len(TOOL_REGISTRY),
            "categories": list(
                {tool.category.value for tool in TOOL_REGISTRY.values()}
            ),
            "authentication": "JWT with API key header",
            "real_time_updates": True,
        },
        "features": {
            "session_management": "Multi-agent collaboration sessions",
            "agent_memory": "Private memory with TTL support",
            "context_search": "RapidFuzz-powered fuzzy search",
            "visibility_control": ["public", "private", "agent_only", "admin_only"],
            "websocket_support": True,
            "resource_notifications": True,
        },
        "architecture": {
            "database": "SQLAlchemy with SQLite/PostgreSQL/MySQL support",
            "authentication": "ContextVar-based JWT with dual-token system",
            "performance_targets": {
                "message_operations": "<30ms",
                "fuzzy_search": "2-3ms",
                "concurrent_agents": "20+ per session",
            },
        },
    }

    return TextResource(
        uri=AnyUrl("server://info/default"),
        name="Server Information",
        description="Shared Context Server capabilities and architecture overview",
        mime_type="application/json",
        text=json.dumps(server_info, indent=2, ensure_ascii=False),
    )


@mcp.resource("docs://tools/{_}")
async def get_tools_documentation_resource(
    _: str = "default",
    ctx: Any = None,  # noqa: ARG001
) -> Resource:
    """
    Comprehensive tool documentation with usage examples.

    Provides detailed documentation for all available MCP tools,
    organized by category with practical usage examples.
    """

    tools_by_category: dict[str, list[dict[str, object]]] = {}
    for tool_name, metadata in TOOL_REGISTRY.items():
        category = metadata.category.value
        if category not in tools_by_category:
            tools_by_category[category] = []

        tool_doc = {
            "name": tool_name,
            "description": metadata.description,
            "version": metadata.version,
            "requires_auth": metadata.requires_auth,
            "is_experimental": metadata.is_experimental,
            "tags": metadata.tags or [],
        }
        tools_by_category[category].append(tool_doc)

    # Add usage examples for key tools
    usage_examples = {
        "session_management": {
            "create_session": {
                "purpose": "Start a new multi-agent collaboration session",
                "example": {
                    "purpose": "Feature development: User authentication system",
                    "metadata": {"project": "webapp", "phase": "implementation"},
                },
            },
            "add_message": {
                "purpose": "Add messages with visibility control",
                "example": {
                    "session_id": "session_abc123",
                    "content": "Implementation progress update",
                    "visibility": "public",
                    "metadata": {"agent_type": "developer"},
                },
            },
        },
        "agent_memory": {
            "set_memory": {
                "purpose": "Store agent-specific data with TTL",
                "example": {
                    "key": "current_task",
                    "value": {"feature": "auth", "status": "in_progress"},
                    "expires_in": 3600,
                    "session_id": "session_abc123",
                },
            }
        },
        "context_search": {
            "search_context": {
                "purpose": "Fuzzy search across session messages",
                "example": {
                    "session_id": "session_abc123",
                    "query": "authentication implementation",
                    "fuzzy_threshold": 80,
                    "limit": 10,
                },
            }
        },
    }

    documentation = {
        "tools_documentation": {
            "total_tools": len(TOOL_REGISTRY),
            "categories": len(tools_by_category),
            "authentication_required": "Most tools require JWT authentication",
            "tools_by_category": tools_by_category,
            "usage_examples": usage_examples,
        },
        "getting_started": {
            "authentication": "Use authenticate_agent tool to obtain JWT token",
            "workflow": [
                "1. Authenticate with API key to get JWT token",
                "2. Create session for collaboration context",
                "3. Add agents and coordinate through session messages",
                "4. Use memory and search tools for state management",
            ],
            "client_integration": {
                "claude_code": "Use @server://info and @docs://tools for context",
                "vs_code": "Access via MCP context menu and resource providers",
            },
        },
    }

    return TextResource(
        uri=AnyUrl("docs://tools/default"),
        name="Tools Documentation",
        description="Comprehensive documentation for all shared-context-server MCP tools",
        mime_type="application/json",
        text=json.dumps(documentation, indent=2, ensure_ascii=False),
    )
