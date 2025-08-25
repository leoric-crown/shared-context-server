"""
Modernized tests for JWT authentication flow in the server.

These tests focus on what actually matters: that authentication works correctly
for different agent types and scenarios. They use minimal mocking and test real
business logic rather than complex integration scenarios.
"""

from unittest.mock import AsyncMock, patch

from tests.conftest import MockContext


class TestAuthenticateAgentCore:
    """Test core authentication functionality with focused mocking."""

    async def test_authentication_success_flow(self, isolated_db):
        """Test that successful authentication generates tokens correctly."""
        from shared_context_server.auth_tools import _authenticate_agent_impl
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.auth_tools.validate_api_key_header"
            ) as mock_validate,
            patch(
                "shared_context_server.auth_tools.generate_agent_jwt_token"
            ) as mock_jwt,
            patch(
                "shared_context_server.auth_tools.get_secure_token_manager"
            ) as mock_token_manager,
        ):
            # Mock successful API key validation
            mock_validate.return_value = True
            # Mock JWT token generation
            mock_jwt.return_value = "test.jwt.token"
            # Mock protected token creation
            mock_manager = mock_token_manager.return_value
            mock_manager.create_protected_token = AsyncMock(
                return_value="sct_test-token-12345"
            )

            # Test the core functionality
            result = await _authenticate_agent_impl(
                MockContext(),
                agent_id="test_agent",
                agent_type="claude",
                requested_permissions=["read", "write"],
            )

            # Test what actually matters
            assert result["success"] is True
            assert result["agent_id"] == "test_agent"
            assert result["agent_type"] == "claude"
            assert result["token"].startswith("sct_")
            assert result["token_type"] == "Protected"
            assert "permissions" in result

    async def test_authentication_api_key_failure(self, isolated_db):
        """Test authentication failure when API key is invalid."""
        from shared_context_server.auth_tools import _authenticate_agent_impl
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.auth_tools.validate_api_key_header"
            ) as mock_validate,
            patch(
                "shared_context_server.auth_tools.audit_log_auth_event"
            ) as mock_audit,
        ):
            # Mock API key validation failure
            mock_validate.return_value = False

            result = await _authenticate_agent_impl(
                MockContext(),
                agent_id="test_agent",
                agent_type="claude",
                requested_permissions=["read"],
            )

            # Should return error response
            assert result["success"] is False
            assert "api key" in result["error"].lower()

            # Should audit the failure
            mock_audit.assert_called_once()

    async def test_different_agent_types_permissions(self, isolated_db):
        """Test that different agent types get appropriate permissions."""
        from shared_context_server.auth_tools import _authenticate_agent_impl
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.auth_tools.validate_api_key_header",
                return_value=True,
            ),
            patch(
                "shared_context_server.auth_tools.generate_agent_jwt_token",
                return_value="test.jwt.token",
            ),
            patch(
                "shared_context_server.auth_tools.get_secure_token_manager"
            ) as mock_token_manager,
        ):
            mock_manager = mock_token_manager.return_value
            mock_manager.create_protected_token = AsyncMock(
                return_value="sct_test-token"
            )

            # Test different agent types
            agent_types = ["claude", "admin", "generic"]

            for agent_type in agent_types:
                result = await _authenticate_agent_impl(
                    MockContext(),
                    agent_id=f"test_{agent_type}",
                    agent_type=agent_type,
                    requested_permissions=["read", "write"],
                )

                assert result["success"] is True
                assert result["agent_type"] == agent_type
                assert "permissions" in result
                assert isinstance(result["permissions"], list)

    async def test_authentication_error_handling(self, isolated_db):
        """Test error handling when authentication fails due to system errors."""
        from shared_context_server.auth_tools import _authenticate_agent_impl
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.auth_tools.validate_api_key_header",
                return_value=True,
            ),
            patch(
                "shared_context_server.auth_tools.generate_agent_jwt_token"
            ) as mock_jwt,
        ):
            mock_jwt.side_effect = Exception("JWT generation failed")

            # Mock audit logging
            with patch(
                "shared_context_server.auth_tools.audit_log_auth_event"
            ) as mock_audit:
                result = await _authenticate_agent_impl(
                    MockContext(),
                    agent_id="test_agent",
                    agent_type="claude",
                    requested_permissions=["read"],
                )

                # Should return system error
                assert "error" in result or result.get("success") is False
                # Should attempt to audit the error
                mock_audit.assert_called_once()

    async def test_token_format_validation(self, isolated_db):
        """Test that tokens are properly formatted and contain expected data."""
        from datetime import datetime

        from shared_context_server.auth_tools import _authenticate_agent_impl
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.auth_tools.validate_api_key_header",
                return_value=True,
            ),
            patch(
                "shared_context_server.auth_tools.generate_agent_jwt_token",
                return_value="test.jwt.token",
            ),
            patch(
                "shared_context_server.auth_tools.get_secure_token_manager"
            ) as mock_token_manager,
        ):
            mock_manager = mock_token_manager.return_value
            mock_manager.create_protected_token = AsyncMock(
                return_value="sct_test-token-12345"
            )

            result = await _authenticate_agent_impl(
                MockContext(),
                agent_id="format_test",
                agent_type="claude",
                requested_permissions=["read"],
            )

            # Test token format requirements
            assert result["success"] is True
            assert result["token"].startswith("sct_")
            assert result["token_type"] == "Protected"
            assert result["token_format"] == "sct_*"

            # Test timestamp formats
            expires_at = result["expires_at"]
            issued_at = result["issued_at"]

            # Should be valid ISO format
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            issued_dt = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
            assert expires_dt > issued_dt


class TestAuthenticationErrorCases:
    """Test comprehensive error handling scenarios."""

    async def test_audit_logging_failure_resilience(self, isolated_db):
        """Test authentication succeeds even when audit logging fails."""
        from shared_context_server.auth_tools import _authenticate_agent_impl
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.auth_tools.validate_api_key_header",
                return_value=True,
            ),
            patch(
                "shared_context_server.auth_tools.generate_agent_jwt_token",
                return_value="test.jwt.token",
            ),
            patch(
                "shared_context_server.auth_tools.get_secure_token_manager"
            ) as mock_token_manager,
        ):
            mock_manager = mock_token_manager.return_value
            mock_manager.create_protected_token = AsyncMock(
                return_value="sct_test-token"
            )

            # Mock audit logging failure
            with patch(
                "shared_context_server.auth_tools.audit_log_auth_event"
            ) as mock_audit:
                mock_audit.side_effect = Exception("Database error during audit")

                result = await _authenticate_agent_impl(
                    MockContext(),
                    agent_id="resilience_test",
                    agent_type="claude",
                    requested_permissions=["read"],
                )

                # Authentication should succeed even if audit fails
                assert result["success"] is True
                assert result["agent_id"] == "resilience_test"
                assert "token" in result
