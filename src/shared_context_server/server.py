"""
FastMCP Server implementation for Shared Context MCP Server.

This module implements the core MCP server functionality using FastMCP for:
- Session management and message coordination
- Agent memory operations with TTL support
- Context search and retrieval with fuzzy matching
- Multi-agent collaboration patterns
- Audit logging and security
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp import Context, FastMCP
from pydantic import Field

from .config import get_config
from .database import db_manager
from .models import (
    AddMessageRequest,
    CreateSessionRequest,
    GetMemoryRequest,
    MessageVisibility,
    SearchContextRequest,
    SetMemoryRequest,
    create_error_response,
    create_standard_response,
)

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# MCP SERVER SETUP
# ============================================================================

# Create FastMCP server instance
mcp = FastMCP("Shared Context MCP Server")

# ============================================================================
# AUTHENTICATION & CONTEXT
# ============================================================================


async def authenticate_agent(context: Context) -> str:
    """
    Authenticate agent from MCP context and return agent ID.

    For now, we'll use a simple scheme based on the context information.
    In Phase 3, this will be replaced with proper JWT authentication.

    Args:
        context: MCP context with agent information

    Returns:
        str: Agent identifier

    Raises:
        ValueError: If authentication fails
    """
    # For MVP, generate agent ID from context
    # This is a placeholder - proper auth will be implemented in Phase 3
    agent_id = f"agent_{hash(str(context)) % 10000:04d}"
    return agent_id


# ============================================================================
# SESSION MANAGEMENT TOOLS
# ============================================================================


@mcp.tool()
async def create_session(
    context: Context,
    purpose: str = Field(description="Purpose or description of the session"),
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional session metadata"
    ),
) -> dict[str, Any]:
    """
    Create a new collaboration session.

    Sessions provide isolated contexts for multi-agent collaboration,
    with each session maintaining its own message history and state.

    Args:
        context: MCP context
        purpose: Session purpose or description
        metadata: Optional metadata for the session

    Returns:
        Dict containing success status and session details
    """
    try:
        logger.info(f"Creating new session with purpose: {purpose}")

        # Authenticate agent
        agent_id = await authenticate_agent(context)

        # Create request model for validation
        request = CreateSessionRequest(purpose=purpose, metadata=metadata)

        # Create session using database manager
        async with db_manager.get_connection() as db:
            session_data = await db.create_session(
                purpose=request.purpose, created_by=agent_id, metadata=request.metadata
            )

        logger.info(f"Session created successfully: {session_data['session_id']}")

        return create_standard_response(
            success=True,
            session_id=session_data["session_id"],
            created_by=agent_id,
            created_at=session_data["created_at"],
            purpose=purpose,
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        logger.debug(traceback.format_exc())
        return create_error_response(error=str(e), code="session_creation_failed")


@mcp.tool()
async def add_message(
    context: Context,
    session_id: str = Field(description="Target session ID"),
    content: str = Field(description="Message content"),
    visibility: str = Field(default="public", description="Message visibility level"),
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional message metadata"
    ),
    parent_message_id: Optional[int] = Field(
        default=None, description="Parent message ID for threading"
    ),
) -> dict[str, Any]:
    """
    Add a message to an existing session.

    Messages are the primary communication mechanism between agents,
    with support for threading, visibility controls, and rich metadata.

    Args:
        context: MCP context
        session_id: Target session identifier
        content: Message content
        visibility: Message visibility (public, private, agent_only, admin_only)
        metadata: Optional message metadata
        parent_message_id: Optional parent message for threading

    Returns:
        Dict containing success status and message details
    """
    try:
        logger.info(f"Adding message to session {session_id}")

        # Authenticate agent
        agent_id = await authenticate_agent(context)

        # Validate visibility level
        try:
            visibility_level = MessageVisibility(visibility)
        except ValueError:
            return create_error_response(
                error=f"Invalid visibility level: {visibility}",
                code="invalid_visibility",
            )

        # Create request model for validation
        request = AddMessageRequest(
            session_id=session_id,
            content=content,
            visibility=visibility_level,
            metadata=metadata,
            parent_message_id=parent_message_id,
        )

        # Add message using database manager
        async with db_manager.get_connection() as db:
            message_data = await db.add_message(
                session_id=request.session_id,
                sender=agent_id,
                content=request.content,
                visibility=request.visibility,
                metadata=request.metadata,
                parent_message_id=request.parent_message_id,
            )

        logger.info(f"Message added successfully: {message_data['message_id']}")

        return create_standard_response(
            success=True,
            message_id=message_data["message_id"],
            timestamp=message_data["timestamp"],
            sender=agent_id,
        )

    except Exception as e:
        logger.error(f"Failed to add message: {e}")
        logger.debug(traceback.format_exc())
        return create_error_response(error=str(e), code="message_addition_failed")


@mcp.tool()
async def get_session_messages(
    context: Context,
    session_id: str = Field(description="Session ID to retrieve messages from"),
    limit: Optional[int] = Field(
        default=50, description="Maximum number of messages to return"
    ),
    offset: Optional[int] = Field(default=0, description="Number of messages to skip"),
    visibility_filter: Optional[str] = Field(
        default=None, description="Filter messages by visibility level"
    ),
) -> dict[str, Any]:
    """
    Retrieve messages from a session with optional filtering.

    Supports pagination and visibility filtering to control what
    messages are returned based on agent permissions.

    Args:
        context: MCP context
        session_id: Session identifier
        limit: Maximum messages to return
        offset: Number of messages to skip (for pagination)
        visibility_filter: Optional visibility level filter

    Returns:
        Dict containing messages and pagination info
    """
    try:
        logger.info(f"Retrieving messages from session {session_id}")

        # Authenticate agent
        agent_id = await authenticate_agent(context)

        # Retrieve messages using database manager
        async with db_manager.get_connection() as db:
            messages = await db.get_session_messages(
                session_id=session_id,
                agent_id=agent_id,
                limit=limit or 50,
                offset=offset or 0,
                visibility_filter=visibility_filter,
            )

        logger.info(f"Retrieved {len(messages)} messages from session {session_id}")

        return create_standard_response(
            success=True,
            messages=messages,
            count=len(messages),
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to retrieve session messages: {e}")
        logger.debug(traceback.format_exc())
        return create_error_response(error=str(e), code="message_retrieval_failed")


# ============================================================================
# AGENT MEMORY TOOLS
# ============================================================================


@mcp.tool()
async def set_agent_memory(
    context: Context,
    key: str = Field(description="Memory key identifier"),
    value: Any = Field(description="JSON-serializable value to store"),
    session_id: Optional[str] = Field(
        default=None, description="Session ID for scoped memory (null for global)"
    ),
    expires_in: Optional[int] = Field(
        default=None, description="TTL in seconds (max 1 year)"
    ),
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional memory metadata"
    ),
    overwrite: bool = Field(
        default=True, description="Whether to overwrite existing values"
    ),
) -> dict[str, Any]:
    """
    Store a value in agent memory with optional TTL and scoping.

    Agent memory supports both global (cross-session) and scoped (session-specific)
    storage with automatic expiration and conflict resolution.

    Args:
        context: MCP context
        key: Memory key identifier
        value: JSON-serializable value to store
        session_id: Optional session ID for scoped memory
        expires_in: Optional TTL in seconds
        metadata: Optional metadata
        overwrite: Whether to overwrite existing values

    Returns:
        Dict containing success status and memory details
    """
    try:
        logger.info(f"Setting agent memory key: {key}")

        # Authenticate agent
        agent_id = await authenticate_agent(context)

        # Create request model for validation
        request = SetMemoryRequest(
            key=key,
            value=value,
            session_id=session_id,
            expires_in=expires_in,
            metadata=metadata,
            overwrite=overwrite,
        )

        # Set memory using database manager
        async with db_manager.get_connection() as db:
            memory_data = await db.set_agent_memory(
                agent_id=agent_id,
                key=request.key,
                value=request.value,
                session_id=request.session_id,
                expires_in=request.expires_in,
                metadata=request.metadata,
                overwrite=request.overwrite,
            )

        logger.info(f"Agent memory set successfully: {key}")

        return create_standard_response(
            success=True,
            memory_id=memory_data["memory_id"],
            key=key,
            expires_at=memory_data.get("expires_at"),
            scope="session" if session_id else "global",
        )

    except Exception as e:
        logger.error(f"Failed to set agent memory: {e}")
        logger.debug(traceback.format_exc())
        return create_error_response(error=str(e), code="memory_set_failed")


@mcp.tool()
async def get_agent_memory(
    context: Context,
    key: str = Field(description="Memory key identifier"),
    session_id: Optional[str] = Field(
        default=None, description="Session ID for scoped memory (null for global)"
    ),
) -> dict[str, Any]:
    """
    Retrieve a value from agent memory.

    Searches both session-scoped and global memory, with session-scoped
    values taking precedence over global ones.

    Args:
        context: MCP context
        key: Memory key identifier
        session_id: Optional session ID for scoped lookup

    Returns:
        Dict containing the stored value and metadata
    """
    try:
        logger.info(f"Getting agent memory key: {key}")

        # Authenticate agent
        agent_id = await authenticate_agent(context)

        # Create request model for validation
        request = GetMemoryRequest(key=key, session_id=session_id)

        # Get memory using database manager
        async with db_manager.get_connection() as db:
            memory_data = await db.get_agent_memory(
                agent_id=agent_id, key=request.key, session_id=request.session_id
            )

        if memory_data:
            logger.info(f"Agent memory retrieved successfully: {key}")
            return create_standard_response(
                success=True,
                key=key,
                value=memory_data["value"],
                metadata=memory_data.get("metadata"),
                created_at=memory_data["created_at"],
                updated_at=memory_data["updated_at"],
                expires_at=memory_data.get("expires_at"),
                scope="session" if memory_data.get("session_id") else "global",
            )
        return create_error_response(
            error=f"Memory key not found: {key}", code="memory_not_found"
        )

    except Exception as e:
        logger.error(f"Failed to get agent memory: {e}")
        logger.debug(traceback.format_exc())
        return create_error_response(error=str(e), code="memory_get_failed")


# ============================================================================
# CONTEXT SEARCH TOOLS
# ============================================================================


@mcp.tool()
async def search_context(
    context: Context,
    session_id: str = Field(description="Session ID to search within"),
    query: str = Field(description="Search query string"),
    fuzzy_threshold: float = Field(
        default=60.0, description="Fuzzy search threshold (0-100)"
    ),
    limit: int = Field(default=10, description="Maximum number of results"),
    search_metadata: bool = Field(
        default=True, description="Whether to search in metadata"
    ),
    search_scope: str = Field(
        default="all", description="Search scope (all, public, private)"
    ),
) -> dict[str, Any]:
    """
    Search for content within a session using fuzzy matching.

    Provides intelligent context retrieval using RapidFuzz for semantic
    matching across message content and metadata.

    Args:
        context: MCP context
        session_id: Session to search within
        query: Search query string
        fuzzy_threshold: Minimum similarity threshold (0-100)
        limit: Maximum results to return
        search_metadata: Whether to include metadata in search
        search_scope: Scope of search (all, public, private)

    Returns:
        Dict containing search results with similarity scores
    """
    try:
        logger.info(f"Searching context in session {session_id} for: {query}")

        # Authenticate agent
        agent_id = await authenticate_agent(context)

        # Create request model for validation
        request = SearchContextRequest(
            session_id=session_id,
            query=query,
            fuzzy_threshold=fuzzy_threshold,
            limit=limit,
            search_metadata=search_metadata,
            search_scope=search_scope,
        )

        # Search using database manager
        async with db_manager.get_connection() as db:
            results = await db.search_context(
                session_id=request.session_id,
                agent_id=agent_id,
                query=request.query,
                fuzzy_threshold=request.fuzzy_threshold,
                limit=request.limit,
                search_metadata=request.search_metadata,
                search_scope=request.search_scope,
            )

        logger.info(f"Context search returned {len(results)} results")

        return create_standard_response(
            success=True,
            results=results,
            count=len(results),
            query=query,
            session_id=session_id,
            fuzzy_threshold=fuzzy_threshold,
        )

    except Exception as e:
        logger.error(f"Context search failed: {e}")
        logger.debug(traceback.format_exc())
        return create_error_response(error=str(e), code="context_search_failed")


# ============================================================================
# UTILITY & STATUS TOOLS
# ============================================================================


@mcp.tool()
async def get_server_info(context: Context) -> dict[str, Any]:
    """
    Get server information and health status.

    Returns current server status, configuration info, and
    basic health metrics for monitoring and debugging.

    Args:
        context: MCP context

    Returns:
        Dict containing server information and status
    """
    try:
        config = get_config()

        # Get database status
        async with db_manager.get_connection() as db:
            db_status = await db.get_health_status()

        return create_standard_response(
            success=True,
            server_name=config.mcp_server.mcp_server_name,
            server_version=config.mcp_server.mcp_server_version,
            environment=config.development.environment,
            database_status=db_status,
            uptime_info={
                "startup_time": datetime.now(timezone.utc).isoformat(),
                "status": "healthy",
            },
        )

    except Exception as e:
        logger.error(f"Failed to get server info: {e}")
        return create_error_response(error=str(e), code="server_info_failed")


# ============================================================================
# SERVER LIFECYCLE
# ============================================================================


async def initialize_server() -> None:
    """Initialize the MCP server and all dependencies."""
    try:
        logger.info("Initializing Shared Context MCP Server...")

        # Load and validate configuration
        config = get_config()
        logger.info(
            f"Configuration loaded for {config.development.environment} environment"
        )

        # Initialize database
        await db_manager.initialize()
        logger.info("Database initialized successfully")

        # Perform any additional startup tasks
        logger.info("Server initialization completed successfully")

    except Exception as e:
        logger.error(f"Server initialization failed: {e}")
        logger.error(traceback.format_exc())
        raise


async def shutdown_server() -> None:
    """Clean shutdown of the MCP server."""
    try:
        logger.info("Shutting down Shared Context MCP Server...")

        # Close database connections
        await db_manager.close()
        logger.info("Database connections closed")

        logger.info("Server shutdown completed successfully")

    except Exception as e:
        logger.error(f"Server shutdown error: {e}")
        logger.error(traceback.format_exc())


# ============================================================================
# SERVER INSTANCE
# ============================================================================


def create_server() -> FastMCP:
    """
    Create and configure the MCP server instance.

    Returns:
        FastMCP: Configured server instance
    """
    logger.info("Creating Shared Context MCP Server instance")
    return mcp


# Export the server instance
server = create_server()

# Set up server lifecycle hooks if FastMCP supports them
if hasattr(mcp, "on_startup"):
    mcp.on_startup(initialize_server)
if hasattr(mcp, "on_shutdown"):
    mcp.on_shutdown(shutdown_server)
