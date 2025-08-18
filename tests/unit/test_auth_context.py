"""
Unit tests for authentication context enhancement and agent context extraction.

Tests the enhance_context_with_auth function and extract_agent_context function
to ensure proper authentication context management across different auth methods.
"""

import os
from unittest.mock import patch

import pytest

from shared_context_server.auth import (
    AuthInfo,
    extract_agent_context,
    set_auth_info,
    validate_api_key_header,
    validate_jwt_token_parameter,
)


class MockContext:
    """Mock FastMCP context for authentication testing."""

    def __init__(self, session_id="test_session"):
        self.session_id = session_id
        # Start with default AuthInfo
        self._auth_info = AuthInfo()


class TestValidateJWTTokenParameter:
    """Test validate_jwt_token_parameter function for JWT parameter authentication."""

    @pytest.fixture
    def mock_auth_manager(self):
        """Mock JWT authentication manager."""
        with patch("shared_context_server.auth_secure.auth_manager") as mock:
            yield mock

    async def test_validate_jwt_token_parameter_success(self, mock_auth_manager):
        """Test successful JWT token parameter validation."""
        # Mock successful token validation
        mock_auth_manager.validate_token.return_value = {
            "valid": True,
            "agent_id": "claude_agent_123",
            "agent_type": "claude",
            "permissions": ["read", "write"],
            "token_id": "jwt_token_456",
        }

        result = await validate_jwt_token_parameter("valid.jwt.token")

        assert result is not None
        assert result["agent_id"] == "claude_agent_123"
        assert result["agent_type"] == "claude"
        assert result["authenticated"] is True
        assert result["auth_method"] == "jwt"
        assert result["permissions"] == ["read", "write"]
        assert result["token_id"] == "jwt_token_456"

    async def test_validate_jwt_token_parameter_failure(self, mock_auth_manager):
        """Test JWT token parameter validation failure."""
        # Mock failed token validation
        mock_auth_manager.validate_token.return_value = {
            "valid": False,
            "error": "Token expired",
        }

        result = await validate_jwt_token_parameter("invalid.jwt.token")

        # Should return authentication error marker instead of None
        assert result is not None
        assert "authentication_error" in result
        assert "JWT authentication failed" in result["authentication_error"]
        assert "Token expired" in result["authentication_error"]

    async def test_validate_jwt_token_parameter_none(self, mock_auth_manager):
        """Test JWT token parameter validation with None token."""
        result = await validate_jwt_token_parameter(None)

        assert result is None
        mock_auth_manager.validate_token.assert_not_called()

    async def test_validate_jwt_token_parameter_exception(self, mock_auth_manager):
        """Test JWT token parameter validation with exception."""
        # Mock auth_manager to return error result (exceptions are caught internally)
        mock_auth_manager.validate_token.return_value = {
            "valid": False,
            "error": "Token validation failed: Validation error",
        }

        result = await validate_jwt_token_parameter("some.jwt.token")

        # Should return authentication error marker instead of None for better error handling
        assert result is not None
        assert "authentication_error" in result
        assert "JWT authentication failed" in result["authentication_error"]
        assert "Validation error" in result["authentication_error"]


