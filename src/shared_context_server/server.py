"""
Phase 1 - Core Infrastructure Implementation for Shared Context MCP Server.

Implements FastMCP server with 4 core tools for multi-agent collaboration:
1. FastMCP Server Foundation - Server setup, lifecycle management, transport configuration
2. Session Management System - create_session, get_session tools with UUID-based isolation
3. Message Storage with Visibility Controls - add_message, get_messages with public/private/agent_only filtering
4. Agent Identity & Authentication - MCP context extraction, basic API key auth, audit logging

Built according to PRP-002: Phase 1 - Core Infrastructure specification.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

if TYPE_CHECKING:
    from starlette.requests import Request

import aiosqlite
from fastmcp import Context, FastMCP
from fastmcp.resources import Resource
from pydantic import AnyUrl, Field
from rapidfuzz import fuzz, process
from starlette.responses import JSONResponse

from .auth import (
    audit_log_auth_event,
    auth_manager,
    extract_agent_context,
)
from .database import get_db_connection, initialize_database
from .models import (
    parse_mcp_metadata,
    sanitize_text_input,
    serialize_metadata,
)
from .utils.caching import (
    cache_manager,
    generate_search_cache_key,
    generate_session_cache_key,
    invalidate_agent_memory_cache,
    invalidate_session_cache,
)
from .utils.llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    ErrorSeverity,
    create_llm_error_response,
    create_system_error,
)
from .utils.performance import get_performance_metrics_dict


def _raise_session_not_found_error(session_id: str) -> None:
    """Raise a session not found error."""
    raise ValueError(f"Session {session_id} not found")


def _raise_unauthorized_access_error(agent_id: str) -> None:
    """Raise an unauthorized access error."""
    raise ValueError(f"Unauthorized access to agent memory for {agent_id}")


class ConcreteResource(Resource):
    """Concrete Resource implementation for FastMCP."""

    def __init__(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str,
        text: str,
        **kwargs: Any,
    ) -> None:
        # Initialize parent Resource with standard fields
        super().__init__(
            uri=AnyUrl(uri),
            name=name,
            description=description,
            mime_type=mime_type,
            **kwargs,
        )
        # Store text content separately
        self._text = text

    async def read(self) -> str:
        """Return the text content of this resource."""
        return self._text


# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# FASTMCP SERVER FOUNDATION
# ============================================================================

# Initialize FastMCP server according to Phase 1 specification
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "shared-context-server"),
    version=os.getenv("MCP_SERVER_VERSION", "1.0.0"),
    instructions="Centralized memory store for multi-agent collaboration",
)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """
    Health check endpoint for Docker containers and load balancers.

    Returns:
        JSONResponse: Health status with timestamp
    """
    try:
        # Import here to avoid circular imports
        from .database import health_check as db_health_check

        # Check database connectivity
        db_status = await db_health_check()

        return JSONResponse(
            {
                "status": "healthy"
                if db_status["status"] == "healthy"
                else "unhealthy",
                "timestamp": db_status["timestamp"],
                "database": db_status,
                "server": "shared-context-server",
                "version": os.getenv("MCP_SERVER_VERSION", "1.0.0"),
            }
        )
    except Exception as e:
        logger.exception("Health check failed")
        return JSONResponse(
            {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status_code=500,
        )


# ============================================================================
# AGENT IDENTITY & AUTHENTICATION
# ============================================================================


# Legacy extract_agent_context function removed - now imported from auth.py


async def audit_log(
    conn: aiosqlite.Connection,
    event_type: str,
    agent_id: str,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Log security and operational events for debugging and monitoring.
    """

    await conn.execute(
        """
        INSERT INTO audit_log
        (event_type, agent_id, session_id, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            event_type,
            agent_id,
            session_id,
            json.dumps(metadata or {}),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


# ============================================================================
# PHASE 3: JWT AUTHENTICATION SYSTEM
# ============================================================================


@mcp.tool()
async def authenticate_agent(
    _ctx: Context,
    agent_id: str = Field(description="Agent identifier", min_length=1, max_length=100),
    agent_type: str = Field(
        description="Agent type (claude, gemini, custom)", max_length=50
    ),
    api_key: str = Field(description="Agent API key for initial authentication"),
    requested_permissions: list[str] = Field(
        default=["read", "write"], description="Requested permissions for the agent"
    ),
) -> dict[str, Any]:
    """
    Authenticate agent and return JWT token with appropriate permissions.

    This tool exchanges an API key for a JWT token with role-based permissions.
    The JWT token can then be used for all subsequent authenticated requests.
    """
    try:
        # Validate API key against environment or database
        valid_api_key = os.getenv("API_KEY", "")
        if not api_key or api_key != valid_api_key:
            await audit_log_auth_event(
                "authentication_failed",
                agent_id,
                None,
                {
                    "agent_type": agent_type,
                    "error": "invalid_api_key",
                    "requested_permissions": requested_permissions,
                },
            )

            return ERROR_MESSAGE_PATTERNS["invalid_api_key"](agent_id)  # type: ignore[no-any-return,operator]

        # Determine granted permissions based on agent type and request
        granted_permissions = auth_manager.determine_permissions(
            agent_type, requested_permissions
        )

        # Generate JWT token
        token = auth_manager.generate_token(agent_id, agent_type, granted_permissions)

        # Log successful authentication
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=auth_manager.token_expiry
        )
        try:
            await audit_log_auth_event(
                "agent_authenticated",
                agent_id,
                None,
                {
                    "agent_type": agent_type,
                    "permissions_granted": granted_permissions,
                    "permissions_requested": requested_permissions,
                    "token_expires_at": expires_at.isoformat(),
                    "auth_method": "jwt",
                },
            )
        except Exception as audit_error:
            logger.warning(f"Failed to audit successful authentication: {audit_error}")

        return {
            "success": True,
            "token": token,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permissions": granted_permissions,
            "expires_at": expires_at.isoformat(),
            "token_type": "Bearer",
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception("Agent authentication failed")
        try:
            await audit_log_auth_event(
                "authentication_error",
                agent_id,
                None,
                {"error": str(e), "agent_type": agent_type},
            )
        except Exception as audit_error:
            logger.warning(f"Failed to audit authentication error: {audit_error}")

        return create_system_error(
            "authenticate_agent", "authentication_service", temporary=True
        )


# ============================================================================
# SESSION MANAGEMENT TOOLS
# ============================================================================


@mcp.tool()
async def create_session(
    ctx: Context,
    purpose: str = Field(description="Purpose or description of the session"),
    metadata: Any = Field(
        default=None,
        description="Optional metadata for the session (JSON object or null)",
        examples=[{"test": True, "version": 1}, None],
    ),
) -> dict[str, Any]:
    """
    Create a new shared context session.

    Returns session_id for future operations.
    """

    try:
        # Generate unique session ID
        session_id = f"session_{uuid4().hex[:16]}"

        # Get agent identity from context - use actual agent_id if available, otherwise derive from session
        # In Phase 3, this will be extracted from proper authentication
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        # Input sanitization
        purpose = sanitize_text_input(purpose)
        if not purpose:
            return ERROR_MESSAGE_PATTERNS["purpose_empty"]()  # type: ignore[no-any-return,operator]

        # Parse metadata from MCP client (handles both string and dict inputs)
        try:
            metadata = parse_mcp_metadata(metadata)
        except ValueError:
            return ERROR_MESSAGE_PATTERNS["invalid_json_format"]("metadata")  # type: ignore[no-any-return,operator]

        # Serialize metadata for database storage
        metadata_str = serialize_metadata(metadata) if metadata else None

        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (id, purpose, created_by, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (session_id, purpose, agent_id, metadata_str),
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


@mcp.tool()
async def get_session(
    ctx: Context, session_id: str = Field(description="Session ID to retrieve")
) -> dict[str, Any]:
    """
    Retrieve session information and recent messages.
    """

    try:
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            conn.row_factory = aiosqlite.Row

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


@mcp.tool()
async def add_message(
    ctx: Context,
    session_id: str = Field(description="Session ID to add message to"),
    content: str = Field(description="Message content"),
    visibility: str = Field(
        default="public",
        description="Message visibility: public, private, or agent_only",
    ),
    metadata: Any = Field(
        default=None,
        description="Optional message metadata (JSON object or null)",
        examples=[{"message_type": "test", "priority": "high"}, None],
    ),
    parent_message_id: int | None = Field(
        default=None, description="ID of parent message for threading"
    ),
) -> dict[str, Any]:
    """
    Add a message to the shared context session.

    Visibility controls:
    - public: Visible to all agents in session
    - private: Visible only to sender
    - agent_only: Visible only to agents of same type
    """

    try:
        # Extract enhanced agent context (includes JWT authentication if available)
        agent_context = extract_agent_context(ctx)
        agent_id = agent_context["agent_id"]
        agent_type = agent_context["agent_type"]

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
        except ValueError:
            return ERROR_MESSAGE_PATTERNS["invalid_json_format"]("metadata")  # type: ignore[no-any-return,operator]

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
            cursor = await conn.execute(
                """
                INSERT INTO messages
                (session_id, sender, sender_type, content, visibility, metadata, parent_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    agent_id,
                    agent_type,
                    content,
                    visibility,
                    metadata_str,
                    parent_message_id,
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

            # Trigger resource notifications
            await trigger_resource_notifications(session_id, agent_id)

        return {
            "success": True,
            "message_id": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        logger.exception("Failed to add message")
        logger.debug(traceback.format_exc())
        return create_system_error("add_message", "database", temporary=True)


@mcp.tool()
async def get_messages(
    ctx: Context,
    session_id: str = Field(description="Session ID to retrieve messages from"),
    limit: int = Field(
        default=50, description="Maximum messages to return", ge=1, le=1000
    ),
    offset: int = Field(default=0, description="Offset for pagination", ge=0),
    visibility_filter: str | None = Field(
        default=None, description="Filter by visibility: public, private, agent_only"
    ),
) -> dict[str, Any]:
    """
    Retrieve messages from session with agent-specific filtering.
    """

    try:
        from .auth import get_auth_info

        auth_info = get_auth_info(ctx)
        agent_id = auth_info.agent_id

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
            logger.debug(f"Cache hit for get_messages: {cache_key}")
            return cached_result  # type: ignore[no-any-return]

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            conn.row_factory = aiosqlite.Row

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
            agent_context = extract_agent_context(ctx)
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
                # Default visibility rules: public + own private/agent_only + admin_only (if admin)
                visibility_conditions = [
                    "visibility = 'public'",
                    "(visibility = 'private' AND sender = ?)",
                    "(visibility = 'agent_only' AND sender = ?)",
                ]
                params.extend([agent_id, agent_id])

                # Add admin_only messages if agent has admin permission
                if has_admin_permission:
                    visibility_conditions.append("visibility = 'admin_only'")

                where_conditions.append(f"({' OR '.join(visibility_conditions)})")

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
            logger.debug(f"Cached get_messages result: {cache_key}")

            return result

    except Exception:
        logger.exception("Failed to retrieve messages")
        logger.debug(traceback.format_exc())
        return create_system_error("get_messages", "database", temporary=True)


# ============================================================================
# PHASE 2: RAPIDFUZZ SEARCH SYSTEM
# ============================================================================


@mcp.tool()
async def search_context(
    ctx: Context,
    session_id: str = Field(description="Session ID to search within"),
    query: str = Field(description="Search query"),
    fuzzy_threshold: float = Field(
        default=60.0, description="Minimum similarity score (0-100)", ge=0, le=100
    ),
    limit: int = Field(
        default=10, description="Maximum results to return", ge=1, le=100
    ),
    search_metadata: bool = Field(
        default=True, description="Include metadata in search"
    ),
    search_scope: Literal["all", "public", "private"] = Field(
        default="all", description="Search scope: all, public, private"
    ),
) -> dict[str, Any]:
    """
    Fuzzy search messages using RapidFuzz for 5-10x performance improvement.

    Searches content, sender, and optionally metadata fields with agent-specific
    visibility controls.
    """

    try:
        start_time = time.time()
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        # Phase 4: Try cache first for search results (10-minute TTL due to compute cost)
        cache_key = generate_search_cache_key(
            session_id, query, fuzzy_threshold, search_scope
        )
        cache_context = {"agent_id": agent_id, "search_metadata": search_metadata}

        cached_result = await cache_manager.get(cache_key, cache_context)
        if cached_result is not None:
            logger.debug(f"Cache hit for search_context: {cache_key}")
            # Update search_time_ms to reflect cache hit
            cached_result["search_time_ms"] = round(
                (time.time() - start_time) * 1000, 2
            )
            cached_result["cache_hit"] = True
            return cached_result  # type: ignore[no-any-return]

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            conn.row_factory = aiosqlite.Row

            # First, verify session exists
            cursor = await conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            )
            if not await cursor.fetchone():
                return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            # Pre-filter optimization: Apply time window and row limits first
            max_rows_scanned = 1000  # Maximum rows to scan for large datasets
            recent_hours = 168  # 7 days default window

            # Build query with visibility, scope, and pre-filtering
            where_conditions = ["session_id = ?"]
            params = [session_id]

            # Add recency filter to reduce scan scope
            where_conditions.append(
                f"datetime(timestamp) >= datetime('now', '-{recent_hours} hours')"
            )

            # Apply visibility controls with admin support
            if search_scope == "public":
                where_conditions.append("visibility = 'public'")
            elif search_scope == "private":
                where_conditions.append("visibility = 'private' AND sender = ?")
                params.append(agent_id)
            else:  # all accessible messages
                # Check if agent has admin permissions
                auth_info = getattr(ctx, "_auth_info", None)
                has_admin_permission = (
                    auth_info
                    and hasattr(auth_info, "permissions")
                    and "admin" in auth_info.permissions
                )

                if has_admin_permission:
                    where_conditions.append("""
                        (visibility = 'public' OR
                         (visibility = 'private' AND sender = ?) OR
                         (visibility = 'agent_only' AND sender = ?) OR
                         visibility = 'admin_only')
                    """)
                else:
                    where_conditions.append("""
                        (visibility = 'public' OR
                         (visibility = 'private' AND sender = ?) OR
                         (visibility = 'agent_only' AND sender = ?))
                    """)
                params.append(agent_id)
                params.append(agent_id)

            cursor = await conn.execute(
                f"""
                SELECT * FROM messages
                WHERE {" AND ".join(where_conditions)}
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                params + [max_rows_scanned],
            )

            rows = await cursor.fetchall()

            if not rows:
                return {
                    "success": True,
                    "results": [],
                    "query": query,
                    "message_count": 0,
                    "search_time_ms": round((time.time() - start_time) * 1000, 2),
                }

            # Prepare searchable text with optimized processing
            searchable_items = []
            for row in rows:
                msg = dict(row)

                # Build searchable text efficiently
                text_parts = [msg.get("sender", ""), msg.get("content", "")]

                if search_metadata and msg.get("metadata"):
                    try:
                        metadata = json.loads(msg["metadata"])
                        if isinstance(metadata, dict):
                            # Extract searchable metadata values
                            searchable_values = [
                                str(v)
                                for v in metadata.values()
                                if v and isinstance(v, (str, int, float, bool))
                            ]
                            text_parts.extend(searchable_values)
                    except json.JSONDecodeError:
                        pass

                searchable_text = " ".join(text_parts).lower()
                searchable_items.append((searchable_text, msg))

            # Use RapidFuzz for high-performance matching
            # Extract just the searchable text for simpler processing
            searchable_texts = [item[0] for item in searchable_items]

            # RapidFuzz process.extract for optimal performance
            matches = process.extract(
                query.lower(),
                searchable_texts,
                scorer=fuzz.partial_ratio,  # Better for finding substrings in search context
                limit=limit,
                score_cutoff=fuzzy_threshold,
            )

            # Build optimized results
            results = []
            for match in matches:
                match_text, score, _ = match

                # Find the corresponding message by matching the searchable text
                message = None
                for text, msg in searchable_items:
                    if text == match_text:
                        message = msg
                        break

                if not message:
                    continue

                # Parse metadata for result
                metadata = {}
                if message.get("metadata"):
                    try:
                        metadata = json.loads(message["metadata"])
                    except json.JSONDecodeError:
                        metadata = {}

                # Create match preview with highlighting context
                content = message["content"]
                preview_length = 150
                if len(content) > preview_length:
                    content = content[:preview_length] + "..."

                results.append(
                    {
                        "message": {
                            "id": message["id"],
                            "sender": message["sender"],
                            "content": message["content"],
                            "timestamp": message["timestamp"],
                            "visibility": message["visibility"],
                            "metadata": metadata,
                        },
                        "score": round(score, 2),
                        "match_preview": content,
                        "relevance": "high"
                        if score >= 80
                        else "medium"
                        if score >= 60
                        else "low",
                    }
                )

            search_time_ms = round((time.time() - start_time) * 1000, 2)

            # Audit search operation
            await audit_log(
                conn,
                "context_searched",
                agent_id,
                session_id,
                {
                    "query": query,
                    "results_count": len(results),
                    "threshold": fuzzy_threshold,
                    "search_scope": search_scope,
                    "search_time_ms": search_time_ms,
                },
            )

        result = {
            "success": True,
            "results": results,
            "query": query,
            "threshold": fuzzy_threshold,
            "search_scope": search_scope,
            "message_count": len(results),
            "search_time_ms": search_time_ms,
            "performance_note": "RapidFuzz enabled (5-10x faster than standard fuzzy search)",
            "cache_hit": False,
        }

        # Phase 4: Cache search results (10-minute TTL due to computational cost)
        await cache_manager.set(cache_key, result, ttl=600, context=cache_context)
        logger.debug(f"Cached search_context result: {cache_key}")

    except Exception:
        logger.exception("Failed to search context")
        logger.debug(traceback.format_exc())
        return create_system_error("search_context", "database", temporary=True)
    else:
        return result


@mcp.tool()
async def search_by_sender(
    ctx: Context,
    session_id: str = Field(description="Session ID to search within"),
    sender: str = Field(description="Sender to search for"),
    limit: int = Field(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Search messages by specific sender with agent visibility controls."""

    try:
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        async with get_db_connection() as conn:
            conn.row_factory = (
                aiosqlite.Row
            )  # CRITICAL: Set row factory for dict access

            # First, verify session exists
            cursor = await conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            )
            if not await cursor.fetchone():
                return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            cursor = await conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ? AND sender = ?
                AND (visibility = 'public' OR
                     (visibility = 'private' AND sender = ?) OR
                     (visibility = 'agent_only' AND sender = ?))
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (session_id, sender, agent_id, agent_id, limit),
            )

            messages_rows = await cursor.fetchall()
            messages = [dict(msg) for msg in messages_rows]

            return {
                "success": True,
                "messages": messages,
                "sender": sender,
                "count": len(messages),
            }

    except Exception:
        logger.exception("Failed to search by sender")
        logger.debug(traceback.format_exc())
        return create_system_error("search_by_sender", "database", temporary=True)


@mcp.tool()
async def search_by_timerange(
    ctx: Context,
    session_id: str = Field(description="Session ID to search within"),
    start_time: str = Field(description="Start time (ISO format)"),
    end_time: str = Field(description="End time (ISO format)"),
    limit: int = Field(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """Search messages within a specific time range."""

    try:
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        async with get_db_connection() as conn:
            conn.row_factory = (
                aiosqlite.Row
            )  # CRITICAL: Set row factory for dict access

            # First, verify session exists
            cursor = await conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            )
            if not await cursor.fetchone():
                return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            cursor = await conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                AND datetime(timestamp) >= datetime(?)
                AND datetime(timestamp) <= datetime(?)
                AND (visibility = 'public' OR
                     (visibility = 'private' AND sender = ?) OR
                     (visibility = 'agent_only' AND sender = ?))
                ORDER BY timestamp ASC
                LIMIT ?
            """,
                (session_id, start_time, end_time, agent_id, agent_id, limit),
            )

            messages_rows = await cursor.fetchall()
            messages = [dict(msg) for msg in messages_rows]

            return {
                "success": True,
                "messages": messages,
                "timerange": {"start": start_time, "end": end_time},
                "count": len(messages),
            }

    except Exception:
        logger.exception("Failed to search by timerange")
        logger.debug(traceback.format_exc())
        return create_system_error("search_by_timerange", "database", temporary=True)


# ============================================================================
# PHASE 2: AGENT MEMORY SYSTEM
# ============================================================================


@mcp.tool()
async def set_memory(
    ctx: Context,
    key: str = Field(description="Memory key", min_length=1, max_length=255),
    value: Any = Field(description="Value to store (JSON serializable)"),
    session_id: str | None = Field(
        default=None, description="Session scope (null for global memory)"
    ),
    expires_in: int | None = Field(
        default=None,
        description="TTL in seconds (null for permanent)",
        ge=1,
        le=86400 * 365,  # Max 1 year
    ),
    metadata: Any = Field(
        default=None,
        description="Optional metadata for the memory entry (JSON object or null)",
        examples=[{"source": "user_input", "tags": ["important"]}, None],
    ),
    overwrite: bool = Field(
        default=True, description="Whether to overwrite existing key"
    ),
) -> dict[str, Any]:
    """
    Store value in agent's private memory with TTL and scope management.

    Memory can be session-scoped (isolated to specific session) or global
    (available across all sessions for the agent).
    """

    try:
        # Validate and sanitize the key
        key = key.strip()
        if not key:
            return create_llm_error_response(
                error="Memory key cannot be empty after trimming whitespace",
                code="INVALID_KEY",
                suggestions=[
                    "Provide a non-empty memory key",
                    "Use descriptive key names like 'user_preferences' or 'session_state'",
                    "Keys should be alphanumeric with underscores or dashes",
                ],
                context={"field": "key", "requirement": "non_empty_string"},
                severity=ErrorSeverity.WARNING,
            )

        # Parse metadata from MCP client (handles both string and dict inputs)
        try:
            metadata = parse_mcp_metadata(metadata)
        except ValueError:
            return ERROR_MESSAGE_PATTERNS["invalid_json_format"]("metadata")  # type: ignore[no-any-return,operator]

        if len(key) > 255:
            return create_llm_error_response(
                error="Memory key too long (max 255 characters)",
                code="INVALID_KEY",
                suggestions=[
                    "Shorten the memory key to 255 characters or less",
                    "Use abbreviated key names",
                    "Consider using hierarchical keys with dots or underscores",
                ],
                context={"key_length": len(key), "max_length": 255},
                severity=ErrorSeverity.WARNING,
            )

        if "\n" in key or "\t" in key or " " in key:
            return ERROR_MESSAGE_PATTERNS["memory_key_invalid"](key)  # type: ignore[no-any-return,operator]

        # Use actual agent_id from context if available, otherwise derive from session
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        # Calculate timestamps
        now_timestamp = datetime.now(timezone.utc)
        created_at_timestamp = now_timestamp.timestamp()
        expires_at = None
        if expires_in:
            expires_at = created_at_timestamp + expires_in

        # Serialize value to JSON with error handling
        try:
            if not isinstance(value, str):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = value
        except (TypeError, ValueError) as e:
            return create_llm_error_response(
                error=f"Value is not JSON serializable: {str(e)}",
                code="SERIALIZATION_ERROR",
                suggestions=[
                    "Ensure the value contains only JSON-compatible data types",
                    "Supported types: strings, numbers, booleans, lists, dictionaries",
                    "Remove or convert unsupported types like functions, classes, or custom objects",
                ],
                context={"value_type": type(value).__name__, "error_detail": str(e)},
                severity=ErrorSeverity.WARNING,
            )

        async with get_db_connection() as conn:
            conn.row_factory = (
                aiosqlite.Row
            )  # CRITICAL: Set row factory for dict access
            # Check if session exists (if session-scoped)
            if session_id:
                cursor = await conn.execute(
                    "SELECT id FROM sessions WHERE id = ?", (session_id,)
                )
                if not await cursor.fetchone():
                    return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            # Check for existing key if overwrite is False
            if not overwrite:
                cursor = await conn.execute(
                    """
                    SELECT key FROM agent_memory
                    WHERE agent_id = ? AND key = ?
                    AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
                    AND (expires_at IS NULL OR expires_at > ?)
                """,
                    (
                        agent_id,
                        key,
                        session_id,
                        session_id,
                        datetime.now(timezone.utc).timestamp(),
                    ),
                )

                if await cursor.fetchone():
                    return ERROR_MESSAGE_PATTERNS["memory_key_exists"](key)  # type: ignore[no-any-return,operator]

            # Insert or update memory entry
            await conn.execute(
                """
                INSERT INTO agent_memory
                (agent_id, session_id, key, value, metadata, created_at, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id, session_id, key)
                DO UPDATE SET
                    value = excluded.value,
                    metadata = excluded.metadata,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at
            """,
                (
                    agent_id,
                    session_id,
                    key,
                    serialized_value,
                    json.dumps(metadata or {}),
                    created_at_timestamp,  # Explicit created_at to ensure constraint works
                    expires_at,
                    now_timestamp.isoformat(),
                ),
            )
            await conn.commit()

            # Audit log
            await audit_log(
                conn,
                "memory_set",
                agent_id,
                session_id,
                {
                    "key": key,
                    "session_scoped": session_id is not None,
                    "has_expiration": expires_at is not None,
                    "value_size": len(serialized_value),
                },
            )

            # Trigger resource notifications
            await trigger_resource_notifications(session_id or "global", agent_id)

        return {
            "success": True,
            "key": key,
            "session_scoped": session_id is not None,
            "expires_at": expires_at,
            "scope": "session" if session_id else "global",
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        logger.exception("Failed to set memory")
        logger.debug(traceback.format_exc())
        return create_system_error("set_memory", "database", temporary=True)


@mcp.tool()
async def get_memory(
    ctx: Context,
    key: str = Field(description="Memory key to retrieve"),
    session_id: str | None = Field(
        default=None, description="Session scope (null for global memory)"
    ),
) -> dict[str, Any]:
    """
    Retrieve value from agent's private memory with automatic cleanup.
    """

    try:
        # Use actual agent_id from context if available, otherwise derive from session
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")
        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            conn.row_factory = (
                aiosqlite.Row
            )  # CRITICAL: Set row factory for dict access
            # Clean expired entries first
            await conn.execute(
                """
                DELETE FROM agent_memory
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """,
                (current_timestamp,),
            )

            # Retrieve memory entry
            cursor = await conn.execute(
                """
                SELECT key, value, metadata, created_at, updated_at, expires_at
                FROM agent_memory
                WHERE agent_id = ? AND key = ?
                AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
                AND (expires_at IS NULL OR expires_at > ?)
            """,
                (agent_id, key, session_id, session_id, current_timestamp),
            )

            row = await cursor.fetchone()

            if not row:
                return ERROR_MESSAGE_PATTERNS["memory_not_found"](key)  # type: ignore[no-any-return,operator]

            # Parse stored value
            stored_value = row["value"]
            try:
                # Try to deserialize JSON
                parsed_value = json.loads(stored_value)
            except json.JSONDecodeError:
                # If not JSON, return as string
                parsed_value = stored_value

            # Parse metadata
            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    metadata = {}

            return {
                "success": True,
                "key": key,
                "value": parsed_value,
                "metadata": metadata,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"],
                "scope": "session" if session_id else "global",
            }

    except Exception:
        logger.exception("Failed to get memory")
        logger.debug(traceback.format_exc())
        return create_system_error("get_memory", "database", temporary=True)


@mcp.tool()
async def list_memory(
    ctx: Context,
    session_id: str | None = Field(
        default=None, description="Session scope (null for global, 'all' for both)"
    ),
    prefix: str | None = Field(default=None, description="Key prefix filter"),
    limit: int = Field(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """
    List agent's memory entries with filtering options.
    """

    try:
        # Use actual agent_id from context if available, otherwise derive from session
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")
        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            conn.row_factory = (
                aiosqlite.Row
            )  # CRITICAL: Set row factory for dict access
            # Clean expired entries
            await conn.execute(
                """
                DELETE FROM agent_memory
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """,
                (current_timestamp,),
            )

            # Build query based on scope
            where_conditions = ["agent_id = ?"]
            params = [agent_id]

            if session_id and session_id != "all":
                where_conditions.append("session_id = ?")
                params.append(session_id)

            if prefix:
                where_conditions.append("key LIKE ?")
                params.append(f"{prefix}%")

            where_conditions.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(current_timestamp)

            params.append(limit)

            cursor = await conn.execute(
                f"""
                SELECT key, session_id, created_at, updated_at, expires_at,
                       length(value) as value_size
                FROM agent_memory
                WHERE {" AND ".join(where_conditions)}
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                params,
            )

            entries_rows = await cursor.fetchall()
            entries = [
                {
                    "key": entry["key"],
                    "scope": "session" if entry["session_id"] else "global",
                    "session_id": entry["session_id"],
                    "created_at": entry["created_at"],
                    "updated_at": entry["updated_at"],
                    "expires_at": entry["expires_at"],
                    "value_size": entry["value_size"],
                }
                for entry in entries_rows
            ]

            return {
                "success": True,
                "entries": entries,
                "count": len(entries),
                "scope_filter": session_id or "global",
            }

    except Exception:
        logger.exception("Failed to list memory")
        logger.debug(traceback.format_exc())
        return create_system_error("list_memory", "database", temporary=True)


# ============================================================================
# PHASE 4: PERFORMANCE MONITORING TOOL
# ============================================================================


@mcp.tool()
async def get_performance_metrics(
    ctx: Context,
) -> dict[str, Any]:
    """
    Get comprehensive performance metrics for monitoring.
    Requires admin permission.
    """

    try:
        # Extract enhanced agent context (includes JWT authentication if available)
        agent_context = extract_agent_context(ctx)
        agent_id = agent_context["agent_id"]

        # Check permission for admin access
        if "admin" not in agent_context.get("permissions", []):
            return ERROR_MESSAGE_PATTERNS["admin_required"]()  # type: ignore[no-any-return,operator]

        # Get performance metrics from the performance module
        metrics = get_performance_metrics_dict()

        # Add requesting agent info
        if metrics.get("success"):
            metrics["requesting_agent"] = agent_id
            metrics["request_timestamp"] = datetime.now(timezone.utc).isoformat()

    except Exception:
        logger.exception("Failed to get performance metrics")
        return create_system_error(
            "get_performance_metrics", "performance_monitoring", temporary=True
        )
    else:
        return metrics


# ============================================================================
# PHASE 2: MCP RESOURCES & SUBSCRIPTIONS
# ============================================================================


class ResourceNotificationManager:
    """Resource notification system for real-time updates with leak prevention."""

    def __init__(self) -> None:
        self.subscribers: dict[str, set[str]] = {}  # {resource_uri: set(client_ids)}
        self.client_last_seen: dict[str, float] = {}  # {client_id: timestamp}
        self.subscription_timeout = 300  # 5 minutes idle timeout

    async def subscribe(self, client_id: str, resource_uri: str) -> None:
        """Subscribe client to resource updates with timeout tracking."""
        if resource_uri not in self.subscribers:
            self.subscribers[resource_uri] = set()
        self.subscribers[resource_uri].add(client_id)
        self.client_last_seen[client_id] = time.time()

    async def unsubscribe(
        self, client_id: str, resource_uri: str | None = None
    ) -> None:
        """Unsubscribe client from resource updates. If resource_uri is None, unsubscribe from all."""
        if resource_uri:
            if resource_uri in self.subscribers:
                self.subscribers[resource_uri].discard(client_id)
        else:
            # Unsubscribe from all resources
            for resource_subscribers in self.subscribers.values():
                resource_subscribers.discard(client_id)

        # Remove client tracking if no longer subscribed to anything
        if not any(
            client_id in subscribers for subscribers in self.subscribers.values()
        ):
            self.client_last_seen.pop(client_id, None)

    async def cleanup_stale_subscriptions(self) -> None:
        """Remove subscriptions for clients that haven't been seen recently."""
        current_time = time.time()
        stale_clients = {
            client_id
            for client_id, last_seen in self.client_last_seen.items()
            if current_time - last_seen > self.subscription_timeout
        }

        for client_id in stale_clients:
            await self.unsubscribe(client_id)

    async def _notify_single_client(self, client_id: str, resource_uri: str) -> bool:
        """Notify a single client of resource update. Returns True if successful."""
        try:
            # Note: FastMCP resource notification would be implemented here
            # For now, we'll update the client_last_seen timestamp
            self.client_last_seen[client_id] = time.time()
            logger.debug(
                f"Notified client {client_id} of resource update: {resource_uri}"
            )
        except Exception as e:
            logger.warning(f"Failed to notify client {client_id}: {e}")
            return False
        else:
            return True

    async def notify_resource_updated(
        self, resource_uri: str, debounce_ms: int = 100
    ) -> None:
        """Notify all subscribers of resource changes with debouncing."""
        if resource_uri in self.subscribers:
            # Simple debounce: batch updates within debounce_ms window
            await asyncio.sleep(debounce_ms / 1000)

            # Collect failed clients to unsubscribe later (avoid concurrent modification)
            failed_clients = []
            for client_id in self.subscribers[resource_uri].copy():
                if not await self._notify_single_client(client_id, resource_uri):
                    failed_clients.append(client_id)  # noqa: PERF401

            # Remove failed client subscriptions
            for client_id in failed_clients:
                await self.unsubscribe(client_id, resource_uri)


# Global notification manager
notification_manager = ResourceNotificationManager()


@mcp.resource("session://{session_id}")
async def get_session_resource(session_id: str, ctx: Context) -> Resource:
    """
    Provide session as an MCP resource with real-time updates.

    Clients can subscribe to changes and receive notifications.
    """

    try:
        # Extract agent_id from MCP context (Phase 3 implementation)
        agent_id = getattr(ctx, "agent_id", None)
        if agent_id is None:
            try:
                agent_id = f"agent_{ctx.session_id[:8]}"
            except (ValueError, AttributeError):
                # Fallback for test environment or contexts without request
                agent_id = "current_agent"

        async with get_db_connection() as conn:
            conn.row_factory = (
                aiosqlite.Row
            )  # CRITICAL: Set row factory for dict access
            # Get session information
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await cursor.fetchone()

            if not session:
                _raise_session_not_found_error(session_id)
            assert session is not None

            # Get visible messages for this agent
            cursor = await conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                AND (visibility = 'public' OR
                     (visibility = 'private' AND sender = ?) OR
                     (visibility = 'agent_only' AND sender = ?))
                ORDER BY timestamp ASC
            """,
                (session_id, agent_id, agent_id),
            )

            messages = list(await cursor.fetchall())

            # Get session statistics
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT sender) as unique_agents,
                    MAX(timestamp) as last_activity
                FROM messages
                WHERE session_id = ?
            """,
                (session_id,),
            )

            stats = await cursor.fetchone()
            assert stats is not None

            # Format resource content
            content = {
                "session": {
                    "id": session["id"],
                    "purpose": session["purpose"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "created_by": session["created_by"],
                    "is_active": bool(session["is_active"]),
                    "metadata": json.loads(session["metadata"] or "{}"),
                },
                "messages": [
                    {
                        "id": msg["id"],
                        "sender": msg["sender"],
                        "content": msg["content"],
                        "timestamp": msg["timestamp"],
                        "visibility": msg["visibility"],
                        "metadata": json.loads(msg["metadata"] or "{}"),
                        "parent_message_id": msg["parent_message_id"],
                    }
                    for msg in messages
                ],
                "statistics": {
                    "message_count": stats["total_messages"] if stats else 0,
                    "visible_message_count": len(messages),
                    "unique_agents": stats["unique_agents"] if stats else 0,
                    "last_activity": stats["last_activity"] if stats else None,
                },
                "resource_info": {
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "requesting_agent": agent_id,
                    "supports_subscriptions": True,
                },
            }

            return ConcreteResource(
                uri=f"session://{session_id}",
                name=f"Session: {session['purpose']}",
                description=f"Shared context session with {len(messages)} visible messages",
                mime_type="application/json",
                text=json.dumps(content, indent=2, ensure_ascii=False),
            )

    except Exception as e:
        logger.exception("Failed to get session resource")
        raise ValueError(f"Failed to get session resource: {e}") from e


@mcp.resource("agent://{agent_id}/memory")
async def get_agent_memory_resource(agent_id: str, ctx: Context) -> Resource:
    """
    Provide agent memory as a resource with security controls.

    Only accessible by the agent itself for security.
    """

    try:
        # Extract requesting agent from MCP context (Phase 3 implementation)
        requesting_agent = getattr(ctx, "agent_id", None)
        if requesting_agent is None:
            try:
                requesting_agent = f"agent_{ctx.session_id[:8]}"
            except (ValueError, AttributeError):
                # Fallback for test environment or contexts without request
                requesting_agent = "current_agent"

        # Security check: only allow agents to access their own memory
        if requesting_agent != agent_id:
            _raise_unauthorized_access_error(agent_id)

        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            conn.row_factory = (
                aiosqlite.Row
            )  # CRITICAL: Set row factory for dict access
            # Clean expired memory entries
            await conn.execute(
                """
                DELETE FROM agent_memory
                WHERE agent_id = ? AND expires_at IS NOT NULL AND expires_at < ?
            """,
                (agent_id, current_timestamp),
            )

            # Get all memory entries for the agent
            cursor = await conn.execute(
                """
                SELECT key, value, session_id, metadata, created_at, updated_at, expires_at
                FROM agent_memory
                WHERE agent_id = ?
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY updated_at DESC
            """,
                (agent_id, current_timestamp),
            )

            memories = list(await cursor.fetchall())

            # Organize memory by scope
            memory_by_scope: dict[str, dict[str, Any]] = {"global": {}, "sessions": {}}

            for row in memories:
                # Parse value
                try:
                    value = json.loads(row["value"])
                except json.JSONDecodeError:
                    value = row["value"]

                # Parse metadata
                metadata = {}
                if row["metadata"]:
                    with suppress(json.JSONDecodeError):
                        metadata = json.loads(row["metadata"])

                memory_entry = {
                    "value": value,
                    "metadata": metadata,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "expires_at": row["expires_at"],
                }

                if row["session_id"] is None:
                    # Global memory
                    memory_by_scope["global"][row["key"]] = memory_entry
                else:
                    # Session-scoped memory
                    session_id = row["session_id"]
                    if session_id not in memory_by_scope["sessions"]:
                        memory_by_scope["sessions"][session_id] = {}
                    memory_by_scope["sessions"][session_id][row["key"]] = memory_entry

            # Create resource content
            content = {
                "agent_id": agent_id,
                "memory": memory_by_scope,
                "statistics": {
                    "global_keys": len(memory_by_scope["global"]),
                    "session_scopes": len(memory_by_scope["sessions"]),
                    "total_entries": len(memories),
                },
                "resource_info": {
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "supports_subscriptions": True,
                },
            }

            return ConcreteResource(
                uri=f"agent://{agent_id}/memory",
                name=f"Agent Memory: {agent_id}",
                description=f"Private memory store with {len(memories)} entries",
                mime_type="application/json",
                text=json.dumps(content, indent=2, ensure_ascii=False),
            )

    except Exception as e:
        logger.exception("Failed to get agent memory resource")
        raise ValueError(f"Failed to get agent memory resource: {e}") from e


async def trigger_resource_notifications(session_id: str, agent_id: str) -> None:
    """Trigger resource update notifications after changes."""

    try:
        # Phase 4: Invalidate caches for updated data
        await invalidate_session_cache(cache_manager, session_id)
        await invalidate_agent_memory_cache(cache_manager, agent_id)

        # Notify session resource subscribers
        await notification_manager.notify_resource_updated(f"session://{session_id}")

        # Notify agent memory subscribers
        await notification_manager.notify_resource_updated(f"agent://{agent_id}/memory")

    except Exception as e:
        logger.warning(f"Failed to trigger resource notifications: {e}")


# Background cleanup task for subscriptions
async def _perform_subscription_cleanup() -> None:
    """Perform a single subscription cleanup operation."""
    try:
        await notification_manager.cleanup_stale_subscriptions()
    except Exception:
        logger.exception("Subscription cleanup failed")


async def cleanup_subscriptions_task() -> None:
    """Periodic cleanup of stale subscriptions."""
    while True:
        await asyncio.sleep(60)  # Run every minute
        await _perform_subscription_cleanup()


async def _perform_memory_cleanup() -> None:
    """Perform a single memory cleanup operation."""
    try:
        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            cursor = await conn.execute(
                """
                DELETE FROM agent_memory
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """,
                (current_timestamp,),
            )

            deleted_count = cursor.rowcount
            await conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired memory entries")

    except Exception:
        logger.exception("Memory cleanup failed")


async def cleanup_expired_memory_task() -> None:
    """Lightweight TTL sweeper for expired memory entries."""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        await _perform_memory_cleanup()


# ============================================================================
# SERVER LIFECYCLE MANAGEMENT
# ============================================================================


@asynccontextmanager
async def lifespan() -> Any:
    """FastMCP server lifespan management."""

    # Startup
    print("Initializing Shared Context MCP Server...")

    # Use unified connection management from Phase 0
    # Initialize database schema
    await initialize_database()

    # Phase 4: Initialize performance optimization system
    from .utils.caching import start_cache_maintenance
    from .utils.performance import db_pool, start_performance_monitoring

    try:
        # Initialize connection pool
        database_url = os.getenv("DATABASE_URL", "chat_history.db")
        await db_pool.initialize_pool(database_url, min_size=5, max_size=50)
        print("Database connection pool initialized")

    except Exception:
        logger.exception("Failed to initialize connection pool")
        print("Warning: Running without connection pooling")

    # Start background tasks
    cleanup_tasks = []
    try:
        # Phase 4: Start performance monitoring
        perf_task = await start_performance_monitoring()
        cleanup_tasks.append(perf_task)

        # Phase 4: Start cache maintenance
        cache_task = await start_cache_maintenance()
        cleanup_tasks.append(cache_task)

        # Start subscription cleanup task
        cleanup_task = asyncio.create_task(cleanup_subscriptions_task())
        cleanup_tasks.append(cleanup_task)

        # Start memory cleanup task
        memory_task = asyncio.create_task(cleanup_expired_memory_task())
        cleanup_tasks.append(memory_task)

        print("Background tasks started (performance, cache, cleanup)")
    except Exception as e:
        logger.warning(f"Could not start background tasks: {e}")

    print("Server ready with Phase 4 production features!")

    yield

    # Shutdown
    print("Shutting down...")

    # Phase 4: Shutdown performance system
    try:
        await db_pool.shutdown_pool()
        print("Connection pool shutdown complete")
    except Exception as e:
        logger.warning(f"Error shutting down connection pool: {e}")

    # Cancel background tasks
    for task in cleanup_tasks:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    # Connection cleanup handled by get_db_connection context manager
    print("Shutdown complete")


# ============================================================================
# AUTHENTICATION MIDDLEWARE (PLACEHOLDER FOR PHASE 3)
# ============================================================================

# Note: Full authentication middleware will be implemented in Phase 3
# For Phase 1, we use basic context extraction through mcp.context

# ============================================================================
# SERVER INSTANCE & EXPORT
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


# Server lifecycle functions for development
async def initialize_server() -> FastMCP:
    """Initialize the server for development."""
    return server


async def shutdown_server() -> None:
    """Shutdown the server gracefully."""
    logger.info("Server shutdown initiated")


# Set up server lifecycle hooks if FastMCP supports them
# Note: FastMCP lifecycle management varies by version - this may need adjustment
try:
    if hasattr(mcp, "on_startup"):
        mcp.on_startup(initialize_database)
    if hasattr(mcp, "lifespan"):
        mcp.lifespan = lifespan
except Exception as e:
    logger.warning(f"Could not set lifecycle hooks: {e}")
    logger.info("Server will rely on manual initialization")
