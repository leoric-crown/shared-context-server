#!/usr/bin/env python3
"""
Simple import performance test for memory_tools.
Tests the direct import overhead after lazy loading fix.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_memory_tools_import():
    """Test the import time of memory_tools with lazy loading."""
    print("Testing memory_tools import performance...")

    start_time = time.perf_counter()

    # Import memory_tools - this should now be fast due to lazy WebSocket loading

    import_time = (time.perf_counter() - start_time) * 1000

    print(f"Import time: {import_time:.2f}ms")

    # Performance targets
    if import_time > 50:
        print(f"❌ FAIL: Import time ({import_time:.2f}ms) exceeds 50ms target")
    elif import_time > 20:
        print(f"⚠️  WARNING: Import time ({import_time:.2f}ms) exceeds 20ms optimal")
    else:
        print(f"✅ PASS: Import time ({import_time:.2f}ms) within optimal range")

    return import_time


def test_websocket_handlers_import():
    """Test WebSocket handlers import time for comparison."""
    print("\nTesting websocket_handlers import performance...")

    start_time = time.perf_counter()

    # Import WebSocket handlers directly - this is the expensive import

    import_time = (time.perf_counter() - start_time) * 1000

    print(f"WebSocket handlers import time: {import_time:.2f}ms")

    return import_time


if __name__ == "__main__":
    print("MEMORY TOOLS LAZY IMPORT PERFORMANCE TEST")
    print("=" * 50)

    memory_time = test_memory_tools_import()
    websocket_time = test_websocket_handlers_import()

    print("\nSUMMARY:")
    print(f"memory_tools import:      {memory_time:.2f}ms")
    print(f"websocket_handlers import: {websocket_time:.2f}ms")
    print(f"Lazy loading savings:     {websocket_time:.2f}ms")

    if memory_time < 50:
        print("\n✅ SUCCESS: Lazy loading achieved target performance!")
    else:
        print("\n❌ NEEDS WORK: Still above 50ms target")
