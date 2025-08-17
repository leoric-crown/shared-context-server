#!/usr/bin/env python3
"""
Test Performance Analysis
Analyze the specific performance bottleneck in test_performance_contract_maintenance
"""

import os
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def analyze_test_import_performance():
    """Analyze exactly what happens during test execution."""
    print("🧪 TEST PERFORMANCE ANALYSIS")
    print("=" * 60)

    # Phase 1: Measure server import time (what test does)
    print("\n📦 PHASE 1: Server Import (Test Load)")
    start_time = time.perf_counter()
    from shared_context_server import server

    import_time = (time.perf_counter() - start_time) * 1000
    print(f"  Server import time: {import_time:.2f}ms")

    # Phase 2: Measure FastMCP tool call setup
    print("\n🔧 PHASE 2: FastMCP Tool Setup")
    start_time = time.perf_counter()

    # Get the actual tool we'd be calling
    add_message_tool = server.add_message
    setup_time = (time.perf_counter() - start_time) * 1000
    print(f"  Tool reference time: {setup_time:.2f}ms")

    # Phase 3: Analyze what call_fastmcp_tool does
    print("\n📡 PHASE 3: FastMCP Call Analysis")
    try:
        from tests.conftest import call_fastmcp_tool

        start_time = time.perf_counter()
        # Just analyze the call_fastmcp_tool function setup
        conftest_time = (time.perf_counter() - start_time) * 1000
        print(f"  conftest import time: {conftest_time:.2f}ms")

    except ImportError as e:
        print(f"  conftest import failed: {e}")

    # Phase 4: Analyze total overhead
    print("\n📊 ANALYSIS SUMMARY")
    print("=" * 60)
    total_overhead = import_time + setup_time
    print(f"Total overhead: {total_overhead:.2f}ms")
    print("Target: 100ms")
    print(f"Over target by: {total_overhead - 100:.2f}ms")

    if total_overhead > 100:
        print(
            f"🚨 CRITICAL: Test overhead ({total_overhead:.2f}ms) exceeds target (100ms)"
        )
        print("   This explains why the performance test is failing")
    else:
        print("✅ Test overhead within target")

    # Phase 5: FastMCP Framework Analysis
    print("\n🏗️ PHASE 5: FastMCP Framework Deep Dive")

    # Check if FastMCP tools are already initialized
    if hasattr(server, "_mcp_tools_initialized"):
        print("  FastMCP tools already initialized")
    else:
        print("  FastMCP tools not yet initialized")

    # Test actual tool execution overhead
    from shared_context_server.auth import AuthInfo
    from tests.conftest import MockContext

    # Create mock context
    mock_ctx = MockContext(session_id="perf_test", agent_id="perf_analyzer")
    mock_ctx._auth_info = AuthInfo(
        jwt_validated=True,
        agent_id="perf_analyzer",
        agent_type="claude",
        permissions=["read", "write", "admin"],
        authenticated=True,
        auth_method="jwt",
        token_id="perf_test_token",
    )

    print("  Mock context created successfully")

    return total_overhead


def detailed_fastmcp_analysis():
    """Detailed analysis of FastMCP initialization."""
    print("\n🔬 DETAILED FASTMCP ANALYSIS")
    print("=" * 60)

    # Check what FastMCP actually does during import
    import importlib
    import time

    # Test individual FastMCP components
    components = [
        "fastmcp",
        "fastmcp.server",
        "fastmcp.resources",
        "fastmcp.context",
    ]

    for component in components:
        try:
            start_time = time.perf_counter()
            importlib.import_module(component)
            import_time = (time.perf_counter() - start_time) * 1000
            print(f"  {component}: {import_time:.2f}ms")
        except ImportError as e:
            print(f"  {component}: FAILED - {e}")


if __name__ == "__main__":
    overhead = analyze_test_import_performance()
    detailed_fastmcp_analysis()

    if overhead > 100:
        print("\n💡 SOLUTION RECOMMENDATIONS:")
        print("  1. Implement server facade lazy loading")
        print("  2. Defer FastMCP tool registration until first use")
        print("  3. Consider test-specific import optimization")
        print("  4. Optimize conftest.py call_fastmcp_tool function")
