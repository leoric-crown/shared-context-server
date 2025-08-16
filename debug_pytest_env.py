#!/usr/bin/env python3
"""
Debug script to test exactly what pytest is doing.
"""

import subprocess


# Run a simple test with verbose output to understand pytest environment
def run_test_with_debug():
    """Run a test with maximum debugging."""

    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "pytest",
        "tests/unit/test_server_search.py::TestRapidFuzzSearchSystem::test_search_context_basic_functionality",
        "-xvs",
        "--tb=long",
        "--capture=no",
    ]

    print("=== Running test with debug output ===")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    print("=== STDOUT ===")
    print(result.stdout)
    print("=== STDERR ===")
    print(result.stderr)
    print("=== Return Code ===")
    print(result.returncode)


if __name__ == "__main__":
    run_test_with_debug()
