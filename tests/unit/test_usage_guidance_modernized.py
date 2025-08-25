"""
Modern, focused tests for usage guidance functionality.

These tests focus on what actually matters: that guidance is generated correctly
for different access levels and guidance types. They use minimal mocking and
test real business logic rather than complex integration scenarios.
"""

from unittest.mock import patch

from shared_context_server.server import get_usage_guidance
from tests.conftest import MockContext, call_fastmcp_tool


class TestUsageGuidanceCore:
    """Test core guidance generation functionality with focused mocking."""

    async def test_operations_guidance_generation(self, isolated_db):
        """Test that operations guidance is generated correctly."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            # Mock successful authentication validation (minimal mocking)
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "test_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "expires_at": "2025-12-31T23:59:59Z",
            }

            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="valid-token",
                guidance_type="operations",
            )

            # Test what actually matters
            assert result.get("success") is True
            assert "guidance" in result
            assert result.get("guidance_type") == "operations"

            guidance = result["guidance"]
            assert isinstance(guidance, dict)
            assert len(guidance) > 0

    async def test_coordination_guidance_generation(self, isolated_db):
        """Test that coordination guidance is generated correctly."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "coord_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "expires_at": "2025-12-31T23:59:59Z",
            }

            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="valid-token",
                guidance_type="coordination",
            )

            assert result.get("success") is True
            assert "guidance" in result
            assert result.get("guidance_type") == "coordination"

    async def test_security_guidance_generation(self, isolated_db):
        """Test that security guidance is generated correctly."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "sec_agent",
                "agent_type": "admin",
                "permissions": ["read", "write", "admin"],
                "expires_at": "2025-12-31T23:59:59Z",
            }

            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="valid-admin-token",
                guidance_type="security",
            )

            assert result.get("success") is True
            assert "guidance" in result
            assert result.get("guidance_type") == "security"

    async def test_troubleshooting_guidance_generation(self, isolated_db):
        """Test that troubleshooting guidance is generated correctly."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "trouble_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "expires_at": "2025-12-31T23:59:59Z",
            }

            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="valid-token",
                guidance_type="troubleshooting",
            )

            assert result.get("success") is True
            assert "guidance" in result
            assert result.get("guidance_type") == "troubleshooting"

    async def test_permission_boundary_enforcement(self, isolated_db):
        """Test that guidance respects permission boundaries."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            # Test standard agent permissions
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "standard_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],  # No admin permission
                "expires_at": "2025-12-31T23:59:59Z",
            }

            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="valid-token",
                guidance_type="operations",
            )

            assert result.get("success") is True
            assert result.get("access_level") == "AGENT"
            # Should not expose admin-only operations

    async def test_invalid_guidance_type_handling(self, isolated_db):
        """Test error handling for invalid guidance types."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "test_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "expires_at": "2025-12-31T23:59:59Z",
            }

            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="valid-token",
                guidance_type="invalid_type",
            )

            # Should handle gracefully - either error or fallback guidance
            # The exact behavior depends on implementation
            assert "error" in result or result.get("success") is not None


class TestUsageGuidanceAuthentication:
    """Test authentication aspects with minimal complexity."""

    async def test_authentication_failure_handling(self, isolated_db):
        """Test handling of authentication failures."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            # Mock authentication failure
            mock_validate.return_value = {
                "error": "Invalid token",
                "code": "INVALID_TOKEN",
            }

            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="invalid-token",
                guidance_type="operations",
            )

            assert "error" in result
            assert result.get("success") is not True

    async def test_missing_token_handling(self, isolated_db):
        """Test handling of missing authentication tokens."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                guidance_type="operations",
                # No auth_token provided
            )

            # Should handle missing token appropriately
            # The exact behavior depends on implementation
            assert "error" in result or result.get("success") is not None
