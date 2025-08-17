#!/usr/bin/env python3
"""
Detailed import breakdown to identify performance bottlenecks.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def time_import(import_statement, description):
    """Time a specific import and print results."""
    print(f"Testing: {description}")

    start_time = time.perf_counter()

    try:
        exec(import_statement)
        import_time = (time.perf_counter() - start_time) * 1000
        print(f"  ✅ {import_time:.2f}ms - {import_statement}")
        return import_time
    except Exception as e:
        import_time = (time.perf_counter() - start_time) * 1000
        print(f"  ❌ {import_time:.2f}ms - {import_statement} (ERROR: {e})")
        return import_time


def main():
    """Test individual imports to find bottlenecks."""
    print("IMPORT PERFORMANCE BREAKDOWN")
    print("=" * 50)

    total_time = 0

    # Standard library imports
    total_time += time_import("import json", "Standard library - json")
    total_time += time_import("import logging", "Standard library - logging")
    total_time += time_import("import traceback", "Standard library - traceback")
    total_time += time_import(
        "from datetime import datetime, timezone", "Standard library - datetime"
    )
    total_time += time_import("from typing import Any", "Standard library - typing")

    print()

    # Third-party imports
    total_time += time_import("import aiosqlite", "Third-party - aiosqlite")
    total_time += time_import("from fastmcp import Context", "Third-party - fastmcp")
    total_time += time_import("from pydantic import Field", "Third-party - pydantic")

    print()

    # Local imports (potential bottlenecks)
    total_time += time_import(
        "from shared_context_server.auth import validate_agent_context_or_error",
        "Local - auth",
    )
    total_time += time_import(
        "from shared_context_server.core_server import mcp", "Local - core_server"
    )
    total_time += time_import(
        "from shared_context_server.database import get_db_connection",
        "Local - database",
    )
    total_time += time_import(
        "from shared_context_server.models import parse_mcp_metadata", "Local - models"
    )
    total_time += time_import(
        "from shared_context_server.utils.llm_errors import ERROR_MESSAGE_PATTERNS, ErrorSeverity, create_llm_error_response, create_system_error",
        "Local - utils.llm_errors",
    )

    print()
    print(f"TOTAL ESTIMATED: {total_time:.2f}ms")
    print()

    # Now test the full memory_tools import
    total_time += time_import(
        "from shared_context_server.memory_tools import set_memory, get_memory, list_memory",
        "FULL memory_tools import",
    )

    print("\nACTUAL vs ESTIMATED:")
    print(f"Estimated from parts: {total_time:.2f}ms")


if __name__ == "__main__":
    main()
