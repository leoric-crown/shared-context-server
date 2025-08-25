"""
Comprehensive Testing for Metadata Validation Fix

Tests the fix for critical regression in metadata field validation:
- Type signature changed from `Any` with `json_schema_extra` to `dict[str, Any] | None`
- Validates compatibility between FastMCP/Pydantic and Gemini API requirements
- Ensures backward compatibility with existing functionality

AGENT: scs_tester_1200
SESSION: session_12d4b599997a406f
"""

import pytest

from shared_context_server.auth import AuthInfo
from shared_context_server.memory_tools import set_memory
from shared_context_server.session_tools import add_message, create_session
from tests.conftest import call_fastmcp_tool
from tests.fixtures.database import patch_database_for_test


class MockContext:
    """Mock context for FastMCP testing."""

    def __init__(
        self,
        session_id="test_session",
        agent_id="test_agent",
        agent_type="claude",
        permissions=None,
    ):
        self.session_id = session_id
        if permissions is None:
            permissions = ["read", "write"]

        # Ensure proper API key header for authentication (must match .env file)
        self.headers = {"X-API-Key": "T34PEv/IEUoVx18/g+xOIk/zT4S/MaQUm0dlU9jQhXk="}

        # Set up authentication using AuthInfo pattern
        self._auth_info = AuthInfo(
            jwt_validated=False,
            agent_id=agent_id,
            agent_type=agent_type,
            permissions=permissions,
            authenticated=True,
        )

    def get_auth_info(self):
        return self._auth_info


