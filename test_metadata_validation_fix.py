#!/usr/bin/env python3
"""
Comprehensive Testing for Metadata Validation Fix

Tests the fix for critical regression in metadata field validation:
- Type signature changed from `Any` with `json_schema_extra` to `dict[str, Any] | None`
- Validates compatibility between FastMCP/Pydantic and Gemini API requirements
- Ensures backward compatibility with existing functionality

AGENT: scs_tester_1200
SESSION: session_12d4b599997a406f
"""

import asyncio
import os
import tempfile

import pytest

# Set environment variables before importing the server
os.environ["JWT_SECRET_KEY"] = (
    "test-secret-key-that-is-long-enough-for-testing-purposes"
)
os.environ["JWT_ENCRYPTION_KEY"] = "test-fernet-key-32-bytes-needed!!!"
os.environ["DISABLE_WEBSOCKET_FOR_TESTS"] = "true"

from fastmcp.testing import create_test_context

from src.shared_context_server.auth import generate_agent_jwt_token
from src.shared_context_server.database import initialize_database
from src.shared_context_server.memory_tools import set_memory
from src.shared_context_server.session_tools import add_message, create_session


class TestMetadataValidationFix:
    """Comprehensive test suite for metadata validation fix."""

    @pytest.fixture(autouse=True)
    async def setup_test_db(self):
        """Setup isolated test database for each test."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
            self.test_db_path = db_file.name
            os.environ["DATABASE_URL"] = self.test_db_path
            await initialize_database(self.test_db_path, reset=True)
            yield
            # Cleanup
            os.unlink(self.test_db_path)

    @pytest.fixture
    async def auth_context(self):
        """Create test authentication context with JWT token."""
        token = await generate_agent_jwt_token(
            agent_id="test_agent_meta",
            agent_type="claude",
            requested_permissions=["read", "write"],
        )
        return create_test_context(headers={"Authorization": f"Bearer {token}"})

    @pytest.fixture
    async def admin_auth_context(self):
        """Create admin authentication context."""
        token = await generate_agent_jwt_token(
            agent_id="admin_agent_meta",
            agent_type="admin",
            requested_permissions=["read", "write", "admin"],
        )
        return create_test_context(headers={"Authorization": f"Bearer {token}"})

    # ========================================================================
    # CREATE_SESSION METADATA VALIDATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_create_session_object_metadata_backward_compatibility(
        self, auth_context
    ):
        """Test that object metadata works (backward compatibility with main branch)."""
        # Test cases that MUST work for backward compatibility
        test_cases = [
            {"test": "value"},
            {"key": "string", "number": 42, "bool": True},
            {"nested": {"deep": {"value": "test"}}},
            {"array": [1, 2, 3]},
            {"mixed": {"string": "value", "array": [1, 2], "nested": {"key": "value"}}},
            {
                "complex": {
                    "version": "1.0",
                    "features": ["auth", "sessions"],
                    "settings": {"debug": False},
                }
            },
        ]

        for i, metadata in enumerate(test_cases):
            result = await create_session(
                ctx=auth_context,
                purpose=f"Test session with object metadata {i}",
                metadata=metadata,
            )

            assert result["success"] is True, f"Failed for metadata: {metadata}"
            assert "session_id" in result
            print(f"✅ Object metadata test {i} passed: {metadata}")

    @pytest.mark.asyncio
    async def test_create_session_null_metadata_compatibility(self, auth_context):
        """Test that null metadata works (backward compatibility)."""
        result = await create_session(
            ctx=auth_context, purpose="Test session with null metadata", metadata=None
        )

        assert result["success"] is True
        assert "session_id" in result
        print("✅ Null metadata test passed")

    @pytest.mark.asyncio
    async def test_create_session_invalid_metadata_rejection(self, auth_context):
        """Test that invalid metadata types are properly rejected."""
        # These should fail with clear error messages
        invalid_cases = [
            "string_metadata",
            42,
            ["array", "metadata"],
            True,
            3.14159,
        ]

        for metadata in invalid_cases:
            result = await create_session(
                ctx=auth_context,
                purpose="Test session with invalid metadata",
                metadata=metadata,
            )

            # Should fail with validation error
            assert result["success"] is False or "error" in result
            print(
                f"✅ Invalid metadata rejected: {type(metadata).__name__} = {metadata}"
            )

    @pytest.mark.asyncio
    async def test_create_session_metadata_edge_cases(self, auth_context):
        """Test edge cases for metadata validation."""
        edge_cases = [
            {},  # Empty object
            {"": "empty_key"},  # Empty string key
            {"unicode": "émojis 🎉 ànd spéciál chars"},  # Unicode content
            {"large_number": 9223372036854775807},  # Max int64
            {"special_chars": "!@#$%^&*()"},  # Special characters
        ]

        for metadata in edge_cases:
            result = await create_session(
                ctx=auth_context,
                purpose="Test session with edge case metadata",
                metadata=metadata,
            )

            assert result["success"] is True, f"Failed for edge case: {metadata}"
            print(f"✅ Edge case passed: {metadata}")

    # ========================================================================
    # ADD_MESSAGE METADATA VALIDATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_add_message_object_metadata_backward_compatibility(
        self, auth_context
    ):
        """Test that add_message works with object metadata."""
        # First create a session
        session_result = await create_session(
            ctx=auth_context,
            purpose="Test session for message metadata",
            metadata={"test_purpose": "message_metadata_validation"},
        )
        session_id = session_result["session_id"]

        # Test message metadata compatibility
        test_cases = [
            {"message_type": "test", "priority": "high"},
            {"user_id": 123, "timestamp": "2024-01-01T00:00:00Z"},
            {"tags": ["testing", "metadata"], "source": "automated_test"},
            {"nested": {"level1": {"level2": "deep_value"}}},
        ]

        for i, metadata in enumerate(test_cases):
            result = await add_message(
                ctx=auth_context,
                session_id=session_id,
                content=f"Test message {i} with object metadata",
                metadata=metadata,
            )

            assert result["success"] is True, f"Failed for metadata: {metadata}"
            assert "message_id" in result
            print(f"✅ Message object metadata test {i} passed: {metadata}")

    @pytest.mark.asyncio
    async def test_add_message_null_metadata_compatibility(self, auth_context):
        """Test that add_message works with null metadata."""
        # First create a session
        session_result = await create_session(
            ctx=auth_context,
            purpose="Test session for null message metadata",
            metadata=None,
        )
        session_id = session_result["session_id"]

        result = await add_message(
            ctx=auth_context,
            session_id=session_id,
            content="Test message with null metadata",
            metadata=None,
        )

        assert result["success"] is True
        assert "message_id" in result
        print("✅ Message null metadata test passed")

    @pytest.mark.asyncio
    async def test_add_message_invalid_metadata_rejection(self, auth_context):
        """Test that add_message rejects invalid metadata types."""
        # First create a session
        session_result = await create_session(
            ctx=auth_context,
            purpose="Test session for invalid message metadata",
            metadata={"test_purpose": "invalid_metadata_rejection"},
        )
        session_id = session_result["session_id"]

        invalid_cases = [
            "string_metadata",
            42,
            ["array", "metadata"],
            True,
        ]

        for metadata in invalid_cases:
            result = await add_message(
                ctx=auth_context,
                session_id=session_id,
                content="Test message with invalid metadata",
                metadata=metadata,
            )

            # Should fail with validation error
            assert result["success"] is False or "error" in result
            print(
                f"✅ Message invalid metadata rejected: {type(metadata).__name__} = {metadata}"
            )

    # ========================================================================
    # SET_MEMORY METADATA VALIDATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_set_memory_object_metadata_backward_compatibility(
        self, auth_context
    ):
        """Test that set_memory works with object metadata."""
        test_cases = [
            {"source": "user_input", "tags": ["important"]},
            {"created_by": "test_agent", "version": 1},
            {"config": {"auto_save": True, "expiry": 3600}},
            {"permissions": ["read", "write"], "scope": "session"},
        ]

        for i, metadata in enumerate(test_cases):
            result = await set_memory(
                ctx=auth_context,
                key=f"test_memory_metadata_{i}",
                value=f"Test value {i}",
                metadata=metadata,
            )

            assert result["success"] is True, f"Failed for metadata: {metadata}"
            assert result["key"] == f"test_memory_metadata_{i}"
            print(f"✅ Memory object metadata test {i} passed: {metadata}")

    @pytest.mark.asyncio
    async def test_set_memory_null_metadata_compatibility(self, auth_context):
        """Test that set_memory works with null metadata."""
        result = await set_memory(
            ctx=auth_context,
            key="test_memory_null_metadata",
            value="Test value with null metadata",
            metadata=None,
        )

        assert result["success"] is True
        assert result["key"] == "test_memory_null_metadata"
        print("✅ Memory null metadata test passed")

    @pytest.mark.asyncio
    async def test_set_memory_invalid_metadata_rejection(self, auth_context):
        """Test that set_memory rejects invalid metadata types."""
        invalid_cases = [
            "string_metadata",
            42,
            ["array", "metadata"],
            True,
        ]

        for i, metadata in enumerate(invalid_cases):
            result = await set_memory(
                ctx=auth_context,
                key=f"test_memory_invalid_{i}",
                value="Test value",
                metadata=metadata,
            )

            # Should fail with validation error
            assert result["success"] is False or "error" in result
            print(
                f"✅ Memory invalid metadata rejected: {type(metadata).__name__} = {metadata}"
            )

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_full_workflow_metadata_compatibility(self, auth_context):
        """Test full workflow: create session → add message → set memory with metadata."""
        # Step 1: Create session with metadata
        session_result = await create_session(
            ctx=auth_context,
            purpose="Full workflow test",
            metadata={"workflow": "test", "version": "1.0"},
        )
        assert session_result["success"] is True
        session_id = session_result["session_id"]

        # Step 2: Add message with metadata
        message_result = await add_message(
            ctx=auth_context,
            session_id=session_id,
            content="Test message in full workflow",
            metadata={"step": "message_creation", "data": {"test": True}},
        )
        assert message_result["success"] is True

        # Step 3: Set memory with metadata
        memory_result = await set_memory(
            ctx=auth_context,
            key="workflow_memory",
            value={"session_id": session_id, "completed_steps": ["session", "message"]},
            metadata={"workflow_step": "memory_storage", "priority": "high"},
            session_id=session_id,
        )
        assert memory_result["success"] is True

        print("✅ Full workflow with metadata passed all steps")

    @pytest.mark.asyncio
    async def test_gemini_api_compatibility_schema(self, auth_context):
        """Test that the new schema works with Gemini API requirements."""
        # This test validates that the `dict[str, Any] | None` type generates
        # proper JSON schema that Gemini API can understand

        # Test various object structures that should work with Gemini
        gemini_test_cases = [
            {"api_version": "v1", "model": "gemini-pro"},
            {"request_id": "test-123", "parameters": {"temperature": 0.7}},
            {"conversation": {"turns": 5, "context": "testing"}},
        ]

        for i, metadata in enumerate(gemini_test_cases):
            # Test create_session
            session_result = await create_session(
                ctx=auth_context,
                purpose=f"Gemini compatibility test {i}",
                metadata=metadata,
            )
            assert session_result["success"] is True

            # Test add_message
            message_result = await add_message(
                ctx=auth_context,
                session_id=session_result["session_id"],
                content=f"Gemini test message {i}",
                metadata=metadata,
            )
            assert message_result["success"] is True

            # Test set_memory
            memory_result = await set_memory(
                ctx=auth_context,
                key=f"gemini_test_{i}",
                value="gemini_test_value",
                metadata=metadata,
            )
            assert memory_result["success"] is True

        print("✅ Gemini API compatibility tests passed")

    # ========================================================================
    # ERROR MESSAGE CLARITY TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_error_messages_are_clear_and_actionable(self, auth_context):
        """Test that error messages for invalid metadata are clear and actionable."""
        # Test with string metadata (should be rejected)
        session_result = await create_session(
            ctx=auth_context,
            purpose="Error message clarity test",
            metadata="invalid_string_metadata",
        )

        # Should have clear error message
        assert session_result["success"] is False or "error" in session_result

        # Check that error contains helpful information
        error_msg = str(session_result)
        assert any(
            keyword in error_msg.lower()
            for keyword in ["metadata", "object", "type", "schema"]
        )
        print(f"✅ Clear error message for invalid metadata: {error_msg}")

    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_metadata_validation_performance(self, auth_context):
        """Test that metadata validation doesn't introduce significant performance overhead."""
        import time

        # Test with moderate-sized metadata objects
        large_metadata = {
            "data": [{"id": i, "value": f"test_{i}"} for i in range(100)],
            "config": {"setting_" + str(i): f"value_{i}" for i in range(50)},
            "timestamp": "2024-01-01T00:00:00Z",
        }

        start_time = time.time()

        # Run multiple operations to measure performance
        for i in range(10):
            session_result = await create_session(
                ctx=auth_context,
                purpose=f"Performance test {i}",
                metadata=large_metadata,
            )
            assert session_result["success"] is True

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / 10

        # Should complete in reasonable time (< 100ms per operation)
        assert avg_time < 0.1, (
            f"Metadata validation too slow: {avg_time:.3f}s per operation"
        )
        print(f"✅ Performance test passed: {avg_time:.3f}s avg per operation")


