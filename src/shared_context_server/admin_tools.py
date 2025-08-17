"""
Administration and Monitoring Tools for Shared Context MCP Server.

Provides MCP tools for system administration and monitoring:
- get_usage_guidance: Context-aware operational guidance based on access level
- get_performance_metrics: Comprehensive performance monitoring for admin users
- ResourceNotificationManager: Real-time resource update notifications
- Background tasks: Subscription cleanup and memory management

Built for production monitoring with admin-level security controls.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from fastmcp import Context
else:
    Context = None

# Lazy import WebSocket manager to avoid performance overhead
from fastmcp.resources import Resource, TextResource
from pydantic import Field

from .auth import validate_agent_context_or_error
from .core_server import mcp
from .database import get_db_connection, initialize_database
from .utils.llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    ErrorSeverity,
    create_llm_error_response,
    create_system_error,
)

logger = logging.getLogger(__name__)


# Audit logging utility
async def audit_log(
    _conn: aiosqlite.Connection,
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
# USAGE GUIDANCE SYSTEM
# ============================================================================


@mcp.tool()
async def get_usage_guidance(
    ctx: Context,
    auth_token: str | None = Field(
        default=None,
        description="JWT token to analyze. If not provided, uses current request context",
    ),
    guidance_type: str = Field(
        default="operations",
        description="Type of guidance: operations, coordination, security, troubleshooting",
    ),
) -> dict[str, Any]:
    """
    Get contextual operational guidance based on JWT access level.

    Provides JWT access-level appropriate operational guidance for multi-agent coordination.
    Returns structured guidance response based on access level (ADMIN/AGENT/READ_ONLY).
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
        permissions = agent_context.get("permissions", [])

        # Validate guidance_type parameter
        valid_types = ["operations", "coordination", "security", "troubleshooting"]
        if guidance_type not in valid_types:
            return create_llm_error_response(
                error=f"Invalid guidance_type: {guidance_type}",
                code="INVALID_GUIDANCE_TYPE",
                suggestions=[
                    "Use one of the supported guidance types",
                    f"Available options: {', '.join(valid_types)}",
                    "Check the API documentation for guidance type descriptions",
                ],
                context={
                    "provided_guidance_type": guidance_type,
                    "allowed_values": valid_types,
                },
                severity=ErrorSeverity.WARNING,
            )

        # Determine access level based on permissions
        def determine_access_level(perms: list[str]) -> str:
            if "admin" in perms:
                return "ADMIN"
            if "write" in perms:
                return "AGENT"
            return "READ_ONLY"

        access_level = determine_access_level(permissions)

        # Generate guidance content based on access level and type
        guidance_content = _generate_guidance_content(access_level, guidance_type)

        # Calculate token expiration info
        expires_at = agent_context.get("expires_at")
        can_refresh = "refresh_token" in permissions

        response = {
            "success": True,
            "access_level": access_level,
            "agent_info": {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "permissions": permissions,
                "expires_at": expires_at,
                "can_refresh": can_refresh,
            },
            "guidance": guidance_content,
            "examples": _generate_guidance_examples(access_level, guidance_type),
            "guidance_type": guidance_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Audit log the guidance request
        async with get_db_connection() as conn:
            await audit_log(
                conn,
                "usage_guidance_accessed",
                agent_id,
                None,
                {
                    "guidance_type": guidance_type,
                    "access_level": access_level,
                    "agent_type": agent_type,
                },
            )

        return response

    except Exception:
        logger.exception("Failed to get usage guidance")
        return create_system_error(
            "get_usage_guidance", "guidance_service", temporary=True
        )


def _generate_guidance_content(access_level: str, guidance_type: str) -> dict[str, Any]:
    """Generate guidance content based on access level and type."""

    if guidance_type == "operations":
        return _generate_operations_guidance(access_level)
    if guidance_type == "coordination":
        return _generate_coordination_guidance(access_level)
    if guidance_type == "security":
        return _generate_security_guidance(access_level)
    if guidance_type == "troubleshooting":
        return _generate_troubleshooting_guidance(access_level)
    return {"error": f"Unknown guidance type: {guidance_type}"}


def _generate_operations_guidance(access_level: str) -> dict[str, Any]:
    """Generate operations guidance based on access level."""

    base_operations = [
        "create_session - Create new shared context sessions",
        "get_session - Retrieve session information and messages",
        "add_message - Add messages to sessions (respects visibility controls)",
        "get_messages - Retrieve messages with agent-specific filtering",
        "search_context - Fuzzy search messages with RapidFuzz",
        "search_by_sender - Find messages by specific sender",
        "search_by_timerange - Search messages within time ranges",
    ]

    agent_operations = base_operations + [
        "set_memory - Store values in agent's private memory",
        "get_memory - Retrieve values from agent's private memory",
        "list_memory - List agent's memory entries with filtering",
        "refresh_token - Refresh authentication tokens",
    ]

    admin_operations = agent_operations + [
        "authenticate_agent - Generate JWT tokens for other agents",
        "get_performance_metrics - Access comprehensive performance data",
    ]

    if access_level == "ADMIN":
        available_ops = admin_operations
        permission_notes = [
            "Full administrative access to all operations",
            "Can generate tokens for other agents",
            "Access to performance metrics and system monitoring",
            "Can view admin_only visibility messages",
        ]
    elif access_level == "AGENT":
        available_ops = agent_operations
        permission_notes = [
            "Standard agent operations for multi-agent coordination",
            "Private memory storage and retrieval capabilities",
            "Can refresh own authentication tokens",
            "Can create and manage sessions and messages",
        ]
    else:  # READ_ONLY
        available_ops = base_operations[:4]  # Only read operations
        permission_notes = [
            "Read-only access to sessions and messages",
            "Cannot create or modify data",
            "Cannot access private memory operations",
            "Limited to public and own private messages",
        ]

    return {
        "available_operations": available_ops,
        "permission_boundaries": permission_notes,
        "next_steps": [
            "Choose operations appropriate for your access level",
            "Review visibility controls for message operations",
            "Use search operations to find relevant context",
        ],
    }


def _generate_coordination_guidance(access_level: str) -> dict[str, Any]:
    """Generate coordination guidance based on access level."""

    if access_level == "ADMIN":
        return {
            "coordination_instructions": [
                "Use authenticate_agent to generate tokens for coordinating agents",
                "Create shared sessions with create_session for multi-agent workflows",
                "Monitor agent activity with get_performance_metrics",
                "Use admin_only visibility for system coordination messages",
            ],
            "handoff_patterns": [
                "Generate agent tokens before handoff operations",
                "Create coordination session with clear purpose",
                "Use structured metadata for workflow state tracking",
                "Monitor performance metrics during complex workflows",
            ],
            "escalation_triggers": [
                "Performance degradation detected in metrics",
                "Agent authentication failures",
                "Database connection issues",
                "Memory cleanup failures",
            ],
        }
    if access_level == "AGENT":
        return {
            "coordination_instructions": [
                "Use shared sessions for multi-agent collaboration",
                "Leverage agent_only visibility for coordination messages",
                "Store workflow state in private memory for persistence",
                "Use search operations to understand session context",
            ],
            "handoff_patterns": [
                "Add coordination messages before handoff",
                "Store handoff state in agent memory",
                "Use metadata to track workflow progress",
                "Search context before taking over tasks",
            ],
            "escalation_triggers": [
                "Token expiration or authentication errors",
                "Session not found errors",
                "Memory storage failures",
                "Search operation timeouts",
            ],
        }
    # READ_ONLY
    return {
        "coordination_instructions": [
            "Monitor session activity through get_session",
            "Use search operations to understand workflow context",
            "Track coordination through message visibility",
        ],
        "handoff_patterns": [
            "Observe coordination messages in sessions",
            "Use search to understand agent handoffs",
            "Monitor public coordination activity",
        ],
        "escalation_triggers": [
            "Cannot access required session data",
            "Search operations return insufficient results",
            "Authentication token issues",
        ],
    }


def _generate_security_guidance(access_level: str) -> dict[str, Any]:
    """Generate security guidance based on access level."""

    base_security = [
        "Never expose JWT tokens in message content or metadata",
        "Use appropriate visibility levels for sensitive information",
        "Monitor token expiration and refresh proactively",
        "Validate all input parameters for security",
    ]

    if access_level == "ADMIN":
        return {
            "security_boundaries": base_security
            + [
                "Secure token generation and distribution to agents",
                "Monitor authentication events through audit logs",
                "Access to all visibility levels including admin_only",
                "Responsibility for system security monitoring",
            ],
            "token_management": [
                "Generate tokens with minimal required permissions",
                "Monitor token usage through performance metrics",
                "Implement token rotation policies",
                "Audit authentication events regularly",
            ],
            "best_practices": [
                "Use admin_only visibility for sensitive coordination",
                "Regularly review agent permissions and access",
                "Monitor for unusual authentication patterns",
                "Implement proper token lifecycle management",
            ],
        }
    if access_level == "AGENT":
        return {
            "security_boundaries": base_security
            + [
                "Access limited to own private memory and sessions",
                "Cannot generate tokens for other agents",
                "Responsible for own token security and refresh",
                "Limited to agent_only and public message visibility",
            ],
            "token_management": [
                "Refresh tokens before expiration",
                "Never share tokens with other agents",
                "Store tokens securely in client environment",
                "Handle authentication errors gracefully",
            ],
            "best_practices": [
                "Use private visibility for sensitive agent data",
                "Implement proper error handling for auth failures",
                "Monitor own token expiration times",
                "Use agent_only visibility for coordination with same agent type",
            ],
        }
    # READ_ONLY
    return {
        "security_boundaries": base_security
        + [
            "Limited to read operations only",
            "Cannot modify any data or create sessions",
            "Access limited to public and own private messages",
            "Cannot access agent memory operations",
        ],
        "token_management": [
            "Monitor token expiration status",
            "Handle authentication errors appropriately",
            "Cannot refresh own tokens",
            "Limited token permissions for security",
        ],
        "best_practices": [
            "Respect read-only access limitations",
            "Handle permission errors gracefully",
            "Use search operations within access bounds",
            "Monitor for access permission changes",
        ],
    }


def _generate_troubleshooting_guidance(access_level: str) -> dict[str, Any]:
    """Generate troubleshooting guidance based on access level."""

    common_issues = {
        "Authentication Errors": [
            "Check token format (should start with 'sct_' for protected tokens)",
            "Verify token has not expired",
            "Use refresh_token if available in permissions",
            "Re-authenticate if token is invalid",
        ],
        "Session Not Found": [
            "Verify session_id format and existence",
            "Check if session was created successfully",
            "Ensure proper session access permissions",
            "Use search operations to find available sessions",
        ],
        "Permission Denied": [
            "Review access level and required permissions",
            "Check visibility settings for messages",
            "Verify token permissions match operation requirements",
            "Use operations appropriate for access level",
        ],
    }

    if access_level == "ADMIN":
        admin_issues = common_issues.copy()
        admin_issues.update(
            {
                "Performance Issues": [
                    "Use get_performance_metrics to identify bottlenecks",
                    "Check database connection pool status",
                    "Monitor cache hit rates and effectiveness",
                    "Review audit logs for unusual patterns",
                ],
                "Agent Coordination Problems": [
                    "Check agent token generation and distribution",
                    "Review authentication audit logs",
                    "Monitor multi-agent session activity",
                    "Verify agent permissions and access levels",
                ],
            }
        )
        return {
            "common_issues": admin_issues,
            "recovery_procedures": [
                "Use performance metrics to diagnose system issues",
                "Check audit logs for authentication problems",
                "Monitor background task health and operation",
                "Use admin_only messages for system coordination",
            ],
            "debugging_steps": [
                "Enable debug logging in environment variables",
                "Check database connectivity and pool status",
                "Monitor cache performance and hit rates",
                "Review agent authentication patterns",
            ],
        }
    if access_level == "AGENT":
        return {
            "common_issues": common_issues,
            "recovery_procedures": [
                "Refresh authentication token if expired",
                "Check session existence before operations",
                "Use private memory to store recovery state",
                "Search context to understand current state",
            ],
            "debugging_steps": [
                "Verify token permissions and expiration",
                "Check session access and visibility settings",
                "Test memory operations with simple values",
                "Use search to verify session context access",
            ],
        }
    # READ_ONLY
    return {
        "common_issues": common_issues,
        "recovery_procedures": [
            "Contact admin for permission or access issues",
            "Use available search operations to gather information",
            "Check session access through get_session",
            "Monitor public message activity",
        ],
        "debugging_steps": [
            "Verify read-only token is valid and not expired",
            "Check session existence and public access",
            "Use search operations within access limits",
            "Contact admin for permission elevation if needed",
        ],
    }


def _generate_guidance_examples(
    access_level: str, guidance_type: str
) -> dict[str, Any]:
    """Generate usage examples based on access level and guidance type."""

    if guidance_type == "operations" and access_level == "ADMIN":
        return {
            "typical_workflow": [
                "# Admin coordinating multi-agent workflow",
                "admin_guidance = await get_usage_guidance(guidance_type='coordination')",
                "# Generate tokens for agents",
                "agent_token = await authenticate_agent(agent_id='worker_agent', agent_type='claude')",
                "# Create coordination session",
                "session = await create_session(purpose='Multi-agent task coordination')",
                "# Monitor performance",
                "metrics = await get_performance_metrics()",
            ]
        }
    if guidance_type == "operations" and access_level == "AGENT":
        return {
            "typical_workflow": [
                "# Agent understanding operational boundaries",
                "my_guidance = await get_usage_guidance()",
                "# Create or join session",
                "session = await create_session(purpose='Task processing')",
                "# Store workflow state",
                "await set_memory(key='workflow_state', value={'step': 1, 'status': 'active'})",
                "# Coordinate with other agents",
                "await add_message(session_id=session_id, content='Task started', visibility='agent_only')",
            ]
        }
    if guidance_type == "security":
        return {
            "typical_workflow": [
                "# Security-focused usage pattern",
                "security_guidance = await get_usage_guidance(guidance_type='security')",
                "# Check token status",
                "if expires_at < current_time + 300:  # 5 minutes",
                "    new_token = await refresh_token(current_token=token)",
                "# Use appropriate visibility",
                "await add_message(session_id=session_id, content='Sensitive coordination', visibility='agent_only')",
            ]
        }
    return {
        "typical_workflow": [
            f"# {access_level} level {guidance_type} usage",
            f"guidance = await get_usage_guidance(guidance_type='{guidance_type}'",
            "# Follow guidance recommendations",
            "# Use operations appropriate for access level",
        ]
    }


# ============================================================================
# PERFORMANCE MONITORING TOOL
# ============================================================================


@mcp.tool()
async def get_performance_metrics(
    ctx: Context,
    auth_token: str | None = Field(
        default=None, description="Optional JWT token for admin access"
    ),
) -> dict[str, Any]:
    """
    Get comprehensive performance metrics for monitoring.
    Requires admin permission.
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

        # Check permission for admin access
        if "admin" not in agent_context.get("permissions", []):
            return ERROR_MESSAGE_PATTERNS["admin_required"]()  # type: ignore[no-any-return,operator]

        # Get performance metrics from the performance module
        from .utils.performance import get_performance_metrics_dict

        metrics = get_performance_metrics_dict()

        # Add requesting agent info
        if metrics.get("success"):
            metrics["requesting_agent"] = agent_id
            metrics["request_timestamp"] = datetime.now(timezone.utc).isoformat()

        return metrics

    except Exception:
        logger.exception("Failed to get performance metrics")
        return create_system_error(
            "get_performance_metrics", "performance_monitoring", temporary=True
        )


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
async def get_session_resource(session_id: str, ctx: Context = None) -> Resource:
    """
    Provide session as an MCP resource with real-time updates.

    Clients can subscribe to changes and receive notifications.
    """

    try:
        # Extract agent_id from MCP context
        try:
            if ctx is not None:
                agent_id = getattr(ctx, "agent_id", None)
                if agent_id is None:
                    agent_id = f"agent_{ctx.session_id[:8]}"
            else:
                # Fallback for direct function calls or test environment
                agent_id = "current_agent"
        except (AttributeError, ValueError):
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
                from .utils.llm_errors import create_resource_not_found_error

                error_response = create_resource_not_found_error("session", session_id)
                raise ValueError(
                    error_response.get("error", f"Session {session_id} not found")
                )
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
async def get_agent_memory_resource(agent_id: str, ctx: Context = None) -> Resource:
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
            raise ValueError(f"Unauthorized access to agent {agent_id} memory")

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

            return TextResource(
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


# ============================================================================
# BACKGROUND TASK MANAGEMENT
# ============================================================================


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


@asynccontextmanager  # type: ignore[misc]
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
# SERVER MANAGEMENT FUNCTIONS
# ============================================================================


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
