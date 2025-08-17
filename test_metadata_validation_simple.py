#!/usr/bin/env python3
"""
Streamlined Metadata Validation Fix Testing

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

# Set environment variables before importing the server
os.environ["JWT_SECRET_KEY"] = (
    "test-secret-key-that-is-long-enough-for-testing-purposes"
)
os.environ["JWT_ENCRYPTION_KEY"] = "test-fernet-key-32-bytes-needed!!!"
os.environ["DISABLE_WEBSOCKET_FOR_TESTS"] = "true"

from src.shared_context_server.auth import AuthInfo
from src.shared_context_server.database import initialize_database
from src.shared_context_server.memory_tools import set_memory
from src.shared_context_server.session_tools import add_message, create_session


class MockContext:
    """Mock context for FastMCP testing."""

    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        # Set up authentication using AuthInfo pattern
        self._auth_info = AuthInfo(
            jwt_validated=False,
            agent_id=agent_id,
            agent_type="claude",
            permissions=["read", "write"],
            authenticated=True,
            raw_agent_id=agent_id,
        )

    def get_auth_info(self):
        return self._auth_info


async def test_metadata_validation_comprehensive():
    """Comprehensive test of metadata validation fix."""
    print("🔍 STARTING COMPREHENSIVE METADATA VALIDATION TESTING")
    print("=" * 60)

    # Setup test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        test_db_path = db_file.name
        os.environ["DATABASE_URL"] = test_db_path

        try:
            await initialize_database(test_db_path, reset=True)

            # Create test context
            ctx = MockContext("test_session_meta", "scs_tester_1200")

            print("\n📋 CREATE_SESSION METADATA TESTS")
            print("-" * 40)

            # Test 1: Object metadata (backward compatibility)
            test_cases = [
                {"test": "value"},
                {"key": "string", "number": 42, "bool": True},
                {"nested": {"deep": {"value": "test"}}},
                {"array": [1, 2, 3]},
                {"complex": {"version": "1.0", "features": ["auth", "sessions"]}},
            ]

            for i, metadata in enumerate(test_cases):
                result = await create_session(
                    ctx=ctx,
                    purpose=f"Test session with object metadata {i}",
                    metadata=metadata,
                )

                if result.get("success"):
                    print(f"  ✅ Object metadata test {i} passed: {metadata}")
                else:
                    print(f"  ❌ Object metadata test {i} failed: {result}")
                    return False

            # Test 2: Null metadata (backward compatibility)
            result = await create_session(
                ctx=ctx, purpose="Test session with null metadata", metadata=None
            )

            if result.get("success"):
                print("  ✅ Null metadata test passed")
            else:
                print(f"  ❌ Null metadata test failed: {result}")
                return False

            # Test 3: Invalid metadata rejection
            invalid_cases = ["string_metadata", 42, ["array", "metadata"], True]

            for metadata in invalid_cases:
                result = await create_session(
                    ctx=ctx,
                    purpose="Test session with invalid metadata",
                    metadata=metadata,
                )

                # Should fail with validation error
                if not result.get("success") or "error" in result:
                    print(
                        f"  ✅ Invalid metadata rejected: {type(metadata).__name__} = {metadata}"
                    )
                else:
                    print(f"  ❌ Invalid metadata incorrectly accepted: {metadata}")
                    return False

            print("\n📋 ADD_MESSAGE METADATA TESTS")
            print("-" * 40)

            # Create a session first
            session_result = await create_session(
                ctx=ctx,
                purpose="Test session for message metadata",
                metadata={"test_purpose": "message_metadata_validation"},
            )
            session_id = session_result["session_id"]

            # Test message metadata
            message_test_cases = [
                {"message_type": "test", "priority": "high"},
                {"user_id": 123, "timestamp": "2024-01-01T00:00:00Z"},
                {"tags": ["testing", "metadata"], "source": "automated_test"},
            ]

            for i, metadata in enumerate(message_test_cases):
                result = await add_message(
                    ctx=ctx,
                    session_id=session_id,
                    content=f"Test message {i} with object metadata",
                    metadata=metadata,
                )

                if result.get("success"):
                    print(f"  ✅ Message object metadata test {i} passed: {metadata}")
                else:
                    print(f"  ❌ Message object metadata test {i} failed: {result}")
                    return False

            # Test message null metadata
            result = await add_message(
                ctx=ctx,
                session_id=session_id,
                content="Test message with null metadata",
                metadata=None,
            )

            if result.get("success"):
                print("  ✅ Message null metadata test passed")
            else:
                print(f"  ❌ Message null metadata test failed: {result}")
                return False

            # Test message invalid metadata
            for metadata in invalid_cases:
                result = await add_message(
                    ctx=ctx,
                    session_id=session_id,
                    content="Test message with invalid metadata",
                    metadata=metadata,
                )

                if not result.get("success") or "error" in result:
                    print(
                        f"  ✅ Message invalid metadata rejected: {type(metadata).__name__} = {metadata}"
                    )
                else:
                    print(
                        f"  ❌ Message invalid metadata incorrectly accepted: {metadata}"
                    )
                    return False

            print("\n📋 SET_MEMORY METADATA TESTS")
            print("-" * 40)

            # Test memory metadata
            memory_test_cases = [
                {"source": "user_input", "tags": ["important"]},
                {"created_by": "test_agent", "version": 1},
                {"config": {"auto_save": True, "expiry": 3600}},
            ]

            for i, metadata in enumerate(memory_test_cases):
                result = await set_memory(
                    ctx=ctx,
                    key=f"test_memory_metadata_{i}",
                    value=f"Test value {i}",
                    metadata=metadata,
                )

                if result.get("success"):
                    print(f"  ✅ Memory object metadata test {i} passed: {metadata}")
                else:
                    print(f"  ❌ Memory object metadata test {i} failed: {result}")
                    return False

            # Test memory null metadata
            result = await set_memory(
                ctx=ctx,
                key="test_memory_null_metadata",
                value="Test value with null metadata",
                metadata=None,
            )

            if result.get("success"):
                print("  ✅ Memory null metadata test passed")
            else:
                print(f"  ❌ Memory null metadata test failed: {result}")
                return False

            # Test memory invalid metadata
            for i, metadata in enumerate(invalid_cases):
                result = await set_memory(
                    ctx=ctx,
                    key=f"test_memory_invalid_{i}",
                    value="Test value",
                    metadata=metadata,
                )

                if not result.get("success") or "error" in result:
                    print(
                        f"  ✅ Memory invalid metadata rejected: {type(metadata).__name__} = {metadata}"
                    )
                else:
                    print(
                        f"  ❌ Memory invalid metadata incorrectly accepted: {metadata}"
                    )
                    return False

            print("\n📋 INTEGRATION WORKFLOW TEST")
            print("-" * 40)

            # Full workflow test
            workflow_session_result = await create_session(
                ctx=ctx,
                purpose="Full workflow test",
                metadata={"workflow": "test", "version": "1.0"},
            )

            if not workflow_session_result.get("success"):
                print(
                    f"  ❌ Workflow session creation failed: {workflow_session_result}"
                )
                return False

            workflow_session_id = workflow_session_result["session_id"]

            workflow_message_result = await add_message(
                ctx=ctx,
                session_id=workflow_session_id,
                content="Test message in full workflow",
                metadata={"step": "message_creation", "data": {"test": True}},
            )

            if not workflow_message_result.get("success"):
                print(
                    f"  ❌ Workflow message creation failed: {workflow_message_result}"
                )
                return False

            workflow_memory_result = await set_memory(
                ctx=ctx,
                key="workflow_memory",
                value={
                    "session_id": workflow_session_id,
                    "completed_steps": ["session", "message"],
                },
                metadata={"workflow_step": "memory_storage", "priority": "high"},
                session_id=workflow_session_id,
            )

            if workflow_memory_result.get("success"):
                print("  ✅ Full workflow with metadata passed all steps")
            else:
                print(f"  ❌ Workflow memory creation failed: {workflow_memory_result}")
                return False

            print("\n" + "=" * 60)
            print("🎉 ALL METADATA VALIDATION TESTS PASSED!")
            print("✅ Metadata validation fix is working correctly")
            print("✅ Backward compatibility maintained")
            print("✅ Invalid inputs properly rejected")
            print("✅ Gemini API compatibility preserved")
            print("=" * 60)

            return True

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR during testing: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)


async def test_gemini_compatibility_edge_cases():
    """Test specific Gemini API compatibility edge cases."""
    print("\n🔍 TESTING GEMINI API COMPATIBILITY EDGE CASES")
    print("-" * 50)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        test_db_path = db_file.name
        os.environ["DATABASE_URL"] = test_db_path

        try:
            await initialize_database(test_db_path, reset=True)
            ctx = MockContext("gemini_test_session", "gemini_tester")

            # Test various object structures that should work with Gemini
            gemini_test_cases = [
                {"api_version": "v1", "model": "gemini-pro"},
                {"request_id": "test-123", "parameters": {"temperature": 0.7}},
                {"conversation": {"turns": 5, "context": "testing"}},
                {},  # Empty object
                {"unicode": "émojis 🎉 ànd spéciál chars"},  # Unicode content
            ]

            for i, metadata in enumerate(gemini_test_cases):
                # Test create_session
                session_result = await create_session(
                    ctx=ctx, purpose=f"Gemini compatibility test {i}", metadata=metadata
                )

                if not session_result.get("success"):
                    print(f"  ❌ Gemini session test {i} failed: {session_result}")
                    return False

                print(f"  ✅ Gemini test {i} passed: {metadata}")

            print("✅ All Gemini API compatibility tests passed")
            return True

        finally:
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)


if __name__ == "__main__":

    async def main():
        success1 = await test_metadata_validation_comprehensive()
        success2 = await test_gemini_compatibility_edge_cases()

        if success1 and success2:
            print("\n🎊 COMPREHENSIVE TESTING COMPLETE - ALL TESTS PASSED")
            return True
        print("\n⚠️ SOME TESTS FAILED - REVIEW REQUIRED")
        return False

    result = asyncio.run(main())
    exit(0 if result else 1)
