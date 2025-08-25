"""
Session Management Tools for Shared Context MCP Server.

Provides MCP tools for creating, retrieving, and managing sessions:
- create_session: Create new shared context sessions with purpose and metadata
- get_session: Retrieve session information and recent messages
- add_message: Add messages to sessions with visibility controls
- get_messages: Retrieve messages with filtering and pagination

Built for multi-agent coordination with visibility controls and real-time updates.
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

# aiosqlite removed in favor of SQLAlchemy-only backend
from pydantic import Field

if TYPE_CHECKING:
    pass  # TYPE_CHECKING imports removed
else:
    TestConnectionType = Any

from fastmcp import Context  # noqa: TC002

from .auth import validate_agent_context_or_error
from .core_server import mcp
from .database import get_db_connection
from .models import parse_mcp_metadata, sanitize_text_input, serialize_metadata
from .utils.caching import cache_manager, generate_session_cache_key
from .utils.llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    ErrorSeverity,
    create_llm_error_response,
    create_system_error,
)

# Removed sanitization imports - using generic logging instead

# PERFORMANCE OPTIMIZATION: Cache expensive WebSocket imports
_websocket_imports = None


def get_websocket_imports() -> dict:
    """Get WebSocket imports with caching to avoid repeated import overhead."""
    import os

    global _websocket_imports
    if _websocket_imports is None:
        # Check if WebSocket is disabled for testing
        if os.environ.get("DISABLE_WEBSOCKET_FOR_TESTS", "").lower() in (
            "true",
            "1",
            "yes",
        ):

            async def noop_notifier(*_args: Any, **_kwargs: Any) -> None:
                logger.debug("WebSocket disabled for testing, skipping notification")

            _websocket_imports = {
                "notify_websocket_server": noop_notifier,
                "available": False,
            }
        else:
            try:
                from .websocket_handlers import notify_websocket_server

                _websocket_imports = {
                    "notify_websocket_server": notify_websocket_server,
                    "available": True,
                }
            except ImportError:
                # Create no-op implementation for testing
                async def noop_notifier(*_args: Any, **_kwargs: Any) -> None:
                    logger.debug(
                        "WebSocket support not available, skipping notification"
                    )

                _websocket_imports = {
                    "notify_websocket_server": noop_notifier,
                    "available": False,
                }
    return _websocket_imports


logger = logging.getLogger(__name__)


# Audit logging utility
async def audit_log(
    _conn: Any,  # SQLAlchemy connection wrapper
    action: str,
    agent_id: str,
    session_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add audit log entry for security tracking."""
    try:
        from .auth import audit_log_auth_event

        await audit_log_auth_event(action, agent_id, session_id, details)
    except Exception as e:
        logger.warning(f"Failed to write audit log: {e}")


# ============================================================================
# SESSION MANAGEMENT TOOLS
# ============================================================================


