#!/usr/bin/env python3
"""
Test the actual memory operation execution time (not import time).
This focuses on the reported 2,600ms vs 10ms target issue.
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_actual_memory_operations():
    """Test the actual runtime performance of memory operations."""
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
    os.environ["USE_SQLALCHEMY"] = "false"  # Use aiosqlite backend

    try:
        print("MEMORY OPERATION EXECUTION TIME TEST")
        print("=" * 50)

        # Import after environment setup
        start_import = time.perf_counter()

        from shared_context_server.server import (
            authenticate_agent,
            get_memory,
            initialize_database,
            set_memory,
        )

        import_time = (time.perf_counter() - start_import) * 1000
        print(f"Import time: {import_time:.2f}ms")

        # Initialize database
        start_db = time.perf_counter()
        await initialize_database()
        db_time = (time.perf_counter() - start_db) * 1000
        print(f"Database init: {db_time:.2f}ms")

        # Get auth token
        start_auth = time.perf_counter()
        token_response = await authenticate_agent(
            ctx=None, agent_id="test_agent", agent_type="admin"
        )
        auth_time = (time.perf_counter() - start_auth) * 1000
        print(f"Auth token creation: {auth_time:.2f}ms")

        if not token_response.get("success"):
            print(f"❌ Auth failed: {token_response}")
            return None

        token = token_response["token"]

        # Test actual memory operations (this is what should be <10ms)
        print("\n--- MEMORY OPERATION TIMING ---")

        # Test set_memory operation
        start_set = time.perf_counter()
        set_result = await set_memory(
            ctx=None, key="test_key", value="test_value", auth_token=token
        )
        set_time = (time.perf_counter() - start_set) * 1000
        print(f"set_memory execution: {set_time:.2f}ms")

        if not set_result.get("success"):
            print(f"❌ set_memory failed: {set_result}")
            return None

        # Test get_memory operation
        start_get = time.perf_counter()
        get_result = await get_memory(ctx=None, key="test_key", auth_token=token)
        get_time = (time.perf_counter() - start_get) * 1000
        print(f"get_memory execution: {get_time:.2f}ms")

        if not get_result.get("success"):
            print(f"❌ get_memory failed: {get_result}")
            return None

        total_operation_time = set_time + get_time
        print(f"Total memory ops: {total_operation_time:.2f}ms")

        # Performance analysis
        print("\n--- PERFORMANCE ANALYSIS ---")
        target_time = 10.0  # 10ms target from requirements

        if total_operation_time <= target_time:
            print(
                f"✅ PASS: Memory operations ({total_operation_time:.2f}ms) within {target_time}ms target"
            )
        else:
            overage = total_operation_time - target_time
            ratio = total_operation_time / target_time
            print(
                f"❌ FAIL: Memory operations ({total_operation_time:.2f}ms) exceed {target_time}ms target"
            )
            print(f"   Overage: {overage:.2f}ms ({ratio:.1f}x over target)")

        if total_operation_time >= 2600:
            print("🚨 CRITICAL: Approaching 2,600ms regression level!")

        return {
            "import_time": import_time,
            "db_time": db_time,
            "auth_time": auth_time,
            "set_time": set_time,
            "get_time": get_time,
            "total_ops": total_operation_time,
        }

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    asyncio.run(test_actual_memory_operations())
