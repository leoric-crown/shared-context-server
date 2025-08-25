"""
Authentication tools for the Shared Context MCP Server.

Provides MCP tools for JWT authentication, token refresh, and agent registration.
Includes audit logging and security utilities for multi-agent coordination.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastmcp import Context  # noqa: TC002
from pydantic import Field

from .auth import (
    audit_log_auth_event,
    auth_manager,
    extract_agent_context,
    generate_agent_jwt_token,
    validate_api_key_header,
)
from .auth_context import get_secure_token_manager
from .core_server import mcp
from .utils.llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    ErrorSeverity,
    create_llm_error_response,
    create_system_error,
)

# Set up logging
logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _generate_agent_type_field_description() -> str:
    """Generate dynamic field description for agent_type parameter."""
    try:
        from .config import get_agent_permissions_config

        permissions_config = get_agent_permissions_config()
        agent_types = list(permissions_config.agent_type_permissions.keys())

        # Find admin-capable types
        admin_types = [
            t
            for t, p in permissions_config.agent_type_permissions.items()
            if "admin" in p
        ]

        # Check for standard agent types
        standard_types = {"claude", "gemini", "generic"}
        has_standard = any(t in standard_types for t in agent_types)

        if admin_types:
            admin_str = f"Use '{admin_types[0]}' for admin access"
            if len(admin_types) > 1:
                admin_str = (
                    f"Use '{admin_types[0]}' or '{admin_types[1]}' for admin access"
                )
        else:
            admin_str = "No admin types configured"

        # Add note about standard agents if they're missing
        if not has_standard:
            admin_str += ", standard agents available"

        return f"Agent type - determines base permissions. Available: {', '.join(agent_types)}. {admin_str}."

    except Exception:
        return "Agent type - determines base permissions (e.g., 'claude', 'admin')"


def _generate_authenticate_agent_docstring() -> str:
    """Generate dynamic docstring for authenticate_agent function."""
    try:
        from .config import get_agent_permissions_config

        permissions_config = get_agent_permissions_config()

        # Build docstring with current configuration
        base_doc = """
        Generate JWT token for agent authentication.

        This is the primary authentication gateway for multi-agent coordination.
        Only the orchestrator agent should call this - subagents receive tokens via handoff.

        **Multi-Agent Pattern:**
        1. Orchestrator agent calls authenticate_agent to get tokens
        2. Orchestrator provisions tokens to subagents with appropriate permissions
        3. Subagents use refresh_token to maintain their sessions

        {}

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type determining permissions
            requested_permissions: Permissions to request (will be filtered by type)

        Returns:
            Protected token (sct_*) with agent credentials and expiry details
        """.strip()

        # Use the config's agent types docstring method if available
        agent_types_doc = ""
        if hasattr(permissions_config, "generate_agent_types_docstring"):
            agent_types_doc = permissions_config.generate_agent_types_docstring()
        else:
            # Fallback to manual generation
            agent_types = list(permissions_config.agent_type_permissions.keys())
            admin_types = [
                t
                for t, p in permissions_config.agent_type_permissions.items()
                if "admin" in p
            ]

            type_desc = f"choose from {agent_types}"
            if admin_types:
                type_desc += f" (use '{admin_types[0]}' for admin access)"
            agent_types_doc = f"**Agent Types:** {type_desc}"

        return base_doc.format(agent_types_doc)

    except Exception:
        return """
        Generate JWT token for agent authentication.

        Multi-agent authentication gateway that validates the MCP client's API key.
        """


async def audit_log(
    conn: Any,
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
# AUTHENTICATION TOOLS
# ============================================================================


def _create_authenticate_agent_tool() -> Any:
    """Create the authenticate_agent tool with dynamic docstring."""

    # Generate dynamic field description
    agent_type_description = _generate_agent_type_field_description()

    @mcp.tool(
        exclude_args=["ctx"], description=_generate_authenticate_agent_docstring()
    )
    async def authenticate_agent(
        agent_id: str = Field(
            description="Agent identifier", min_length=1, max_length=100
        ),
        agent_type: str = Field(description=agent_type_description, max_length=50),
        requested_permissions: list[str] = Field(
            default=["read", "write"], description="Requested permissions for the agent"
        ),
        ctx: Context = None,  # type: ignore[assignment]
    ) -> dict[str, Any]:
        return await _authenticate_agent_impl(
            ctx, agent_id, agent_type, requested_permissions
        )

    return authenticate_agent


# Create the tool instance
authenticate_agent = _create_authenticate_agent_tool()


async def _authenticate_agent_impl(
    ctx: Context, agent_id: str, agent_type: str, requested_permissions: list[str]
) -> dict[str, Any]:
    """Implementation of authenticate_agent functionality."""
    try:
        # Validate MCP client authentication via API key header
        api_key_valid = validate_api_key_header(ctx)
        if not api_key_valid:
            await audit_log_auth_event(
                "authentication_failed",
                agent_id,
                None,
                {
                    "agent_type": agent_type,
                    "error": "invalid_api_key_header",
                    "requested_permissions": requested_permissions,
                },
            )
            return ERROR_MESSAGE_PATTERNS["invalid_api_key"](agent_id)  # type: ignore[no-any-return,operator]

        # Generate JWT token using the new utility function
        jwt_token = await generate_agent_jwt_token(
            agent_id, agent_type, requested_permissions
        )

        # PRP-006: Create protected token instead of returning raw JWT
        token_manager = get_secure_token_manager()
        protected_token = await token_manager.create_protected_token(
            jwt_token, agent_id
        )

        # Get granted permissions for response
        granted_permissions = auth_manager.determine_permissions(
            agent_type, requested_permissions
        )

        # Calculate expiration (1 hour for protected tokens)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        return {
            "success": True,
            "token": protected_token,  # Return protected token instead of JWT
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permissions": granted_permissions,
            "expires_at": expires_at.isoformat(),
            "token_type": "Protected",  # Changed from Bearer to indicate protected format
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "token_format": "sct_*",  # Indicate protected token format
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
        except Exception:
            logger.warning("Failed to audit authentication error")

        return create_system_error(
            "authenticate_agent", "authentication_service", temporary=True
        )


@mcp.tool(exclude_args=["ctx"])
async def refresh_token(
    current_token: str = Field(
        description="Current protected token to refresh", pattern=r"^sct_[a-f0-9-]{36}$"
    ),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Refresh a protected token (PRP-006: Secure Token Authentication).

    Returns a new protected token with extended expiry using the atomic
    refresh pattern to prevent race conditions in multi-agent environments.
    """
    try:
        # Validate MCP client authentication via API key header
        api_key_valid = validate_api_key_header(ctx)
        if not api_key_valid:
            await audit_log_auth_event(
                "token_refresh_failed",
                "unknown",
                None,
                {
                    "error": "invalid_api_key_header",
                    "token_prefix": current_token[:8] if current_token else "none",
                },
            )
            return ERROR_MESSAGE_PATTERNS["invalid_api_key"]("token_refresh")  # type: ignore[no-any-return,operator]

        # Extract agent context from current token
        agent_context = await extract_agent_context(ctx, current_token)

        # Handle case where token is expired/invalid but can be used for recovery
        if not agent_context.get("authenticated"):
            # Check if this is an authentication error (expired token) that we can recover from
            if agent_context.get("authentication_error") and agent_context.get(
                "recovery_token"
            ):
                logger.info(
                    f"Attempting recovery refresh for expired token: {current_token[:12]}..."
                )

                # Try to extract agent info for recovery
                token_manager = get_secure_token_manager()
                recovery_info = await token_manager.extract_agent_info_for_recovery(
                    current_token
                )

                if recovery_info:
                    agent_id = recovery_info["agent_id"]
                    agent_type = recovery_info["agent_type"]
                    logger.info(
                        f"Successfully extracted agent info for recovery: {agent_id}"
                    )

                    # Generate new token for the recovered agent
                    new_jwt = await generate_agent_jwt_token(
                        agent_id,
                        agent_type,
                        recovery_info.get("permissions", ["read", "write"]),
                    )
                    new_token = await token_manager.create_protected_token(
                        new_jwt, agent_id
                    )

                    # Log successful recovery refresh
                    await audit_log_auth_event(
                        "token_recovered",
                        agent_id,
                        None,
                        {
                            "old_token_prefix": current_token[:8],
                            "new_token_prefix": new_token[:8],
                            "recovery_method": "expired_token_refresh",
                            "agent_type": agent_type,
                        },
                    )

                    return {
                        "success": True,
                        "token": new_token,
                        "expires_in": 3600,  # 1 hour
                        "expires_at": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat(),
                        "token_type": "Protected",
                        "token_format": "sct_*",
                        "issued_at": datetime.now(timezone.utc).isoformat(),
                        "recovery_performed": True,
                        "original_agent_id": agent_id,
                    }

            # If recovery failed or this wasn't an authentication error, return error
            await audit_log_auth_event(
                "token_refresh_failed",
                "unknown",
                None,
                {
                    "error": "token_not_recoverable",
                    "token_prefix": current_token[:8] if current_token else "none",
                    "error_type": agent_context.get("authentication_error", "unknown"),
                },
            )
            return create_llm_error_response(
                error="Token cannot be refreshed",
                code="TOKEN_REFRESH_FAILED",
                suggestions=[
                    "Token may be permanently invalid or corrupted",
                    "Use authenticate_agent to get a completely new token",
                    "Ensure you're using the correct protected token format (sct_*)",
                ],
                context={
                    "token_format": "sct_*",
                    "current_token_prefix": current_token[:8]
                    if current_token
                    else "none",
                    "error_details": agent_context.get(
                        "authentication_error", "Unknown error"
                    ),
                },
                severity=ErrorSeverity.ERROR,
            )

        agent_id = agent_context["agent_id"]

        # Use the race-condition-safe refresh method
        token_manager = get_secure_token_manager()
        new_token = await token_manager.refresh_token_safely(current_token, agent_id)

        # Log successful refresh
        await audit_log_auth_event(
            "token_refreshed",
            agent_id,
            None,
            {
                "old_token_prefix": current_token[:8],
                "new_token_prefix": new_token[:8],
                "agent_type": agent_context.get("agent_type", "unknown"),
            },
        )

        return {
            "success": True,
            "token": new_token,
            "expires_in": 3600,  # 1 hour
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "token_type": "Protected",
            "token_format": "sct_*",
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }

    except ValueError as e:
        # Handle token validation errors
        logger.warning(f"Token refresh failed: {e}")
        return create_llm_error_response(
            error=str(e),
            code="TOKEN_REFRESH_FAILED",
            suggestions=[
                "Verify the current token is valid and not expired",
                "Re-authenticate if the token is no longer valid",
                "Ensure the token format is correct (sct_*)",
            ],
            context={
                "current_token_prefix": current_token[:8] if current_token else "none",
            },
            severity=ErrorSeverity.WARNING,
        )
    except Exception as e:
        logger.exception("Token refresh system error")
        try:
            await audit_log_auth_event(
                "token_refresh_error",
                "unknown",
                None,
                {
                    "error": str(e),
                    "token_prefix": current_token[:8] if current_token else "none",
                },
            )
        except Exception:
            logger.warning("Failed to audit token refresh error")

        return create_system_error(
            "refresh_token", "token_refresh_service", temporary=True
        )