@mcp.tool(exclude_args=["ctx"])
async def create_session(
    purpose: str = Field(description="Purpose or description of the session"),
    metadata: Any = Field(
        default=None,
        description="Optional metadata for the session (JSON object or null)",
        examples=[{"test": True, "version": 1}, None],
        json_schema_extra={"type": "object", "additionalProperties": True},
    ),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Create a new shared context session.

    Returns session_id for future operations.
    """

    try:
        # Generate unique session ID
        session_id = f"session_{uuid4().hex[:16]}"

        # Extract agent identity from context using the standard auth validation
        agent_context = await validate_agent_context_or_error(ctx, None)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]

        # Check write permission
        if "write" not in agent_context.get("permissions", []):
            return ERROR_MESSAGE_PATTERNS["write_required"](  # type: ignore[no-any-return,operator]
                agent_context.get("permissions", [])
            )

        # Input sanitization
        purpose = sanitize_text_input(purpose)
        if not purpose:
            return ERROR_MESSAGE_PATTERNS["purpose_empty"]()  # type: ignore[no-any-return,operator]

        # Parse metadata from MCP client (handles both string and dict inputs)
        try:
            metadata = parse_mcp_metadata(metadata)
        except ValueError as e:
            return create_llm_error_response(
                error=f"Invalid metadata format: {str(e)}",
                code="INVALID_METADATA_FORMAT",
                suggestions=[
                    "Provide metadata as a JSON object (dictionary)",
                    "Use null for no metadata",
                    'Example: {"key": "value", "nested": {"data": "example"}}',
                ],
                context={"field": "metadata", "expected_type": "dict or null"},
                severity=ErrorSeverity.WARNING,
            )

        # Serialize metadata for database storage
        metadata_str = serialize_metadata(metadata) if metadata else None
        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    purpose,
                    agent_id,
                    metadata_str,
                    current_timestamp,
                    current_timestamp,
                ),
            )
            await conn.commit()

            # Audit log
            await audit_log(conn, "session_created", agent_id, session_id)

        return {
            "success": True,
            "session_id": session_id,
            "created_by": agent_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        logger.exception("Failed to create session")
        logger.debug(traceback.format_exc())
        return create_system_error("create_session", "database", temporary=True)


@mcp.tool(exclude_args=["ctx"])
async def get_session(
    session_id: str = Field(description="Session ID to retrieve"),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Retrieve session information and recent messages.
    """

    try:
        # Extract agent identity from context using the standard auth validation
        agent_context = await validate_agent_context_or_error(ctx, None)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            # Row factory handled by SQLAlchemy connection wrapper

            # Get session info
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await cursor.fetchone()

            if not session:
                return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            # Get accessible messages
            cursor = await conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                AND (visibility = 'public' OR
                     (visibility = 'private' AND sender = ?) OR
                     (visibility = 'agent_only' AND sender = ?))
                ORDER BY timestamp DESC
                LIMIT 50
            """,
                (session_id, agent_id, agent_id),
            )

            messages = await cursor.fetchall()

            message_list = [dict(msg) for msg in messages]
            return {
                "success": True,
                "session": dict(session),
                "messages": message_list,
                "message_count": len(message_list),
            }

    except Exception:
        logger.exception("Failed to get session")
        logger.debug(traceback.format_exc())
        return create_system_error("get_session", "database", temporary=True)


@mcp.tool(exclude_args=["ctx"])
async def add_message(
    session_id: str = Field(description="Session ID to add message to"),
    content: str = Field(description="Message content"),
    metadata: Any = Field(
        default=None,
        description="Optional message metadata (JSON object or null)",
        examples=[{"message_type": "test", "priority": "high"}, None],
        json_schema_extra={"type": "object", "additionalProperties": True},
    ),
    parent_message_id: Any = Field(
        default=None,
        description="ID of parent message for threading (integer or null)",
        examples=[565, None],
        json_schema_extra={"type": ["integer", "null"]},
    ),
    auth_token: str | None = Field(
        default=None,
        description="Optional JWT token for elevated permissions (e.g., admin_only visibility)",
    ),
    visibility: str = Field(
        default="public",
        description="Message visibility: public, private, agent_only, or admin_only (requires admin permissions)",
    ),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Add a message to the shared context session.

    Visibility controls:
    - public: Visible to all agents in session
    - private: Visible only to sender
    - agent_only: Visible only to agents of same type
    - admin_only: Visible only to agents with admin permissions (⚠️ REQUIRES ADMIN TOKEN)

    ⚠️ IMPORTANT: admin_only visibility requires admin permissions. Use get_usage_guidance()
    first to check your access level and available operations to avoid permission errors.
    """

    try:
        # Extract and validate agent context (with token validation error handling)
        agent_context = await validate_agent_context_or_error(ctx, auth_token)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]
        agent_type = agent_context["agent_type"]

        # Check write permission
        if "write" not in agent_context.get("permissions", []):
            return ERROR_MESSAGE_PATTERNS["write_required"](  # type: ignore[no-any-return,operator]
                agent_context.get("permissions", [])
            )

        # Validate visibility level (Phase 3 adds admin_only)
        if visibility not in ["public", "private", "agent_only", "admin_only"]:
            return create_llm_error_response(
                error=f"Invalid visibility level: {visibility}",
                code="INVALID_VISIBILITY",
                suggestions=[
                    "Use one of the supported visibility levels",
                    "Available options: 'public', 'private', 'agent_only', 'admin_only'",
                    "Check the API documentation for visibility rules",
                ],
                context={
                    "provided_visibility": visibility,
                    "allowed_values": ["public", "private", "agent_only", "admin_only"],
                },
                severity=ErrorSeverity.WARNING,
            )

        # Check permission for admin_only visibility
        if visibility == "admin_only" and "admin" not in agent_context.get(
            "permissions", []
        ):
            return ERROR_MESSAGE_PATTERNS["admin_required"]()  # type: ignore[no-any-return,operator]

        # Input sanitization
        content = sanitize_text_input(content)
        if not content:
            return ERROR_MESSAGE_PATTERNS["content_empty"]()  # type: ignore[no-any-return,operator]

        # Parse metadata from MCP client (handles both string and dict inputs)
        try:
            metadata = parse_mcp_metadata(metadata)
        except ValueError as e:
            return create_llm_error_response(
                error=f"Invalid metadata format: {str(e)}",
                code="INVALID_METADATA_FORMAT",
                suggestions=[
                    "Provide metadata as a JSON object (dictionary)",
                    "Use null for no metadata",
                    'Example: {"key": "value", "nested": {"data": "example"}}',
                ],
                context={"field": "metadata", "expected_type": "dict or null"},
                severity=ErrorSeverity.WARNING,
            )

        # Serialize metadata for database storage
        metadata_str = serialize_metadata(metadata) if metadata else None

        async with get_db_connection() as conn:
            # Verify session exists
            cursor = await conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            )
            if not await cursor.fetchone():
                return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            # Insert message with sender_type (Phase 3 enhancement)
            current_timestamp = datetime.now(timezone.utc).timestamp()
            cursor = await conn.execute(
                """
                INSERT INTO messages
                (session_id, sender, sender_type, content, visibility, metadata, parent_message_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    agent_id,
                    agent_type,
                    content,
                    visibility,
                    metadata_str,
                    parent_message_id,
                    current_timestamp,
                ),
            )

            message_id = cursor.lastrowid
            await conn.commit()

            # Audit log
            await audit_log(
                conn,
                "message_added",
                agent_id,
                session_id,
                {"message_id": message_id, "visibility": visibility},
            )

            # Trigger resource notifications using admin_tools
            try:
                from .admin_tools import trigger_resource_notifications

                await trigger_resource_notifications(session_id, agent_id)
            except Exception as e:
                logger.warning(f"Failed to trigger resource notifications: {e}")

            # Send real-time message update via WebSocket
            try:
                message_data = {
                    "type": "new_message",
                    "data": {
                        "id": message_id,
                        "sender": agent_id,
                        "sender_type": agent_type,
                        "content": content,
                        "visibility": visibility,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": metadata or {},
                    },
                }
                # OPTIMIZED: Use lazy loading to avoid WebSocket import overhead
                websocket_imports = get_websocket_imports()
                if websocket_imports["available"]:
                    try:
                        from .websocket_handlers import websocket_manager

                        # Broadcast to session via WebSocket manager
                        await websocket_manager.broadcast_to_session(
                            session_id, message_data
                        )
                    except ImportError:
                        logger.debug("WebSocket manager not available")

                # HTTP bridge notification to WebSocket server
                await websocket_imports["notify_websocket_server"](
                    session_id, message_data
                )
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message notification: {e}")

        return {
            "success": True,
            "message_id": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        logger.exception("Failed to add message")
        logger.debug(traceback.format_exc())
        return create_system_error("add_message", "database", temporary=True)


@mcp.tool(exclude_args=["ctx"])
async def get_messages(
    session_id: str = Field(description="Session ID to retrieve messages from"),
    visibility_filter: str | None = Field(
        default=None,
        description="Filter by visibility: public, private, agent_only",
    ),
    auth_token: str | None = Field(
        default=None,
        description="Optional JWT token for elevated permissions (e.g., admin_only visibility)",
    ),
    limit: int = Field(
        default=50, description="Maximum messages to return", ge=1, le=1000
    ),
    offset: int = Field(default=0, description="Offset for pagination", ge=0),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Retrieve messages from session with agent-specific filtering.
    """

    try:
        # Extract and validate agent context (with token validation error handling)
        agent_context = await validate_agent_context_or_error(ctx, auth_token)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]

        # Phase 4: Try cache first for frequently accessed message lists
        cache_context = {
            "agent_id": agent_id,
            "visibility_filter": visibility_filter or "all",
            "offset": offset,
        }
        cache_key = generate_session_cache_key(session_id, agent_id, limit)

        # Check cache for this specific query (5-minute TTL for message lists)
        cached_result = await cache_manager.get(cache_key, cache_context)
        if cached_result is not None:
            # Log cache hit without sensitive cache key
            logger.debug("Cache hit for get_messages operation")
            return cached_result  # type: ignore[no-any-return]

        # Regular production connection
        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            # Row factory handled by SQLAlchemy connection wrapper

            # First, verify session exists
            cursor = await conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            )
            if not await cursor.fetchone():
                return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            # Build query with visibility controls
            where_conditions = ["session_id = ?"]
            params: list[Any] = [session_id]

            # Agent-specific visibility filtering
            has_admin_permission = "admin" in agent_context.get("permissions", [])

            if visibility_filter:
                # Apply specific visibility filter with agent access rules
                if visibility_filter == "public":
                    where_conditions.append("visibility = 'public'")
                elif visibility_filter == "private":
                    where_conditions.append("visibility = 'private' AND sender = ?")
                    params.append(agent_id)
                elif visibility_filter == "agent_only":
                    where_conditions.append("visibility = 'agent_only' AND sender = ?")
                    params.append(agent_id)
                elif visibility_filter == "admin_only" and has_admin_permission:
                    where_conditions.append("visibility = 'admin_only'")
            else:
                # Admin gets unrestricted access to all messages
                if has_admin_permission:
                    visibility_conditions = [
                        "visibility = 'public'",
                        "visibility = 'private'",  # ADMIN: All private messages
                        "visibility = 'agent_only'",  # ADMIN: All agent_only messages
                        "visibility = 'admin_only'",  # ADMIN: All admin_only messages
                    ]
                    # No sender restrictions for admin - they can read all messages
                else:
                    # Default visibility rules for non-admin: public + own private/agent_only
                    visibility_conditions = [
                        "visibility = 'public'",
                        "(visibility = 'private' AND sender = ?)",
                        "(visibility = 'agent_only' AND sender = ?)",
                    ]
                    params.extend([agent_id, agent_id])

                visibility_clause = f"({' OR '.join(visibility_conditions)})"
                where_conditions.append(visibility_clause)

            # First, get total count for pagination
            count_query = f"""
                    SELECT COUNT(*) FROM messages
                    WHERE {" AND ".join(where_conditions)}
                """
            cursor = await conn.execute(count_query, params)
            count_row = await cursor.fetchone()
            total_count = count_row[0] if count_row else 0

            # Then get the actual messages
            query = f"""
                    SELECT * FROM messages
                    WHERE {" AND ".join(where_conditions)}
                    ORDER BY timestamp ASC
                    LIMIT ? OFFSET ?
                """
            params.extend([limit, offset])

            cursor = await conn.execute(query, params)
            messages_rows = await cursor.fetchall()
            messages = [dict(msg) for msg in messages_rows]

            result = {
                "success": True,
                "messages": messages,
                "count": len(messages),
                "total_count": total_count,
                "has_more": offset + limit < total_count,
            }

            # Phase 4: Cache the result for faster subsequent access (5-minute TTL)
            await cache_manager.set(cache_key, result, ttl=300, context=cache_context)
            # Log cache set without sensitive cache key
            logger.debug("Cached get_messages result successfully")

            return result

    except Exception:
        logger.exception("Failed to retrieve messages")
        logger.debug(traceback.format_exc())
        return create_system_error("get_messages", "database", temporary=True)
