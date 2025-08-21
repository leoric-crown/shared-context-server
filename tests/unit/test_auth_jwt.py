"""
Unit tests for JWT token lifecycle and validation in authentication system.

Tests JWT token generation, validation, expiration handling, and security scenarios
to ensure comprehensive coverage of authentication security code.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest

from shared_context_server.auth import JWTAuthenticationManager


class TestJWTTokenGeneration:
    """Test JWT token generation functionality."""

    @pytest.fixture
    def auth_manager(self):
        """Create JWT manager with test configuration."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key"}):
            return JWTAuthenticationManager()

    def test_generate_token_basic_functionality(self, auth_manager):
        """Test basic JWT token generation with valid inputs."""
        agent_id = "test_agent_123"
        agent_type = "claude"
        permissions = ["read", "write"]

        token = auth_manager.generate_token(agent_id, agent_type, permissions)

        # Verify token is a valid JWT string
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has three parts separated by dots

        # Decode and verify payload
        payload = jwt.decode(
            token,
            "test-secret-key",
            algorithms=["HS256"],
            audience="mcp-agents",
            issuer="shared-context-server",
        )
        assert payload["agent_id"] == agent_id
        assert payload["agent_type"] == agent_type
        assert payload["permissions"] == permissions
        assert payload["iss"] == "shared-context-server"
        assert payload["aud"] == "mcp-agents"

        # Verify timestamps
        now = datetime.now(timezone.utc)
        assert abs(payload["iat"] - now.timestamp()) < 5  # Within 5 seconds
        assert payload["exp"] > payload["iat"]

        # Verify unique token ID format
        assert payload["jti"].startswith(f"{agent_id}_")

    def test_generate_token_empty_permissions(self, auth_manager):
        """Test token generation with empty permissions list."""
        token = auth_manager.generate_token("agent_123", "generic", [])

        payload = jwt.decode(
            token,
            "test-secret-key",
            algorithms=["HS256"],
            audience="mcp-agents",
            issuer="shared-context-server",
        )
        assert payload["permissions"] == []

    def test_generate_token_special_characters(self, auth_manager):
        """Test token generation with special characters in inputs."""
        agent_id = "agent@domain.com"
        agent_type = "custom-bot"
        permissions = ["read", "write", "admin"]

        token = auth_manager.generate_token(agent_id, agent_type, permissions)
        payload = jwt.decode(
            token,
            "test-secret-key",
            algorithms=["HS256"],
            audience="mcp-agents",
            issuer="shared-context-server",
        )

        assert payload["agent_id"] == agent_id
        assert payload["agent_type"] == agent_type
        assert payload["permissions"] == permissions

    def test_generate_token_custom_expiry(self):
        """Test token generation with custom expiry time."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key",
                "JWT_TOKEN_EXPIRY": "3600",  # 1 hour
            },
        ):
            auth_manager = JWTAuthenticationManager()
            token = auth_manager.generate_token("agent_123", "test", ["read"])

            payload = jwt.decode(
                token,
                "test-secret-key",
                algorithms=["HS256"],
                audience="mcp-agents",
                issuer="shared-context-server",
            )
            exp_delta = payload["exp"] - payload["iat"]
            assert abs(exp_delta - 3600) < 5  # Within 5 seconds of 1 hour


class TestJWTTokenValidation:
    """Test JWT token validation functionality."""

    @pytest.fixture
    def auth_manager(self):
        """Create JWT manager with test configuration."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key"}):
            return JWTAuthenticationManager()

    @pytest.fixture
    def valid_token(self, auth_manager):
        """Generate a valid test token."""
        return auth_manager.generate_token("test_agent", "claude", ["read", "write"])

    def test_validate_token_success(self, auth_manager, valid_token):
        """Test successful token validation."""
        result = auth_manager.validate_token(valid_token)

        assert result["valid"] is True
        assert result["agent_id"] == "test_agent"
        assert result["agent_type"] == "claude"
        assert result["permissions"] == ["read", "write"]
        assert "issued_at" in result
        assert "expires_at" in result
        assert "token_id" in result
        assert "error" not in result

    def test_validate_token_expired(self, auth_manager):
        """Test validation of expired token."""
        # Create expired token manually
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "agent_id": "test_agent",
            "agent_type": "claude",
            "permissions": ["read"],
            "iat": past_time,
            "exp": past_time + timedelta(seconds=1),  # Expired 59 minutes ago
            "iss": "shared-context-server",
            "aud": "mcp-agents",
            "jti": "expired_token",
        }

        expired_token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        result = auth_manager.validate_token(expired_token)
        assert result["valid"] is False
        assert result["error"] == "Token expired"

    def test_validate_token_invalid_signature(self, auth_manager):
        """Test validation with invalid signature."""
        # Generate token with different secret
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "different-secret"}):
            different_manager = JWTAuthenticationManager()
            token = different_manager.generate_token("test_agent", "claude", ["read"])

        result = auth_manager.validate_token(token)
        assert result["valid"] is False
        assert "Invalid token" in result["error"]

    def test_validate_token_malformed(self, auth_manager):
        """Test validation with malformed token."""
        malformed_tokens = [
            "not.a.jwt",
            "invalid_token",
            "",
            "header.payload",  # Missing signature
            "too.many.parts.here.invalid",
        ]

        for token in malformed_tokens:
            result = auth_manager.validate_token(token)
            assert result["valid"] is False
            assert "error" in result

    def test_validate_token_missing_claims(self, auth_manager):
        """Test validation with missing required claims."""
        # Create token with missing agent_id
        payload = {
            "agent_type": "claude",
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": "shared-context-server",
            "aud": "mcp-agents",
        }

        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        result = auth_manager.validate_token(token)

        assert result["valid"] is False
        assert result["error"] == "Missing required claims"

    def test_validate_token_invalid_permissions(self, auth_manager):
        """Test validation with invalid permissions."""
        # Create token with invalid permissions
        payload = {
            "agent_id": "test_agent",
            "agent_type": "claude",
            "permissions": ["read", "invalid_permission", "write"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": "shared-context-server",
            "aud": "mcp-agents",
            "jti": "test_token_id",
        }

        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        result = auth_manager.validate_token(token)

        # Should still be valid but log warning about invalid permissions
        assert result["valid"] is True
        assert result["permissions"] == ["read", "invalid_permission", "write"]

    def test_validate_token_wrong_audience(self, auth_manager):
        """Test validation with wrong audience."""
        payload = {
            "agent_id": "test_agent",
            "agent_type": "claude",
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": "shared-context-server",
            "aud": "wrong-audience",
            "jti": "test_token_id",
        }

        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        result = auth_manager.validate_token(token)

        assert result["valid"] is False
        assert "Invalid token" in result["error"]

    def test_validate_token_wrong_issuer(self, auth_manager):
        """Test validation with wrong issuer."""
        payload = {
            "agent_id": "test_agent",
            "agent_type": "claude",
            "permissions": ["read"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": "wrong-issuer",
            "aud": "mcp-agents",
            "jti": "test_token_id",
        }

        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        result = auth_manager.validate_token(token)

        assert result["valid"] is False
        assert "Invalid token" in result["error"]

    def test_validate_token_clock_skew_tolerance(self, auth_manager):
        """Test clock skew tolerance in token validation."""
        # Create token with slightly future issued_at (within tolerance)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=200)  # 200s future
        payload = {
            "agent_id": "test_agent",
            "agent_type": "claude",
            "permissions": ["read"],
            "iat": future_time,
            "exp": future_time + timedelta(hours=1),
            "iss": "shared-context-server",
            "aud": "mcp-agents",
            "jti": "test_token_id",
        }

        token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
        result = auth_manager.validate_token(token)

        # Should be valid due to clock skew tolerance (5 minutes)
        assert result["valid"] is True

    def test_validate_token_exception_handling(self, auth_manager):
        """Test exception handling during token validation."""
        # Mock jwt.decode to raise unexpected exception
        with patch("jwt.decode", side_effect=Exception("Unexpected error")):
            result = auth_manager.validate_token("some_token")

            assert result["valid"] is False
            assert "Token validation failed: Unexpected error" in result["error"]


class TestJWTManagerInitialization:
    """Test JWT manager initialization and configuration."""

    def test_initialization_with_secret_key(self):
        """Test successful initialization with secret key."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "secure-secret-key"}):
            manager = JWTAuthenticationManager()
            assert manager.secret_key == "secure-secret-key"
            assert manager.algorithm == "HS256"
            assert manager.token_expiry == 86400  # Default 24 hours
            assert manager.clock_skew_leeway == 300  # 5 minutes

    def test_initialization_production_without_secret(self):
        """Test initialization failure in production without secret key."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            # Remove JWT_SECRET_KEY if present
            if "JWT_SECRET_KEY" in os.environ:
                del os.environ["JWT_SECRET_KEY"]

            with pytest.raises(
                ValueError,
                match="JWT_SECRET_KEY environment variable must be set",
            ):
                JWTAuthenticationManager()

    def test_initialization_development_no_fallback(self):
        """Test that development also requires JWT secret key (security hardened)."""
        env_vars = {"ENVIRONMENT": "development"}
        # Explicitly remove JWT_SECRET_KEY
        if "JWT_SECRET_KEY" in os.environ:
            env_vars["JWT_SECRET_KEY"] = ""

        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(
                ValueError,
                match="JWT_SECRET_KEY environment variable must be set",
            ),
        ):
            JWTAuthenticationManager()

    def test_initialization_custom_token_expiry(self):
        """Test initialization with custom token expiry."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-key",
                "JWT_TOKEN_EXPIRY": "7200",  # 2 hours
            },
        ):
            manager = JWTAuthenticationManager()
            assert manager.token_expiry == 7200

    def test_available_permissions_list(self):
        """Test that available permissions are correctly defined."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-key"}):
            manager = JWTAuthenticationManager()
            expected_permissions = ["read", "write", "admin", "debug"]
            assert manager.available_permissions == expected_permissions