class TestMetadataValidationFix:
    """Comprehensive test suite for metadata validation fix."""

    # ========================================================================
    # CREATE_SESSION METADATA VALIDATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_create_session_object_metadata_backward_compatibility(
        self, isolated_db
    ):
        """Test that object metadata works (backward compatibility with main branch)."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_session_meta", "test_agent_meta")

            # Test cases that MUST work for backward compatibility
            test_cases = [
                {"test": "value"},
                {"key": "string", "number": 42, "bool": True},
                {"nested": {"deep": {"value": "test"}}},
                {"array": [1, 2, 3]},
                {
                    "mixed": {
                        "string": "value",
                        "array": [1, 2],
                        "nested": {"key": "value"},
                    }
                },
                {
                    "complex": {
                        "version": "1.0",
                        "features": ["auth", "sessions"],
                        "settings": {"debug": False},
                    }
                },
            ]

            for i, metadata in enumerate(test_cases):
                result = await call_fastmcp_tool(
                    create_session,
                    ctx,
                    purpose=f"Test session with object metadata {i}",
                    metadata=metadata,
                )

                assert result["success"] is True, f"Failed for metadata: {metadata}"
                assert "session_id" in result

    @pytest.mark.asyncio
    async def test_create_session_null_metadata_compatibility(self, isolated_db):
        """Test that null metadata works (backward compatibility)."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_session_null", "test_agent_null")

            result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Test session with null metadata",
                metadata=None,
            )

            assert result["success"] is True
            assert "session_id" in result

    @pytest.mark.asyncio
    async def test_create_session_invalid_metadata_rejection(self, isolated_db):
        """Test that invalid metadata types are properly rejected."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_session_invalid", "test_agent_invalid")

            # These should fail with clear error messages
            invalid_cases = [
                "string_metadata",
                42,
                ["array", "metadata"],
                True,
                3.14159,
            ]

            for metadata in invalid_cases:
                result = await call_fastmcp_tool(
                    create_session,
                    ctx,
                    purpose="Test session with invalid metadata",
                    metadata=metadata,
                )

                # Should fail with validation error
                assert result["success"] is False or "error" in result, (
                    f"Invalid metadata incorrectly accepted: {metadata}"
                )

    @pytest.mark.asyncio
    async def test_create_session_metadata_edge_cases(self, isolated_db):
        """Test edge cases for metadata validation."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_session_edge", "test_agent_edge")

            edge_cases = [
                {},  # Empty object
                {"": "empty_key"},  # Empty string key
                {"unicode": "émojis 🎉 ànd spéciál chars"},  # Unicode content
                {"large_number": 9223372036854775807},  # Max int64
                {"special_chars": "!@#$%^&*()"},  # Special characters
            ]

            for metadata in edge_cases:
                result = await call_fastmcp_tool(
                    create_session,
                    ctx,
                    purpose="Test session with edge case metadata",
                    metadata=metadata,
                )

                assert result["success"] is True, f"Failed for edge case: {metadata}"

    # ========================================================================
    # ADD_MESSAGE METADATA VALIDATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_add_message_object_metadata_backward_compatibility(
        self, isolated_db
    ):
        """Test that add_message works with object metadata."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_message_meta", "test_agent_message")

            # First create a session
            session_result = await call_fastmcp_tool(
                create_session,
                ctx,
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
                result = await call_fastmcp_tool(
                    add_message,
                    ctx,
                    session_id=session_id,
                    content=f"Test message {i} with object metadata",
                    metadata=metadata,
                )

                assert result["success"] is True, f"Failed for metadata: {metadata}"
                assert "message_id" in result

    @pytest.mark.asyncio
    async def test_add_message_null_metadata_compatibility(self, isolated_db):
        """Test that add_message works with null metadata."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_message_null", "test_agent_message_null")

            # First create a session
            session_result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Test session for null message metadata",
                metadata=None,
            )
            session_id = session_result["session_id"]

            result = await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content="Test message with null metadata",
                metadata=None,
            )

            assert result["success"] is True
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_add_message_invalid_metadata_rejection(self, isolated_db):
        """Test that add_message rejects invalid metadata types."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_message_invalid", "test_agent_message_invalid")

            # First create a session
            session_result = await call_fastmcp_tool(
                create_session,
                ctx,
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
                result = await call_fastmcp_tool(
                    add_message,
                    ctx,
                    session_id=session_id,
                    content="Test message with invalid metadata",
                    metadata=metadata,
                )

                # Should fail with validation error
                assert result["success"] is False or "error" in result, (
                    f"Invalid metadata incorrectly accepted: {metadata}"
                )

    # ========================================================================
    # SET_MEMORY METADATA VALIDATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_set_memory_object_metadata_backward_compatibility(self, isolated_db):
        """Test that set_memory works with object metadata."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_memory_meta", "test_agent_memory")

            test_cases = [
                {"source": "user_input", "tags": ["important"]},
                {"created_by": "test_agent", "version": 1},
                {"config": {"auto_save": True, "expiry": 3600}},
                {"permissions": ["read", "write"], "scope": "session"},
            ]

            for i, metadata in enumerate(test_cases):
                result = await call_fastmcp_tool(
                    set_memory,
                    ctx,
                    key=f"test_memory_metadata_{i}",
                    value=f"Test value {i}",
                    metadata=metadata,
                )

                assert result["success"] is True, f"Failed for metadata: {metadata}"
                assert result["key"] == f"test_memory_metadata_{i}"

    @pytest.mark.asyncio
    async def test_set_memory_null_metadata_compatibility(self, isolated_db):
        """Test that set_memory works with null metadata."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_memory_null", "test_agent_memory_null")

            result = await call_fastmcp_tool(
                set_memory,
                ctx,
                key="test_memory_null_metadata",
                value="Test value with null metadata",
                metadata=None,
            )

            assert result["success"] is True
            assert result["key"] == "test_memory_null_metadata"

    @pytest.mark.asyncio
    async def test_set_memory_invalid_metadata_rejection(self, isolated_db):
        """Test that set_memory rejects invalid metadata types with stricter validation."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_memory_strict", "test_agent_memory_strict")

            # These should be rejected with stricter validation
            invalid_metadata_cases = [
                "string_metadata",
                42,
                ["array", "metadata"],
                True,
                3.14159,
            ]

            for i, metadata in enumerate(invalid_metadata_cases):
                result = await call_fastmcp_tool(
                    set_memory,
                    ctx,
                    key=f"test_memory_invalid_{i}",
                    value="Test value",
                    metadata=metadata,
                )

                # Should fail with validation error
                assert result["success"] is False or "error" in result, (
                    f"Invalid metadata incorrectly accepted: {metadata}"
                )

            # But valid metadata should still work
            valid_cases = [{"object": "metadata"}, None]

            for i, metadata in enumerate(valid_cases):
                result = await call_fastmcp_tool(
                    set_memory,
                    ctx,
                    key=f"test_memory_valid_{i}",
                    value="Test value",
                    metadata=metadata,
                )

                assert result["success"] is True, f"Valid metadata rejected: {metadata}"

    # ========================================================================
    # INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.asyncio
    async def test_full_workflow_metadata_compatibility(self, isolated_db):
        """Test full workflow: create session → add message → set memory with metadata."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_workflow", "test_agent_workflow")

            # Step 1: Create session with metadata
            session_result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Full workflow test",
                metadata={"workflow": "test", "version": "1.0"},
            )
            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # Step 2: Add message with metadata
            message_result = await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content="Test message in full workflow",
                metadata={"step": "message_creation", "data": {"test": True}},
            )
            assert message_result["success"] is True

            # Step 3: Set memory with metadata
            memory_result = await call_fastmcp_tool(
                set_memory,
                ctx,
                key="workflow_memory",
                value={
                    "session_id": session_id,
                    "completed_steps": ["session", "message"],
                },
                metadata={"workflow_step": "memory_storage", "priority": "high"},
                session_id=session_id,
            )
            assert memory_result["success"] is True

    @pytest.mark.asyncio
    async def test_gemini_api_compatibility_schema(self, isolated_db):
        """Test that the new schema works with Gemini API requirements."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_gemini", "test_agent_gemini")

            # Test various object structures that should work with Gemini
            gemini_test_cases = [
                {"api_version": "v1", "model": "gemini-pro"},
                {"request_id": "test-123", "parameters": {"temperature": 0.7}},
                {"conversation": {"turns": 5, "context": "testing"}},
            ]

            for i, metadata in enumerate(gemini_test_cases):
                # Test create_session
                session_result = await call_fastmcp_tool(
                    create_session,
                    ctx,
                    purpose=f"Gemini compatibility test {i}",
                    metadata=metadata,
                )
                assert session_result["success"] is True

                # Test add_message
                message_result = await call_fastmcp_tool(
                    add_message,
                    ctx,
                    session_id=session_result["session_id"],
                    content=f"Gemini test message {i}",
                    metadata=metadata,
                )
                assert message_result["success"] is True

                # Test set_memory
                memory_result = await call_fastmcp_tool(
                    set_memory,
                    ctx,
                    key=f"gemini_test_{i}",
                    value="gemini_test_value",
                    metadata=metadata,
                )
                assert memory_result["success"] is True

    @pytest.mark.asyncio
    async def test_error_messages_are_clear_and_actionable(self, isolated_db):
        """Test that error messages for invalid metadata are clear and actionable."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_errors", "test_agent_errors")

            # Test with string metadata (should be rejected with stricter validation)
            session_result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Error message clarity test",
                metadata="invalid_string_metadata",
            )

            # Should have clear error message indicating validation failure
            assert session_result["success"] is False or "error" in session_result

            # Check that error contains helpful information about validation
            error_msg = str(session_result)
            assert any(
                keyword in error_msg.lower()
                for keyword in [
                    "metadata",
                    "dict",
                    "object",
                    "type",
                    "validation",
                    "input",
                ]
            )

    @pytest.mark.asyncio
    async def test_metadata_validation_performance(self, isolated_db):
        """Test that metadata validation doesn't introduce significant performance overhead."""
        with patch_database_for_test(isolated_db):
            ctx = MockContext("test_perf", "test_agent_perf")

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
                session_result = await call_fastmcp_tool(
                    create_session,
                    ctx,
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
