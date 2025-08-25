"""
Search and Discovery Tools for Shared Context MCP Server.

Provides MCP tools for searching and discovering content:
- search_context: RapidFuzz-powered fuzzy search with caching and performance optimization
- search_by_sender: Find messages by specific sender with visibility controls
- search_by_timerange: Search messages within time windows

Built for high performance with 5-10x faster search than standard fuzzy search.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

# aiosqlite removed in favor of SQLAlchemy-only backend
from pydantic import Field
from rapidfuzz import fuzz, process

if TYPE_CHECKING:
    # TestConnectionType now handled by SQLAlchemy connection wrapper
    TestConnectionType = Any
else:
    TestConnectionType = Any

from fastmcp import Context  # noqa: TC002

from .auth import validate_agent_context_or_error
from .core_server import mcp
from .database import get_db_connection
from .utils.caching import cache_manager, generate_search_cache_key
from .utils.llm_errors import ERROR_MESSAGE_PATTERNS, create_system_error

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
# RAPIDFUZZ SEARCH SYSTEM
# ============================================================================


@mcp.tool(exclude_args=["ctx"])
async def search_context(
    session_id: str = Field(description="Session ID to search within"),
    query: str = Field(description="Search query"),
    auth_token: str | None = Field(
        default=None,
        description="Optional JWT token for elevated permissions",
    ),
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
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Fuzzy search messages using RapidFuzz for 5-10x performance improvement.

    Searches content, sender, and optionally metadata fields with agent-specific
    visibility controls.
    """

    try:
        start_time = time.time()
        # Extract and validate agent context (with token validation error handling)
        agent_context = await validate_agent_context_or_error(ctx, auth_token)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]

        # Phase 4: Try cache first for search results (10-minute TTL due to compute cost)
        cache_key = generate_search_cache_key(
            session_id, query, fuzzy_threshold, search_scope, limit
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

        # Production connection path
        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            # Row factory handled by SQLAlchemy connection wrapper

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
            # Handle both Unix timestamp (numeric) and ISO datetime (string) formats
            where_conditions.append(
                f"(timestamp >= unixepoch('now', '-{recent_hours} hours') OR datetime(timestamp) >= datetime('now', '-{recent_hours} hours'))"
            )

            # Apply visibility controls with admin support
            if search_scope == "public":
                where_conditions.append("visibility = 'public'")
            elif search_scope == "private":
                where_conditions.append("visibility = 'private' AND sender = ?")
                params.append(agent_id)
            else:  # all accessible messages
                # Check if agent has admin permissions using extracted agent context
                has_admin_permission = "admin" in agent_context.get("permissions", [])

                if has_admin_permission:
                    # ADMIN: Unrestricted access to all messages
                    where_conditions.append("""
                        (visibility = 'public' OR
                         visibility = 'private' OR
                         visibility = 'agent_only' OR
                         visibility = 'admin_only')
                    """)
                    # No sender restrictions for admin
                else:
                    # Non-admin: Limited to public + own private/agent_only
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


@mcp.tool(exclude_args=["ctx"])
async def search_by_sender(
    session_id: str = Field(description="Session ID to search within"),
    sender: str = Field(description="Sender to search for"),
    limit: int = Field(default=20, ge=1, le=100),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Search messages by specific sender with agent visibility controls."""

    try:
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        async with get_db_connection() as conn:
            conn.row_factory = None  # Use SQLAlchemy row type

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


@mcp.tool(exclude_args=["ctx"])
async def search_by_timerange(
    session_id: str = Field(description="Session ID to search within"),
    start_time: str = Field(description="Start time (ISO format)"),
    end_time: str = Field(description="End time (ISO format)"),
    limit: int = Field(default=50, ge=1, le=200),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Search messages within a specific time range."""

    try:
        agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")

        # Convert ISO datetime strings to Unix timestamps for comparison
        try:
            start_unix = datetime.fromisoformat(
                start_time.replace("Z", "+00:00")
            ).timestamp()
            end_unix = datetime.fromisoformat(
                end_time.replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            return {
                "success": False,
                "error": "Invalid datetime format",
                "code": "INVALID_DATETIME",
            }

        async with get_db_connection() as conn:
            conn.row_factory = None  # Use SQLAlchemy row type

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
                AND timestamp >= ?
                AND timestamp <= ?
                AND (visibility = 'public' OR
                     (visibility = 'private' AND sender = ?) OR
                     (visibility = 'agent_only' AND sender = ?))
                ORDER BY timestamp ASC
                LIMIT ?
            """,
                (session_id, start_unix, end_unix, agent_id, agent_id, limit),
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
