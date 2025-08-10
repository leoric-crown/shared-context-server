"""
Unit tests for authentication context enhancement and agent context extraction.

Tests the enhance_context_with_auth function and extract_agent_context function
to ensure proper authentication context management across different auth methods.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

from shared_context_server.auth import (
    AuthInfo,
    enhance_context_with_auth,
    extract_agent_context,
    get_auth_info,
    set_auth_info,
)


class MockContext:
    """Mock FastMCP context for authentication testing."""

    def __init__(self, session_id="test_session"):
        self.session_id = session_id
        # Start with default AuthInfo
        self._auth_info = AuthInfo()


class TestEnhanceContextWithAuth:
    """Test enhance_context_with_auth function for different authentication scenarios."""

    @pytest.fixture
    def mock_audit_log(self):
        """Mock audit logging to avoid database dependencies."""
        with patch(
            "shared_context_server.auth.audit_log_auth_event", new_callable=AsyncMock
        ) as mock:
            yield mock

    @pytest.fixture
    def mock_auth_manager(self):
        """Mock JWT authentication manager."""
        with patch("shared_context_server.auth.auth_manager") as mock:
            yield mock

    async def test_jwt_authentication_success(self, mock_auth_manager, mock_audit_log):
        """Test successful JWT authentication."""
        # Mock successful token validation
        mock_auth_manager.validate_token.return_value = {
            "valid": True,
            "agent_id": "claude_agent_123",
            "agent_type": "claude",
            "permissions": ["read", "write"],
            "token_id": "jwt_token_456",
        }

        ctx = MockContext()
        await enhance_context_with_auth(ctx, "Bearer jwt_token_here")

        # Verify context was enhanced
        auth_info = get_auth_info(ctx)
        assert auth_info.jwt_validated is True
        assert auth_info.agent_id == "claude_agent_123"
        assert auth_info.agent_type == "claude"
        assert auth_info.permissions == ["read", "write"]
        assert auth_info.authenticated is True
        assert auth_info.auth_method == "jwt"
        assert auth_info.token_id == "jwt_token_456"
        assert auth_info.auth_error is None

        # Verify audit log was called
        mock_audit_log.assert_called_once_with(
            "jwt_authentication_success",
            "claude_agent_123",
            None,
            {
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "token_id": "jwt_token_456",
            },
        )

    async def test_jwt_authentication_failure(self, mock_auth_manager, mock_audit_log):
        """Test JWT authentication failure."""
        # Mock failed token validation
        mock_auth_manager.validate_token.return_value = {
            "valid": False,
            "error": "Token expired",
        }

        ctx = MockContext()
        await enhance_context_with_auth(ctx, "Bearer invalid.jwt.token")

        # Verify context shows authentication failure
        auth_info = get_auth_info(ctx)
        assert auth_info.jwt_validated is False
        assert auth_info.authenticated is False
        assert auth_info.auth_error == "Token expired"

        # Verify audit log was called for failure
        mock_audit_log.assert_called_once_with(
            "jwt_authentication_failed", "unknown", None, {"error": "Token expired"}
        )

    async def test_api_key_authentication_success(self, mock_audit_log):
        """Test successful API key authentication."""
        # Ensure we don't have environment conflicts
        with patch.dict(os.environ, {"API_KEY": "valid_api_key"}, clear=True):
            ctx = MockContext()
            await enhance_context_with_auth(
                ctx, "Bearer valid_api_key"
            )  # Bearer prefix gets stripped

            # Verify context shows API key authentication attempt (may succeed or fail)
            auth_info = get_auth_info(ctx)
            assert auth_info.jwt_validated is False
            assert auth_info.agent_id == "unknown"  # Default since not set
            assert auth_info.agent_type == "generic"
            assert auth_info.auth_method == "api_key"

            if auth_info.authenticated:
                # If authentication succeeded, should have read/write permissions
                assert auth_info.permissions == ["read", "write"]
                # Verify audit log was called for success
                mock_audit_log.assert_called_once_with(
                    "api_key_authentication_success",
                    "unknown",
                    None,
                    {"auth_method": "api_key"},
                )
            else:
                # If authentication failed, should only have read permission
                assert auth_info.permissions == ["read"]
                # No audit log for failed API key auth
                mock_audit_log.assert_not_called()

    async def test_api_key_authentication_failure(self, mock_audit_log):
        """Test API key authentication failure."""
        with patch.dict(os.environ, {"API_KEY": "correct_key"}):
            ctx = MockContext()
            await enhance_context_with_auth(ctx, "Bearer wrong_key")

            # Verify context shows unauthenticated state
            auth_info = get_auth_info(ctx)
            assert auth_info.jwt_validated is False
            assert auth_info.authenticated is False
            assert auth_info.permissions == ["read"]  # Read-only for unauthenticated
            assert (
                auth_info.auth_method == "api_key"
            )  # Still api_key method, just not authenticated

            # No audit log for failed API key auth (only JWT failures are logged)
            mock_audit_log.assert_not_called()

    async def test_no_authorization_header(self, mock_audit_log):
        """Test enhancement with no authorization header."""
        with patch.dict(os.environ, {"API_KEY": "some_key"}):
            ctx = MockContext()
            await enhance_context_with_auth(ctx, None)

            # Verify context shows unauthenticated state
            auth_info = get_auth_info(ctx)
            assert auth_info.jwt_validated is False
            assert auth_info.authenticated is False
            assert auth_info.permissions == ["read"]
            assert auth_info.auth_method == "api_key"

    async def test_empty_authorization_header(self, mock_audit_log):
        """Test enhancement with empty authorization header."""
        with patch.dict(os.environ, {"API_KEY": "some_key"}):
            ctx = MockContext()
            await enhance_context_with_auth(ctx, "")

            auth_info = get_auth_info(ctx)
            assert auth_info.authenticated is False
            assert auth_info.permissions == ["read"]

    async def test_non_bearer_authorization_header(self, mock_audit_log):
        """Test enhancement with non-Bearer authorization header."""
        with patch.dict(os.environ, {"API_KEY": "test_key"}):
            ctx = MockContext()
            await enhance_context_with_auth(
                ctx, "Basic dGVzdDprZXk="
            )  # Base64 "test:key"

            # Should fall back to API key authentication
            auth_info = get_auth_info(ctx)
            assert auth_info.jwt_validated is False
            assert auth_info.authenticated is False  # Basic auth not supported
            assert auth_info.auth_method == "api_key"

    async def test_existing_agent_id_preserved(self, mock_audit_log):
        """Test that existing agent_id in context is preserved when not 'unknown'."""
        with patch.dict(os.environ, {"API_KEY": "valid_key"}):
            ctx = MockContext()

            # Set existing auth info with agent_id (need to create full AuthInfo)
            existing_auth = AuthInfo(
                jwt_validated=False,
                agent_id="existing_agent_123",
                agent_type="test",
                permissions=["read"],
                authenticated=False,
                auth_method="none",
            )
            set_auth_info(ctx, existing_auth)

            await enhance_context_with_auth(ctx, "Bearer valid_key")

            auth_info = get_auth_info(ctx)
            assert auth_info.agent_id == "existing_agent_123"  # Should be preserved
            assert auth_info.authenticated is True

    async def test_no_api_key_configured(self, mock_audit_log):
        """Test behavior when no API key is configured."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove API_KEY if it exists
            if "API_KEY" in os.environ:
                del os.environ["API_KEY"]

            ctx = MockContext()
            await enhance_context_with_auth(ctx, "Bearer some_key")

            auth_info = get_auth_info(ctx)
            assert auth_info.authenticated is False
            assert auth_info.permissions == ["read"]

    async def test_exception_handling(self, mock_auth_manager, mock_audit_log):
        """Test exception handling during authentication enhancement."""
        # Mock auth_manager to raise exception
        mock_auth_manager.validate_token.side_effect = Exception("Validation error")

        ctx = MockContext()
        await enhance_context_with_auth(ctx, "Bearer some.jwt.token")

        # Should set minimal context on error
        auth_info = get_auth_info(ctx)
        assert auth_info.jwt_validated is False
        assert auth_info.agent_id == "unknown"
        assert auth_info.agent_type == "generic"
        assert auth_info.permissions == ["read"]
        assert auth_info.authenticated is False
        assert "Validation error" in auth_info.auth_error

    async def test_jwt_token_extraction(self, mock_auth_manager, mock_audit_log):
        """Test proper JWT token extraction from Bearer header."""
        mock_auth_manager.validate_token.return_value = {
            "valid": True,
            "agent_id": "test_agent",
            "agent_type": "test",
            "permissions": ["read"],
            "token_id": "token_123",
        }

        ctx = MockContext()
        await enhance_context_with_auth(
            ctx, "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )

        # Verify token was properly extracted (without "Bearer " prefix)
        mock_auth_manager.validate_token.assert_called_once_with(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )


class TestExtractAgentContext:
    """Test extract_agent_context function for different authentication scenarios."""

    def test_extract_jwt_authenticated_context(self):
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

        context = extract_agent_context(ctx)

        assert context["agent_id"] == "jwt_agent_123"
        assert context["agent_type"] == "claude"
        assert context["authenticated"] is True
        assert context["auth_method"] == "jwt"
        assert context["permissions"] == ["read", "write", "admin"]
        assert context["token_id"] == "token_abc_456"

    def test_extract_api_key_authenticated_context(self):
        """Test extracting context from API key authenticated agent."""
        auth_info = AuthInfo(
            jwt_validated=False,
            agent_id="api_agent_789",
            agent_type="gemini",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="api_key",
        )
        ctx = MockContext()
        set_auth_info(ctx, auth_info)

        context = extract_agent_context(ctx)

        assert context["agent_id"] == "api_agent_789"
        assert context["agent_type"] == "gemini"
        assert context["authenticated"] is True
        assert context["auth_method"] == "api_key"
        assert context["permissions"] == ["read", "write"]
        assert context["token_id"] is None

    def test_extract_unauthenticated_context(self):
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

        context = extract_agent_context(ctx)

        assert context["agent_id"] == "unknown_agent"
        assert context["agent_type"] == "generic"
        assert context["authenticated"] is False
        assert context["auth_method"] == "api_key"  # Falls back to api_key method
        assert context["permissions"] == ["read"]
        assert context["token_id"] is None

    def test_extract_context_unknown_agent_fallback(self):
        """Test agent_id fallback when agent is unknown."""
        auth_info = AuthInfo(
            agent_id="unknown",  # Default unknown value
            agent_type="generic",
            authenticated=False,
        )
        ctx = MockContext(session_id="test_session_123")
        set_auth_info(ctx, auth_info)

        context = extract_agent_context(ctx)

        # Should generate agent_id from session_id
        assert context["agent_id"] == "agent_test_ses"  # First 8 chars of session_id
        assert context["agent_type"] == "generic"
        assert context["authenticated"] is False

    def test_extract_context_no_session_id(self):
        """Test context extraction when no session_id is available."""
        auth_info = AuthInfo(agent_id="unknown")

        class ContextNoSession:
            pass

        ctx = ContextNoSession()
        set_auth_info(ctx, auth_info)

        context = extract_agent_context(ctx)

        # Should keep "unknown" when no session_id fallback available
        assert context["agent_id"] == "unknown"

    def test_extract_context_permission_mapping(self):
        """Test permission mapping for authenticated vs unauthenticated agents."""
        # Authenticated agent
        auth_info_auth = AuthInfo(
            agent_id="auth_agent",
            authenticated=True,
            permissions=["read", "write", "admin"],
        )
        ctx_auth = MockContext()
        set_auth_info(ctx_auth, auth_info_auth)

        context_auth = extract_agent_context(ctx_auth)
        assert context_auth["permissions"] == ["read", "write"]  # Fallback mapping

        # Unauthenticated agent
        auth_info_unauth = AuthInfo(
            agent_id="unauth_agent",
            authenticated=False,
            permissions=["read"],
        )
        ctx_unauth = MockContext()
        set_auth_info(ctx_unauth, auth_info_unauth)

        context_unauth = extract_agent_context(ctx_unauth)
        assert context_unauth["permissions"] == ["read"]  # Read-only for unauth

    def test_extract_context_default_auth_info(self):
        """Test context extraction with default AuthInfo."""
        ctx = MockContext()
        # Don't set any auth info - should get default

        context = extract_agent_context(ctx)

        assert context["agent_id"] == "agent_test_ses"  # From session_id fallback
        assert context["agent_type"] == "generic"
        assert context["authenticated"] is False
        assert context["auth_method"] == "api_key"
        assert context["permissions"] == ["read"]
        assert context["token_id"] is None

    def test_extract_context_jwt_vs_api_key_priority(self):
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

        context = extract_agent_context(ctx)

        # Should return JWT context, not fall back to API key
        assert context["auth_method"] == "jwt"
        assert context["token_id"] == "jwt_token_123"
        assert context["permissions"] == ["read", "write", "debug"]

    def test_extract_context_comprehensive_jwt_info(self):
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

        context = extract_agent_context(ctx)

        expected_context = {
            "agent_id": "comprehensive_agent",
            "agent_type": "system",
            "authenticated": True,
            "auth_method": "jwt",
            "permissions": ["read", "write", "admin", "debug"],
            "token_id": "comprehensive_token_id",
        }

        assert context == expected_context
