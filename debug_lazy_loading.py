#!/usr/bin/env python3
"""
Debug lazy loading implementation
"""

import os
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def debug_lazy_loading():
    """Debug step by step what happens with lazy loading."""
    print("🔍 DEBUGGING LAZY LOADING")
    print("=" * 60)

    # Step 1: Just import the server module
    print("\n📦 STEP 1: Import server module only")
    start_time = time.perf_counter()
    from shared_context_server import server

    import_time = (time.perf_counter() - start_time) * 1000
    print(f"  Server module import: {import_time:.2f}ms")

    # Step 2: Access add_message (should trigger lazy loading)
    print("\n🔧 STEP 2: Access add_message attribute")
    start_time = time.perf_counter()
    add_message_func = server.add_message
    access_time = (time.perf_counter() - start_time) * 1000
    print(f"  add_message access: {access_time:.2f}ms")

    # Step 3: Check what got imported
    print("\n📊 STEP 3: Check import cache")
    if hasattr(server, "_LAZY_IMPORTS"):
        for key in server._LAZY_IMPORTS:
            print(f"  Cached: {key}")
    else:
        print("  No _LAZY_IMPORTS found")

    # Step 4: Test direct access without server module
    print("\n🧪 STEP 4: Direct tool import test")
    start_time = time.perf_counter()

    direct_time = (time.perf_counter() - start_time) * 1000
    print(f"  Direct session_tools import: {direct_time:.2f}ms")

    # Step 5: Compare overhead
    total_lazy = import_time + access_time
    print("\n📈 COMPARISON:")
    print(f"  Lazy loading total: {total_lazy:.2f}ms")
    print(f"  Direct import: {direct_time:.2f}ms")
    print(f"  Lazy overhead: {total_lazy - direct_time:.2f}ms")


if __name__ == "__main__":
    debug_lazy_loading()
