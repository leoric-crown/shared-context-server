#!/usr/bin/env python3
"""
Performance profiling script for import timing analysis.
Measures the import overhead of modularized vs pre-modularization structure.
"""

import subprocess
import sys
from pathlib import Path


def measure_import_time(
    module_path: str, repeat: int = 5
) -> tuple[float, float, float]:
    """Measure import time for a module.

    Returns:
        tuple: (min_time, avg_time, max_time) in milliseconds
    """
    times = []

    for _ in range(repeat):
        cmd = [
            sys.executable,
            "-c",
            f"import os, logging; os.environ['PYTHONPATH']='.'; logging.getLogger().setLevel(logging.CRITICAL); import time; start=time.perf_counter(); import {module_path}; end=time.perf_counter(); print(f'TIMING:{{(end-start)*1000:.3f}}')",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
        if result.returncode == 0:
            # Extract timing from output, handling logging noise
            output_lines = result.stdout.strip().split("\n")
            timing_line = next(
                (line for line in output_lines if line.startswith("TIMING:")), None
            )
            if timing_line:
                import_time = float(timing_line.replace("TIMING:", ""))
                times.append(import_time)
            else:
                print(f"No timing found in output: {result.stdout}")
                return float("inf"), float("inf"), float("inf")
        else:
            print(f"Error importing {module_path}: {result.stderr}")
            return float("inf"), float("inf"), float("inf")

    return min(times), sum(times) / len(times), max(times)


def profile_individual_modules():
    """Profile each module individually."""
    modules = [
        "src.shared_context_server.core_server",
        "src.shared_context_server.auth_tools",
        "src.shared_context_server.session_tools",
        "src.shared_context_server.search_tools",
        "src.shared_context_server.memory_tools",
        "src.shared_context_server.admin_tools",
        "src.shared_context_server.web_endpoints",
        "src.shared_context_server.websocket_handlers",
    ]

    print("=== Individual Module Import Times ===")
    total_min = total_avg = total_max = 0.0

    for module in modules:
        min_time, avg_time, max_time = measure_import_time(module)
        total_min += min_time
        total_avg += avg_time
        total_max += max_time
        print(
            f"{module:50} | Min: {min_time:7.2f}ms | Avg: {avg_time:7.2f}ms | Max: {max_time:7.2f}ms"
        )

    print(
        f"{'TOTAL (individual)':50} | Min: {total_min:7.2f}ms | Avg: {total_avg:7.2f}ms | Max: {total_max:7.2f}ms"
    )
    return total_avg


def profile_server_import():
    """Profile the main server.py facade import."""
    print("\n=== Server Facade Import Time ===")
    min_time, avg_time, max_time = measure_import_time(
        "src.shared_context_server.server"
    )
    print(
        f"{'server.py (facade)':50} | Min: {min_time:7.2f}ms | Avg: {avg_time:7.2f}ms | Max: {max_time:7.2f}ms"
    )
    return avg_time


def profile_progressive_imports():
    """Profile imports progressively to identify bottlenecks."""
    print("\n=== Progressive Import Analysis ===")

    progressive_imports = [
        ("Core dependencies", "import asyncio, time, json, os"),
        ("+ FastMCP", "import asyncio, time, json, os; from fastmcp import Context"),
        (
            "+ Database",
            "import asyncio, time, json, os; from fastmcp import Context; import aiosqlite",
        ),
        (
            "+ RapidFuzz",
            "import asyncio, time, json, os; from fastmcp import Context; import aiosqlite; from rapidfuzz import fuzz",
        ),
        ("+ Core Server", "from src.shared_context_server.core_server import mcp"),
        (
            "+ Auth Tools",
            "from src.shared_context_server.core_server import mcp; from src.shared_context_server import auth_tools",
        ),
        (
            "+ Session Tools",
            "from src.shared_context_server.core_server import mcp; from src.shared_context_server import auth_tools, session_tools",
        ),
        (
            "+ Memory Tools",
            "from src.shared_context_server.core_server import mcp; from src.shared_context_server import auth_tools, session_tools, memory_tools",
        ),
        ("+ Full Server", "from src.shared_context_server.server import mcp"),
    ]

    for label, import_code in progressive_imports:
        cmd = [
            sys.executable,
            "-c",
            f"import os, logging; os.environ['PYTHONPATH']='.'; logging.getLogger().setLevel(logging.CRITICAL); import time; start=time.perf_counter(); {import_code}; end=time.perf_counter(); print(f'TIMING:{{(end-start)*1000:.3f}}')",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
        if result.returncode == 0:
            # Extract timing from output, handling logging noise
            output_lines = result.stdout.strip().split("\n")
            timing_line = next(
                (line for line in output_lines if line.startswith("TIMING:")), None
            )
            if timing_line:
                import_time = float(timing_line.replace("TIMING:", ""))
                print(f"{label:30} | {import_time:7.2f}ms")
            else:
                print(f"{label:30} | No timing found")
        else:
            print(f"{label:30} | ERROR: {result.stderr.strip()}")


def main():
    """Run comprehensive import performance analysis."""
    print("SHARED CONTEXT SERVER - IMPORT PERFORMANCE ANALYSIS")
    print("=" * 80)

    # Individual module analysis
    total_individual = profile_individual_modules()

    # Server facade analysis
    server_time = profile_server_import()

    # Progressive import analysis
    profile_progressive_imports()

    # Summary
    print("\n=== ANALYSIS SUMMARY ===")
    print(f"Individual modules total: {total_individual:.2f}ms")
    print(f"Server facade import:     {server_time:.2f}ms")
    print(
        f"Import overhead:          {server_time - total_individual:.2f}ms ({((server_time / total_individual - 1) * 100):+.1f}%)"
    )

    # Performance thresholds
    if server_time > 100:
        print(
            f"⚠️  WARNING: Server import time ({server_time:.2f}ms) exceeds 100ms threshold"
        )
    if server_time > 50:
        print(
            f"⚠️  CAUTION: Server import time ({server_time:.2f}ms) exceeds 50ms threshold"
        )
    if server_time <= 50:
        print(f"✅ Server import time ({server_time:.2f}ms) within acceptable range")


if __name__ == "__main__":
    main()
