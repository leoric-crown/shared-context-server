"""
Core JWT Authentication System for Shared Context MCP Server.

Implements the primary JWT authentication system with secure key management,
role-based permissions, and comprehensive audit logging.

Separated from auth.py for better maintainability while preserving all
existing functionality and public interfaces.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

import jwt

# Lazy import FastMCP to avoid performance overhead
if TYPE_CHECKING:
    from fastmcp import Context
    from fastmcp.server.dependencies import get_http_request
else:
    Context = None
    get_http_request = None

from .database import get_db_connection
from .models import create_error_response

logger = logging.getLogger(__name__)


@dataclass
class AuthInfo:
    """Authentication information container for FastMCP Context."""

    jwt_validated: bool = False
    agent_id: str = "unknown"
    agent_type: str = "generic"
    permissions: list[str] = field(default_factory=lambda: ["read"])
    authenticated: bool = False
    auth_method: str = "none"
    token_id: str | None = None
    auth_error: str | None = None


def get_auth_info(ctx: Context) -> AuthInfo:
    """Retrieve AuthInfo from FastMCP Context."""
    return getattr(ctx, "_auth_info", AuthInfo())


def set_auth_info(ctx: Context, auth_info: AuthInfo) -> None:
    """Store AuthInfo in FastMCP Context."""
    ctx._auth_info = auth_info  # type: ignore[attr-defined]


class JWTAuthenticationManager:
    """JWT Authentication Manager with secure key management and RBAC."""

    def __init__(self) -> None:
        """Initialize JWT authentication manager with secure configuration."""
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable must be set")

        self.secret_key: str = secret_key
        self.algorithm = "HS256"
        self.token_expiry = int(os.getenv("JWT_TOKEN_EXPIRY", "86400"))  # 24 hours
        self.clock_skew_leeway = 300  # 5 minutes
        self.available_permissions = ["read", "write", "admin", "debug"]

        logger.info("JWT Authentication Manager initialized")

    def generate_token(
        self, agent_id: str, agent_type: str, permissions: list[str]
    ) -> str:
        """Generate JWT token for agent authentication."""
        now = datetime.now(timezone.utc)

        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permissions": permissions,
            "iat": now,
            "exp": now + timedelta(seconds=self.token_expiry),
            "iss": "shared-context-server",
            "aud": "mcp-agents",
            "jti": f"{agent_id}_{int(now.timestamp())}",
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(
            f"Generated JWT token for agent {agent_id} with permissions: {permissions}"
        )
        return token

    def validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token and extract claims."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="mcp-agents",
                issuer="shared-context-server",
                leeway=self.clock_skew_leeway,
            )

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
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {e}"}
        except Exception as e:
            return {"valid": False, "error": f"Token validation failed: {e}"}

    def determine_permissions(
        self, agent_type: str, requested_permissions: list[str]
    ) -> list[str]:
        """Determine granted permissions based on agent type and request."""
        # Import config here to avoid circular imports
        from .config import get_agent_permissions_config

        permissions_config = get_agent_permissions_config()
        base_permissions = permissions_config.get_permissions_for_agent_type(agent_type)

        granted_permissions = [
            permission
            for permission in requested_permissions
            if (
                permission in self.available_permissions
                and permission in base_permissions
            )
        ]

        if not granted_permissions:
            granted_permissions = permissions_config.default_permissions.copy()

        logger.info(f"Granted permissions {granted_permissions} to {agent_type} agent")
        return granted_permissions


# LEGACY: LazyAuthManager singleton anti-pattern (DEPRECATED)
# Maintained for backward compatibility only
class LazyAuthManager:
    """
    DEPRECATED: Legacy lazy-initialized auth manager.

    This class is maintained for backward compatibility only.
    New code should use get_jwt_auth_manager() from auth_core_context.py
    which provides proper thread-safe ContextVar-based management.
    """

    def __init__(self) -> None:
        # Deferred import to avoid circular import issues
        pass

    def _get_instance(self) -> JWTAuthenticationManager:
        """Get instance from ContextVar (thread-safe)."""
        from .auth_core_context import get_jwt_auth_manager

        return get_jwt_auth_manager()

    def __getattr__(self, name: str) -> Any:
        """Proxy all attributes to ContextVar-managed instance."""
        return getattr(self._get_instance(), name)

    def reset(self) -> None:
        """
        DEPRECATED: No-op for backward compatibility.

        ContextVar provides automatic isolation, making manual resets unnecessary.
        This method is retained for backward compatibility but does nothing.
        """
        pass  # No-op - ContextVar provides automatic isolation


# LEGACY: Global instance for backward compatibility
auth_manager = LazyAuthManager()


def get_auth_manager() -> JWTAuthenticationManager:
    """
    DEPRECATED: Get auth manager (redirects to ContextVar implementation).

    This function is maintained for backward compatibility.
    New code should use get_jwt_auth_manager() from auth_core_context.py
    """
    from .auth_core_context import get_jwt_auth_manager

    return get_jwt_auth_manager()


def reset_auth_manager() -> None:
    """
    DEPRECATED: No-op for backward compatibility.

    ContextVar provides automatic isolation, making manual resets unnecessary.
    This function is retained for backward compatibility but does nothing.
    """
    pass  # No-op - ContextVar provides automatic isolation


def require_permission(permission: str) -> Callable[[Callable], Callable]:
    """Decorator to require specific permission for tool access."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = None
            for arg in args:
                if hasattr(arg, "_auth_info") or (
                    hasattr(arg, "__class__") and "Context" in str(type(arg))
                ):
                    ctx = arg
                    break

            if not ctx:
                return create_error_response(
                    error="No context available for permission check", code="NO_CONTEXT"
                )

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


