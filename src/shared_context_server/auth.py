"""
JWT Authentication System for Shared Context MCP Server.

Implements a clean two-tier authentication system:
1. API Key (header-based): Static authentication for MCP client connection
2. JWT Token (parameter-based): Dynamic per-request agent authentication

Key Features:
- Header-based API key validation for MCP client authentication
- Parameter-based JWT tokens for dynamic agent authentication
- Role-based permission system (read, write, admin, debug)
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
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import aiosqlite

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
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError(
                    "JWT_SECRET_KEY environment variable must be set for production"
                )
            secret_key = "dev-secret-key-not-for-production-use"
            logger.warning(
                "Using development JWT secret key - not suitable for production!"
            )

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


# Global auth manager with lazy initialization
class LazyAuthManager:
    """Lazy-initialized auth manager that behaves like the actual manager."""

    def __init__(self) -> None:
        self._instance: JWTAuthenticationManager | None = None

    def _get_instance(self) -> JWTAuthenticationManager:
        if self._instance is None:
            self._instance = JWTAuthenticationManager()
        return self._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_instance(), name)

    def reset(self) -> None:
        """Reset the auth manager instance (for testing)."""
        self._instance = None


auth_manager = LazyAuthManager()


def get_auth_manager() -> JWTAuthenticationManager:
    """Get the global auth manager, initializing lazily."""
    return auth_manager._get_instance()


def reset_auth_manager() -> None:
    """Reset the global auth manager (for testing)."""
    auth_manager.reset()


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


async def validate_jwt_token_parameter(auth_token: str | None) -> dict[str, Any] | None:
    """
    Validate JWT token passed as tool parameter for dynamic agent authentication.

    This enables per-request agent identification while the MCP connection
    uses static API key authentication.

    PRP-006: Enhanced to support protected token resolution for JWT hiding.
    """
    if not auth_token:
        return None

    try:
        # First, validate token format to reject malformed tokens explicitly
        if not _is_valid_token_format(auth_token):
            logger.warning(f"Malformed token format rejected: {auth_token}")
            # Return a special error marker instead of None to prevent fallback
            return {"validation_error": f"Malformed token format: {auth_token}"}

        # Check if this is a protected token (sct_*)
        if auth_token.startswith("sct_"):
            # Resolve protected token to JWT
            token_manager = get_secure_token_manager()
            jwt_token = await token_manager.resolve_protected_token(auth_token)

            if not jwt_token:
                logger.warning(f"Invalid or expired protected token: {auth_token}")
                # Return authentication error marker instead of None to prevent fallback
                return {
                    "authentication_error": f"Protected token invalid or expired: {auth_token[:12]}..."
                }

            # Validate the resolved JWT
            jwt_result = auth_manager.validate_token(jwt_token)
            if jwt_result["valid"]:
                logger.info(
                    f"Protected token validated for agent {jwt_result['agent_id']}"
                )
                return {
                    "agent_id": jwt_result["agent_id"],
                    "agent_type": jwt_result["agent_type"],
                    "authenticated": True,
                    "auth_method": "protected_jwt",
                    "permissions": jwt_result["permissions"],
                    "token_id": jwt_result.get("token_id"),
                    "protected_token": auth_token,  # Include original protected token
                }
            logger.warning(
                f"Invalid JWT from protected token: {jwt_result.get('error')}"
            )
            # Return authentication error marker for expired/invalid JWT
            return {
                "authentication_error": f"JWT validation failed: {jwt_result.get('error')}"
            }
        # Original JWT token validation (for backward compatibility)
        jwt_result = auth_manager.validate_token(auth_token)
        if jwt_result["valid"]:
            logger.info(f"JWT token validated for agent {jwt_result['agent_id']}")
            return {
                "agent_id": jwt_result["agent_id"],
                "agent_type": jwt_result["agent_type"],
                "authenticated": True,
                "auth_method": "jwt",
                "permissions": jwt_result["permissions"],
                "token_id": jwt_result.get("token_id"),
            }
        logger.warning(f"Invalid JWT token provided: {jwt_result.get('error')}")
        # Return authentication error marker for invalid/expired JWT tokens
        return {
            "authentication_error": f"JWT authentication failed: {jwt_result.get('error')}"
        }
    except Exception:
        logger.exception("Error validating JWT token parameter")
        return None


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


def validate_api_key_header(ctx: Context) -> bool:
    """
    Validate API key from MCP headers for connection-level authentication.

    This should be called by middleware to validate the MCP client connection.
    """
    try:
        # Try various header extraction methods for MCP context
        api_key = None

        # Use the new FastMCP 2.x API to get HTTP request with lazy import
        try:
            from fastmcp.server.dependencies import (
                get_http_request as _get_http_request,
            )

            http_request = _get_http_request()
            if http_request and hasattr(http_request, "headers"):
                headers = http_request.headers
                api_key = headers.get("x-api-key") or headers.get("X-API-Key")
        except ImportError:
            # FastMCP dependencies not available
            pass
        except Exception as e:
            # Log other exceptions for debugging but continue
            logger.debug(f"Failed to get HTTP request from FastMCP: {e}")
            pass

        if not api_key and hasattr(ctx, "headers"):
            ctx_headers = getattr(ctx, "headers", {})
            api_key = ctx_headers.get("x-api-key") or ctx_headers.get("X-API-Key")

        if not api_key and hasattr(ctx, "meta") and isinstance(ctx.meta, dict):
            api_key = ctx.meta.get("x-api-key") or ctx.meta.get("X-API-Key")

        valid_api_key = os.getenv("API_KEY", "")
        if valid_api_key and api_key:
            return api_key == valid_api_key
        return False

    except Exception:
        logger.exception("Error validating API key header")
        return False


async def extract_agent_context(
    ctx: Context, auth_token: str | None = None
) -> dict[str, Any]:
    """
    Extract agent context with two-tier authentication:
    1. Validate MCP client via API key header (connection-level)
    2. Identify agent via JWT token parameter (request-level)
    """
    # Check MCP client authentication via API key header
    api_key_valid = validate_api_key_header(ctx)

    # Primary: JWT token parameter for agent identification
    if auth_token:
        jwt_context = await validate_jwt_token_parameter(auth_token)
        if jwt_context:
            # Check if this is a validation error (malformed token)
            if "validation_error" in jwt_context:
                # Return the error directly - don't fall back to generic agent
                return {
                    "agent_id": "validation_failed",
                    "agent_type": "invalid",
                    "authenticated": False,
                    "auth_method": "failed",
                    "permissions": [],
                    "token_id": None,
                    "api_key_authenticated": api_key_valid,
                    "validation_error": jwt_context["validation_error"],
                }

            # Check if this is an authentication error (expired/invalid token)
            if "authentication_error" in jwt_context:
                # Return the error directly - don't fall back to generic agent
                return {
                    "agent_id": "authentication_failed",
                    "agent_type": "expired",
                    "authenticated": False,
                    "auth_method": "failed",
                    "permissions": [],
                    "token_id": None,
                    "api_key_authenticated": api_key_valid,
                    "authentication_error": jwt_context["authentication_error"],
                    "recovery_token": auth_token,  # Include original token for recovery
                }
            # Enhanced context with API key validation status
            jwt_context["api_key_authenticated"] = api_key_valid
            return jwt_context

    # Get existing auth info from context
    auth_info = get_auth_info(ctx)

    # Check for pre-validated JWT authentication
    if auth_info.jwt_validated:
        return {
            "agent_id": auth_info.agent_id,
            "agent_type": auth_info.agent_type,
            "authenticated": True,
            "auth_method": "jwt",
            "permissions": auth_info.permissions,
            "token_id": auth_info.token_id,
            "api_key_authenticated": api_key_valid,
        }

    # Fallback: Basic session-based identification
    agent_id = auth_info.agent_id
    if agent_id == "unknown" and hasattr(ctx, "session_id"):
        agent_id = f"agent_{ctx.session_id[:8]}"

    return {
        "agent_id": agent_id,
        "agent_type": auth_info.agent_type,
        "authenticated": api_key_valid,  # Basic auth based on API key
        "auth_method": "api_key",
        "permissions": ["read", "write"] if api_key_valid else ["read"],
        "token_id": None,
        "api_key_authenticated": api_key_valid,
    }


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


async def validate_agent_context_or_error(
    ctx: Context, auth_token: str | None
) -> dict[str, Any]:
    """
    Extract and validate agent context, returning error response if validation fails.

    This is a common helper function that extracts agent context and handles
    token validation errors consistently across all MCP tools.

    Args:
        ctx: FastMCP context
        auth_token: Optional authentication token

    Returns:
        dict: Either agent context or error response structure
    """
    agent_context = await extract_agent_context(ctx, auth_token)

    # Check for token validation errors
    if "validation_error" in agent_context:
        from .utils.llm_errors import ErrorSeverity, create_llm_error_response

        return create_llm_error_response(
            error="Invalid authentication token format",
            code="INVALID_TOKEN_FORMAT",
            suggestions=[
                "Ensure token follows the correct format (sct_* for protected tokens or valid JWT)",
                "Use authenticate_agent to get a valid token",
                "Check that the token is not corrupted or malformed",
            ],
            context={"validation_error": agent_context["validation_error"]},
            severity=ErrorSeverity.ERROR,
        )

    # Check for authentication errors (expired/invalid tokens)
    if "authentication_error" in agent_context:
        from .utils.llm_errors import ErrorSeverity, create_llm_error_response

        return create_llm_error_response(
            error="Authentication token invalid or expired",
            code="TOKEN_AUTHENTICATION_FAILED",
            suggestions=[
                "Use refresh_token with your current token to get a new one",
                "No need to remember your agent_id - the system will extract it",
                "If refresh fails, use authenticate_agent to get a new token",
            ],
            context={
                "authentication_error": agent_context["authentication_error"],
                "recovery_method": "refresh_token",
                "recovery_token": agent_context.get("recovery_token"),
            },
            severity=ErrorSeverity.ERROR,
        )

    return agent_context


# ============================================================================
# PRP-006: SECURE TOKEN AUTHENTICATION SYSTEM
# ============================================================================


class SecureTokenManager:
    """
    Secure Token Manager with Fernet encryption for JWT hiding.

    Implements protected token format (sct_<uuid>) with multi-agent concurrency
    safety and race-condition-safe refresh patterns.
    """

    def __init__(self) -> None:
        """Initialize SecureTokenManager with Fernet encryption."""
        import uuid

        from cryptography.fernet import Fernet

        # Store imports as instance attributes to avoid repeated imports
        self._uuid = uuid
        self._fernet_cls = Fernet

        # Get encryption key from environment
        key = os.getenv("JWT_ENCRYPTION_KEY")
        if not key:
            raise ValueError("JWT_ENCRYPTION_KEY environment variable required")

        # Initialize Fernet cipher
        self.fernet = self._fernet_cls(key.encode())

        logger.info("Secure Token Manager initialized")

    async def create_protected_token(self, jwt_token: str, agent_id: str) -> str:
        """
        Create encrypted protected token with simple UUID.

        Args:
            jwt_token: Original JWT token to encrypt
            agent_id: Agent identifier for audit purposes

        Returns:
            Protected token ID (sct_<uuid>)
        """
        # Generate protected token ID
        token_id = f"sct_{self._uuid.uuid4()}"

        # Encrypt JWT token
        encrypted_jwt = self.fernet.encrypt(jwt_token.encode())

        # Store in database with transaction safety
        async with get_db_connection() as conn:
            # Check if this is SQLAlchemy backend (which handles transactions automatically)
            is_sqlalchemy = hasattr(conn, "engine") and hasattr(conn, "conn")

            if not is_sqlalchemy:
                await conn.execute("BEGIN IMMEDIATE")

            try:
                await conn.execute(
                    """
                    INSERT INTO secure_tokens (token_id, encrypted_jwt, agent_id, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        token_id,
                        encrypted_jwt,
                        agent_id,
                        datetime.now(timezone.utc) + timedelta(hours=1),
                    ),
                )

                if not is_sqlalchemy:
                    await conn.commit()
            except Exception:
                if not is_sqlalchemy:
                    await conn.rollback()
                raise

        logger.info(f"Created protected token for agent {agent_id}")
        return token_id

    async def refresh_token_safely(self, current_token: str, agent_id: str) -> str:
        """
        Atomic refresh: create new, then delete old to prevent race conditions.

        Args:
            current_token: Current protected token to refresh
            agent_id: Agent identifier for validation

        Returns:
            New protected token ID
        """

        # Helper function to handle token validation errors
        async def _handle_token_error(
            conn: aiosqlite.Connection, is_sqlalchemy: bool
        ) -> None:
            """Handle token validation error with proper rollback."""
            if not is_sqlalchemy:
                await conn.rollback()
            raise ValueError("Token invalid or expired")

        # Perform the entire refresh operation in a single transaction to prevent race conditions
        try:
            async with get_db_connection() as conn:
                # Check if this is SQLAlchemy backend (which handles transactions automatically)
                is_sqlalchemy = hasattr(conn, "engine") and hasattr(conn, "conn")

                if not is_sqlalchemy:
                    await conn.execute("BEGIN IMMEDIATE")

                try:
                    # First, get and validate the current token within the transaction
                    cursor = await conn.execute(
                        """
                        SELECT encrypted_jwt, expires_at FROM secure_tokens
                        WHERE token_id = ?
                        """,
                        (current_token,),
                    )

                    row = await cursor.fetchone()
                    if not row:
                        await _handle_token_error(conn, is_sqlalchemy)

                    # Type assertion for mypy - we know row is not None here
                    assert row is not None

                    # Check expiration - handle both string and datetime objects
                    expires_at_raw = row[1]
                    if isinstance(expires_at_raw, str):
                        expires_at = datetime.fromisoformat(expires_at_raw)
                        # Ensure timezone awareness for naive datetime objects
                        if expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)
                    else:
                        expires_at = expires_at_raw
                        # Ensure timezone awareness for naive datetime objects
                        if expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)

                    if expires_at <= datetime.now(timezone.utc):
                        await _handle_token_error(conn, is_sqlalchemy)

                    # Decrypt JWT within transaction
                    try:
                        jwt_token = self.fernet.decrypt(row[0]).decode()
                    except Exception as err:
                        if not is_sqlalchemy:
                            await conn.rollback()
                        raise ValueError("Token invalid or expired") from err

                    # Generate new token ID
                    new_token_id = f"sct_{self._uuid.uuid4()}"
                    encrypted_jwt = self.fernet.encrypt(jwt_token.encode())

                    # Insert new token and delete old token atomically
                    await conn.execute(
                        """
                        INSERT INTO secure_tokens (token_id, encrypted_jwt, agent_id, expires_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            new_token_id,
                            encrypted_jwt,
                            agent_id,
                            datetime.now(timezone.utc) + timedelta(hours=1),
                        ),
                    )

                    await conn.execute(
                        "DELETE FROM secure_tokens WHERE token_id = ?", (current_token,)
                    )

                    if not is_sqlalchemy:
                        await conn.commit()

                    logger.info(f"Refreshed protected token for agent {agent_id}")
                    return new_token_id

                except ValueError:
                    # Re-raise ValueError for invalid/expired tokens
                    if not is_sqlalchemy:
                        await conn.rollback()
                    raise
                except Exception:
                    if not is_sqlalchemy:
                        await conn.rollback()
                    raise
        except ValueError:
            # Re-raise ValueError so tests can catch it properly
            raise
        except Exception as err:
            # For any other exceptions, wrap them appropriately
            raise ValueError("Token invalid or expired") from err

    async def resolve_protected_token(self, token_id: str) -> str | None:
        """
        Resolve protected token to original JWT.

        Args:
            token_id: Protected token ID to resolve

        Returns:
            Original JWT token if valid and not expired, None otherwise
        """
        if not token_id.startswith("sct_"):
            return None

        async with get_db_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT encrypted_jwt, expires_at FROM secure_tokens
                WHERE token_id = ?
                """,
                (token_id,),
            )

            row = await cursor.fetchone()
            if not row:
                return None

            # Check expiration - handle both string (manual parsing) and datetime (adapter converted)
            expires_at_raw = row[1]
            if isinstance(expires_at_raw, str):
                expires_at = datetime.fromisoformat(expires_at_raw)
                # Ensure timezone awareness for naive datetime objects
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            else:
                # Already a datetime object (from datetime adapter)
                expires_at = expires_at_raw
                # Ensure timezone awareness for naive datetime objects
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                return None

            # Decrypt and return JWT
            try:
                return self.fernet.decrypt(row[0]).decode()
            except Exception:
                logger.warning(f"Failed to decrypt protected token {token_id}")
                return None

    async def extract_agent_info_for_recovery(
        self, token_id: str
    ) -> dict[str, Any] | None:
        """
        Extract agent information from expired/invalid tokens for recovery purposes.

        This method can retrieve agent info even from expired tokens to enable
        seamless token refresh without requiring agent_id input.

        Args:
            token_id: Protected token ID to extract info from

        Returns:
            Dictionary with agent_id, agent_type, etc. or None if token not found
        """
        if not token_id.startswith("sct_"):
            return None

        async with get_db_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT encrypted_jwt, agent_id, expires_at FROM secure_tokens
                WHERE token_id = ?
                """,
                (token_id,),
            )

            row = await cursor.fetchone()
            if not row:
                logger.warning(f"Protected token not found for recovery: {token_id}")
                return None

            # Try to decrypt and parse JWT even if expired
            try:
                jwt_token = self.fernet.decrypt(row[0]).decode()

                # Parse JWT to extract agent information
                jwt_result = auth_manager.validate_token(jwt_token)
                if jwt_result.get("agent_id"):
                    # Return agent info for recovery, regardless of expiration
                    return {
                        "agent_id": jwt_result["agent_id"],
                        "agent_type": jwt_result.get("agent_type", "unknown"),
                        "permissions": jwt_result.get("permissions", ["read"]),
                        "stored_agent_id": row[1],  # Cross-check with stored value
                        "token_expired": (
                            datetime.fromisoformat(row[2])
                            if isinstance(row[2], str)
                            else row[2]
                        )
                        <= datetime.now(timezone.utc),
                        "original_token": token_id,
                    }
                logger.warning(
                    f"Could not extract agent info from JWT in token {token_id}"
                )
                return None

            except Exception as e:
                logger.warning(
                    f"Failed to decrypt/parse token for recovery {token_id}: {e}"
                )
                return None

    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from database.

        Returns:
            Number of tokens cleaned up
        """
        try:
            async with get_db_connection() as conn:
                cursor = await conn.execute(
                    """
                    DELETE FROM secure_tokens
                    WHERE expires_at <= ?
                    """,
                    (datetime.now(timezone.utc).isoformat(),),
                )
                await conn.commit()
                count = cursor.rowcount

                if count > 0:
                    logger.info(f"Cleaned up {count} expired secure tokens")

                return count
        except Exception:
            logger.exception("Failed to cleanup expired tokens")
            return 0


# Global secure token manager
secure_token_manager: SecureTokenManager | None = None


def get_secure_token_manager() -> SecureTokenManager:
    """Get global secure token manager instance."""
    global secure_token_manager

    if secure_token_manager is None:
        secure_token_manager = SecureTokenManager()

    return secure_token_manager
