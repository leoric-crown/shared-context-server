"""
Phase 3 - JWT Authentication System for Shared Context MCP Server.

Implements JWT token-based authentication with role-based access control (RBAC),
secure key management, and comprehensive audit logging.

Key Features:
- JWT token generation and validation with secure key management
- Role-based permission system (read, write, admin, debug)
- Token expiration and clock skew handling
- Comprehensive audit logging for security events
- Permission decorators for tool access control
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

import jwt
from fastmcp import Context

from .database import get_db_connection
from .models import create_error_response

logger = logging.getLogger(__name__)


@dataclass
class AuthInfo:
    """
    Authentication information container for FastMCP Context.

    This dataclass encapsulates all authentication-related information
    to avoid dynamic attribute assignment on Context objects.
    """

    jwt_validated: bool = False
    agent_id: str = "unknown"
    agent_type: str = "generic"
    permissions: list[str] = field(default_factory=lambda: ["read"])
    authenticated: bool = False
    auth_method: str = "none"
    token_id: str | None = None
    auth_error: str | None = None


def get_auth_info(ctx: Context) -> AuthInfo:
    """
    Retrieve AuthInfo from FastMCP Context.

    Args:
        ctx: FastMCP context object

    Returns:
        AuthInfo object, either stored or default
    """
    return getattr(ctx, "_auth_info", AuthInfo())


def set_auth_info(ctx: Context, auth_info: AuthInfo) -> None:
    """
    Store AuthInfo in FastMCP Context.

    Args:
        ctx: FastMCP context object
        auth_info: AuthInfo object to store
    """
    ctx._auth_info = auth_info  # type: ignore[attr-defined]


class JWTAuthenticationManager:
    """
    JWT Authentication Manager with secure key management and RBAC.

    Handles token generation, validation, and permission management for
    multi-agent authentication and authorization.
    """

    def __init__(self) -> None:
        """Initialize JWT authentication manager with secure configuration."""
        # CRITICAL: Persistent secret key required, no random fallbacks in production
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError(
                    "JWT_SECRET_KEY environment variable must be set for production"
                )
            # Development fallback - generate a temporary key
            secret_key = "dev-secret-key-not-for-production-use"
            logger.warning(
                "Using development JWT secret key - not suitable for production!"
            )

        # Ensure secret_key is always str type for JWT library
        self.secret_key: str = secret_key

        self.algorithm = "HS256"
        self.token_expiry = int(
            os.getenv("JWT_TOKEN_EXPIRY", "86400")
        )  # 24 hours default
        self.clock_skew_leeway = 300  # 5 minutes clock skew tolerance

        # Available permissions in the system
        self.available_permissions = ["read", "write", "admin", "debug"]

        logger.info("JWT Authentication Manager initialized")

    def generate_token(
        self, agent_id: str, agent_type: str, permissions: list[str]
    ) -> str:
        """
        Generate JWT token for agent authentication.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (claude, gemini, custom, etc.)
            permissions: List of permissions to grant

        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)

        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permissions": permissions,
            "iat": now,
            "exp": now + timedelta(seconds=self.token_expiry),
            "iss": "shared-context-server",
            "aud": "mcp-agents",
            "jti": f"{agent_id}_{int(now.timestamp())}",  # Unique token ID for revocation
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(
            f"Generated JWT token for agent {agent_id} with permissions: {permissions}"
        )

        return token

    def validate_token(self, token: str) -> dict[str, Any]:
        """
        Validate JWT token and extract claims.

        Args:
            token: JWT token to validate

        Returns:
            Dictionary with validation result and extracted claims
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="mcp-agents",
                issuer="shared-context-server",
                leeway=self.clock_skew_leeway,  # Handle clock skew between servers
            )

            # Additional validation
            agent_id = payload.get("agent_id")
            agent_type = payload.get("agent_type")
            permissions = payload.get("permissions", [])

            if not agent_id or not agent_type:
                return {"valid": False, "error": "Missing required claims"}

            # Validate permissions are known
            invalid_permissions = [
                p for p in permissions if p not in self.available_permissions
            ]
            if invalid_permissions:
                logger.warning(
                    f"Token contains invalid permissions: {invalid_permissions}"
                )

            return {
                "valid": True,
                "agent_id": agent_id,
                "agent_type": agent_type,
                "permissions": permissions,
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "token_id": payload.get("jti"),
            }

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return {"valid": False, "error": f"Invalid token: {e}"}
        except Exception as e:
            logger.exception("Token validation failed")
            return {"valid": False, "error": f"Token validation failed: {e}"}

    def determine_permissions(
        self, agent_type: str, requested_permissions: list[str]
    ) -> list[str]:
        """
        Determine granted permissions based on agent type and request.

        Args:
            agent_type: Type of agent requesting permissions
            requested_permissions: List of requested permissions

        Returns:
            List of granted permissions
        """
        # Base permission mappings by agent type
        type_permissions = {
            "claude": ["read", "write"],
            "gemini": ["read", "write"],
            "admin": ["read", "write", "admin", "debug"],
            "system": ["read", "write", "admin", "debug"],
            "test": ["read", "write", "debug"],  # For testing
            "generic": ["read"],
        }

        # Get base permissions for agent type
        base_permissions = type_permissions.get(agent_type.lower(), ["read"])

        # Grant intersection of requested and allowed permissions
        granted_permissions = [
            permission
            for permission in requested_permissions
            if (
                permission in self.available_permissions
                and permission in base_permissions
            )
        ]

        # Ensure minimum read permission
        if not granted_permissions:
            granted_permissions = ["read"]

        logger.info(f"Granted permissions {granted_permissions} to {agent_type} agent")
        return granted_permissions


# Global authentication manager
auth_manager = JWTAuthenticationManager()


def require_permission(permission: str) -> Callable[[Callable], Callable]:
    """
    Decorator to require specific permission for tool access.

    Args:
        permission: Required permission name

    Returns:
        Decorated function that checks permissions
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract context - assume first argument is Context
            ctx = None
            for arg in args:
                if isinstance(arg, Context):
                    ctx = arg
                    break

            if not ctx:
                return create_error_response(
                    error="No context available for permission check", code="NO_CONTEXT"
                )

            # Get agent permissions from context (set by authentication middleware)
            auth_info = get_auth_info(ctx)
            agent_permissions = auth_info.permissions
            agent_id = auth_info.agent_id

            if permission not in agent_permissions:
                logger.warning(
                    f"Permission denied: {agent_id} lacks '{permission}' permission"
                )
                return create_error_response(
                    error=f"Permission '{permission}' required",
                    code="PERMISSION_DENIED",
                    metadata={
                        "required_permission": permission,
                        "agent_permissions": agent_permissions,
                        "agent_id": agent_id,
                    },
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def extract_agent_context(ctx: Context) -> dict[str, Any]:
    """
    Extract comprehensive agent context from FastMCP context.

    Args:
        ctx: FastMCP context object

    Returns:
        Dictionary with agent identity and authentication info
    """
    # Get authentication info from context
    auth_info = get_auth_info(ctx)

    # Check for JWT authentication first (Phase 3)
    if auth_info.jwt_validated:
        return {
            "agent_id": auth_info.agent_id,
            "agent_type": auth_info.agent_type,
            "authenticated": True,
            "auth_method": "jwt",
            "permissions": auth_info.permissions,
            "token_id": auth_info.token_id,
        }

    # Fallback to basic authentication (Phase 1/2)
    # Use session_id fallback if agent_id is still "unknown"
    agent_id = auth_info.agent_id
    if agent_id == "unknown" and hasattr(ctx, "session_id"):
        agent_id = f"agent_{ctx.session_id[:8]}"

    agent_type = auth_info.agent_type

    # Basic API key check
    authenticated = auth_info.authenticated

    return {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "authenticated": authenticated,
        "auth_method": "api_key",
        "permissions": ["read", "write"] if authenticated else ["read"],
        "token_id": None,
    }


async def audit_log_auth_event(
    event_type: str,
    agent_id: str,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Log authentication and authorization events for security monitoring.

    Args:
        event_type: Type of authentication event
        agent_id: ID of the agent involved
        session_id: Optional session ID
        metadata: Additional event metadata
    """
    try:
        async with get_db_connection() as conn:
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
            await conn.commit()
    except Exception:
        logger.exception("Failed to log auth event")


# Authentication middleware context enhancer
async def enhance_context_with_auth(
    ctx: Context, authorization_header: str | None = None
) -> None:
    """
    Enhance FastMCP context with authentication information.

    This function should be called by middleware to enrich the context
    with authentication and authorization information.

    Args:
        ctx: FastMCP context to enhance
        authorization_header: Authorization header value
    """
    try:
        if authorization_header and authorization_header.startswith("Bearer "):
            # JWT authentication
            token = authorization_header[7:]  # Remove "Bearer " prefix

            validation_result = auth_manager.validate_token(token)

            if validation_result["valid"]:
                # Create JWT authentication context
                auth_info = AuthInfo(
                    jwt_validated=True,
                    agent_id=validation_result["agent_id"],
                    agent_type=validation_result["agent_type"],
                    permissions=validation_result["permissions"],
                    authenticated=True,
                    auth_method="jwt",
                    token_id=validation_result.get("token_id"),
                )
                set_auth_info(ctx, auth_info)

                # Log successful authentication
                await audit_log_auth_event(
                    "jwt_authentication_success",
                    auth_info.agent_id,
                    None,
                    {
                        "agent_type": auth_info.agent_type,
                        "permissions": auth_info.permissions,
                        "token_id": auth_info.token_id,
                    },
                )
            else:
                # Failed JWT authentication
                auth_info = AuthInfo(
                    jwt_validated=False,
                    authenticated=False,
                    auth_error=validation_result["error"],
                )
                set_auth_info(ctx, auth_info)

                # Log authentication failure
                await audit_log_auth_event(
                    "jwt_authentication_failed",
                    "unknown",
                    None,
                    {"error": validation_result["error"]},
                )
        else:
            # Fallback to basic API key authentication
            api_key = (
                authorization_header.replace("Bearer ", "")
                if authorization_header
                else ""
            )
            valid_api_key = os.getenv("API_KEY", "")

            authenticated = api_key == valid_api_key if valid_api_key else False

            # Get existing agent_id from context if available
            existing_auth = get_auth_info(ctx)
            agent_id = (
                existing_auth.agent_id
                if existing_auth.agent_id != "unknown"
                else "unknown"
            )

            # Set basic authentication context
            auth_info = AuthInfo(
                jwt_validated=False,
                agent_id=agent_id,
                agent_type="generic",
                permissions=["read", "write"] if authenticated else ["read"],
                authenticated=authenticated,
                auth_method="api_key",
            )
            set_auth_info(ctx, auth_info)

            if authenticated:
                await audit_log_auth_event(
                    "api_key_authentication_success",
                    auth_info.agent_id,
                    None,
                    {"auth_method": "api_key"},
                )

    except Exception as e:
        logger.exception("Authentication context enhancement failed")

        # Set minimal context on error
        auth_info = AuthInfo(
            jwt_validated=False,
            agent_id="unknown",
            agent_type="generic",
            permissions=["read"],
            authenticated=False,
            auth_error=str(e),
        )
        set_auth_info(ctx, auth_info)
