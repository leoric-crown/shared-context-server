#!/usr/bin/env python3
"""
Database connection pattern analysis for performance regression investigation.
"""

import asyncio
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Suppress logging
logging.getLogger().setLevel(logging.CRITICAL)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def analyze_database_connection_patterns():
    """Analyze database connection patterns in modularized vs direct access."""
    print("=== DATABASE CONNECTION PATTERN ANALYSIS ===")

    # Setup environment
    os.environ["API_KEY"] = "test-key-for-db-performance-testing"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"
    os.environ["JWT_ENCRYPTION_KEY"] = "test-encryption-key-32-characters-long"
    os.environ["USE_SQLALCHEMY"] = "false"

    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    try:
        print("\n1. Direct Database Access Pattern")
        start = time.perf_counter()

        # Import database directly
        from shared_context_server.database import (
            get_db_connection,
            initialize_database,
        )

        import_time = (time.perf_counter() - start) * 1000
        print(f"Direct database import: {import_time:.2f}ms")

        # Initialize database
        start_init = time.perf_counter()
        await initialize_database()
        init_time = (time.perf_counter() - start_init) * 1000
        print(f"Database initialization: {init_time:.2f}ms")

        # Test direct connection operations
        print("\n--- Direct Connection Operations ---")
        connection_times = []
        for i in range(5):
            start_conn = time.perf_counter()
            async with get_db_connection() as db:
                await db.execute("SELECT 1")
            conn_time = (time.perf_counter() - start_conn) * 1000
            connection_times.append(conn_time)
            print(f"Connection {i + 1}: {conn_time:.2f}ms")

        avg_conn_direct = sum(connection_times) / len(connection_times)
        print(f"Average direct connection: {avg_conn_direct:.2f}ms")

        print("\n2. Module-Based Access Pattern")

        # Import through memory tools module
        start_module = time.perf_counter()
        from shared_context_server.auth_tools import authenticate_agent
        from shared_context_server.memory_tools import set_memory

        module_import_time = (time.perf_counter() - start_module) * 1000
        print(f"Memory tools module import: {module_import_time:.2f}ms")

        # Test module-based database operations
        print("\n--- Module-Based Operations ---")

        # Get auth token
        start_auth = time.perf_counter()
        token_response = await authenticate_agent.tool_impl(
            None, agent_id="test_agent", agent_type="admin"
        )
        auth_time = (time.perf_counter() - start_auth) * 1000
        print(f"Authentication: {auth_time:.2f}ms")

        # Test memory operations (which use database internally)
        memory_times = []
        for i in range(5):
            start_mem = time.perf_counter()
            await set_memory.tool_impl(
                None,
                key=f"test_key_{i}",
                value=f"test_value_{i}",
                auth_token=token_response["token"],
            )
            mem_time = (time.perf_counter() - start_mem) * 1000
            memory_times.append(mem_time)
            print(f"Memory operation {i + 1}: {mem_time:.2f}ms")

        avg_mem_module = sum(memory_times) / len(memory_times)
        print(f"Average module memory op: {avg_mem_module:.2f}ms")

        print("\n3. Connection Pool Analysis")

        # Test concurrent connections
        print("\n--- Concurrent Connection Test ---")

        async def test_concurrent_connection():
            start = time.perf_counter()
            async with get_db_connection() as db:
                await db.execute("SELECT 1")
            return (time.perf_counter() - start) * 1000

        # Run 10 concurrent connections
        start_concurrent = time.perf_counter()
        concurrent_times = await asyncio.gather(
            *[test_concurrent_connection() for _ in range(10)]
        )
        total_concurrent_time = (time.perf_counter() - start_concurrent) * 1000

        print(f"10 concurrent connections total: {total_concurrent_time:.2f}ms")
        print(
            f"Average per connection: {sum(concurrent_times) / len(concurrent_times):.2f}ms"
        )
        print(f"Min: {min(concurrent_times):.2f}ms, Max: {max(concurrent_times):.2f}ms")

        return {
            "direct_import": import_time,
            "db_init": init_time,
            "avg_direct_conn": avg_conn_direct,
            "module_import": module_import_time,
            "auth_time": auth_time,
            "avg_module_mem": avg_mem_module,
            "concurrent_total": total_concurrent_time,
            "concurrent_avg": sum(concurrent_times) / len(concurrent_times),
        }

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def analyze_tool_registration_overhead():
    """Analyze FastMCP tool registration timing across modules."""
    print("\n=== FASTMCP TOOL REGISTRATION ANALYSIS ===")

    # Test individual module tool registration
    modules_and_tools = [
        ("auth_tools", ["authenticate_agent", "refresh_token"]),
        (
            "session_tools",
            ["create_session", "add_message", "get_session", "get_messages"],
        ),
        ("memory_tools", ["set_memory", "get_memory", "list_memory"]),
        ("search_tools", ["search_context", "search_by_sender", "search_by_timerange"]),
        ("admin_tools", ["get_performance_metrics", "get_usage_guidance"]),
    ]

    total_registration_time = 0

    for module_name, tools in modules_and_tools:
        start = time.perf_counter()

        # Import the module (which triggers tool registration)
        module = __import__(
            f"shared_context_server.{module_name}", fromlist=[module_name]
        )

        registration_time = (time.perf_counter() - start) * 1000
        total_registration_time += registration_time

        print(f"{module_name:15} ({len(tools)} tools): {registration_time:.2f}ms")

    print(f"{'Total registration':15}: {total_registration_time:.2f}ms")

    return total_registration_time


async def main():
    """Run database and tool registration analysis."""
    print("DATABASE PATTERNS & TOOL REGISTRATION PERFORMANCE ANALYSIS")
    print("=" * 70)

    # Database connection analysis
    db_results = await analyze_database_connection_patterns()

    # Tool registration analysis
    registration_time = await analyze_tool_registration_overhead()

    print("\n=== ANALYSIS SUMMARY ===")
    print(
        f"Direct database operations:  {db_results['avg_direct_conn']:.2f}ms per connection"
    )
    print(
        f"Module memory operations:    {db_results['avg_module_mem']:.2f}ms per operation"
    )
    print(
        f"Database vs memory overhead: {db_results['avg_module_mem'] - db_results['avg_direct_conn']:+.2f}ms"
    )
    print(f"Tool registration overhead:  {registration_time:.2f}ms total")

    # Performance impact assessment
    memory_overhead = db_results["avg_module_mem"] - db_results["avg_direct_conn"]
    print("\n=== PERFORMANCE IMPACT ===")

    if memory_overhead > 20:
        print(f"❌ HIGH OVERHEAD: {memory_overhead:.2f}ms per memory operation")
        print("   This explains significant performance regression")
    elif memory_overhead > 5:
        print(f"⚠️  MODERATE OVERHEAD: {memory_overhead:.2f}ms per memory operation")
    else:
        print(f"✅ LOW OVERHEAD: {memory_overhead:.2f}ms per memory operation")

    if registration_time > 100:
        print(f"❌ SLOW REGISTRATION: {registration_time:.2f}ms for all tools")
    elif registration_time > 50:
        print(f"⚠️  MODERATE REGISTRATION: {registration_time:.2f}ms for all tools")
    else:
        print(f"✅ FAST REGISTRATION: {registration_time:.2f}ms for all tools")


if __name__ == "__main__":
    asyncio.run(main())
