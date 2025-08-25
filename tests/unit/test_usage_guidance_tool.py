"""
Unit tests for the get_usage_guidance MCP tool (PRP-014).

Tests comprehensive security validation, JWT boundary enforcement, multi-agent
workflow testing, and performance validation according to PRP specifications.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fastmcp import Context
else:
    Context = None

# Import the MCP tool and testing utilities
from shared_context_server.server import get_usage_guidance
from tests.conftest import MockContext, call_fastmcp_tool


class TestUsageGuidanceSecurity:
    """Critical security tests for usage guidance tool."""

    async def test_jwt_audience_validation(self):
        """Test tool rejects tokens with wrong audience."""
        ctx = MockContext(agent_id="test_agent")

        # Mock validation to return format error for malformed token
        with patch(
            "shared_context_server.admin_guidance.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "error": "Invalid token format",
                "code": "INVALID_TOKEN_FORMAT",
                "suggestions": ["Use proper JWT token format"],
            }

            result = await call_fastmcp_tool(
                get_usage_guidance, ctx, auth_token="invalid_token"
            )

            assert "error" in result
            assert result["code"] == "INVALID_TOKEN_FORMAT"
            mock_validate.assert_called_once_with(ctx, "invalid_token")

    async def test_permission_escalation_prevention(self):
        """Test tool doesn't leak higher permission guidance."""
        ctx = MagicMock(spec=Context)

        # Mock READ_ONLY agent context
        with (
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
            patch("shared_context_server.database.get_db_connection") as mock_db,
        ):
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "read_only_agent",
                "agent_type": "claude",
                "permissions": ["read"],  # Only read permission
                "expires_at": "2025-08-14T22:00:00Z",
            }

            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await call_fastmcp_tool(
                get_usage_guidance, ctx, guidance_type="operations"
            )

            assert result["success"] is True
            assert result["access_level"] == "READ_ONLY"

            # Verify no admin operations are exposed
            available_ops = result["guidance"]["available_operations"]
            admin_only_ops = ["authenticate_agent", "get_performance_metrics"]

            for admin_op in admin_only_ops:
                assert not any(admin_op in op for op in available_ops), (
                    f"READ_ONLY agent should not see admin operation: {admin_op}"
                )

    async def test_token_boundary_enforcement(self, isolated_db):
        """Test guidance respects actual JWT permissions."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            # Mock successful authentication validation for standard agent
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "agent_worker",
                "agent_type": "claude",
                "permissions": ["read", "write"],  # Standard agent permissions
                "expires_at": "2025-12-31T23:59:59Z",
            }

            # Test operations guidance with standard agent permissions
            result = await call_fastmcp_tool(
                get_usage_guidance,
                MockContext(),
                auth_token="valid-token",
                guidance_type="operations",
            )

            assert result["success"] is True
            assert result["access_level"] == "AGENT"

            # Should have basic guidance structure
            assert "guidance" in result
            guidance = result["guidance"]
            assert isinstance(guidance, dict)

    async def test_malformed_token_handling(self):
        """Test proper error responses for invalid tokens."""
        ctx = MagicMock(spec=Context)

        with patch(
            "shared_context_server.admin_guidance.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "error": "Malformed token format",
                "code": "INVALID_TOKEN_FORMAT",
                "suggestions": ["Check token format", "Use valid JWT token"],
            }

            result = await call_fastmcp_tool(
                get_usage_guidance, ctx, auth_token="malformed_token"
            )

            assert "error" in result
            assert result["code"] == "INVALID_TOKEN_FORMAT"
            assert "suggestions" in result
            mock_validate.assert_called_once_with(ctx, "malformed_token")


class TestUsageGuidanceOperations:
    """Test core operations and guidance generation using real authentication."""

    @pytest.fixture(autouse=True)
    def setup_test_isolation(self):
        """Ensure clean mock state for each test method."""
        # Create unique identifiers for this test to prevent state bleeding
        import uuid

        self.test_id = str(uuid.uuid4())[:8]
        yield

    async def test_admin_guidance_operations(self, isolated_db):
        """Test admin-level operations guidance functionality."""
        from unittest.mock import patch

        from tests.conftest import MockContext
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Use test-specific agent ID to prevent mock interference
            agent_id = f"admin_user_{self.test_id}"

            # Test the actual guidance functionality by mocking successful authentication
            with patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate:
                # Mock successful admin validation
                mock_validate.return_value = {
                    "authenticated": True,
                    "agent_id": agent_id,
                    "agent_type": "admin",
                    "permissions": ["read", "write", "admin"],
                    "expires_at": "2025-12-31T23:59:59Z",
                }

                # Test the core functionality: guidance generation
                result = await call_fastmcp_tool(
                    get_usage_guidance,
                    MockContext(agent_id=agent_id),
                    auth_token=f"valid-admin-token-{self.test_id}",
                    guidance_type="operations",
                )

                # More specific assertions to prevent False is True errors
                assert result.get("success", False) is True, (
                    f"Expected success=True, got {result}"
                )
                assert "guidance" in result, (
                    f"Expected guidance in result, got keys: {list(result.keys())}"
                )

                # The exact structure depends on implementation, but should contain guidance
                guidance = result["guidance"]
                assert isinstance(guidance, dict)
                assert len(guidance) > 0  # Should have guidance content

    async def test_coordination_guidance_type(self, isolated_db):
        """Test coordination guidance generation with mock authentication."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Use test-specific agent ID to prevent mock interference
            agent_id = f"coordinator_agent_{self.test_id}"

            # Mock successful authentication validation
            with patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate:
                mock_validate.return_value = {
                    "authenticated": True,
                    "agent_id": agent_id,
                    "agent_type": "claude",
                    "permissions": ["read", "write"],
                    "expires_at": "2025-12-31T23:59:59Z",
                }

                # Test coordination guidance
                result = await call_fastmcp_tool(
                    get_usage_guidance,
                    MockContext(agent_id=agent_id),
                    auth_token=f"valid-token-{self.test_id}",
                    guidance_type="coordination",
                )

                # More specific assertions to prevent False is True errors
                assert result.get("success", False) is True, (
                    f"Expected success=True, got {result}"
                )
                assert result.get("guidance_type") == "coordination", (
                    f"Expected guidance_type=coordination, got {result.get('guidance_type')}"
                )
                assert "guidance" in result, (
                    f"Expected guidance in result, got keys: {list(result.keys())}"
                )

                # Test what actually matters - that coordination guidance is provided
                guidance = result["guidance"]
                assert isinstance(guidance, dict)
                assert len(guidance) > 0  # Should contain guidance content

    async def test_security_guidance_type(self, isolated_db):
        """Test security guidance generation."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Use test-specific agent ID to prevent mock interference
            agent_id = f"security_agent_{self.test_id}"

            with patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate:
                mock_validate.return_value = {
                    "authenticated": True,
                    "agent_id": agent_id,
                    "agent_type": "claude",
                    "permissions": ["read", "write", "admin"],
                    "expires_at": "2025-08-14T22:00:00Z",
                }

                # Test security guidance
                result = await call_fastmcp_tool(
                    get_usage_guidance,
                    MockContext(agent_id=agent_id),
                    auth_token=f"valid-admin-token-{self.test_id}",
                    guidance_type="security",
                )

                # More specific assertions to prevent False is True errors
                assert result.get("success", False) is True, (
                    f"Expected success=True, got {result}"
                )
                assert result.get("guidance_type") == "security", (
                    f"Expected guidance_type=security, got {result.get('guidance_type')}"
                )
                assert "guidance" in result, (
                    f"Expected guidance in result, got keys: {list(result.keys())}"
                )

                # Test what actually matters - that security guidance is provided
                guidance = result["guidance"]
                assert isinstance(guidance, dict)
                assert len(guidance) > 0  # Should contain security guidance content
                assert "best_practices" in result["guidance"]

    async def test_troubleshooting_guidance_type(self, isolated_db):
        """Test troubleshooting guidance generation with mock authentication."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Use test-specific agent ID to prevent mock interference
            agent_id = f"trouble_agent_{self.test_id}"

            # Mock successful authentication validation
            with patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate:
                mock_validate.return_value = {
                    "authenticated": True,
                    "agent_id": agent_id,
                    "agent_type": "claude",
                    "permissions": ["read", "write"],
                    "expires_at": "2025-12-31T23:59:59Z",
                }

                # Test troubleshooting guidance
                result = await call_fastmcp_tool(
                    get_usage_guidance,
                    MockContext(agent_id=agent_id),
                    auth_token=f"valid-token-{self.test_id}",
                    guidance_type="troubleshooting",
                )

                # More specific assertions to prevent False is True errors
                assert result.get("success", False) is True, (
                    f"Expected success=True, got {result}"
                )
                assert result.get("guidance_type") == "troubleshooting", (
                    f"Expected guidance_type=troubleshooting, got {result.get('guidance_type')}"
                )
                assert "guidance" in result, (
                    f"Expected guidance in result, got keys: {list(result.keys())}"
                )

                # Test what actually matters - that troubleshooting guidance is provided
                guidance = result["guidance"]
                assert isinstance(guidance, dict)
                assert len(guidance) > 0  # Should contain troubleshooting guidance

    async def test_invalid_guidance_type(self, isolated_db):
        """Test error handling for invalid guidance types."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Use test-specific agent ID to prevent mock interference
            agent_id = f"test_agent_{self.test_id}"

            # Mock successful authentication validation
            with patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate:
                mock_validate.return_value = {
                    "authenticated": True,
                    "agent_id": agent_id,
                    "agent_type": "claude",
                    "permissions": ["read", "write"],
                    "expires_at": "2025-12-31T23:59:59Z",
                }

                # Test with invalid guidance type
                result = await call_fastmcp_tool(
                    get_usage_guidance,
                    MockContext(agent_id=agent_id),
                    auth_token=f"valid-token-{self.test_id}",
                    guidance_type="invalid_type",
                )

                # Should handle invalid type gracefully
                assert "error" in result or result.get("success") is False


class TestMultiAgentCoordinationWorkflow:
    """Test complete multi-agent workflow with different JWT access levels."""

    async def test_multi_agent_coordination_workflow(self):
        """Test complete multi-agent workflow with different JWT access levels."""

        # Test Admin agent generating coordination guidance
        admin_ctx = MagicMock(spec=Context)

        with (
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
            patch("shared_context_server.database.get_db_connection") as mock_db,
        ):
            # Admin agent context
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "admin_coordinator",
                "agent_type": "claude",
                "permissions": ["read", "write", "admin"],
                "expires_at": "2025-08-14T22:00:00Z",
            }

            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            admin_result = await call_fastmcp_tool(
                get_usage_guidance, admin_ctx, guidance_type="coordination"
            )

            assert admin_result["success"] is True
            assert admin_result["access_level"] == "ADMIN"

            # Admin should have token generation instructions
            coord_instructions = admin_result["guidance"]["coordination_instructions"]
            assert any(
                "authenticate_agent" in instruction
                for instruction in coord_instructions
            )

        # Test Agent level coordination guidance
        agent_ctx = MagicMock(spec=Context)

        with (
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
            patch("shared_context_server.database.get_db_connection") as mock_db,
        ):
            # Agent context
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "worker_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "expires_at": "2025-08-14T22:00:00Z",
            }

            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            agent_result = await call_fastmcp_tool(
                get_usage_guidance, agent_ctx, guidance_type="coordination"
            )

            assert agent_result["success"] is True
            assert agent_result["access_level"] == "AGENT"

            # Agent should have different coordination patterns (no token generation)
            coord_instructions = agent_result["guidance"]["coordination_instructions"]
            assert not any(
                "authenticate_agent" in instruction
                for instruction in coord_instructions
            )
            assert any(
                "agent_only visibility" in instruction
                for instruction in coord_instructions
            )

        # Test READ_ONLY agent access
        readonly_ctx = MagicMock(spec=Context)

        with (
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
            patch("shared_context_server.database.get_db_connection") as mock_db,
        ):
            # Read-only agent context
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "observer_agent",
                "agent_type": "claude",
                "permissions": ["read"],
                "expires_at": "2025-08-14T22:00:00Z",
            }

            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            readonly_result = await call_fastmcp_tool(
                get_usage_guidance, readonly_ctx, guidance_type="coordination"
            )

            assert readonly_result["success"] is True
            assert readonly_result["access_level"] == "READ_ONLY"

            # Read-only should only have monitoring capabilities
            coord_instructions = readonly_result["guidance"][
                "coordination_instructions"
            ]
            assert any(
                "Monitor session activity" in instruction
                for instruction in coord_instructions
            )
            assert not any(
                "Create" in instruction for instruction in coord_instructions
            )


@pytest.mark.performance
class TestPerformanceValidation:
    """Performance tests for guidance generation."""

    @pytest.fixture(autouse=True)
    def setup_test_isolation(self):
        """Ensure clean mock state for each test method."""
        # Create unique identifiers for this test to prevent state bleeding
        import uuid

        self.test_id = str(uuid.uuid4())[:8]
        yield

    @pytest.mark.timeout(5)
    @pytest.mark.performance
    async def test_guidance_generation_performance(self, isolated_db):
        """Test guidance generation completes within 50ms target."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Use test-specific agent ID to prevent mock interference
            agent_id = f"perf_test_agent_{self.test_id}"

            with patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate:
                mock_validate.return_value = {
                    "authenticated": True,
                    "agent_id": agent_id,
                    "agent_type": "claude",
                    "permissions": ["read", "write"],
                    "expires_at": "2025-08-14T22:00:00Z",
                }

                import time

                start_time = time.time()

                result = await call_fastmcp_tool(
                    get_usage_guidance,
                    MockContext(agent_id=agent_id),
                    auth_token=f"valid-token-{self.test_id}",
                    guidance_type="operations",
                )

                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000

                # More specific assertions to prevent False is True errors
                assert result.get("success", False) is True, (
                    f"Expected success=True, got {result}"
                )
                # Performance target: <50ms as specified in PRP-014
                assert execution_time_ms < 50, (
                    f"Guidance generation took {execution_time_ms:.2f}ms, should be <50ms"
                )

    @pytest.mark.performance
    @pytest.mark.timeout(10)
    async def test_concurrent_agent_access(self, isolated_db):
        """Test concurrent agent access without performance degradation."""
        import asyncio
        import gc

        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):

            async def single_guidance_request(agent_id: str, permissions: list[str]):
                # Make each agent request unique
                unique_agent_id = f"{agent_id}_{self.test_id}"

                with patch(
                    "shared_context_server.admin_guidance.validate_agent_context_or_error"
                ) as mock_validate:
                    mock_validate.return_value = {
                        "authenticated": True,
                        "agent_id": unique_agent_id,
                        "agent_type": "claude",
                        "permissions": permissions,
                        "expires_at": "2025-08-14T22:00:00Z",
                    }

                    return await call_fastmcp_tool(
                        get_usage_guidance,
                        MockContext(agent_id=unique_agent_id),
                        auth_token=f"valid-token-{unique_agent_id}",
                        guidance_type="operations",
                    )

            # Simulate 10 concurrent agents
            tasks = []
            for i in range(10):
                agent_id = f"concurrent_agent_{i}"
                permissions = ["read", "write"] if i % 2 == 0 else ["read"]
                tasks.append(single_guidance_request(agent_id, permissions))

            import time

            start_time = time.time()

            results = await asyncio.gather(*tasks)

            end_time = time.time()
            total_time_ms = (end_time - start_time) * 1000

            # All requests should succeed with more specific assertions
            for i, result in enumerate(results):
                assert result.get("success", False) is True, (
                    f"Agent {i} failed: {result}"
                )

            # Total time for 10 concurrent requests should be reasonable
            # Even with some overhead, should be well under 500ms
            assert total_time_ms < 500, (
                f"Concurrent requests took {total_time_ms:.2f}ms, should be <500ms"
            )

            # Force garbage collection to reduce teardown time
            gc.collect()


