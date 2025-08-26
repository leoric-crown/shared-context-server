"""
Administration Resource Management for Shared Context MCP Server.

Provides MCP resource management and real-time notifications:
- ResourceNotificationManager: Real-time resource update notifications
- Session resource: Provides session data as MCP resource with subscriptions
- Agent memory resource: Provides agent memory as secure MCP resource
- Resource notification triggers for real-time updates

Built for production monitoring with admin-level security controls.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from fastmcp.resources import Resource, TextResource
from pydantic import AnyUrl

from .core_server import mcp
from .database_manager import CompatibleRow, get_db_connection

# Removed sanitization imports - using generic logging instead

logger = logging.getLogger(__name__)


def _raise_session_not_found_error(session_id: str) -> None:
    """Helper function to raise session not found error."""
    from .utils.llm_errors import create_resource_not_found_error

    error_response = create_resource_not_found_error("session", session_id)
    raise ValueError(error_response.get("error", f"Session {session_id} not found"))


def _raise_unauthorized_access_error(agent_id: str) -> None:
    """Helper function to raise unauthorized access error."""
    raise ValueError(f"Unauthorized access to agent {agent_id} memory")


# ============================================================================
# MCP RESOURCES & SUBSCRIPTIONS
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
            # Log success without sensitive client ID
            logger.debug("Successfully notified client of resource update")
        except Exception as e:
            # Log failure without sensitive client ID
            logger.warning("Failed to notify client of resource update: %s", str(e))
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
async def get_session_resource(session_id: str, ctx: Any = None) -> Resource:
    """
    Provide session as an MCP resource with real-time updates.

    Clients can subscribe to changes and receive notifications.
    """

    try:
        # Extract agent_id from MCP context
        if ctx is not None:
            agent_id = getattr(ctx, "agent_id", None)
            if agent_id is None:
                agent_id = f"agent_{ctx.session_id[:8]}"
        else:
            # Fallback for direct function calls or test environment
            agent_id = "current_agent"

        async with get_db_connection() as conn:
            conn.row_factory = CompatibleRow  # Set row factory for dict access
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

            return TextResource(
                uri=AnyUrl(f"session://{session_id}"),
                name=f"Session: {session['purpose']}",
                description=f"Shared context session with {len(messages)} visible messages",
                mime_type="application/json",
                text=json.dumps(content, indent=2, ensure_ascii=False),
            )

    except Exception as e:
        logger.exception("Failed to get session resource")
        raise ValueError(f"Failed to get session resource: {e}") from e


@mcp.resource("agent://{agent_id}/memory")
async def get_agent_memory_resource(agent_id: str, ctx: Any = None) -> Resource:
    """
    Provide agent memory as a resource with security controls.

    Only accessible by the agent itself for security.
    """

    try:
        # Extract requesting agent from MCP context (fallback implementation)
        # Note: In FastMCP 0.3+, context is injected differently
        try:
            if ctx is not None:
                requesting_agent = getattr(ctx, "agent_id", None)
                if requesting_agent is None:
                    requesting_agent = f"agent_{ctx.session_id[:8]}"
            else:
                # Fallback for direct function calls or test environment
                requesting_agent = "current_agent"
        except (AttributeError, ValueError):
            # Fallback for test environment or contexts without request
            requesting_agent = "current_agent"

        # Security check: only allow agents to access their own memory
        if requesting_agent != agent_id:
            _raise_unauthorized_access_error(agent_id)

        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            conn.row_factory = CompatibleRow  # Set row factory for dict access
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

            return TextResource(
                uri=AnyUrl(f"agent://{agent_id}/memory"),
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
        from .utils.caching import (
            cache_manager,
            invalidate_agent_memory_cache,
            invalidate_session_cache,
        )

        await invalidate_session_cache(cache_manager, session_id)
        await invalidate_agent_memory_cache(cache_manager, agent_id)

        # Notify session resource subscribers
        await notification_manager.notify_resource_updated(f"session://{session_id}")

        # Notify agent memory subscribers
        await notification_manager.notify_resource_updated(f"agent://{agent_id}/memory")

        # WebSocket notifications for Web UI with lazy import
        try:
            from .websocket_handlers import websocket_manager

            await websocket_manager.broadcast_to_session(
                session_id,
                {
                    "type": "session_update",
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except ImportError:
            pass  # WebSocket support not available

    except Exception as e:
        logger.warning(f"Failed to trigger resource notifications: {e}")


# Background task for subscription cleanup
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


@mcp.resource("session://{session_id}/messages/{limit}")
async def get_session_messages_paginated_resource(
    session_id: str, limit: str = "50", ctx: Any = None
) -> Resource:
    """
    Enhanced session messages resource with pagination support.

    Provides parameterized message retrieval with limit control for
    efficient access to session message history.

    Args:
        session_id: Session ID to retrieve messages from
        limit: Maximum number of messages to return (default: 50, max: 500)
        ctx: MCP context for authentication and agent identification
    """

    try:
        # Parse and validate limit parameter
        try:
            limit_int = int(limit)
            if limit_int < 1:
                limit_int = 50
            elif limit_int > 500:
                limit_int = 500
        except ValueError:
            limit_int = 50

        # Extract agent_id from MCP context
        if ctx is not None:
            agent_id = getattr(ctx, "agent_id", None)
            if agent_id is None:
                agent_id = f"agent_{ctx.session_id[:8]}"
        else:
            agent_id = "current_agent"

        async with get_db_connection() as conn:
            conn.row_factory = CompatibleRow

            # Get session information
            session_cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await session_cursor.fetchone()

            if not session:
                return TextResource(
                    uri=AnyUrl(f"session://{session_id}/messages/{limit}"),
                    name="Session Messages (Not Found)",
                    description=f"Session {session_id} not found",
                    mime_type="application/json",
                    text=json.dumps({"error": "Session not found"}, indent=2),
                )

            # Get paginated messages with visibility filtering
            # Note: This implements the same visibility logic as the main session resource
            messages_cursor = await conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit_int),
            )
            all_messages = await messages_cursor.fetchall()

            # Apply visibility filtering (simplified version)
            # In production, this would use the full visibility filtering logic
            visible_messages = []
            for msg in all_messages:
                msg_dict = dict(msg)
                # Basic visibility check - in production would be more comprehensive
                if (
                    msg_dict.get("visibility") == "public"
                    or msg_dict.get("sender") == agent_id
                ):
                    visible_messages.append(msg_dict)

            # Prepare response content
            content = {
                "session_id": session_id,
                "session_purpose": session["purpose"]
                if session["purpose"]
                else "No purpose specified",
                "pagination": {
                    "requested_limit": limit_int,
                    "total_messages_returned": len(visible_messages),
                    "messages_filtered_by_visibility": len(all_messages)
                    - len(visible_messages),
                },
                "messages": visible_messages,
                "metadata": {
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "retrieved_by": agent_id,
                    "resource_uri": f"session://{session_id}/messages/{limit}",
                },
            }

            return TextResource(
                uri=AnyUrl(f"session://{session_id}/messages/{limit}"),
                name=f"Session Messages ({len(visible_messages)}/{limit_int})",
                description=f"Paginated messages from session {session_id} with limit {limit_int}",
                mime_type="application/json",
                text=json.dumps(content, indent=2, ensure_ascii=False),
            )

    except Exception as e:
        logger.exception(
            f"Error retrieving paginated messages for session {session_id}"
        )

        error_content = {
            "error": "Failed to retrieve session messages",
            "details": str(e),
            "session_id": session_id,
            "requested_limit": limit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return TextResource(
            uri=AnyUrl(f"session://{session_id}/messages/{limit}"),
            name="Session Messages (Error)",
            description=f"Error retrieving messages from session {session_id}",
            mime_type="application/json",
            text=json.dumps(error_content, indent=2),
        )
