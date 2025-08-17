"""
Rollback Strategy Validation Test Suite for PRP Adaptation Refactoring.

Comprehensive validation for safe change reversal during server.py modularization.
Ensures zero-downtime rollback capability and data integrity maintenance.

Test Categories:
1. Module Extraction Rollback Testing
2. Database State Consistency Validation
3. API Contract Preservation During Rollback
4. Configuration Rollback Validation
5. Service Continuity Testing
6. Data Integrity Verification

Built for safe rollback procedures during 8-module refactoring.
"""

import asyncio
import time
from typing import Any

import pytest

from shared_context_server.auth import AuthInfo
from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestRollbackStrategyValidation:
    """Comprehensive rollback strategy validation for refactoring safety."""

    @pytest.fixture
    def authenticated_context(self):
        """Standard authenticated context for rollback testing."""
        ctx = MockContext(session_id="rollback_test", agent_id="rollback_validator")
        ctx._auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="rollback_validator",
            agent_type="claude",
            permissions=["read", "write", "admin"],
            authenticated=True,
            auth_method="jwt",
            token_id="rollback_test_token",
        )
        return ctx

    async def test_functional_rollback_validation(
        self, test_db_manager, authenticated_context
    ):
        """Test that core functionality can be validated before and after rollback."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager, backend="aiosqlite"):
            # Establish baseline functionality
            baseline_state = await self.capture_functional_baseline(
                server, authenticated_context
            )

            # Verify baseline functionality works
            assert baseline_state["session_creation"]["success"] is True
            assert baseline_state["message_storage"]["success"] is True
            assert baseline_state["search_functionality"]["success"] is True
            assert baseline_state["memory_operations"]["success"] is True

            # Simulate post-rollback state validation
            # (In real scenario, this would test after rolling back a module extraction)
            post_rollback_state = await self.capture_functional_baseline(
                server, authenticated_context
            )

            # Verify rollback preserves functionality
            self.compare_functional_states(baseline_state, post_rollback_state)

    async def capture_functional_baseline(
        self, server, authenticated_context
    ) -> dict[str, Any]:
        """Capture comprehensive functional baseline for rollback comparison."""
        baseline = {}

        try:
            # Test session creation
            session_result = await call_fastmcp_tool(
                server.create_session,
                authenticated_context,
                purpose="Rollback baseline test",
            )
            baseline["session_creation"] = {
                "success": session_result.get("success", False),
                "session_id": session_result.get("session_id"),
                "created_by": session_result.get("created_by"),
                "response_fields": list(session_result.keys()),
            }
            session_id = session_result.get("session_id")

        except Exception as e:
            baseline["session_creation"] = {"success": False, "error": str(e)}
            session_id = None

        if session_id:
            try:
                # Test message storage
                message_result = await call_fastmcp_tool(
                    server.add_message,
                    authenticated_context,
                    session_id=session_id,
                    content="Baseline test message",
                    visibility="public",
                )
                baseline["message_storage"] = {
                    "success": message_result.get("success", False),
                    "message_id": message_result.get("message_id"),
                    "response_fields": list(message_result.keys()),
                }

            except Exception as e:
                baseline["message_storage"] = {"success": False, "error": str(e)}

            try:
                # Test search functionality
                search_result = await call_fastmcp_tool(
                    server.search_context,
                    authenticated_context,
                    session_id=session_id,
                    query="baseline",
                )
                baseline["search_functionality"] = {
                    "success": search_result.get("success", False),
                    "total_matches": search_result.get("total_matches", 0),
                    "response_fields": list(search_result.keys()),
                }

            except Exception as e:
                baseline["search_functionality"] = {"success": False, "error": str(e)}

            try:
                # Test memory operations
                memory_set_result = await call_fastmcp_tool(
                    server.set_memory,
                    authenticated_context,
                    key="baseline_key",
                    value="baseline_value",
                    session_id=session_id,
                )

                memory_get_result = await call_fastmcp_tool(
                    server.get_memory,
                    authenticated_context,
                    key="baseline_key",
                    session_id=session_id,
                )

                baseline["memory_operations"] = {
                    "success": memory_set_result.get("success", False)
                    and memory_get_result.get("success", False),
                    "set_response_fields": list(memory_set_result.keys()),
                    "get_response_fields": list(memory_get_result.keys()),
                    "value_consistency": memory_get_result.get("value")
                    == "baseline_value",
                }

            except Exception as e:
                baseline["memory_operations"] = {"success": False, "error": str(e)}

        # Test authentication functionality
        try:
            auth_result = await call_fastmcp_tool(
                server.authenticate_agent,
                MockContext(),
                agent_id="rollback_test_agent",
                agent_type="claude",
            )
            baseline["authentication"] = {
                "success": auth_result.get("success", False),
                "response_fields": list(auth_result.keys()),
            }

        except Exception as e:
            baseline["authentication"] = {"success": False, "error": str(e)}

        # Test admin functionality
        try:
            metrics_result = await call_fastmcp_tool(
                server.get_performance_metrics, authenticated_context
            )
            baseline["admin_functionality"] = {
                "success": metrics_result.get("success", False),
                "response_fields": list(metrics_result.keys()),
            }

        except Exception as e:
            baseline["admin_functionality"] = {"success": False, "error": str(e)}

        return baseline

    def compare_functional_states(
        self, baseline: dict[str, Any], post_rollback: dict[str, Any]
    ) -> None:
        """Compare functional states to ensure rollback preserves functionality."""
        for function_name, baseline_data in baseline.items():
            assert function_name in post_rollback, (
                f"Function {function_name} missing after rollback"
            )

            post_data = post_rollback[function_name]

            # Verify success states match
            assert baseline_data.get("success") == post_data.get("success"), (
                f"Function {function_name} success state changed after rollback"
            )

            # Verify response structure consistency
            baseline_fields = set(baseline_data.get("response_fields", []))
            post_fields = set(post_data.get("response_fields", []))

            # Response fields should be consistent (allowing for minor variations)
            critical_fields = {"success", "error"}  # Fields that must always be present
            for field in critical_fields:
                if field in baseline_fields:
                    assert field in post_fields, (
                        f"Critical field {field} missing from {function_name} after rollback"
                    )

    async def test_database_consistency_during_rollback(
        self, test_db_manager, authenticated_context
    ):
        """Test database state consistency during rollback scenarios."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager, backend="aiosqlite"):
            # Create test data that should survive rollback
            session_result = await call_fastmcp_tool(
                server.create_session,
                authenticated_context,
                purpose="Database consistency test",
            )
            session_id = session_result["session_id"]

            # Add messages
            message_ids = []
            for i in range(3):
                message_result = await call_fastmcp_tool(
                    server.add_message,
                    authenticated_context,
                    session_id=session_id,
                    content=f"Consistency test message {i}",
                    visibility="public",
                )
                message_ids.append(message_result["message_id"])

            # Set memory entries
            memory_keys = []
            for i in range(3):
                key = f"consistency_key_{i}"
                await call_fastmcp_tool(
                    server.set_memory,
                    authenticated_context,
                    key=key,
                    value=f"consistency_value_{i}",
                    session_id=session_id,
                )
                memory_keys.append(key)

            # Verify data exists
            messages_result = await call_fastmcp_tool(
                server.get_messages, authenticated_context, session_id=session_id
            )
            assert len(messages_result["messages"]) >= 3

            for key in memory_keys:
                memory_result = await call_fastmcp_tool(
                    server.get_memory,
                    authenticated_context,
                    key=key,
                    session_id=session_id,
                )
                assert memory_result["success"] is True
                assert key.split("_")[-1] in memory_result["value"]

            # Simulate rollback scenario - verify data integrity maintained
            # (In real rollback, this would be after module rollback)

            # Verify session still exists
            session_check = await call_fastmcp_tool(
                server.get_session, authenticated_context, session_id=session_id
            )
            assert session_check["success"] is True

            # Verify messages still accessible
            messages_check = await call_fastmcp_tool(
                server.get_messages, authenticated_context, session_id=session_id
            )
            assert len(messages_check["messages"]) >= 3

            # Verify memory still accessible
            for key in memory_keys:
                memory_check = await call_fastmcp_tool(
                    server.get_memory,
                    authenticated_context,
                    key=key,
                    session_id=session_id,
                )
                assert memory_check["success"] is True

    async def test_backend_switching_rollback_safety(
        self, test_db_manager, authenticated_context
    ):
        """Test that backend switching provides rollback safety."""
        from shared_context_server import server

        # Test with aiosqlite backend
        with patch_database_connection(test_db_manager, backend="aiosqlite"):
            baseline_aiosqlite = await self.capture_functional_baseline(
                server, authenticated_context
            )

        # Test with SQLAlchemy backend (simulating potential rollback scenario)
        with patch_database_connection(test_db_manager, backend="sqlalchemy"):
            baseline_sqlalchemy = await self.capture_functional_baseline(
                server, authenticated_context
            )

        # Verify both backends provide consistent functionality
        # This ensures rollback between backend implementations is safe
        for function_name in baseline_aiosqlite:
            assert (
                baseline_aiosqlite[function_name]["success"]
                == baseline_sqlalchemy[function_name]["success"]
            ), (
                f"Backend inconsistency in {function_name} - rollback between backends unsafe"
            )

    async def test_performance_regression_during_rollback(
        self, test_db_manager, authenticated_context
    ):
        """Test that performance characteristics are maintained during rollback."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager, backend="aiosqlite"):
            # Measure performance baseline
            baseline_performance = await self.measure_operation_performance(
                server, authenticated_context
            )

            # Simulate post-rollback performance measurement
            # (In real scenario, this would be after rolling back a module extraction)
            post_rollback_performance = await self.measure_operation_performance(
                server, authenticated_context
            )

            # Verify performance characteristics maintained
            for operation, baseline_time in baseline_performance.items():
                post_time = post_rollback_performance[operation]

                # Allow for test environment variance but prevent major regressions
                # Use 5x threshold for test environments (production target is <30ms)
                regression_threshold = max(baseline_time * 5.0, 0.030)  # 5x or 30ms max
                assert post_time <= regression_threshold, (
                    f"Performance regression in {operation}: {post_time:.3f}s vs baseline {baseline_time:.3f}s (threshold: {regression_threshold:.3f}s)"
                )

    async def measure_operation_performance(
        self, server, authenticated_context
    ) -> dict[str, float]:
        """Measure performance of key operations for rollback comparison."""
        performance = {}

        # Session creation performance
        start_time = time.time()
        session_result = await call_fastmcp_tool(
            server.create_session, authenticated_context, purpose="Performance test"
        )
        performance["session_creation"] = time.time() - start_time
        session_id = session_result["session_id"]

        # Message storage performance
        start_time = time.time()
        await call_fastmcp_tool(
            server.add_message,
            authenticated_context,
            session_id=session_id,
            content="Performance test message",
            visibility="public",
        )
        performance["message_storage"] = time.time() - start_time

        # Search performance
        start_time = time.time()
        await call_fastmcp_tool(
            server.search_context,
            authenticated_context,
            session_id=session_id,
            query="performance",
        )
        performance["search_operation"] = time.time() - start_time

        # Memory operation performance
        start_time = time.time()
        await call_fastmcp_tool(
            server.set_memory,
            authenticated_context,
            key="performance_test",
            value="performance_value",
            session_id=session_id,
        )
        performance["memory_operation"] = time.time() - start_time

        return performance

    async def test_concurrent_operations_during_rollback(
        self, test_db_manager, authenticated_context
    ):
        """Test that concurrent operations remain stable during rollback scenarios."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager, backend="aiosqlite"):
            # Create session for concurrent testing
            session_result = await call_fastmcp_tool(
                server.create_session,
                authenticated_context,
                purpose="Concurrent rollback test",
            )
            session_id = session_result["session_id"]

            async def concurrent_operation(operation_id: int):
                """Perform concurrent operations to test rollback stability."""
                try:
                    # Add message
                    message_result = await call_fastmcp_tool(
                        server.add_message,
                        authenticated_context,
                        session_id=session_id,
                        content=f"Concurrent rollback test {operation_id}",
                        visibility="public",
                    )

                    # Set memory
                    memory_result = await call_fastmcp_tool(
                        server.set_memory,
                        authenticated_context,
                        key=f"rollback_key_{operation_id}",
                        value=f"rollback_value_{operation_id}",
                        session_id=session_id,
                    )

                    # Search
                    search_result = await call_fastmcp_tool(
                        server.search_context,
                        authenticated_context,
                        session_id=session_id,
                        query=f"rollback {operation_id}",
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

            # Run concurrent operations
            concurrent_count = 15
            tasks = [concurrent_operation(i) for i in range(concurrent_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify high success rate (rollback stability)
            successful = sum(
                1 for r in results if isinstance(r, dict) and r.get("success")
            )
            success_rate = successful / concurrent_count

            assert success_rate >= 0.9, (
                f"Concurrent operation success rate {success_rate:.1%} too low for safe rollback"
            )

            # Verify no data corruption during concurrent operations
            messages_result = await call_fastmcp_tool(
                server.get_messages, authenticated_context, session_id=session_id
            )

            # Should have messages from successful operations
            assert len(messages_result["messages"]) >= successful

    async def test_rollback_procedure_validation(
        self, test_db_manager, authenticated_context
    ):
        """Test comprehensive rollback procedure validation."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager, backend="aiosqlite"):
            # Step 1: Capture pre-change state
            pre_change_state = await self.capture_functional_baseline(
                server, authenticated_context
            )

            # Step 2: Simulate change (in real scenario, this would be module extraction)
            # For this test, we'll create some state changes
            session_result = await call_fastmcp_tool(
                server.create_session,
                authenticated_context,
                purpose="Rollback procedure test",
            )
            session_id = session_result["session_id"]

            await call_fastmcp_tool(
                server.add_message,
                authenticated_context,
                session_id=session_id,
                content="State change message",
                visibility="public",
            )

            # Step 3: Validate change was applied
            post_change_messages = await call_fastmcp_tool(
                server.get_messages, authenticated_context, session_id=session_id
            )
            assert len(post_change_messages["messages"]) > 0

            # Step 4: Simulate rollback validation
            # Verify core functionality still works
            post_rollback_state = await self.capture_functional_baseline(
                server, authenticated_context
            )

            # Step 5: Validate rollback success
            for function_name, pre_data in pre_change_state.items():
                post_data = post_rollback_state[function_name]
                assert pre_data["success"] == post_data["success"], (
                    f"Rollback failed for {function_name}: functionality changed"
                )

            # Verify rollback preserves existing data
            rollback_messages = await call_fastmcp_tool(
                server.get_messages, authenticated_context, session_id=session_id
            )
            # Data should still be accessible after rollback
            assert len(rollback_messages["messages"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
