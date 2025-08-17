#!/usr/bin/env python3
"""
Trace exactly what's importing FastMCP during session_tools import
"""

import os
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def trace_session_tools_import():
    """Trace what happens when session_tools is imported."""
    print("🕵️ TRACING SESSION_TOOLS IMPORT")
    print("=" * 60)

    # Step 1: Import session_tools directly
    print("\n📦 STEP 1: Direct session_tools import")
    start_time = time.perf_counter()

    direct_time = (time.perf_counter() - start_time) * 1000
    print(f"  Direct session_tools import: {direct_time:.2f}ms")

    # Step 2: Check what session_tools imports
    import shared_context_server.session_tools as st

    print("\n📊 STEP 2: Session tools module attributes:")
    for attr in dir(st):
        if not attr.startswith("_"):
            print(f"  {attr}")


def trace_individual_imports():
    """Trace individual imports in session_tools dependencies."""
    print("\n🔬 TRACING INDIVIDUAL DEPENDENCIES")
    print("=" * 60)

    dependencies = [
        "shared_context_server.auth",
        "shared_context_server.models",
        "shared_context_server.utils.caching",
        "shared_context_server.utils.llm_errors",
    ]

    for dep in dependencies:
        try:
            start_time = time.perf_counter()
            __import__(dep)
            import_time = (time.perf_counter() - start_time) * 1000
            print(f"  {dep}: {import_time:.2f}ms")
        except ImportError as e:
            print(f"  {dep}: FAILED - {e}")


def trace_auth_module():
    """Deep trace of auth module since it likely imports FastMCP."""
    print("\n🔐 TRACING AUTH MODULE")
    print("=" * 60)

    start_time = time.perf_counter()

    auth_time = (time.perf_counter() - start_time) * 1000
    print(f"  Auth module import: {auth_time:.2f}ms")


if __name__ == "__main__":
    trace_individual_imports()
    trace_auth_module()
    trace_session_tools_import()
