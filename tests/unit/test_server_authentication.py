"""
Unit tests for JWT authentication flow in the server.

Tests the authenticate_agent tool with comprehensive scenarios including
token validation, permission determination, audit logging, and error handling.
"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestAuthenticateAgentTool:
    """Test the authenticate_agent tool with comprehensive scenarios."""

    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Setup method to ensure clean singleton state for each test."""

        yield

    @property
    def test_env_vars(self):
        """Standard environment variables for authentication tests."""
        return {
            "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
            "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
        }

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server
        from tests.fixtures.database import is_sqlalchemy_backend

        # Use the correct backend based on environment variable
        backend = "sqlalchemy" if is_sqlalchemy_backend() else "aiosqlite"

        with patch_database_connection(test_db_manager, backend=backend):
            yield server

    async def test_authenticate_agent_success(self, server_with_db, test_db_manager):
        """Test successful agent authentication with valid API key header."""

        ctx = MockContext(session_id="test_session", agent_id="test_agent")
        ctx.headers = {"X-API-Key": "valid_test_key"}  # Add API key header

        with patch.dict(
            os.environ, {"API_KEY": "valid_test_key", **self.test_env_vars}, clear=False
        ):
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="test_claude",
                agent_type="claude",
                requested_permissions=["read", "write"],
            )

        assert result["success"] is True
        assert result["agent_id"] == "test_claude"
        assert result["agent_type"] == "claude"
        assert "token" in result
        assert "expires_at" in result
        assert "issued_at" in result
        assert result["token_type"] == "Protected"
        assert (
            result["token_format"] == "sct_*"
        )  # PRP-006: Verify protected token format
        assert result["token"].startswith(
            "sct_"
        )  # PRP-006: Verify protected token prefix

        # Verify permissions were granted
        assert "permissions" in result
        assert isinstance(result["permissions"], list)

    async def test_authenticate_agent_invalid_api_key(
        self, server_with_db, test_db_manager
    ):
        """Test authentication failure with invalid API key."""
        ctx = MockContext()
        ctx.headers = {"X-API-Key": "invalid_key"}  # Invalid API key header

        with patch.dict(os.environ, {"API_KEY": "correct_key", **self.test_env_vars}):
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="test_agent",
                agent_type="claude",
                requested_permissions=["read"],
            )

        assert result["success"] is False
        assert "invalid api key" in result["error"].lower()
        assert result["code"] == "AUTH_FAILED"
        assert "context" in result
        assert result["context"]["agent_id"] == "test_agent"

    async def test_authenticate_agent_empty_api_key(
        self, server_with_db, test_db_manager
    ):
        """Test authentication failure with empty API key."""
        ctx = MockContext()
        # No API key header provided (empty case)

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
        ):
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="test_agent",
                agent_type="claude",
                requested_permissions=["read"],
            )

        assert result["success"] is False
        assert "invalid api key" in result["error"].lower()
        assert result["code"] == "AUTH_FAILED"

    async def test_authenticate_agent_no_api_key_configured(
        self, server_with_db, test_db_manager
    ):
        """Test authentication when no API key is configured in environment."""
        ctx = MockContext()
        ctx.headers = {
            "X-API-Key": "any_key"
        }  # API key provided but env not configured

        with patch.dict(os.environ, {}, clear=True):
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="test_agent",
                agent_type="claude",
                requested_permissions=["read"],
            )

        assert result["success"] is False
        assert "invalid api key" in result["error"].lower()
        assert result["code"] == "AUTH_FAILED"

    async def test_authenticate_agent_different_types(
        self, server_with_db, test_db_manager
    ):
        """Test authentication with different agent types."""

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header
        agent_types = ["claude", "gemini", "custom", "test", "system"]

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            for agent_type in agent_types:
                result = await call_fastmcp_tool(
                    server_with_db.authenticate_agent,
                    ctx,
                    agent_id=f"test_{agent_type}",
                    agent_type=agent_type,
                    requested_permissions=["read", "write"],
                )

                if not result.get("success"):
                    print(f"Authentication failed for {agent_type}: {result}")
                assert result["success"] is True, (
                    f"Authentication failed for {agent_type}: {result}"
                )
                assert result["agent_type"] == agent_type
                assert "permissions" in result

    async def test_authenticate_agent_permission_variations(
        self, server_with_db, test_db_manager
    ):
        """Test authentication with different permission requests."""

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header
        permission_sets = [
            [],  # Empty permissions
            ["read"],  # Single permission
            ["read", "write"],  # Common permissions
            ["read", "write", "admin"],  # Including admin
            ["read", "write", "debug"],  # Including debug
            ["invalid_permission"],  # Invalid permission
            ["read", "invalid", "write"],  # Mix of valid and invalid
        ]

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            for permissions in permission_sets:
                result = await call_fastmcp_tool(
                    server_with_db.authenticate_agent,
                    ctx,
                    agent_id="test_agent",
                    agent_type="claude",
                    requested_permissions=permissions,
                )

                assert result["success"] is True
                assert "permissions" in result
                # Permissions are determined by auth manager based on agent type and request

    async def test_authenticate_agent_audit_logging_success(
        self, server_with_db, test_db_manager
    ):
        """Test that successful authentication is properly audit logged."""

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="audit_test_agent",
                agent_type="claude",
                requested_permissions=["read", "write"],
            )

        assert result["success"] is True

        # Verify audit log entry was created
        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM audit_log WHERE event_type = 'jwt_token_generated' AND agent_id = ?",
                ("audit_test_agent",),
            )
            audit_entry = await cursor.fetchone()

        assert audit_entry is not None
        assert audit_entry[2] == "jwt_token_generated"  # event_type (index 2)
        assert audit_entry[3] == "audit_test_agent"  # agent_id (index 3)

    async def test_authenticate_agent_audit_logging_failure(
        self, server_with_db, test_db_manager
    ):
        """Test that authentication failures are properly audit logged."""
        ctx = MockContext()
        ctx.headers = {"X-API-Key": "invalid_key"}  # Invalid API key to trigger failure

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
        ):
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="audit_fail_agent",
                agent_type="claude",
                requested_permissions=["read"],
            )

        assert result["success"] is False

        # Verify audit log entry was created
        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM audit_log WHERE event_type = 'authentication_failed' AND agent_id = ?",
                ("audit_fail_agent",),
            )
            audit_entry = await cursor.fetchone()

        assert audit_entry is not None
        assert audit_entry[2] == "authentication_failed"  # event_type (index 2)
        assert audit_entry[3] == "audit_fail_agent"  # agent_id (index 3)

    async def test_authenticate_agent_token_expiry_format(
        self, server_with_db, test_db_manager
    ):
        """Test that token expiry timestamps are properly formatted."""

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="expiry_test",
                agent_type="claude",
                requested_permissions=["read"],
            )

        assert result["success"] is True

        # Verify timestamp format (ISO format with timezone)
        expires_at = result["expires_at"]
        issued_at = result["issued_at"]

        # Should be able to parse as ISO datetime
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        issued_dt = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))

        # Expiry should be after issued time
        assert expires_dt > issued_dt

        # Both should be UTC (have timezone info)
        assert expires_dt.tzinfo is not None
        assert issued_dt.tzinfo is not None

    async def test_authenticate_agent_database_error_handling(
        self, server_with_db, test_db_manager
    ):
        """Test authentication with database error during audit logging."""

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header

        # Mock audit_log_auth_event to raise exception
        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Reset singleton AFTER environment is set to ensure clean state

            with patch(
                "shared_context_server.server.audit_log_auth_event"
            ) as mock_audit:
                mock_audit.side_effect = Exception("Database error during audit")

                result = await call_fastmcp_tool(
                    server_with_db.authenticate_agent,
                    ctx,
                    agent_id="db_error_test",
                    agent_type="claude",
                    requested_permissions=["read"],
                )

                # Authentication should succeed even if audit logging fails
                assert result["success"] is True
                assert "token" in result
                assert result["agent_id"] == "db_error_test"
                assert result["agent_type"] == "claude"

    async def test_authenticate_agent_auth_manager_error(
        self, server_with_db, test_db_manager
    ):
        """Test authentication when auth manager raises exception."""
        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header

        with (
            patch.dict(os.environ, {"API_KEY": "valid_key"}),
            patch(
                "shared_context_server.auth_tools.generate_agent_jwt_token"
            ) as mock_generate_token,
        ):
            mock_generate_token.side_effect = Exception("Token generation failed")

            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="auth_error_test",
                agent_type="claude",
                requested_permissions=["read"],
            )

        assert result["success"] is False
        assert "authentication" in result["error"].lower() and (
            "failed" in result["error"].lower()
            or "unavailable" in result["error"].lower()
        )
        assert result["code"] in [
            "AUTHENTICATION_ERROR",
            "AUTHENTICATION_SERVICE_UNAVAILABLE",
        ]

    async def test_authenticate_agent_edge_case_inputs(
        self, server_with_db, test_db_manager
    ):
        """Test authentication with edge case inputs."""

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header

        edge_cases = [
            # Very long agent_id (but within limits)
            {
                "agent_id": "a" * 100,  # Max length
                "agent_type": "claude",
                "description": "max_length_agent_id",
            },
            # Long agent type
            {
                "agent_id": "test_agent",
                "agent_type": "custom_very_long_agent_type_name",
                "description": "long_agent_type",
            },
            # Special characters in agent_id
            {
                "agent_id": "agent-with-dashes_and_underscores.123",
                "agent_type": "custom",
                "description": "special_chars_agent_id",
            },
        ]

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Reset singleton AFTER environment is set to ensure clean state
            for case in edge_cases:
                result = await call_fastmcp_tool(
                    server_with_db.authenticate_agent,
                    ctx,
                    agent_id=case["agent_id"],
                    agent_type=case["agent_type"],
                    requested_permissions=["read"],
                )

                assert result["success"] is True, (
                    f"Failed for case: {case['description']}"
                )
                assert result["agent_id"] == case["agent_id"]
                assert result["agent_type"] == case["agent_type"]

    @pytest.mark.performance
    async def test_authenticate_agent_concurrent_requests(
        self, server_with_db, test_db_manager
    ):
        """Test multiple concurrent authentication requests."""
        import asyncio

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header

        # Set environment once for all concurrent requests
        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Reset singleton AFTER environment is set to ensure clean state

            async def authenticate_agent(agent_id: str) -> dict:
                return await call_fastmcp_tool(
                    server_with_db.authenticate_agent,
                    ctx,
                    agent_id=agent_id,
                    agent_type="claude",
                    requested_permissions=["read", "write"],
                )

            # Run multiple authentications concurrently
            tasks = [authenticate_agent(f"concurrent_agent_{i}") for i in range(5)]

            results = await asyncio.gather(*tasks)

            # All should succeed
            for i, result in enumerate(results):
                assert result["success"] is True
                assert result["agent_id"] == f"concurrent_agent_{i}"

        # Clean up singleton after concurrent operations to prevent state pollution

        # Force garbage collection to reduce teardown time
        import gc

        gc.collect()

    async def test_authenticate_agent_default_permission_handling(
        self, server_with_db, test_db_manager
    ):
        """Test authentication when no permissions are explicitly requested."""

        ctx = MockContext()
        ctx.headers = {"X-API-Key": "valid_key"}  # Valid API key header

        with patch.dict(
            os.environ,
            {
                "API_KEY": "valid_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Test with default permissions (should be ["read", "write"])
            result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                ctx,
                agent_id="default_perms",
                agent_type="claude",
                # requested_permissions parameter omitted - should use default
            )

        assert result["success"] is True
        assert "permissions" in result
        # Default permissions should be applied based on auth manager logic
