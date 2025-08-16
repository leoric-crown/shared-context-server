#!/usr/bin/env python3
"""
Debug script to understand database isolation issues.
"""

import asyncio

from tests.conftest import MockContext, call_fastmcp_tool
from tests.fixtures.database import DatabaseTestManager


async def debug_search_issue():
    """Debug the database isolation issue in search tests."""

    # Setup test database
    test_db_manager = DatabaseTestManager()
    await test_db_manager.setup()

    # Create mock context
    ctx = MockContext(agent_id="debug_agent")

    # Import server module
    from shared_context_server import server

    print(f"Test database path: {test_db_manager.temp_db_path}")
    print(f"Backend: {test_db_manager.backend}")
    print(f"DB Manager: {test_db_manager.db_manager}")

    # Create session
    create_result = await call_fastmcp_tool(
        server.create_session, ctx, purpose="Debug search test"
    )
    print(f"Create session result: {create_result}")

    session_id = create_result["session_id"]

    # Add a test message
    add_result = await call_fastmcp_tool(
        server.add_message,
        ctx,
        session_id=session_id,
        content="Test message for search",
        visibility="public",
    )
    print(f"Add message result: {add_result}")

    # Check if session exists from search function perspective
    try:
        from shared_context_server.database import get_db_connection

        async with get_db_connection() as conn:
            cursor = await conn.execute(
                "SELECT id FROM sessions WHERE id = ?", (session_id,)
            )
            session_check = await cursor.fetchone()
            print(f"Session exists in main database: {session_check}")

            cursor = await conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
            )
            message_count = await cursor.fetchone()
            print(f"Message count in main database: {message_count}")

    except Exception as e:
        print(f"Error checking main database: {e}")

    # Try search
    search_result = await call_fastmcp_tool(
        server.search_context,
        ctx,
        session_id=session_id,
        query="Test message",
        fuzzy_threshold=60.0,
    )
    print(f"Search result: {search_result}")

    # Cleanup
    await test_db_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(debug_search_issue())
