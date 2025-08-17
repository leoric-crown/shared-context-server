#!/usr/bin/env python3
"""
Test that memory functions work correctly after lazy loading changes.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_memory_functions():
    """Test that memory tools work after lazy loading optimization."""
    # Set up test environment
    os.environ["API_KEY"] = "test-key-123456789012345678901234567890123456"  # 32+ chars
    os.environ["JWT_SECRET_KEY"] = (
        "test-jwt-secret-key-for-testing-only-12345678901234567890"
    )
    os.environ["JWT_ENCRYPTION_KEY"] = (
        "test-encryption-key-32-characters-long-for-jwt-encryption"
    )

    # Use temporary database
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["USE_SQLALCHEMY"] = "false"

    try:
        print("MEMORY FUNCTIONALITY TEST")
        print("=" * 30)

        # Import with lazy loading
        from shared_context_server.auth_tools import authenticate_agent
        from shared_context_server.database import initialize_database
        from shared_context_server.memory_tools import get_memory, set_memory

        # Initialize
        await initialize_database()

        # Get auth token
        token_result = await authenticate_agent(
            ctx=None, agent_id="test_agent", agent_type="admin"
        )
        print(f"Auth result: {token_result}")

        if not token_result.get("success"):
            print(f"❌ Authentication failed: {token_result}")
            return False

        token = token_result["token"]

        # Test set_memory
        set_result = await set_memory(
            ctx=None, key="test_key", value="test_value", auth_token=token
        )
        print(f"Set result: {set_result}")

        if not set_result.get("success"):
            print(f"❌ set_memory failed: {set_result}")
            return False

        # Test get_memory
        get_result = await get_memory(ctx=None, key="test_key", auth_token=token)
        print(f"Get result: {get_result}")

        if not get_result.get("success"):
            print(f"❌ get_memory failed: {get_result}")
            return False

        # Check value
        if get_result.get("value") != "test_value":
            print(
                f"❌ Value mismatch: expected 'test_value', got {get_result.get('value')}"
            )
            return False

        print("✅ All memory functions working correctly!")
        return True

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    success = asyncio.run(test_memory_functions())
    if success:
        print("\n🎉 LAZY LOADING PRESERVES FUNCTIONALITY")
    else:
        print("\n💥 LAZY LOADING BROKE FUNCTIONALITY")
