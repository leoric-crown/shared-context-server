#!/usr/bin/env python3
"""
Memory tools performance isolation testing.
Tests memory operations directly vs through facade to identify bottlenecks.
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_memory_operation_direct():
    """Test memory operations by importing memory_tools directly."""
    # Set up test environment
    os.environ["API_KEY"] = "test-key-123"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"
    os.environ["JWT_ENCRYPTION_KEY"] = "test-encryption-key-32-characters"

    # Use temporary database with SQLite URL format
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["USE_SQLALCHEMY"] = "false"  # Use aiosqlite backend

    try:
        print("=== DIRECT MEMORY TOOLS IMPORT TEST ===")
        start_import = time.perf_counter()

        # Import memory tools directly (not through facade)
        from shared_context_server.auth_tools import authenticate_agent
        from shared_context_server.database import initialize_database
        from shared_context_server.memory_tools import get_memory, set_memory

        import_time = (time.perf_counter() - start_import) * 1000
        print(f"Direct import time: {import_time:.2f}ms")

        # Initialize database
        start_db = time.perf_counter()
        await initialize_database()
        db_time = (time.perf_counter() - start_db) * 1000
        print(f"Database init time: {db_time:.2f}ms")

        # Get authentication context
        start_auth = time.perf_counter()

        # Create mock context - using None for simplicity in testing
        context = None  # FastMCP tools can handle None context in test scenarios

        # Mock authenticate_agent response
        token_response = await authenticate_agent.tool_impl(
            context, agent_id="test_agent", agent_type="admin"
        )
        auth_time = (time.perf_counter() - start_auth) * 1000
        print(f"Auth setup time: {auth_time:.2f}ms")

        # Test memory operations
        print("\n--- Memory Operations Performance ---")

        # Test set_memory
        start_set = time.perf_counter()
        await set_memory.tool_impl(
            context,
            key="test_key",
            value="test_value",
            auth_token=token_response["token"],
        )
        set_time = (time.perf_counter() - start_set) * 1000
        print(f"set_memory time: {set_time:.2f}ms")

        # Test get_memory
        start_get = time.perf_counter()
        await get_memory.tool_impl(
            context, key="test_key", auth_token=token_response["token"]
        )
        get_time = (time.perf_counter() - start_get) * 1000
        print(f"get_memory time: {get_time:.2f}ms")

        total_operation_time = set_time + get_time
        print(f"Total memory ops: {total_operation_time:.2f}ms")

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


async def test_memory_operation_facade():
    """Test memory operations through server facade import."""
    # Set up test environment
    os.environ["API_KEY"] = "test-key-123"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"
    os.environ["JWT_ENCRYPTION_KEY"] = "test-encryption-key-32-characters"

    # Use temporary database with SQLite URL format
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["USE_SQLALCHEMY"] = "false"  # Use aiosqlite backend

    try:
        print("\n=== FACADE MEMORY TOOLS IMPORT TEST ===")
        start_import = time.perf_counter()

        # Import through server facade
        from shared_context_server.server import (
            authenticate_agent,
            get_memory,
            initialize_database,
            set_memory,
        )

        import_time = (time.perf_counter() - start_import) * 1000
        print(f"Facade import time: {import_time:.2f}ms")

        # Initialize database
        start_db = time.perf_counter()
        await initialize_database()
        db_time = (time.perf_counter() - start_db) * 1000
        print(f"Database init time: {db_time:.2f}ms")

        # Get authentication context
        start_auth = time.perf_counter()

        # Create mock context - using None for simplicity in testing
        context = None  # FastMCP tools can handle None context in test scenarios

        # Mock authenticate_agent response
        token_response = await authenticate_agent.tool_impl(
            context, agent_id="test_agent", agent_type="admin"
        )
        auth_time = (time.perf_counter() - start_auth) * 1000
        print(f"Auth setup time: {auth_time:.2f}ms")

        # Test memory operations
        print("\n--- Memory Operations Performance ---")

        # Test set_memory
        start_set = time.perf_counter()
        await set_memory.tool_impl(
            context,
            key="test_key",
            value="test_value",
            auth_token=token_response["token"],
        )
        set_time = (time.perf_counter() - start_set) * 1000
        print(f"set_memory time: {set_time:.2f}ms")

        # Test get_memory
        start_get = time.perf_counter()
        await get_memory.tool_impl(
            context, key="test_key", auth_token=token_response["token"]
        )
        get_time = (time.perf_counter() - start_get) * 1000
        print(f"get_memory time: {get_time:.2f}ms")

        total_operation_time = set_time + get_time
        print(f"Total memory ops: {total_operation_time:.2f}ms")

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


async def main():
    """Run memory tools performance comparison."""
    print("MEMORY TOOLS PERFORMANCE ISOLATION TEST")
    print("=" * 60)

    # Test direct import
    direct_results = await test_memory_operation_direct()

    # Test facade import
    facade_results = await test_memory_operation_facade()

    # Comparison analysis
    print("\n=== PERFORMANCE COMPARISON ===")
    print(
        f"Import overhead (facade vs direct): {facade_results['import_time'] - direct_results['import_time']:+.2f}ms"
    )
    print(
        f"Database init difference: {facade_results['db_time'] - direct_results['db_time']:+.2f}ms"
    )
    print(
        f"Auth setup difference: {facade_results['auth_time'] - direct_results['auth_time']:+.2f}ms"
    )
    print(
        f"set_memory difference: {facade_results['set_time'] - direct_results['set_time']:+.2f}ms"
    )
    print(
        f"get_memory difference: {facade_results['get_time'] - direct_results['get_time']:+.2f}ms"
    )
    print(
        f"Total ops difference: {facade_results['total_ops'] - direct_results['total_ops']:+.2f}ms"
    )

    # Performance targets check
    print("\n=== PERFORMANCE TARGET ANALYSIS ===")
    memory_target = 50.0  # 50ms target from requirements

    print(
        f"Direct memory ops: {direct_results['total_ops']:.2f}ms ({'✅ PASS' if direct_results['total_ops'] <= memory_target else '❌ FAIL'})"
    )
    print(
        f"Facade memory ops: {facade_results['total_ops']:.2f}ms ({'✅ PASS' if facade_results['total_ops'] <= memory_target else '❌ FAIL'})"
    )

    if facade_results["total_ops"] > memory_target:
        overage = facade_results["total_ops"] - memory_target
        percentage = (overage / memory_target) * 100
        print(f"⚠️  Facade exceeds target by {overage:.2f}ms ({percentage:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
