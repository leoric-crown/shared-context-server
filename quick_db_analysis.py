#!/usr/bin/env python3
"""
Quick database connection analysis.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def measure_import_times():
    """Measure import times for key components."""
    print("=== IMPORT TIMING ANALYSIS ===")

    # Direct database import
    start = time.perf_counter()

    db_import = (time.perf_counter() - start) * 1000
    print(f"Direct database import: {db_import:.2f}ms")

    # Memory tools import (triggers heavy imports)
    start = time.perf_counter()

    memory_import = (time.perf_counter() - start) * 1000
    print(f"Memory tools import: {memory_import:.2f}ms")

    # Auth tools import
    start = time.perf_counter()

    auth_import = (time.perf_counter() - start) * 1000
    print(f"Auth tools import: {auth_import:.2f}ms")

    # Total overhead calculation
    total_overhead = memory_import + auth_import
    print(f"Combined module overhead: {total_overhead:.2f}ms")

    return {
        "db_import": db_import,
        "memory_import": memory_import,
        "auth_import": auth_import,
        "total_overhead": total_overhead,
    }


def analyze_import_chain():
    """Analyze the import chain to identify bottlenecks."""
    print("\n=== IMPORT CHAIN ANALYSIS ===")

    # Check what each module imports
    import_chains = {
        "memory_tools": [
            "shared_context_server.auth",
            "shared_context_server.database",
            "shared_context_server.models",
            "shared_context_server.utils.caching",
            "shared_context_server.utils.llm_errors",
            "shared_context_server.core_server",
        ],
        "auth_tools": [
            "shared_context_server.auth",
            "shared_context_server.database",
            "shared_context_server.models",
            "shared_context_server.core_server",
        ],
    }

    for module, imports in import_chains.items():
        print(f"\n{module} imports ({len(imports)} modules):")
        for imp in imports:
            print(f"  - {imp}")


def main():
    """Run quick database analysis."""
    print("QUICK DATABASE CONNECTION ANALYSIS")
    print("=" * 50)

    # Import timing analysis
    results = measure_import_times()

    # Import chain analysis
    analyze_import_chain()

    print("\n=== FINDINGS ===")
    print(f"Memory tools import overhead: {results['memory_import']:.2f}ms")
    print(f"Auth tools import overhead: {results['auth_import']:.2f}ms")
    print(f"Total module overhead: {results['total_overhead']:.2f}ms")

    # Performance impact assessment
    if results["total_overhead"] > 200:
        print("❌ CRITICAL: Module import overhead exceeds 200ms")
        print("   This is a major contributor to performance regression")
    elif results["total_overhead"] > 100:
        print("⚠️  WARNING: Module import overhead exceeds 100ms")
    else:
        print("✅ ACCEPTABLE: Module import overhead under 100ms")


if __name__ == "__main__":
    main()
