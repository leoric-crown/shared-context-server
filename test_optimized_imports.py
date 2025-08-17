#!/usr/bin/env python3
"""
Test a more comprehensive lazy loading approach for memory_tools.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_incremental_optimization():
    """Test memory_tools with progressive import optimization."""
    print("TESTING INCREMENTAL IMPORT OPTIMIZATION")
    print("=" * 50)

    # Test 1: Basic imports only (no database/auth)
    start_time = time.perf_counter()

    basic_time = (time.perf_counter() - start_time) * 1000
    print(f"Basic imports:        {basic_time:.2f}ms")

    # Test 2: Add models and utils
    start_time = time.perf_counter()

    models_time = (time.perf_counter() - start_time) * 1000
    print(f"Models/utils imports: {models_time:.2f}ms")

    # Test 3: Add database (but not auth yet)
    start_time = time.perf_counter()

    db_time = (time.perf_counter() - start_time) * 1000
    print(f"Database import:      {db_time:.2f}ms")

    # Test 4: Add auth (expensive)
    start_time = time.perf_counter()

    auth_time = (time.perf_counter() - start_time) * 1000
    print(f"Auth import:          {auth_time:.2f}ms")

    # Test 5: Add FastMCP context
    start_time = time.perf_counter()

    fastmcp_time = (time.perf_counter() - start_time) * 1000
    print(f"FastMCP Context:      {fastmcp_time:.2f}ms")

    # Test 6: Add core server (MCP tools)
    start_time = time.perf_counter()

    core_server_time = (time.perf_counter() - start_time) * 1000
    print(f"Core server (MCP):    {core_server_time:.2f}ms")

    total_incremental = (
        basic_time + models_time + db_time + auth_time + fastmcp_time + core_server_time
    )

    print(f"\nTotal incremental:    {total_incremental:.2f}ms")

    # Test 7: Full memory_tools import for comparison
    # (In a new process to avoid cache effects)
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'src'); import time; start=time.perf_counter(); from shared_context_server.memory_tools import set_memory; print(f'RESULT:{(time.perf_counter()-start)*1000:.2f}')",
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    if result.returncode == 0 and "RESULT:" in result.stdout:
        actual_time = float(result.stdout.split("RESULT:")[1].strip())
        print(f"Actual memory_tools:  {actual_time:.2f}ms")
        print(f"Difference:           {actual_time - total_incremental:.2f}ms")
    else:
        print(f"Failed to measure actual: {result.stderr}")


if __name__ == "__main__":
    test_incremental_optimization()
