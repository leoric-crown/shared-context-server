#!/usr/bin/env python3
"""
Simple memory tool performance test.
"""

import asyncio
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Suppress all logging
logging.getLogger().setLevel(logging.CRITICAL)
os.environ["PYTHONPATH"] = "."

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def run_failing_tests():
    """Run the specific failing performance tests to measure actual regression."""
    print("=== RUNNING ACTUAL FAILING PERFORMANCE TESTS ===")

    # Test 1: Memory performance requirements test
    print("\n1. Memory Performance Requirements Test:")
    start = time.perf_counter()

    import subprocess

    result = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/integration/test_agent_memory.py::test_memory_performance_requirements",
            "-v",
            "--tb=no",
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    duration = (time.perf_counter() - start) * 1000
    print(f"Test execution time: {duration:.2f}ms")
    print(f"Test result: {'PASS' if result.returncode == 0 else 'FAIL'}")
    if result.returncode != 0:
        # Extract the performance number from the error
        lines = result.stdout.split("\n")
        for line in lines:
            if "took" in line and "expected" in line:
                print(f"Performance details: {line.strip()}")

    # Test 2: API stability validation
    print("\n2. API Stability Validation Test:")
    start = time.perf_counter()

    result2 = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/integration/test_api_stability_validation.py::TestAPIStabilityValidation::test_performance_contract_maintenance",
            "-v",
            "--tb=no",
            "-q",
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    duration2 = (time.perf_counter() - start) * 1000
    print(f"Test execution time: {duration2:.2f}ms")
    print(f"Test result: {'PASS' if result2.returncode == 0 else 'FAIL'}")
    if result2.returncode != 0:
        lines = result2.stdout.split("\n")
        for line in lines:
            if "took" in line and "exceeds" in line:
                print(f"Performance details: {line.strip()}")


async def measure_simple_memory_operations():
    """Measure simple memory operations without full test framework overhead."""
    print("\n=== SIMPLIFIED MEMORY OPERATION MEASUREMENT ===")

    # Setup minimal environment
    os.environ["API_KEY"] = "test-key-for-memory-performance-testing-purposes"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"
    os.environ["JWT_ENCRYPTION_KEY"] = "test-encryption-key-32-characters-long"
    os.environ["USE_SQLALCHEMY"] = "false"

    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    try:
        # Time the import
        start_import = time.perf_counter()
        from shared_context_server.server import (
            authenticate_agent,
            get_memory,
            initialize_database,
            set_memory,
        )

        import_time = (time.perf_counter() - start_import) * 1000
        print(f"Server facade import: {import_time:.2f}ms")

        # Initialize database
        start_db = time.perf_counter()
        await initialize_database()
        db_time = (time.perf_counter() - start_db) * 1000
        print(f"Database initialization: {db_time:.2f}ms")

        # Get JWT token
        start_auth = time.perf_counter()
        token_response = await authenticate_agent.tool_impl(
            None, agent_id="test_agent", agent_type="admin"
        )
        auth_time = (time.perf_counter() - start_auth) * 1000
        print(f"Authentication: {auth_time:.2f}ms")

        # Measure memory operations (multiple iterations)
        print("\n--- Memory Operations (5 iterations) ---")
        set_times = []
        get_times = []

        for i in range(5):
            # Set memory
            start_set = time.perf_counter()
            await set_memory.tool_impl(
                None,
                key=f"test_key_{i}",
                value=f"test_value_{i}",
                auth_token=token_response["token"],
            )
            set_time = (time.perf_counter() - start_set) * 1000
            set_times.append(set_time)

            # Get memory
            start_get = time.perf_counter()
            await get_memory.tool_impl(
                None, key=f"test_key_{i}", auth_token=token_response["token"]
            )
            get_time = (time.perf_counter() - start_get) * 1000
            get_times.append(get_time)

        avg_set = sum(set_times) / len(set_times)
        avg_get = sum(get_times) / len(get_times)
        total_avg = avg_set + avg_get

        print(f"Average set_memory: {avg_set:.2f}ms (target: <50ms)")
        print(f"Average get_memory: {avg_get:.2f}ms (target: <50ms)")
        print(f"Combined operation: {total_avg:.2f}ms")

        # Performance assessment
        if total_avg > 50:
            overage = total_avg - 50
            percentage = (overage / 50) * 100
            print(
                f"❌ PERFORMANCE FAILURE: {overage:.2f}ms over target ({percentage:.1f}% regression)"
            )
        else:
            print("✅ PERFORMANCE PASS: Within 50ms target")

        return {
            "import_time": import_time,
            "db_time": db_time,
            "auth_time": auth_time,
            "avg_set": avg_set,
            "avg_get": avg_get,
            "total_avg": total_avg,
        }

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


async def main():
    """Run performance investigation."""
    print("MEMORY TOOLS PERFORMANCE INVESTIGATION")
    print("=" * 50)

    # Run failing tests first to see actual failure
    await run_failing_tests()

    # Run simplified measurement
    results = await measure_simple_memory_operations()

    print("\n=== SUMMARY ===")
    print(f"Import overhead: {results['import_time']:.2f}ms")
    print(f"Memory operation average: {results['total_avg']:.2f}ms")

    if results["total_avg"] > 50:
        regression_factor = results["total_avg"] / 50
        print(f"Performance regression: {regression_factor:.1f}x over target")


if __name__ == "__main__":
    asyncio.run(main())