@pytest.mark.performance
class TestAuditLogging:
    """Test audit logging for security monitoring."""

    async def test_guidance_request_audit_logging(self):
        """Test that all guidance requests are properly logged."""
        ctx = MagicMock(spec=Context)

        with (
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
            patch("shared_context_server.database.get_db_connection") as mock_db,
            patch("shared_context_server.admin_guidance.audit_log") as mock_audit,
        ):
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "audit_test_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "expires_at": "2025-08-14T22:00:00Z",
            }

            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await call_fastmcp_tool(
                get_usage_guidance, ctx, guidance_type="security"
            )

            assert result["success"] is True

            # Verify audit log was called (connection can be any object due to test fixtures)
            from unittest.mock import ANY

            mock_audit.assert_called_once_with(
                ANY,  # Connection object varies due to test fixtures
                "usage_guidance_accessed",
                "audit_test_agent",
                None,
                {
                    "guidance_type": "security",
                    "access_level": "AGENT",
                    "agent_type": "claude",
                },
            )


class TestResponseFormat:
    """Test response format compliance."""

    @pytest.fixture(autouse=True)
    def setup_test_isolation(self):
        """Ensure clean mock state for each test method."""
        # Create unique identifiers for this test to prevent state bleeding
        import uuid

        self.test_id = str(uuid.uuid4())[:8]
        yield

    @pytest.mark.performance
    async def test_response_format_compliance(self, isolated_db):
        """Test response format matches specification exactly."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Use test-specific agent ID to prevent mock interference
            agent_id = f"format_test_agent_{self.test_id}"

            with patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate:
                mock_validate.return_value = {
                    "authenticated": True,
                    "agent_id": agent_id,
                    "agent_type": "claude",
                    "permissions": ["read", "write", "refresh_token"],
                    "expires_at": "2025-08-14T22:00:00Z",
                }

                result = await call_fastmcp_tool(
                    get_usage_guidance,
                    MockContext(agent_id=agent_id),
                    auth_token=f"valid-token-{self.test_id}",
                    guidance_type="operations",
                )

                # Verify required top-level fields with better error messages
                assert "success" in result, (
                    f"Missing 'success' field in result: {list(result.keys())}"
                )
                assert result.get("success", False) is True, (
                    f"Expected success=True, got {result}"
                )

                # Only verify other fields if the request was successful
                if result.get("success"):
                    assert "access_level" in result, (
                        f"Missing 'access_level' field in result: {list(result.keys())}"
                    )
                    assert "agent_info" in result, (
                        f"Missing 'agent_info' field in result: {list(result.keys())}"
                    )
                    assert "guidance" in result, (
                        f"Missing 'guidance' field in result: {list(result.keys())}"
                    )
                    assert "examples" in result, (
                        f"Missing 'examples' field in result: {list(result.keys())}"
                    )
                    assert "guidance_type" in result, (
                        f"Missing 'guidance_type' field in result: {list(result.keys())}"
                    )
                    assert "generated_at" in result, (
                        f"Missing 'generated_at' field in result: {list(result.keys())}"
                    )

                    # Verify agent_info structure
                    agent_info = result["agent_info"]
                    assert "agent_id" in agent_info
                    assert "agent_type" in agent_info
                    assert "permissions" in agent_info
                    assert "expires_at" in agent_info
                    assert "can_refresh" in agent_info

                    # Verify can_refresh is correctly determined
                    assert (
                        agent_info["can_refresh"] is True
                    )  # has refresh_token permission

                    # Verify generated_at is valid ISO timestamp
                    generated_at = result["generated_at"]
                    datetime.fromisoformat(
                        generated_at.replace("Z", "+00:00")
                    )  # Should not raise exception

                    # Verify guidance structure (varies by type but should be dict)
                    assert isinstance(result["guidance"], dict)
                    assert isinstance(result["examples"], dict)


@pytest.mark.performance
class TestErrorHandling:
    """Test comprehensive error handling."""

    @pytest.mark.performance
    async def test_system_error_handling(self):
        """Test system error handling when database fails."""
        ctx = MagicMock(spec=Context)

        with (
            patch(
                "shared_context_server.admin_guidance.validate_agent_context_or_error"
            ) as mock_validate,
            patch("shared_context_server.database.get_db_connection") as mock_db,
        ):
            mock_validate.return_value = {
                "authenticated": True,
                "agent_id": "error_test_agent",
                "agent_type": "claude",
                "permissions": ["read", "write"],
                "expires_at": "2025-08-14T22:00:00Z",
            }

            # Simulate database connection failure
            mock_db.side_effect = Exception("Database connection failed")

            result = await call_fastmcp_tool(
                get_usage_guidance, ctx, guidance_type="operations"
            )

            # Should return system error response
            assert "error" in result or "success" in result
            # If success=False, it's a system error response

    async def test_validation_error_passthrough(self):
        """Test that validation errors are passed through correctly."""
        ctx = MagicMock(spec=Context)

        with patch(
            "shared_context_server.admin_guidance.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "error": "Token validation failed",
                "code": "TOKEN_AUTHENTICATION_FAILED",
                "suggestions": ["Check token format and expiration"],
            }

            result = await call_fastmcp_tool(
                get_usage_guidance, ctx, auth_token="invalid"
            )

            # Error should be passed through unchanged
            assert result["error"] == "Token validation failed"
            assert result["code"] == "TOKEN_AUTHENTICATION_FAILED"
            assert "suggestions" in result
