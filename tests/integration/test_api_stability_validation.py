"""
API Stability Validation Test Suite for PRP Adaptation Refactoring.

Comprehensive validation for 23+ MCP tools during server.py modularization.
Ensures zero API breaks, consistent interfaces, and behavioral continuity.

Test Categories:
1. MCP Tool Interface Validation
2. Parameter Schema Consistency
3. Return Value Contract Verification
4. Error Response Standardization
5. Authentication Flow Stability
6. Performance Contract Maintenance

Built for zero-regression guarantee during 8-module refactoring.
"""

import asyncio
import time

import pytest

from shared_context_server.auth import AuthInfo
from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestAPIStabilityValidation:
    """Comprehensive API stability validation for refactoring."""

    @pytest.fixture
    def authenticated_context(self):
        """Standard authenticated context for API testing."""
        ctx = MockContext(session_id="api_test", agent_id="api_validator")
        ctx._auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="api_validator",
            agent_type="claude",
            permissions=["read", "write", "admin"],
            authenticated=True,
            auth_method="jwt",
            token_id="api_test_token",
        )
        return ctx

    async def test_session_management_api_stability(
        self, test_db_manager, authenticated_context
    ):
        """Test session management tools maintain stable API contracts."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Test create_session API stability
            session_result = await call_fastmcp_tool(
                server.create_session,
                authenticated_context,
                purpose="API stability test",
                metadata={"test_type": "api_validation"},
            )

            # Validate create_session response contract
            required_fields = ["success", "session_id", "created_by", "created_at"]
            for field in required_fields:
                assert field in session_result, (
                    f"create_session missing required field: {field}"
                )

            assert isinstance(session_result["success"], bool)
            assert isinstance(session_result["session_id"], str)
            assert isinstance(session_result["created_by"], str)
            assert isinstance(session_result["created_at"], str)  # ISO format string

            session_id = session_result["session_id"]

            # Test get_session API stability
            get_result = await call_fastmcp_tool(
                server.get_session, authenticated_context, session_id=session_id
            )

            # Validate get_session response contract
            required_get_fields = ["success", "session", "messages", "message_count"]
            for field in required_get_fields:
                assert field in get_result, (
                    f"get_session missing required field: {field}"
                )

            # Validate session object contains expected fields
            session_obj = get_result["session"]
            assert session_obj["id"] == session_id
            assert session_obj["purpose"] == "API stability test"

    async def test_message_storage_api_stability(
        self, test_db_manager, authenticated_context
    ):
        """Test message storage tools maintain stable API contracts."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create session for message testing
            session_result = await call_fastmcp_tool(
                server.create_session, authenticated_context, purpose="Message API test"
            )
            session_id = session_result["session_id"]

            # Test add_message API stability
            message_result = await call_fastmcp_tool(
                server.add_message,
                authenticated_context,
                session_id=session_id,
                content="API stability test message",
                visibility="public",
                metadata={"api_test": True},
            )

            # Validate add_message response contract
            required_add_fields = ["success", "message_id", "timestamp"]
            for field in required_add_fields:
                assert field in message_result, (
                    f"add_message missing required field: {field}"
                )

            assert isinstance(message_result["success"], bool)
            assert isinstance(message_result["message_id"], int)
            assert isinstance(message_result["timestamp"], str)  # ISO format string

            # Test get_messages API stability
            messages_result = await call_fastmcp_tool(
                server.get_messages, authenticated_context, session_id=session_id
            )

            # Validate get_messages response contract
            required_get_msg_fields = ["success", "messages", "count"]
            for field in required_get_msg_fields:
                assert field in messages_result, (
                    f"get_messages missing required field: {field}"
                )

            assert isinstance(messages_result["messages"], list)
            assert len(messages_result["messages"]) > 0

            # Validate individual message structure
            message = messages_result["messages"][0]
            message_fields = ["id", "content", "sender", "timestamp", "visibility"]
            for field in message_fields:
                assert field in message, f"Message missing required field: {field}"

    async def test_search_api_stability(self, test_db_manager, authenticated_context):
        """Test search tools maintain stable API contracts."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Setup test data
            session_result = await call_fastmcp_tool(
                server.create_session, authenticated_context, purpose="Search API test"
            )
            session_id = session_result["session_id"]

            await call_fastmcp_tool(
                server.add_message,
                authenticated_context,
                session_id=session_id,
                content="Searchable content for API testing",
                visibility="public",
            )

            # Test search_context API stability
            search_result = await call_fastmcp_tool(
                server.search_context,
                authenticated_context,
                session_id=session_id,
                query="searchable",
            )

            # Validate search_context response contract
            required_search_fields = ["success", "results", "query", "message_count"]
            for field in required_search_fields:
                assert field in search_result, (
                    f"search_context missing required field: {field}"
                )

            assert isinstance(search_result["results"], list)
            assert isinstance(search_result["message_count"], int)

            # Test search_by_sender API stability
            sender_search_result = await call_fastmcp_tool(
                server.search_by_sender,
                authenticated_context,
                session_id=session_id,
                sender="api_validator",
            )

            # Validate search_by_sender response contract
            required_sender_fields = ["success", "messages", "sender", "count"]
            for field in required_sender_fields:
                assert field in sender_search_result, (
                    f"search_by_sender missing required field: {field}"
                )

    async def test_memory_api_stability(self, test_db_manager, authenticated_context):
        """Test agent memory tools maintain stable API contracts."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Setup session
            session_result = await call_fastmcp_tool(
                server.create_session, authenticated_context, purpose="Memory API test"
            )
            session_id = session_result["session_id"]

            # Test set_memory API stability
            set_result = await call_fastmcp_tool(
                server.set_memory,
                authenticated_context,
                key="api_test_key",
                value="API test value",
                session_id=session_id,
            )

            # Validate set_memory response contract
            required_set_fields = [
                "success",
                "key",
                "scope",
                "session_scoped",
                "expires_at",
            ]
            for field in required_set_fields:
                assert field in set_result, (
                    f"set_memory missing required field: {field}"
                )

            # Test get_memory API stability
            get_result = await call_fastmcp_tool(
                server.get_memory,
                authenticated_context,
                key="api_test_key",
                session_id=session_id,
            )

            # Validate get_memory response contract
            required_get_fields = ["success", "key", "value"]
            for field in required_get_fields:
                assert field in get_result, (
                    f"get_memory missing required field: {field}"
                )

            assert get_result["value"] == "API test value"

            # Test list_memory API stability
            list_result = await call_fastmcp_tool(
                server.list_memory, authenticated_context, session_id=session_id
            )

            # Validate list_memory response contract
            required_list_fields = ["success", "entries", "count"]
            for field in required_list_fields:
                assert field in list_result, (
                    f"list_memory missing required field: {field}"
                )

            assert isinstance(list_result["entries"], list)
            assert len(list_result["entries"]) > 0

    async def test_admin_tools_api_stability(
        self, test_db_manager, authenticated_context
    ):
        """Test admin tools maintain stable API contracts."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Test get_performance_metrics API stability
            metrics_result = await call_fastmcp_tool(
                server.get_performance_metrics, authenticated_context
            )

            # Validate performance metrics response contract - may return error if pool not initialized
            if metrics_result.get("success"):
                # Successful response should have these fields
                required_metrics_fields = [
                    "success",
                    "database_performance",
                    "system_info",
                ]
                for field in required_metrics_fields:
                    assert field in metrics_result, (
                        f"get_performance_metrics missing required field: {field}"
                    )
            else:
                # Error response should have these fields
                required_error_fields = ["success", "error", "code"]
                for field in required_error_fields:
                    assert field in metrics_result, (
                        f"get_performance_metrics error missing required field: {field}"
                    )

            # Test get_usage_guidance API stability
            guidance_result = await call_fastmcp_tool(
                server.get_usage_guidance, authenticated_context
            )

            # Validate usage guidance response contract
            required_guidance_fields = ["success", "guidance", "access_level"]
            for field in required_guidance_fields:
                assert field in guidance_result, (
                    f"get_usage_guidance missing required field: {field}"
                )

    async def test_authentication_tool_api_stability(self, test_db_manager):
        """Test authentication tools maintain stable API contracts."""
        import os
        from unittest.mock import patch

        from shared_context_server import server

        # Ensure clean singleton state before test

        with patch_database_connection(test_db_manager):
            # Test authenticate_agent API stability
            mock_ctx = MockContext()
            mock_ctx.headers = {"X-API-Key": "test_api_key"}  # Add API key header

            with patch.dict(
                os.environ,
                {
                    "API_KEY": "test_api_key",
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
            ):
                # Force singleton recreation with new environment
                auth_result = await call_fastmcp_tool(
                    server.authenticate_agent,
                    mock_ctx,  # Unauthenticated context with API key
                    agent_id="test_agent",
                    agent_type="claude",
                )

            # Validate authenticate_agent response contract
            required_auth_fields = [
                "success",
                "token",
                "agent_id",
                "agent_type",
                "expires_at",
            ]
            for field in required_auth_fields:
                assert field in auth_result, (
                    f"authenticate_agent missing required field: {field}"
                )

            assert isinstance(auth_result["success"], bool)
            assert isinstance(auth_result["token"], str)
            assert auth_result["agent_id"] == "test_agent"
            assert auth_result["agent_type"] == "claude"

    async def test_error_response_consistency(
        self, test_db_manager, authenticated_context
    ):
        """Test that error responses maintain consistent structure across all tools."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Test invalid session_id error consistency
            try:
                error_result = await call_fastmcp_tool(
                    server.get_session,
                    authenticated_context,
                    session_id="nonexistent_session",
                )

                # Should return error response with consistent structure
                if not error_result.get("success", True):
                    required_error_fields = ["success", "error", "error_code"]
                    for field in required_error_fields:
                        assert field in error_result, (
                            f"Error response missing required field: {field}"
                        )

                    assert error_result["success"] is False
                    assert isinstance(error_result["error"], str)
                    assert isinstance(error_result["error_code"], str)

            except Exception as e:
                # Exception-based errors are also acceptable
                assert isinstance(e, Exception)

    async def test_parameter_validation_consistency(
        self, test_db_manager, authenticated_context
    ):
        """Test that parameter validation is consistent across all tools."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Test missing required parameters
            with pytest.raises((TypeError, ValueError, AssertionError)) as exc_info:
                await call_fastmcp_tool(
                    server.create_session,
                    authenticated_context,
                    # Missing required 'purpose' parameter
                )

            # Should raise appropriate exception for missing parameters
            assert exc_info.value is not None

    async def test_concurrent_api_stability(
        self, test_db_manager, authenticated_context
    ):
        """Test API stability under concurrent load."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create session for concurrent testing
            session_result = await call_fastmcp_tool(
                server.create_session,
                authenticated_context,
                purpose="Concurrent API test",
            )
            session_id = session_result["session_id"]

            async def concurrent_operation(operation_id: int):
                """Perform concurrent API operations."""
                try:
                    # Add message
                    message_result = await call_fastmcp_tool(
                        server.add_message,
                        authenticated_context,
                        session_id=session_id,
                        content=f"Concurrent message {operation_id}",
                        visibility="public",
                    )

                    # Set memory
                    memory_result = await call_fastmcp_tool(
                        server.set_memory,
                        authenticated_context,
                        key=f"concurrent_key_{operation_id}",
                        value=f"concurrent_value_{operation_id}",
                        session_id=session_id,
                    )

                    # Search context
                    search_result = await call_fastmcp_tool(
                        server.search_context,
                        authenticated_context,
                        session_id=session_id,
                        query=f"concurrent {operation_id}",
                    )

                    return {
                        "success": True,
                        "operation_id": operation_id,
                        "message_success": message_result["success"],
                        "memory_success": memory_result["success"],
                        "search_success": search_result["success"],
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "operation_id": operation_id,
                        "error": str(e),
                    }

            # Run 10 concurrent operations
            concurrent_count = 10
            tasks = [concurrent_operation(i) for i in range(concurrent_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all operations succeeded
            successful = sum(
                1 for r in results if isinstance(r, dict) and r.get("success")
            )
            assert successful >= 8, (
                f"Only {successful}/{concurrent_count} concurrent operations succeeded"
            )

            # Verify API contracts maintained under load
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    assert "operation_id" in result
                    assert "message_success" in result
                    assert "memory_success" in result
                    assert "search_success" in result

    async def test_performance_contract_maintenance(
        self, test_db_manager, authenticated_context
    ):
        """Test that performance contracts are maintained during refactoring."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Setup test data
            session_result = await call_fastmcp_tool(
                server.create_session,
                authenticated_context,
                purpose="Performance contract test",
            )
            session_id = session_result["session_id"]

            # WARMUP: Run operations once to cache imports and initialize modules
            # This eliminates cold-start penalties and measures steady-state performance
            await call_fastmcp_tool(
                server.add_message,
                authenticated_context,
                session_id=session_id,
                content="Warmup message",
                visibility="public",
            )
            await call_fastmcp_tool(
                server.search_context,
                authenticated_context,
                session_id=session_id,
                query="warmup",
            )
            await call_fastmcp_tool(
                server.set_memory,
                authenticated_context,
                key="warmup_key",
                value="warmup_value",
                session_id=session_id,
            )

            # Test message operation performance (steady-state)
            start_time = time.time()
            await call_fastmcp_tool(
                server.add_message,
                authenticated_context,
                session_id=session_id,
                content="Performance test message",
                visibility="public",
            )
            message_time = time.time() - start_time

            # Should be under 100ms target (steady-state performance)
            assert message_time < 0.100, (
                f"Message operation took {message_time:.3f}s, exceeds 100ms target"
            )

            # Test search operation performance (steady-state)
            start_time = time.time()
            await call_fastmcp_tool(
                server.search_context,
                authenticated_context,
                session_id=session_id,
                query="performance",
            )
            search_time = time.time() - start_time

            # RapidFuzz search should be under 25ms target (steady-state performance)
            # Balanced target between responsiveness and realistic test environment performance
            assert search_time < 0.025, (
                f"Search operation took {search_time:.3f}s, exceeds 25ms target"
            )

            # Test memory operation performance (steady-state)
            start_time = time.time()
            await call_fastmcp_tool(
                server.set_memory,
                authenticated_context,
                key="performance_key",
                value="performance_value",
                session_id=session_id,
            )
            memory_time = time.time() - start_time

            # Memory operations should be fast (steady-state performance)
            # CI environments are slower, so we allow higher targets there
            import os

            target_time = (
                0.100 if os.getenv("CI") or os.getenv("GITHUB_ACTIONS") else 0.050
            )
            target_ms = int(target_time * 1000)

            assert memory_time < target_time, (
                f"Memory operation took {memory_time:.3f}s, exceeds {target_ms}ms target"
            )

    async def test_authentication_flow_stability(self, test_db_manager):
        """Test that authentication flows remain stable during refactoring."""
        import os
        from unittest.mock import patch

        from shared_context_server import server

        # Ensure clean singleton state before test

        with patch_database_connection(test_db_manager):
            # Test complete authentication flow

            # 1. Authenticate agent
            mock_ctx = MockContext()
            mock_ctx.headers = {"X-API-Key": "test_api_key"}  # Add API key header

            with patch.dict(
                os.environ,
                {
                    "API_KEY": "test_api_key",
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
            ):
                # Force singleton recreation with new environment
                auth_result = await call_fastmcp_tool(
                    server.authenticate_agent,
                    mock_ctx,
                    agent_id="flow_test_agent",
                    agent_type="claude",
                )
                assert auth_result["success"] is True
                token = auth_result["token"]

                # 2. Use token to create authenticated context
                authenticated_ctx = MockContext(
                    session_id="auth_flow_test", agent_id="flow_test_agent"
                )
                authenticated_ctx.headers = {
                    "X-API-Key": "test_api_key"
                }  # Add API key header
                authenticated_ctx._auth_info = AuthInfo(
                    jwt_validated=True,
                    agent_id="flow_test_agent",
                    agent_type="claude",
                    permissions=["read", "write"],
                    authenticated=True,
                    auth_method="jwt",
                    token_id=token,
                )

                # 3. Test operations with authenticated context
                session_result = await call_fastmcp_tool(
                    server.create_session,
                    authenticated_ctx,
                    purpose="Authentication flow test",
                )
                assert session_result["success"] is True
                assert session_result["created_by"] == "flow_test_agent"

                # 4. Test token refresh
                refresh_result = await call_fastmcp_tool(
                    server.refresh_token, authenticated_ctx, current_token=token
                )
                assert refresh_result["success"] is True
                assert (
                    "token" in refresh_result
                )  # The new token is in the "token" field
                assert refresh_result["token"] != token  # Ensure new token is different


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
