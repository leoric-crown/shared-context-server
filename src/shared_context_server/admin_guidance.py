"""
Administration Guidance Tools for Shared Context MCP Server.

Provides contextual operational guidance based on JWT access levels:
- get_usage_guidance: Context-aware operational guidance for multi-agent coordination
- Supporting guidance generation functions for different access levels and types

Built for production monitoring with admin-level security controls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastmcp import Context  # noqa: TC002
from pydantic import Field

from .auth import validate_agent_context_or_error
from .core_server import mcp
from .database import get_db_connection
from .utils.llm_errors import (
    ErrorSeverity,
    create_llm_error_response,
    create_system_error,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ERROR HELPER FUNCTIONS
# ============================================================================


def _raise_session_not_found_error(session_id: str) -> None:
    """Helper function to raise session not found error."""
    from .utils.llm_errors import create_resource_not_found_error

    error_response = create_resource_not_found_error("session", session_id)
    raise ValueError(error_response.get("error", f"Session {session_id} not found"))


def _raise_unauthorized_access_error(agent_id: str) -> None:
    """Helper function to raise unauthorized access error."""
    raise ValueError(f"Unauthorized access to agent {agent_id} memory")


# Audit logging utility
async def audit_log(
    _conn: Any,
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


@mcp.tool(exclude_args=["ctx"])
async def get_usage_guidance(
    auth_token: str | None = Field(
        default=None,
        description="Optional JWT token for elevated permissions",
    ),
    guidance_type: str = Field(
        default="operations",
        description="Type of guidance: operations, coordination, security, troubleshooting",
    ),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    🚨 **CALL THIS TOOL FIRST** - Get your operational capabilities and permission boundaries.

    Essential first step for multi-agent coordination. Provides JWT access-level appropriate
    operational guidance based on your authentication context (ADMIN/AGENT/READ_ONLY).

    This tool tells you:
    - What operations you can perform
    - Your permission boundaries
    - Available tools based on your access level
    - Examples of proper usage patterns

    Always call this before attempting other operations to avoid permission errors.
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

    read_only_operations = [
        "get_session - Retrieve session information and messages",
        "get_messages - Retrieve messages with agent-specific filtering",
        "search_context - Fuzzy search messages with RapidFuzz",
        "search_by_sender - Find messages by specific sender",
        "search_by_timerange - Search messages within time ranges",
        "get_memory - Retrieve values from agent's private memory",
        "list_memory - List agent's memory entries with filtering",
    ]

    write_operations = [
        "create_session - Create new shared context sessions",
        "add_message - Add messages to sessions (respects visibility controls)",
        "set_memory - Store values in agent's private memory",
    ]

    base_operations = read_only_operations + write_operations

    agent_operations = base_operations + [
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
        available_ops = read_only_operations  # Only read operations
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
                "Use shared sessions for multi-agent collaboration (sessions are collaborative by design)",
                "Any authenticated agent can join existing sessions to contribute",
                "Leverage agent_only visibility for coordination messages with same agent type",
                "Store workflow state in private memory for persistence (memory is agent-isolated)",
                "Use search operations to understand session context before contributing",
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
                "Access limited to own private memory (memory is agent-isolated, sessions are collaborative)",
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
                "agent_token = await authenticate_agent(agent_id='worker_agent', agent_type='generic')",
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
