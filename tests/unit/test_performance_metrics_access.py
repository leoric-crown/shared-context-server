"""
Comprehensive tests for performance metrics access control and edge cases.

This test module focuses on improving coverage for get_performance_metrics
function and related access control mechanisms.
"""

import os
from unittest.mock import patch

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestPerformanceMetricsAccessControl:
    """Test performance metrics access control and functionality."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    async def test_get_performance_metrics_no_auth_token(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics without auth token."""
        ctx = MockContext()

        result = await call_fastmcp_tool(server_with_db.get_performance_metrics, ctx)

        # Should fail due to lack of admin permission
        assert result["success"] is False
        assert "error" in result
        assert "admin permission required" in result[
            "error"
        ].lower() or "admin_required" in result.get("code", "")

    async def test_get_performance_metrics_invalid_token(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with invalid auth token."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        result = await call_fastmcp_tool(
            server_with_db.get_performance_metrics,
            ctx,
            auth_token="sct_invalid-token-format",
        )

        assert result["success"] is False
        assert result["code"] == "INVALID_TOKEN_FORMAT"

    async def test_get_performance_metrics_non_admin_token(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with non-admin token."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        # Mock validate_agent_context_or_error to return non-admin user
        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "test_user",
                "agent_type": "user",
                "permissions": ["read", "write"],  # No admin permission
            }

            result = await call_fastmcp_tool(
                server_with_db.get_performance_metrics,
                ctx,
                auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
            )

            assert result["success"] is False
            assert "error" in result
            assert "admin permission required" in result[
                "error"
            ].lower() or "admin_required" in result.get("code", "")

    async def test_get_performance_metrics_admin_success(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with admin token."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        # Mock validate_agent_context_or_error to return admin user
        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "admin_user",
                "agent_type": "admin",
                "permissions": ["read", "write", "admin"],  # Has admin permission
            }

            # Mock get_performance_metrics_dict to return fake metrics
            with patch(
                "shared_context_server.utils.performance.get_performance_metrics_dict"
            ) as mock_get_metrics:
                mock_get_metrics.return_value = {
                    "success": True,
                    "database": {
                        "connections": 5,
                        "queries_per_second": 125.5,
                    },
                    "memory": {
                        "usage_mb": 256,
                        "peak_mb": 512,
                    },
                    "timestamp": "2024-01-01T12:00:00Z",
                }

                result = await call_fastmcp_tool(
                    server_with_db.get_performance_metrics,
                    ctx,
                    auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
                )

                assert result["success"] is True
                assert "database" in result
                assert "memory" in result
                assert result["requesting_agent"] == "admin_user"
                assert "request_timestamp" in result

    async def test_get_performance_metrics_system_error(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with system error."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        # Mock validate_agent_context_or_error to return admin user
        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "admin_user",
                "agent_type": "admin",
                "permissions": ["read", "write", "admin"],
            }

            # Mock get_performance_metrics_dict to raise exception
            with patch(
                "shared_context_server.utils.performance.get_performance_metrics_dict",
                side_effect=Exception("Metrics system error"),
            ):
                result = await call_fastmcp_tool(
                    server_with_db.get_performance_metrics,
                    ctx,
                    auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
                )

                assert result["success"] is False
                assert (
                    "performance_monitoring temporarily unavailable" in result["error"]
                )
                assert "This is likely temporary." in result["error"]

    async def test_get_performance_metrics_token_validation_error(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with token validation error."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        # Mock validate_agent_context_or_error to return validation error
        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "success": False,
                "error": "Authentication token invalid or expired",
                "code": "TOKEN_AUTHENTICATION_FAILED",
            }

            result = await call_fastmcp_tool(
                server_with_db.get_performance_metrics,
                ctx,
                auth_token="sct_expired-token-12345678-90ab-cdef",
            )

            assert result["success"] is False
            assert result["code"] == "TOKEN_AUTHENTICATION_FAILED"

    async def test_get_performance_metrics_different_admin_types(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with different types of admin users."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        admin_types = [
            ("system_admin", "system", ["read", "write", "admin", "debug"]),
            ("root_admin", "admin", ["read", "write", "admin"]),
            ("test_admin", "test", ["read", "write", "debug", "admin"]),
        ]

        for agent_id, agent_type, permissions in admin_types:
            with patch(
                "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
            ) as mock_validate:
                mock_validate.return_value = {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "permissions": permissions,
                }

                with patch(
                    "shared_context_server.utils.performance.get_performance_metrics_dict"
                ) as mock_get_metrics:
                    mock_get_metrics.return_value = {"success": True, "test": True}

                    result = await call_fastmcp_tool(
                        server_with_db.get_performance_metrics,
                        ctx,
                        auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
                    )

                    assert result["success"] is True
                    assert result["requesting_agent"] == agent_id

    async def test_get_performance_metrics_no_success_field(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics when underlying metrics don't have success field."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "admin_user",
                "agent_type": "admin",
                "permissions": ["read", "write", "admin"],
            }

            # Mock get_performance_metrics_dict to return metrics without success field
            with patch(
                "shared_context_server.utils.performance.get_performance_metrics_dict"
            ) as mock_get_metrics:
                mock_get_metrics.return_value = {
                    # No success field
                    "database_connections": 10,
                    "cache_hits": 500,
                }

                result = await call_fastmcp_tool(
                    server_with_db.get_performance_metrics,
                    ctx,
                    auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
                )

                # Should still return the metrics (no success field enhancement in this case)
                assert "database_connections" in result
                assert "cache_hits" in result
                # Should NOT have requesting_agent added since success field was missing
                assert "requesting_agent" not in result

    async def test_get_performance_metrics_comprehensive_response_format(
        self, server_with_db, test_db_manager
    ):
        """Test comprehensive response format from get_performance_metrics."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "comprehensive_admin",
                "agent_type": "admin",
                "permissions": ["read", "write", "admin", "debug"],
            }

            with patch(
                "shared_context_server.utils.performance.get_performance_metrics_dict"
            ) as mock_get_metrics:
                mock_get_metrics.return_value = {
                    "success": True,
                    "database": {
                        "total_connections": 25,
                        "active_connections": 8,
                        "queries_executed": 15420,
                        "average_query_time_ms": 12.5,
                    },
                    "cache": {
                        "hit_ratio": 0.85,
                        "total_requests": 8500,
                        "cache_size_mb": 128,
                    },
                    "memory": {
                        "rss_mb": 256,
                        "heap_mb": 180,
                        "external_mb": 32,
                    },
                    "system": {
                        "uptime_seconds": 86400,
                        "cpu_usage_percent": 15.2,
                        "load_average": [0.8, 0.9, 1.1],
                    },
                    "timestamp": "2024-01-01T12:00:00Z",
                }

                result = await call_fastmcp_tool(
                    server_with_db.get_performance_metrics,
                    ctx,
                    auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
                )

                # Verify all sections are present
                assert result["success"] is True
                assert "database" in result
                assert "cache" in result
                assert "memory" in result
                assert "system" in result
                assert result["requesting_agent"] == "comprehensive_admin"
                assert "request_timestamp" in result

                # Verify detailed metrics
                assert result["database"]["total_connections"] == 25
                assert result["cache"]["hit_ratio"] == 0.85
                assert result["memory"]["rss_mb"] == 256
                assert result["system"]["uptime_seconds"] == 86400


class TestPerformanceMetricsEdgeCases:
    """Test edge cases and error scenarios for performance metrics."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    async def test_get_performance_metrics_import_error(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics when performance module has issues."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "admin_user",
                "agent_type": "admin",
                "permissions": ["read", "write", "admin"],
            }

            # Mock import error for get_performance_metrics_dict
            with patch(
                "shared_context_server.utils.performance.get_performance_metrics_dict",
                side_effect=ImportError("Performance module not available"),
            ):
                result = await call_fastmcp_tool(
                    server_with_db.get_performance_metrics,
                    ctx,
                    auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
                )

                assert result["success"] is False
                assert (
                    "performance_monitoring temporarily unavailable" in result["error"]
                )

    async def test_get_performance_metrics_with_debug_permission(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with debug permission but no admin."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "debug_user",
                "agent_type": "test",
                "permissions": ["read", "write", "debug"],  # Has debug but not admin
            }

            result = await call_fastmcp_tool(
                server_with_db.get_performance_metrics,
                ctx,
                auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
            )

            # Should still fail - requires admin, not just debug
            assert result["success"] is False
            assert "admin permission required" in result[
                "error"
            ].lower() or "admin_required" in result.get("code", "")

    async def test_get_performance_metrics_empty_permissions(
        self, server_with_db, test_db_manager
    ):
        """Test get_performance_metrics with empty permissions list."""
        ctx = MockContext()
        os.environ["API_KEY"] = "test-key"
        ctx.headers = {"X-API-Key": "test-key"}

        with patch(
            "shared_context_server.admin_lifecycle.validate_agent_context_or_error"
        ) as mock_validate:
            mock_validate.return_value = {
                "agent_id": "no_perms_user",
                "agent_type": "generic",
                "permissions": [],  # Empty permissions
            }

            result = await call_fastmcp_tool(
                server_with_db.get_performance_metrics,
                ctx,
                auth_token="sct_12345678-90ab-cdef-1234-567890abcdef",
            )

            assert result["success"] is False
            assert "admin permission required" in result[
                "error"
            ].lower() or "admin_required" in result.get("code", "")
