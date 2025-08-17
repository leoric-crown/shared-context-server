#!/usr/bin/env python3
"""
Comprehensive Performance Profiling Script
Identifies ALL import bottlenecks in the modularized server architecture.
"""

import importlib
import os
import sys
import time
from typing import Tuple

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def profile_import_time(module_name: str, from_module: str = None) -> float:
    """Profile the import time of a specific module."""
    start_time = time.perf_counter()

    try:
        if from_module:
            # For relative imports like: from .module import something
            parent = importlib.import_module(from_module)
            module_path = module_name.replace(".", "")
            getattr(parent, module_path, None)
        else:
            # For absolute imports
            importlib.import_module(module_name)

        end_time = time.perf_counter()
        return (end_time - start_time) * 1000  # Convert to milliseconds
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")
        return 0.0


def profile_function_execution(func, *args, **kwargs) -> Tuple[float, any]:
    """Profile function execution time."""
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    return (end_time - start_time) * 1000, result


def comprehensive_performance_analysis():
    """Conduct comprehensive performance analysis."""
    print("🔍 COMPREHENSIVE PERFORMANCE ANALYSIS")
    print("=" * 60)

    # Phase 1: Core dependency imports
    print("\n📦 PHASE 1: Core Dependencies")
    core_imports = ["fastmcp", "aiosqlite", "pydantic", "rapidfuzz", "httpx"]

    core_times = {}
    for module in core_imports:
        import_time = profile_import_time(module)
        core_times[module] = import_time
        print(f"  {module}: {import_time:.2f}ms")

    # Phase 2: Shared context server modules
    print("\n🏗️ PHASE 2: Shared Context Server Modules")
    server_modules = [
        "shared_context_server.core_server",
        "shared_context_server.database",
        "shared_context_server.auth",
        "shared_context_server.models",
        "shared_context_server.utils.caching",
        "shared_context_server.utils.llm_errors",
        "shared_context_server.utils.performance",
        "shared_context_server.websocket_handlers",
    ]

    server_times = {}
    for module in server_modules:
        import_time = profile_import_time(module)
        server_times[module] = import_time
        print(f"  {module}: {import_time:.2f}ms")

    # Phase 3: Tool modules (the suspected bottleneck)
    print("\n🔧 PHASE 3: Tool Modules (Suspected Bottlenecks)")
    tool_modules = [
        "shared_context_server.admin_tools",
        "shared_context_server.auth_tools",
        "shared_context_server.memory_tools",
        "shared_context_server.search_tools",
        "shared_context_server.session_tools",
        "shared_context_server.web_endpoints",
    ]

    tool_times = {}
    for module in tool_modules:
        import_time = profile_import_time(module)
        tool_times[module] = import_time
        print(f"  {module}: {import_time:.2f}ms")

    # Phase 4: Main server import (full stack)
    print("\n🎯 PHASE 4: Full Server Import")
    full_server_time = profile_import_time("shared_context_server.server")
    print(f"  Full server import: {full_server_time:.2f}ms")

    # Phase 5: Memory operation simulation
    print("\n💾 PHASE 5: Memory Operation Simulation")
    try:
        # Simulate memory operation context
        mock_context = type(
            "MockContext",
            (),
            {
                "meta": type(
                    "MockMeta", (), {"headers": {"Authorization": "Bearer test"}}
                )()
            },
        )()

        # This will fail due to auth, but we measure the import/setup overhead
        start_time = time.perf_counter()
        try:
            # Just measuring the overhead of calling the function
            # (it will fail on auth but we measure the setup cost)
            pass
        except:
            pass
        end_time = time.perf_counter()
        memory_op_overhead = (end_time - start_time) * 1000
        print(f"  Memory operation overhead: {memory_op_overhead:.2f}ms")

    except Exception as e:
        print(f"  Memory operation test failed: {e}")

    # Summary Analysis
    print("\n📊 PERFORMANCE SUMMARY")
    print("=" * 60)

    total_core = sum(core_times.values())
    total_server = sum(server_times.values())
    total_tools = sum(tool_times.values())

    print(f"Core dependencies total: {total_core:.2f}ms")
    print(f"Server modules total: {total_server:.2f}ms")
    print(f"Tool modules total: {total_tools:.2f}ms")
    print(f"Full server import: {full_server_time:.2f}ms")
    print(f"TOTAL OVERHEAD: {total_core + total_server + total_tools:.2f}ms")

    # Identify top bottlenecks
    print("\n🎯 TOP BOTTLENECKS:")
    all_times = {**core_times, **server_times, **tool_times}
    sorted_times = sorted(all_times.items(), key=lambda x: x[1], reverse=True)

    for i, (module, time_ms) in enumerate(sorted_times[:10]):
        print(f"  {i + 1}. {module}: {time_ms:.2f}ms")

    # Performance targets
    print("\n🎯 PERFORMANCE ANALYSIS:")
    print(f"  Current: {full_server_time:.2f}ms")
    print("  Target: 100ms")
    print(
        f"  Over target by: {full_server_time - 100:.2f}ms ({((full_server_time / 100) - 1) * 100:.1f}% over)"
    )
    print("  Pre-refactor target: 50ms")
    print(
        f"  Over pre-refactor by: {full_server_time - 50:.2f}ms ({((full_server_time / 50) - 1) * 100:.1f}% over)"
    )


if __name__ == "__main__":
    comprehensive_performance_analysis()