class TestValidateAPIKeyHeader:
    """Test validate_api_key_header function for API key header authentication."""

    async def test_validate_api_key_header_success(self):
        """Test successful API key header validation."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            ctx = MockContext()
            ctx.headers = {"X-API-Key": "valid_key"}

            result = validate_api_key_header(ctx)
            assert result is True

    async def test_validate_api_key_header_failure(self):
        """Test API key header validation failure."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            ctx = MockContext()
            ctx.headers = {"X-API-Key": "invalid_key"}

            result = validate_api_key_header(ctx)
            assert result is False

    async def test_validate_api_key_header_missing(self):
        """Test API key header validation with missing header."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            ctx = MockContext()

            result = validate_api_key_header(ctx)
            assert result is False

    async def test_validate_api_key_header_no_env_key(self):
        """Test API key header validation with no environment key."""
        with patch.dict(os.environ, {}, clear=True):
            ctx = MockContext()
            ctx.headers = {"X-API-Key": "some_key"}

            result = validate_api_key_header(ctx)
            assert result is False

    async def test_validate_api_key_header_get_http_request(self):
        """Test API key header extraction via get_http_request."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            ctx = MockContext()

            # Mock the new get_http_request function from fastmcp.server.dependencies
            mock_request = type("MockRequest", (), {})()
            mock_request.headers = {"X-API-Key": "valid_key"}

            with patch(
                "fastmcp.server.dependencies.get_http_request",
                return_value=mock_request,
            ):
                result = validate_api_key_header(ctx)
                assert result is True

    async def test_validate_api_key_header_meta(self):
        """Test API key header extraction via meta."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            ctx = MockContext()
            ctx.meta = {"X-API-Key": "valid_key"}

            result = validate_api_key_header(ctx)
            assert result is True


class TestExtractAgentContext:
    """Test extract_agent_context function for different authentication scenarios."""

    async def test_extract_jwt_authenticated_context(self):
        """Test extracting context from JWT-authenticated agent."""
        auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="jwt_agent_123",
            agent_type="claude",
            permissions=["read", "write", "admin"],
            authenticated=True,
            auth_method="jwt",
            token_id="token_abc_456",
        )
        ctx = MockContext()
        set_auth_info(ctx, auth_info)

        context = await extract_agent_context(ctx)

        assert context["agent_id"] == "jwt_agent_123"
        assert context["agent_type"] == "claude"
        assert context["authenticated"] is True
        assert context["auth_method"] == "jwt"
        assert context["permissions"] == ["read", "write", "admin"]
        assert context["token_id"] == "token_abc_456"

    async def test_extract_api_key_authenticated_context(self):
        """Test extracting context from API key authenticated agent."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            auth_info = AuthInfo(
                jwt_validated=False,
                agent_id="api_agent_789",
                agent_type="gemini",
                permissions=["read", "write"],
                authenticated=True,
                auth_method="api_key",
            )
            ctx = MockContext()
            ctx.headers = {"X-API-Key": "valid_key"}  # Add valid API key header
            set_auth_info(ctx, auth_info)

            context = await extract_agent_context(ctx)

            assert context["agent_id"] == "api_agent_789"
            assert context["agent_type"] == "gemini"
            assert (
                context["authenticated"] is True
            )  # Will be True due to valid API key header
            assert context["auth_method"] == "api_key"
            assert context["permissions"] == ["read", "write"]
            assert context["token_id"] is None
            assert context["api_key_authenticated"] is True

    async def test_extract_unauthenticated_context(self):
        """Test extracting context from unauthenticated agent."""
        auth_info = AuthInfo(
            jwt_validated=False,
            agent_id="unknown_agent",
            agent_type="generic",
            permissions=["read"],
            authenticated=False,
            auth_method="none",
        )
        ctx = MockContext()
        set_auth_info(ctx, auth_info)

        context = await extract_agent_context(ctx)

        assert context["agent_id"] == "unknown_agent"
        assert context["agent_type"] == "generic"
        assert context["authenticated"] is False
        assert context["auth_method"] == "api_key"  # Falls back to api_key method
        assert context["permissions"] == ["read"]
        assert context["token_id"] is None

    async def test_extract_context_unknown_agent_fallback(self):
        """Test agent_id fallback when agent is unknown."""
        auth_info = AuthInfo(
            agent_id="unknown",  # Default unknown value
            agent_type="generic",
            authenticated=False,
        )
        ctx = MockContext(session_id="test_session_123")
        set_auth_info(ctx, auth_info)

        context = await extract_agent_context(ctx)

        # Should generate agent_id from session_id
        assert context["agent_id"] == "agent_test_ses"  # First 8 chars of session_id
        assert context["agent_type"] == "generic"
        assert context["authenticated"] is False

    async def test_extract_context_no_session_id(self):
        """Test context extraction when no session_id is available."""
        auth_info = AuthInfo(agent_id="unknown")

        class ContextNoSession:
            pass

        ctx = ContextNoSession()
        set_auth_info(ctx, auth_info)

        context = await extract_agent_context(ctx)

        # Should keep "unknown" when no session_id fallback available
        assert context["agent_id"] == "unknown"

    async def test_extract_context_permission_mapping(self):
        """Test permission mapping for authenticated vs unauthenticated agents."""
        # Authenticated agent with API key
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            auth_info_auth = AuthInfo(
                agent_id="auth_agent",
                authenticated=True,
                permissions=["read", "write", "admin"],
            )
            ctx_auth = MockContext()
            ctx_auth.headers = {"X-API-Key": "valid_key"}  # Valid API key
            set_auth_info(ctx_auth, auth_info_auth)

            context_auth = await extract_agent_context(ctx_auth)
            assert context_auth["permissions"] == [
                "read",
                "write",
            ]  # Based on API key auth

        # Unauthenticated agent
        auth_info_unauth = AuthInfo(
            agent_id="unauth_agent",
            authenticated=False,
            permissions=["read"],
        )
        ctx_unauth = MockContext()
        set_auth_info(ctx_unauth, auth_info_unauth)

        context_unauth = await extract_agent_context(ctx_unauth)
        assert context_unauth["permissions"] == ["read"]  # Read-only for unauth

    async def test_extract_context_default_auth_info(self):
        """Test context extraction with default AuthInfo."""
        ctx = MockContext()
        # Don't set any auth info - should get default

        context = await extract_agent_context(ctx)

        assert context["agent_id"] == "agent_test_ses"  # From session_id fallback
        assert context["agent_type"] == "generic"
        assert context["authenticated"] is False
        assert context["auth_method"] == "api_key"
        assert context["permissions"] == ["read"]
        assert context["token_id"] is None

    async def test_extract_context_jwt_vs_api_key_priority(self):
        """Test that JWT authentication takes priority over API key."""
        # Set up JWT-authenticated context
        auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="jwt_agent",
            agent_type="claude",
            permissions=["read", "write", "debug"],
            authenticated=True,
            auth_method="jwt",
            token_id="jwt_token_123",
        )
        ctx = MockContext()
        set_auth_info(ctx, auth_info)

        context = await extract_agent_context(ctx)

        # Should return JWT context, not fall back to API key
        assert context["auth_method"] == "jwt"
        assert context["token_id"] == "jwt_token_123"
        assert context["permissions"] == ["read", "write", "debug"]

    async def test_extract_context_comprehensive_jwt_info(self):
        """Test comprehensive JWT context extraction."""
        auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="comprehensive_agent",
            agent_type="system",
            permissions=["read", "write", "admin", "debug"],
            authenticated=True,
            auth_method="jwt",
            token_id="comprehensive_token_id",
        )
        ctx = MockContext()
        set_auth_info(ctx, auth_info)

        context = await extract_agent_context(ctx)

        expected_context = {
            "agent_id": "comprehensive_agent",
            "agent_type": "system",
            "authenticated": True,
            "auth_method": "jwt",
            "permissions": ["read", "write", "admin", "debug"],
            "token_id": "comprehensive_token_id",
            "api_key_authenticated": False,  # No API key header provided
        }

        assert context == expected_context
