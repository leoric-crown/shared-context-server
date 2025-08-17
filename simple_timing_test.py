#!/usr/bin/env python3
"""Simple timing test to identify add_message performance bottlenecks."""

import asyncio
import os
import time
from unittest.mock import patch


async def test_import_timing():
    """Test import timing for various components."""
    print("=== IMPORT TIMING ANALYSIS ===")

    # Test WebSocket handler import
    start = time.time()
    try:
        from shared_context_server.websocket_handlers import (
            notify_websocket_server,
            websocket_manager,
        )

        websocket_time = (time.time() - start) * 1000
        print(f"WebSocket handlers import: {websocket_time:.1f}ms")
    except ImportError as e:
        print(f"WebSocket handlers import: FAILED ({e})")

    # Test auth import
    start = time.time()

    auth_time = (time.time() - start) * 1000
    print(f"Auth validation import: {auth_time:.1f}ms")

    # Test database import
    start = time.time()

    db_time = (time.time() - start) * 1000
    print(f"Database import: {db_time:.1f}ms")

    # Test session tools import
    start = time.time()

    session_tools_time = (time.time() - start) * 1000
    print(f"Session tools import: {session_tools_time:.1f}ms")

    # Test server import (FastMCP registration)
    start = time.time()

    server_time = (time.time() - start) * 1000
    print(f"Server import (FastMCP): {server_time:.1f}ms")

    print(
        f"\nTotal import overhead: {websocket_time + auth_time + db_time + session_tools_time + server_time:.1f}ms"
    )


async def test_database_timing():
    """Test database operation timing."""
    print("\n=== DATABASE TIMING ANALYSIS ===")

    try:
        from shared_context_server.database import get_db_connection

        # Test connection creation
        start = time.time()
        async with get_db_connection() as conn:
            conn_time = (time.time() - start) * 1000
            print(f"Database connection: {conn_time:.1f}ms")

            # Test simple query
            start = time.time()
            await conn.execute("SELECT 1")
            query_time = (time.time() - start) * 1000
            print(f"Simple query: {query_time:.1f}ms")

            # Test table existence check
            start = time.time()
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            result = await cursor.fetchone()
            table_check_time = (time.time() - start) * 1000
            print(f"Table check: {table_check_time:.1f}ms")

            if result:
                # Test session lookup
                start = time.time()
                cursor = await conn.execute("SELECT id FROM sessions LIMIT 1")
                await cursor.fetchone()
                session_lookup_time = (time.time() - start) * 1000
                print(f"Session lookup: {session_lookup_time:.1f}ms")

    except Exception as e:
        print(f"Database operations failed: {e}")


async def test_websocket_timing():
    """Test WebSocket-related timing."""
    print("\n=== WEBSOCKET TIMING ANALYSIS ===")

    try:
        # Test import timing in isolation
        start = time.time()
        from shared_context_server.websocket_handlers import notify_websocket_server

        import1_time = (time.time() - start) * 1000
        print(f"notify_websocket_server import: {import1_time:.1f}ms")

        start = time.time()
        from shared_context_server.websocket_handlers import websocket_manager

        import2_time = (time.time() - start) * 1000
        print(f"websocket_manager import: {import2_time:.1f}ms")

        # Test manager access
        start = time.time()
        _ = websocket_manager  # Just access it
        access_time = (time.time() - start) * 1000
        print(f"WebSocket manager access: {access_time:.1f}ms")

    except ImportError:
        print("WebSocket handlers not available")
    except Exception as e:
        print(f"WebSocket operations failed: {e}")


async def test_complete_flow_timing():
    """Test the complete add_message flow timing using actual test."""
    print("\n=== COMPLETE FLOW TIMING ===")

    # Set up test environment
    with patch.dict(
        os.environ,
        {
            "API_KEY": "test_api_key",
            "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
            "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
        },
    ):
        try:
            # Run the actual performance test
            import subprocess

            start = time.time()
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "pytest",
                    "tests/integration/test_api_stability_validation.py::TestAPIStabilityValidation::test_performance_contract_maintenance",
                    "-v",
                    "-s",
                    "--tb=short",
                ],
                capture_output=True,
                text=True,
                cwd="/Users/Ricardo_Leon1/TestIO/scs/1.1.0-refactor",
            )

            total_time = (time.time() - start) * 1000
            print(f"Complete test execution: {total_time:.1f}ms")

            # Parse output for timing information
            if "AssertionError" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "Message operation took" in line:
                        print(f"Extracted: {line.strip()}")

        except Exception as e:
            print(f"Test execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_import_timing())
    asyncio.run(test_database_timing())
    asyncio.run(test_websocket_timing())
    asyncio.run(test_complete_flow_timing())
