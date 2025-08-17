#!/usr/bin/env python3
"""Profile memory set operation to identify performance bottlenecks."""

import asyncio
import cProfile
import pstats

# Setup similar to test
import sys
import time
from datetime import datetime

sys.path.append("src")

from shared_context_server.memory_tools import set_memory
from tests.conftest import MockContext, call_fastmcp_tool


async def profile_memory_set():
    """Profile the memory set operation."""

    ctx = MockContext("test_session")

    # Warm up
    await call_fastmcp_tool(
        set_memory, ctx, key="warmup", value={"data": "warmup value"}
    )

    # Actual timing
    start_time = time.time()
    result = await call_fastmcp_tool(
        set_memory,
        ctx,
        key="performance_test",
        value={
            "data": "performance test value",
            "timestamp": datetime.now().isoformat(),
        },
    )
    end_time = time.time()

    duration_ms = (end_time - start_time) * 1000
    print(f"Memory set took {duration_ms:.2f}ms")
    print(f"Result: {result}")

    return duration_ms


def run_profile():
    """Run profiler on memory set operation."""
    pr = cProfile.Profile()
    pr.enable()

    # Run the async function
    duration = asyncio.run(profile_memory_set())

    pr.disable()

    # Print stats
    stats = pstats.Stats(pr)
    stats.sort_stats("cumulative")
    stats.print_stats(30)  # Top 30 slowest functions

    return duration


if __name__ == "__main__":
    print("Profiling memory set operation...")
    duration = run_profile()
    print(f"\nTotal duration: {duration:.2f}ms")
