#!/usr/bin/env python3
"""
Quick Metadata Validation Test

Quick test of the metadata validation fix using the existing test infrastructure.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import tests.conftest
from shared_context_server.auth import AuthInfo
from shared_context_server.memory_tools import set_memory
from shared_context_server.session_tools import add_message, create_session
from tests.conftest import call_fastmcp_tool
from tests.fixtures.database import patch_database_for_test

# Force pytest setup
tests.conftest._pytest_quiet_mode = True


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
        )

    def get_auth_info(self):
        return self._auth_info


@pytest.fixture
async def isolated_db():
    """Create isolated database for testing."""
    import os
    import tempfile

    from shared_context_server.database import DatabaseManager

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        db_path = db_file.name

    try:
        db_manager = DatabaseManager(database_url=f"sqlite:///{db_path}")
        await db_manager.initialize()
        yield db_manager
    finally:
        await db_manager.close()
        if os.path.exists(db_path):
            os.unlink(db_path)


async def test_metadata_validation_quick():
    """Quick test of metadata validation fix."""
    print("🔍 QUICK METADATA VALIDATION TEST")
    print("=" * 40)

    # Create isolated database
    import os
    import tempfile

    from shared_context_server.database import DatabaseManager

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        db_path = db_file.name

    try:
        db_manager = DatabaseManager(database_url=f"sqlite:///{db_path}")
        await db_manager.initialize()

        with patch_database_for_test(db_manager):
            ctx = MockContext("test_session_quick", "test_agent_quick")

            print("\n📋 Testing create_session with metadata")

            # Test 1: Valid object metadata (MUST work for backward compatibility)
            result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Test session with valid object metadata",
                metadata={"test": "value", "number": 42},
            )

            print(f"  Object metadata result: {result.get('success', False)}")
            assert result["success"] is True, f"Object metadata failed: {result}"

            # Test 2: Valid null metadata
            result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Test session with null metadata",
                metadata=None,
            )

            print(f"  Null metadata result: {result.get('success', False)}")
            assert result["success"] is True, f"Null metadata failed: {result}"

            # Test 3: Invalid string metadata (should fail)
            result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Test session with invalid string metadata",
                metadata="invalid_string",
            )

            print(f"  String metadata result: {result.get('success', True)}")
            assert result["success"] is False or "error" in result, (
                f"String metadata incorrectly accepted: {result}"
            )

            print("\n📋 Testing add_message with metadata")

            # Create session for message testing
            session_result = await call_fastmcp_tool(
                create_session,
                ctx,
                purpose="Session for message testing",
                metadata={"purpose": "message_testing"},
            )
            session_id = session_result["session_id"]

            # Test valid message metadata
            result = await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content="Test message with valid metadata",
                metadata={"message_type": "test", "priority": "high"},
            )

            print(f"  Message object metadata result: {result.get('success', False)}")
            assert result["success"] is True, (
                f"Message object metadata failed: {result}"
            )

            # Test invalid message metadata
            result = await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content="Test message with invalid metadata",
                metadata="invalid_string_metadata",
            )

            print(f"  Message string metadata result: {result.get('success', True)}")
            assert result["success"] is False or "error" in result, (
                f"Message string metadata incorrectly accepted: {result}"
            )

            print("\n📋 Testing set_memory with metadata")

            # Test valid memory metadata
            result = await call_fastmcp_tool(
                set_memory,
                ctx,
                key="test_memory_key",
                value="test_value",
                metadata={"source": "test", "tags": ["important"]},
            )

            print(f"  Memory object metadata result: {result.get('success', False)}")
            assert result["success"] is True, f"Memory object metadata failed: {result}"

            # Test invalid memory metadata
            result = await call_fastmcp_tool(
                set_memory,
                ctx,
                key="test_memory_key_2",
                value="test_value",
                metadata=42,  # Invalid number metadata
            )

            print(f"  Memory number metadata result: {result.get('success', True)}")
            assert result["success"] is False or "error" in result, (
                f"Memory number metadata incorrectly accepted: {result}"
            )

            print("\n" + "=" * 40)
            print("🎉 ALL QUICK METADATA TESTS PASSED!")
            print("✅ Object metadata works (backward compatibility)")
            print("✅ Null metadata works (backward compatibility)")
            print("✅ Invalid metadata types properly rejected")
            print("✅ Metadata validation fix is working correctly")
            print("=" * 40)

            return True

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await db_manager.close()
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    result = asyncio.run(test_metadata_validation_quick())
    exit(0 if result else 1)