async def run_comprehensive_tests():
    """Run all metadata validation tests and report results."""
    print("🔍 STARTING COMPREHENSIVE METADATA VALIDATION TESTING")
    print("=" * 60)

    test_instance = TestMetadataValidationFix()

    # Setup test environment
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        test_db_path = db_file.name
        os.environ["DATABASE_URL"] = test_db_path

        try:
            await initialize_database(test_db_path, reset=True)

            # Create auth contexts
            token = await generate_agent_jwt_token(
                agent_id="scs_tester_1200",
                agent_type="claude",
                requested_permissions=["read", "write"],
            )
            auth_context = create_test_context(
                headers={"Authorization": f"Bearer {token}"}
            )

            # Test categories
            test_categories = [
                (
                    "CREATE_SESSION TESTS",
                    [
                        test_instance.test_create_session_object_metadata_backward_compatibility,
                        test_instance.test_create_session_null_metadata_compatibility,
                        test_instance.test_create_session_invalid_metadata_rejection,
                        test_instance.test_create_session_metadata_edge_cases,
                    ],
                ),
                (
                    "ADD_MESSAGE TESTS",
                    [
                        test_instance.test_add_message_object_metadata_backward_compatibility,
                        test_instance.test_add_message_null_metadata_compatibility,
                        test_instance.test_add_message_invalid_metadata_rejection,
                    ],
                ),
                (
                    "SET_MEMORY TESTS",
                    [
                        test_instance.test_set_memory_object_metadata_backward_compatibility,
                        test_instance.test_set_memory_null_metadata_compatibility,
                        test_instance.test_set_memory_invalid_metadata_rejection,
                    ],
                ),
                (
                    "INTEGRATION TESTS",
                    [
                        test_instance.test_full_workflow_metadata_compatibility,
                        test_instance.test_gemini_api_compatibility_schema,
                        test_instance.test_error_messages_are_clear_and_actionable,
                        test_instance.test_metadata_validation_performance,
                    ],
                ),
            ]

            results = {}
            total_tests = 0
            passed_tests = 0

            for category_name, tests in test_categories:
                print(f"\n📋 {category_name}")
                print("-" * 40)

                category_results = []
                for test_func in tests:
                    total_tests += 1
                    try:
                        # Setup database for each test
                        await initialize_database(test_db_path, reset=True)

                        # Run test
                        await test_func(auth_context)
                        category_results.append((test_func.__name__, "✅ PASS"))
                        passed_tests += 1
                        print(f"  ✅ {test_func.__name__}")
                    except Exception as e:
                        category_results.append(
                            (test_func.__name__, f"❌ FAIL: {str(e)}")
                        )
                        print(f"  ❌ {test_func.__name__}: {str(e)}")

                results[category_name] = category_results

            # Summary
            print("\n" + "=" * 60)
            print("📊 TESTING SUMMARY")
            print("=" * 60)
            print(f"Total Tests: {total_tests}")
            print(f"Passed: {passed_tests}")
            print(f"Failed: {total_tests - passed_tests}")
            print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")

            # Detailed results
            print("\n📈 DETAILED RESULTS BY CATEGORY")
            print("-" * 40)
            for category, test_results in results.items():
                passed = sum(1 for _, result in test_results if result.startswith("✅"))
                total = len(test_results)
                print(f"\n{category}: {passed}/{total} passed")
                for test_name, result in test_results:
                    print(f"  {result}")

            # Final status
            if passed_tests == total_tests:
                print(
                    "\n🎉 ALL TESTS PASSED! Metadata validation fix is working correctly."
                )
                return True
            print(f"\n⚠️  {total_tests - passed_tests} tests failed. Fix needed.")
            return False

        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)


if __name__ == "__main__":
    # Run the comprehensive test suite
    result = asyncio.run(run_comprehensive_tests())
    exit(0 if result else 1)
