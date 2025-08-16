#!/usr/bin/env python3
"""
Detailed debug script to understand the database isolation in search tests.
"""

import asyncio

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection
from tests.fixtures.database import DatabaseTestManager


async def debug_search_detailed():
    """Debug the search test with detailed connection analysis."""

    # Setup test database
    test_db_manager = DatabaseTestManager()
    await test_db_manager.setup()

    print(f"Test database path: {test_db_manager.temp_db_path}")
    print(f"Backend: {test_db_manager.backend}")

    # Create mock context
    ctx = MockContext(agent_id="debug_agent")

    # Use the exact same pattern as the failing test
    with patch_database_connection(test_db_manager, backend="aiosqlite"):
        # Import server module after patching
        from shared_context_server import server

        print("=== Creating session ===")
        create_result = await call_fastmcp_tool(
            server.create_session, ctx, purpose="Debug search test"
        )
        print(f"Create session result: {create_result}")

        session_id = create_result["session_id"]

        print("=== Adding message ===")
        add_result = await call_fastmcp_tool(
            server.add_message,
            ctx,
            session_id=session_id,
            content="FastAPI is a modern web framework for Python",
            visibility="public",
            metadata={"category": "technology", "language": "python", "rating": 5},
        )
        print(f"Add message result: {add_result}")

        print("=== Verifying data in test database ===")
        async with test_db_manager.get_connection() as conn:
            conn.row_factory = (
                test_db_manager.db_manager.db_manager.Row
                if hasattr(test_db_manager.db_manager, "db_manager")
                else None
            )

            # Check sessions
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session_check = await cursor.fetchone()
            print(f"Session in test DB: {session_check}")

            # Check messages
            cursor = await conn.execute(
                "SELECT * FROM messages WHERE session_id = ?", (session_id,)
            )
            messages = await cursor.fetchall()
            print(f"Messages in test DB: {len(messages)} messages")
            for msg in messages:
                print(f"  Message: {dict(msg) if hasattr(msg, 'keys') else msg}")

        print("=== Testing search function ===")

        # Test the search call with debugging
        try:
            search_result = await call_fastmcp_tool(
                server.search_context,
                ctx,
                session_id=session_id,
                query="FastAPI",
                fuzzy_threshold=60.0,
            )
            print(f"Search result: {search_result}")

            if search_result.get("success"):
                print(f"Search found {len(search_result.get('results', []))} results")
                for result in search_result.get("results", []):
                    print(f"  Result: {result.get('message', {}).get('content', '')}")
            else:
                print(f"Search failed: {search_result}")

        except Exception as e:
            print(f"Search exception: {e}")
            import traceback

            traceback.print_exc()

    # Cleanup
    await test_db_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(debug_search_detailed())
