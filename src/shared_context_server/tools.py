"""
MCP Tools Registry for Shared Context MCP Server.

This module provides a centralized registry of all available MCP tools,
with organized categories and metadata for tool discovery and documentation.

Tool Categories:
- Session Management: create_session, add_message, get_session_messages
- Agent Memory: set_agent_memory, get_agent_memory
- Context Search: search_context
- Server Utilities: get_server_info
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

# ============================================================================
# TOOL METADATA
# ============================================================================


class ToolCategory(str, Enum):
    """Categories for organizing MCP tools."""

    SESSION_MANAGEMENT = "session_management"
    AGENT_MEMORY = "agent_memory"
    CONTEXT_SEARCH = "context_search"
    SERVER_UTILITIES = "server_utilities"


@dataclass
class ToolMetadata:
    """Metadata for MCP tool registration and documentation."""

    name: str
    category: ToolCategory
    description: str
    version: str = "1.0.0"
    requires_auth: bool = True
    is_experimental: bool = False
    tags: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "requires_auth": self.requires_auth,
            "is_experimental": self.is_experimental,
            "tags": self.tags or [],
        }


# ============================================================================
# TOOL REGISTRY
# ============================================================================

# Registry of all available MCP tools with metadata
TOOL_REGISTRY: dict[str, ToolMetadata] = {
    "create_session": ToolMetadata(
        name="create_session",
        category=ToolCategory.SESSION_MANAGEMENT,
        description="Create a new collaboration session with purpose and metadata",
        tags=["session", "collaboration", "creation"],
    ),
    "add_message": ToolMetadata(
        name="add_message",
        category=ToolCategory.SESSION_MANAGEMENT,
        description="Add a message to an existing session with visibility controls",
        tags=["message", "communication", "threading"],
    ),
    "get_session_messages": ToolMetadata(
        name="get_session_messages",
        category=ToolCategory.SESSION_MANAGEMENT,
        description="Retrieve messages from a session with pagination and filtering",
        tags=["message", "retrieval", "pagination", "filtering"],
    ),
    "set_agent_memory": ToolMetadata(
        name="set_agent_memory",
        category=ToolCategory.AGENT_MEMORY,
        description="Store values in agent memory with TTL and scope support",
        tags=["memory", "storage", "ttl", "scoping"],
    ),
    "get_agent_memory": ToolMetadata(
        name="get_agent_memory",
        category=ToolCategory.AGENT_MEMORY,
        description="Retrieve values from agent memory with scope resolution",
        tags=["memory", "retrieval", "scoping"],
    ),
    "search_context": ToolMetadata(
        name="search_context",
        category=ToolCategory.CONTEXT_SEARCH,
        description="Search session context using fuzzy matching and filtering",
        tags=["search", "fuzzy", "context", "similarity"],
    ),
    "get_server_info": ToolMetadata(
        name="get_server_info",
        category=ToolCategory.SERVER_UTILITIES,
        description="Get server information, health status, and configuration",
        tags=["server", "health", "status", "info"],
        requires_auth=False,
    ),
    "get_usage_guidance": ToolMetadata(
        name="get_usage_guidance",
        category=ToolCategory.SERVER_UTILITIES,
        description="Get contextual operational guidance based on JWT access level",
        tags=["guidance", "permissions", "operations", "security"],
        requires_auth=True,
    ),
}

# ============================================================================
# TOOL DISCOVERY FUNCTIONS
# ============================================================================


def get_all_tools() -> dict[str, ToolMetadata]:
    """
    Get all registered MCP tools.

    Returns:
        Dict mapping tool names to metadata
    """
    return TOOL_REGISTRY.copy()


def get_tools_by_category(category: ToolCategory) -> dict[str, ToolMetadata]:
    """
    Get tools filtered by category.

    Args:
        category: Tool category to filter by

    Returns:
        Dict of tools in the specified category
    """
    return {
        name: metadata
        for name, metadata in TOOL_REGISTRY.items()
        if metadata.category == category
    }


def get_tool_metadata(tool_name: str) -> ToolMetadata | None:
    """
    Get metadata for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool metadata or None if tool not found
    """
    return TOOL_REGISTRY.get(tool_name)


def search_tools(query: str) -> dict[str, ToolMetadata]:
    """
    Search for tools by name, description, or tags.

    Args:
        query: Search query string

    Returns:
        Dict of matching tools
    """
    query_lower = query.lower()

    matching_tools = {}
    for name, metadata in TOOL_REGISTRY.items():
        # Check name
        if query_lower in name.lower():
            matching_tools[name] = metadata
            continue

        # Check description
        if query_lower in metadata.description.lower():
            matching_tools[name] = metadata
            continue

        # Check tags
        if metadata.tags:
            for tag in metadata.tags:
                if query_lower in tag.lower():
                    matching_tools[name] = metadata
                    break

    return matching_tools


def get_tool_categories() -> list[str]:
    """
    Get all available tool categories.

    Returns:
        List of category names
    """
    return [category.value for category in ToolCategory]


def get_tools_summary() -> dict[str, Any]:
    """
    Get a summary of all tools organized by category.

    Returns:
        Dict with category summaries and counts
    """
    summary: dict[str, Any] = {
        "total_tools": len(TOOL_REGISTRY),
        "categories": {},
        "auth_required_count": 0,
        "experimental_count": 0,
    }

    # Count by category
    for category in ToolCategory:
        category_tools = get_tools_by_category(category)
        summary["categories"][category.value] = {
            "count": len(category_tools),
            "tools": list(category_tools.keys()),
        }

    # Count special attributes
    for metadata in TOOL_REGISTRY.values():
        if metadata.requires_auth:
            summary["auth_required_count"] = int(summary["auth_required_count"]) + 1
        if metadata.is_experimental:
            summary["experimental_count"] = int(summary["experimental_count"]) + 1

    return summary


# ============================================================================
# TOOL VALIDATION
# ============================================================================


def validate_tool_registry() -> list[str]:
    """
    Validate the tool registry for consistency and completeness.

    Returns:
        List of validation issues (empty if all valid)
    """
    issues = []

    # Check for duplicate tool names
    tool_names = list(TOOL_REGISTRY.keys())
    if len(tool_names) != len(set(tool_names)):
        issues.append("Duplicate tool names detected")

    # Validate individual tools
    for name, metadata in TOOL_REGISTRY.items():
        # Check name consistency
        if name != metadata.name:
            issues.append(
                f"Tool name mismatch: registry key '{name}' != metadata name '{metadata.name}'"
            )

        # Check required fields
        if not metadata.description.strip():
            issues.append(f"Tool '{name}' missing description")

        # Check version format
        if not metadata.version or not isinstance(metadata.version, str):
            issues.append(f"Tool '{name}' has invalid version format")

    return issues


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================


def export_tool_documentation() -> dict[str, Any]:
    """
    Export tool documentation in structured format.

    Returns:
        Complete documentation structure for all tools
    """
    return {
        "server_info": {
            "name": "Shared Context MCP Server",
            "version": "1.0.0",
            "description": "Centralized memory store for multi-agent collaboration",
        },
        "tool_summary": get_tools_summary(),
        "tools": {name: metadata.to_dict() for name, metadata in TOOL_REGISTRY.items()},
        "categories": {
            category.value: {
                "description": _get_category_description(category),
                "tools": list(get_tools_by_category(category).keys()),
            }
            for category in ToolCategory
        },
    }


def _get_category_description(category: ToolCategory) -> str:
    """Get description for a tool category."""
    descriptions = {
        ToolCategory.SESSION_MANAGEMENT: "Tools for creating and managing collaboration sessions",
        ToolCategory.AGENT_MEMORY: "Tools for agent memory storage and retrieval with TTL support",
        ToolCategory.CONTEXT_SEARCH: "Tools for searching and retrieving context with fuzzy matching",
        ToolCategory.SERVER_UTILITIES: "Administrative and monitoring tools for server management",
    }
    return descriptions.get(category, "")


# ============================================================================
# INITIALIZATION
# ============================================================================


def initialize_tool_registry() -> None:
    """
    Initialize and validate the tool registry.

    Raises:
        ValueError: If registry validation fails
    """
    issues = validate_tool_registry()
    if issues:
        raise ValueError(f"Tool registry validation failed: {'; '.join(issues)}")


# Initialize on import
initialize_tool_registry()
