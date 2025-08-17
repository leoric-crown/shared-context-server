#!/usr/bin/env python3
"""Profile add_message performance to identify bottlenecks."""

import asyncio
import cProfile
import os
import pstats
import time
from io import StringIO
from unittest.mock import patch

from shared_context_server import server
from shared_context_server.auth import AuthInfo

# Import test utilities
from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


async def profile_add_message():
    """Profile the add_message operation to identify performance bottlenecks."""

    # Create test database manager
    from tests.conftest import TestDatabaseManager

    test_db_manager = TestDatabaseManager()
    await test_db_manager.setup()

    # Create authenticated context
    authenticated_context = MockContext(
        session_id="profile_test", agent_id="profile_agent"
    )
    authenticated_context._auth_info = AuthInfo(
        jwt_validated=True,
        agent_id="profile_agent",
        agent_type="claude",
        permissions=["read", "write", "admin"],
        authenticated=True,
        auth_method="jwt",
        token_id="profile_test_token",
    )

    with patch_database_connection(test_db_manager, backend="aiosqlite"):
        # Create session first
        session_result = await call_fastmcp_tool(
            server.create_session, authenticated_context, purpose="Profile test session"
        )
        session_id = session_result["session_id"]

        # Profile add_message operation
        pr = cProfile.Profile()

        # Warm up - run once to ensure any lazy imports are done
        await call_fastmcp_tool(
            server.add_message,
            authenticated_context,
            session_id=session_id,
            content="Warmup message",
            visibility="public",
        )

        # Now profile the actual operation
        pr.enable()
        start_time = time.time()

        await call_fastmcp_tool(
            server.add_message,
            authenticated_context,
            session_id=session_id,
            content="Profile test message",
            visibility="public",
        )

        end_time = time.time()
        pr.disable()

        total_time = (end_time - start_time) * 1000  # Convert to milliseconds

        print("\n=== ADD_MESSAGE PERFORMANCE PROFILE ===")
        print(f"Total time: {total_time:.1f}ms")
        print("Target: <100ms")
        print(f"Status: {'PASS' if total_time < 100 else 'FAIL'}")

        # Show detailed profiling results
        s = StringIO()
        sortby = "cumulative"
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()

        print("\n=== TOP 20 SLOWEST FUNCTIONS ===")
        lines = s.getvalue().split("\n")
        for i, line in enumerate(lines):
            if i > 30:  # Skip header lines
                print(line)
            if i > 50:  # Show top 20 functions
                break

    await test_db_manager.cleanup()


async def profile_components():
    """Profile individual components of add_message."""

    from tests.conftest import TestDatabaseManager

    test_db_manager = TestDatabaseManager()
    await test_db_manager.setup()

    authenticated_context = MockContext(
        session_id="component_test", agent_id="component_agent"
    )
    authenticated_context._auth_info = AuthInfo(
        jwt_validated=True,
        agent_id="component_agent",
        agent_type="claude",
        permissions=["read", "write", "admin"],
        authenticated=True,
        auth_method="jwt",
        token_id="component_test_token",
    )

    with patch_database_connection(test_db_manager, backend="aiosqlite"):
        # Create session
        session_result = await call_fastmcp_tool(
            server.create_session,
            authenticated_context,
            purpose="Component profile test",
        )
        session_id = session_result["session_id"]

        print("\n=== COMPONENT TIMING ANALYSIS ===")

        # Test import timing
        start = time.time()
        try:
            from shared_context_server.websocket_handlers import notify_websocket_server

            import_time = (time.time() - start) * 1000
            print(f"WebSocket import time: {import_time:.1f}ms")
        except ImportError:
            print("WebSocket import: Not available")

        # Test database operation timing
        start = time.time()
        from shared_context_server.database import get_db_connection

        async with get_db_connection() as conn:
            await conn.execute("SELECT 1")
        db_time = (time.time() - start) * 1000
        print(f"Database connection time: {db_time:.1f}ms")

        # Test auth validation timing
        start = time.time()
        from shared_context_server.auth import validate_agent_context_or_error

        await validate_agent_context_or_error(authenticated_context, None)
        auth_time = (time.time() - start) * 1000
        print(f"Auth validation time: {auth_time:.1f}ms")

        # Test full add_message timing breakdown
        start = time.time()

        # Step 1: Auth validation
        step1_start = time.time()
        await validate_agent_context_or_error(authenticated_context, None)
        step1_time = (time.time() - step1_start) * 1000

        # Step 2: Database operations
        step2_start = time.time()
        async with get_db_connection() as conn:
            # Session validation
            cursor = await conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            )
            await cursor.fetchone()

            # Message insertion
            current_timestamp = time.time()
            cursor = await conn.execute(
                """
                INSERT INTO messages
                (session_id, sender, sender_type, content, visibility, metadata, parent_message_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    "component_agent",
                    "claude",
                    "Test message",
                    "public",
                    None,
                    None,
                    current_timestamp,
                ),
            )
            await conn.commit()
        step2_time = (time.time() - step2_start) * 1000

        # Step 3: WebSocket notifications (simulate)
        step3_start = time.time()
        try:
            from shared_context_server.websocket_handlers import websocket_manager

            # Just access the manager, don't actually broadcast
            _ = websocket_manager
        except ImportError:
            pass
        step3_time = (time.time() - step3_start) * 1000

        total_breakdown = (time.time() - start) * 1000

        print("\n=== TIMING BREAKDOWN ===")
        print(f"Step 1 - Auth validation: {step1_time:.1f}ms")
        print(f"Step 2 - Database ops: {step2_time:.1f}ms")
        print(f"Step 3 - WebSocket setup: {step3_time:.1f}ms")
        print(f"Total breakdown: {total_breakdown:.1f}ms")

    await test_db_manager.cleanup()


if __name__ == "__main__":
    # Set up test environment
    with patch.dict(
        os.environ,
        {
            "API_KEY": "test_api_key",
            "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
            "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
        },
    ):
        asyncio.run(profile_add_message())
        asyncio.run(profile_components())