async def audit_log_auth_event(
    event_type: str,
    agent_id: str,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log authentication and authorization events for security monitoring."""
    try:
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log
                (event_type, agent_id, session_id, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (
                    event_type,
                    agent_id,
                    session_id,
                    json.dumps(metadata or {}),
                ),
            )
            await conn.commit()
    except Exception:
        logger.exception("Failed to log auth event")


async def generate_agent_jwt_token(
    agent_id: str, agent_type: str, requested_permissions: list[str] | None = None
) -> str:
    """
    Generate JWT token for an agent (utility function for external use).

    This can be used by external systems to generate JWT tokens for agents
    after validating their identity through other means.
    """
    if requested_permissions is None:
        requested_permissions = ["read", "write"]

    granted_permissions = auth_manager.determine_permissions(
        agent_type, requested_permissions
    )

    token = auth_manager.generate_token(agent_id, agent_type, granted_permissions)

    await audit_log_auth_event(
        "jwt_token_generated",
        agent_id,
        None,
        {
            "agent_type": agent_type,
            "permissions": granted_permissions,
            "requested_permissions": requested_permissions,
        },
    )

    return str(token)


def _is_valid_token_format(token: str) -> bool:
    """
    Validate basic token format to reject malformed tokens.

    Valid formats:
    - Protected tokens: sct_[uuid] (e.g., sct_3361ce9d-8d6f-47f5-9a1e-d3ae5149fdb8)
    - JWT tokens: Standard JWT format (3 base64 parts separated by dots)
    """
    import re

    # Protected token format (sct_ followed by UUID)
    if token.startswith("sct_"):
        # UUID pattern: 8-4-4-4-12 hexadecimal digits
        uuid_pattern = (
            r"^sct_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
        )
        return bool(re.match(uuid_pattern, token))

    # JWT format: header.payload.signature (3 base64url-encoded parts)
    jwt_parts = token.split(".")
    if len(jwt_parts) != 3:
        return False

    # Basic base64url character set validation (allow padding)
    base64url_pattern = r"^[A-Za-z0-9_-]+={0,2}$"
    return all(re.match(base64url_pattern, part) for part in jwt_parts)
