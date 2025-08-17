#!/usr/bin/env python3
"""
Test import performance of memory functions without MCP decorators.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_core_imports():
    """Test just the core dependencies without MCP stuff."""
    print("Testing core memory dependencies...")

    start_time = time.perf_counter()

    # Import just the core parts needed for memory logic

    import_time = (time.perf_counter() - start_time) * 1000
    print(f"Core dependencies: {import_time:.2f}ms")

    return import_time


def test_local_imports():
    """Test local shared_context_server imports."""
    print("Testing local dependencies...")

    start_time = time.perf_counter()

    # Import the local modules that memory_tools needs (without MCP)

    import_time = (time.perf_counter() - start_time) * 1000
    print(f"Local dependencies: {import_time:.2f}ms")

    return import_time


def test_auth_import():
    """Test auth import separately."""
    print("Testing auth import...")

    start_time = time.perf_counter()

    import_time = (time.perf_counter() - start_time) * 1000
    print(f"Auth import: {import_time:.2f}ms")

    return import_time


def test_mcp_import():
    """Test MCP core server import."""
    print("Testing MCP core server import...")

    start_time = time.perf_counter()

    import_time = (time.perf_counter() - start_time) * 1000
    print(f"MCP core server: {import_time:.2f}ms")

    return import_time


if __name__ == "__main__":
    print("MEMORY FUNCTIONS IMPORT BREAKDOWN")
    print("=" * 50)

    core_time = test_core_imports()
    local_time = test_local_imports()
    auth_time = test_auth_import()
    mcp_time = test_mcp_import()

    total_time = core_time + local_time + auth_time + mcp_time

    print("\nSUMMARY:")
    print(f"Core dependencies:  {core_time:.2f}ms")
    print(f"Local dependencies: {local_time:.2f}ms")
    print(f"Auth import:        {auth_time:.2f}ms")
    print(f"MCP core server:    {mcp_time:.2f}ms")
    print(f"TOTAL:              {total_time:.2f}ms")

    if mcp_time > 50:
        print(f"\n⚠️ MCP import ({mcp_time:.2f}ms) is the major bottleneck")
