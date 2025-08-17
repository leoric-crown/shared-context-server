#!/usr/bin/env python3
"""
Direct Metadata Validation Testing

Direct test of the metadata validation fix by calling the tools directly
and checking validation behavior.
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


async def test_metadata_validation_direct():
    """Direct test of metadata validation."""
    print("🔍 DIRECT METADATA VALIDATION TESTING")
    print("=" * 50)

    # Setup test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        test_db_path = db_file.name
        os.environ["DATABASE_URL"] = test_db_path

        try:
            # Initialize database
            await initialize_database()

            # Create test context
            ctx = MockContext("test_session", "tester_agent")

            print("\n📋 Testing create_session with object metadata")

            # Test 1: Valid object metadata
            result = await create_session(
                ctx=ctx,
                purpose="Test session with valid object metadata",
                metadata={"test": "value", "number": 42},
            )

            print(f"  Object metadata result: {result}")

            if result.get("success"):
                print("  ✅ Object metadata accepted")
            else:
                print("  ❌ Object metadata rejected")
                return False

            # Test 2: Valid null metadata
            result = await create_session(
                ctx=ctx, purpose="Test session with null metadata", metadata=None
            )

            print(f"  Null metadata result: {result}")

            if result.get("success"):
                print("  ✅ Null metadata accepted")
            else:
                print("  ❌ Null metadata rejected")
                return False

            # Test 3: Invalid string metadata (should be rejected)
            result = await create_session(
                ctx=ctx,
                purpose="Test session with invalid string metadata",
                metadata="invalid_string",
            )

            print(f"  String metadata result: {result}")

            if not result.get("success") or "error" in result:
                print("  ✅ String metadata correctly rejected")
            else:
                print("  ❌ String metadata incorrectly accepted")
                return False

            # Test 4: Invalid array metadata (should be rejected)
            result = await create_session(
                ctx=ctx,
                purpose="Test session with invalid array metadata",
                metadata=["invalid", "array"],
            )

            print(f"  Array metadata result: {result}")

            if not result.get("success") or "error" in result:
                print("  ✅ Array metadata correctly rejected")
            else:
                print("  ❌ Array metadata incorrectly accepted")
                return False

            print("\n📋 Testing add_message with metadata")

            # First create a session for messages
            session_result = await create_session(
                ctx=ctx,
                purpose="Session for message testing",
                metadata={"purpose": "message_testing"},
            )

            if not session_result.get("success"):
                print("  ❌ Could not create session for message testing")
                return False

            session_id = session_result["session_id"]

            # Test valid message metadata
            result = await add_message(
                ctx=ctx,
                session_id=session_id,
                content="Test message with valid metadata",
                metadata={"message_type": "test", "priority": "high"},
            )

            print(f"  Message object metadata result: {result}")

            if result.get("success"):
                print("  ✅ Message object metadata accepted")
            else:
                print("  ❌ Message object metadata rejected")
                return False

            # Test invalid message metadata
            result = await add_message(
                ctx=ctx,
                session_id=session_id,
                content="Test message with invalid metadata",
                metadata="invalid_string_metadata",
            )

            print(f"  Message string metadata result: {result}")

            if not result.get("success") or "error" in result:
                print("  ✅ Message string metadata correctly rejected")
            else:
                print("  ❌ Message string metadata incorrectly accepted")
                return False

            print("\n📋 Testing set_memory with metadata")

            # Test valid memory metadata
            result = await set_memory(
                ctx=ctx,
                key="test_memory_key",
                value="test_value",
                metadata={"source": "test", "tags": ["important"]},
            )

            print(f"  Memory object metadata result: {result}")

            if result.get("success"):
                print("  ✅ Memory object metadata accepted")
            else:
                print("  ❌ Memory object metadata rejected")
                return False

            # Test invalid memory metadata
            result = await set_memory(
                ctx=ctx,
                key="test_memory_key_2",
                value="test_value",
                metadata=42,  # Invalid number metadata
            )

            print(f"  Memory number metadata result: {result}")

            if not result.get("success") or "error" in result:
                print("  ✅ Memory number metadata correctly rejected")
            else:
                print("  ❌ Memory number metadata incorrectly accepted")
                return False

            print("\n" + "=" * 50)
            print("🎉 ALL DIRECT METADATA TESTS PASSED!")
            print("✅ Object metadata works (backward compatibility)")
            print("✅ Null metadata works (backward compatibility)")
            print("✅ Invalid metadata types properly rejected")
            print("✅ Metadata validation fix is working correctly")
            print("=" * 50)

            return True

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)


if __name__ == "__main__":
    result = asyncio.run(test_metadata_validation_direct())
    exit(0 if result else 1)