class TestPermissionDetermination:
    """Test permission determination based on agent type."""

    @pytest.fixture
    def auth_manager(self):
        """Create JWT manager with test configuration."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key"}):
            return JWTAuthenticationManager()

    def test_determine_permissions_claude_agent(self, auth_manager):
        """Test permission determination for Claude agent."""
        permissions = auth_manager.determine_permissions(
            "claude", ["read", "write", "admin"]
        )
        assert permissions == ["read", "write"]  # Claude gets read/write, not admin

    def test_determine_permissions_gemini_agent(self, auth_manager):
        """Test permission determination for Gemini agent."""
        permissions = auth_manager.determine_permissions(
            "gemini", ["read", "write", "debug"]
        )
        assert permissions == ["read", "write"]  # Gemini gets read/write, not debug

    def test_determine_permissions_admin_agent(self, auth_manager):
        """Test permission determination for admin agent."""
        permissions = auth_manager.determine_permissions(
            "admin", ["read", "write", "admin", "debug"]
        )
        assert permissions == ["read", "write", "admin", "debug"]  # Admin gets all

    def test_determine_permissions_system_agent(self, auth_manager):
        """Test permission determination for system agent."""
        permissions = auth_manager.determine_permissions("system", ["admin", "debug"])
        assert permissions == ["admin", "debug"]  # System gets all

    def test_determine_permissions_test_agent(self, auth_manager):
        """Test permission determination for test agent."""
        permissions = auth_manager.determine_permissions(
            "test", ["read", "write", "debug"]
        )
        assert permissions == ["read", "write", "debug"]  # Test gets read/write/debug

    def test_determine_permissions_generic_agent(self, auth_manager):
        """Test permission determination for generic agent."""
        permissions = auth_manager.determine_permissions(
            "generic", ["read", "write", "admin"]
        )
        assert permissions == ["read"]  # Generic only gets read

    def test_determine_permissions_unknown_agent_type(self, auth_manager):
        """Test permission determination for unknown agent type."""
        permissions = auth_manager.determine_permissions(
            "unknown_type", ["read", "write", "admin"]
        )
        assert permissions == ["read"]  # Unknown types get minimal permissions

    def test_determine_permissions_invalid_requested(self, auth_manager):
        """Test permission determination with invalid requested permissions."""
        permissions = auth_manager.determine_permissions(
            "claude", ["invalid_perm", "read", "write"]
        )
        assert permissions == ["read", "write"]  # Only valid permissions granted

    def test_determine_permissions_empty_request(self, auth_manager):
        """Test permission determination with empty permission request."""
        permissions = auth_manager.determine_permissions("claude", [])
        assert permissions == ["read"]  # Minimum read permission always granted

    def test_determine_permissions_case_insensitive(self, auth_manager):
        """Test permission determination is case insensitive for agent types."""
        permissions_upper = auth_manager.determine_permissions(
            "CLAUDE", ["read", "write"]
        )
        permissions_mixed = auth_manager.determine_permissions(
            "Claude", ["read", "write"]
        )

        assert permissions_upper == ["read", "write"]
        assert permissions_mixed == ["read", "write"]

    def test_determine_permissions_no_intersection(self, auth_manager):
        """Test permission determination when requested permissions don't intersect with allowed."""
        # Generic agent requesting admin/debug permissions
        permissions = auth_manager.determine_permissions("generic", ["admin", "debug"])
        assert permissions == ["read"]  # Falls back to minimum read permission
