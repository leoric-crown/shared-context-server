"""
JWT Authentication System for Shared Context MCP Server.

Implements a clean two-tier authentication system:
1. API Key (header-based): Static authentication for MCP client connection
2. JWT Token (parameter-based): Dynamic per-request agent authentication

This module serves as a facade that imports functionality from:
- auth_core.py: Core JWT authentication, permissions, and audit logging
- auth_secure.py: Secure token management with Fernet encryption (PRP-006)

Key Features:
- Header-based API key validation for MCP client authentication
- Parameter-based JWT tokens for dynamic agent authentication
- Role-based permission system (read, write, admin, debug)
- Comprehensive audit logging for security events
- Permission decorators for tool access control
- Protected token format (sct_*) with encryption for JWT hiding
"""

# Import all core authentication functionality
# Import ContextVar-based token manager
from .auth_context import get_secure_token_manager
from .auth_core import (
    AuthInfo,
    JWTAuthenticationManager,
    LazyAuthManager,
    _is_valid_token_format,
    audit_log_auth_event,
    auth_manager,
    generate_agent_jwt_token,
    get_auth_info,
    get_auth_manager,
    require_permission,
    reset_auth_manager,
    set_auth_info,
)

# Import all secure token functionality
from .auth_secure import (
    SecureTokenManager,
    extract_agent_context,
    validate_agent_context_or_error,
    validate_api_key_header,
    validate_jwt_token_parameter,
)

# Import database connection for backward compatibility with tests
from .database import get_db_connection

# Preserve all existing public interfaces for backward compatibility
__all__ = [
    # Core authentication classes and functions
    "AuthInfo",
    "JWTAuthenticationManager",
    "LazyAuthManager",
    "audit_log_auth_event",
    "auth_manager",
    "generate_agent_jwt_token",
    "get_auth_info",
    "get_auth_manager",
    "require_permission",
    "reset_auth_manager",
    "set_auth_info",
    # Secure token classes and functions
    "SecureTokenManager",
    "extract_agent_context",
    "get_secure_token_manager",
    "validate_agent_context_or_error",
    "validate_api_key_header",
    "validate_jwt_token_parameter",
    # Internal utility functions (maintained for compatibility)
    "_is_valid_token_format",
    # Database function (maintained for test compatibility)
    "get_db_connection",
]
