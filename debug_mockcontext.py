#!/usr/bin/env python3
"""Debug MockContext behavior."""

import asyncio
import sys

# Add src to path
sys.path.insert(0, "src")

from shared_context_server.auth import validate_agent_context_or_error
from shared_context_server.server import add_message, create_session
from tests.conftest import MockContext, call_fastmcp_tool


async def debug_mockcontext():
    """Debug MockContext behavior with validate_agent_context_or_error."""

    # Create test context like the test does
    ctx = MockContext("test_session", "test-agent-bridge")

    print("🔍 MockContext attributes:")
    print(f"  session_id: {ctx.session_id}")
    print(f"  agent_id: {ctx.agent_id}")
    print(f"  _auth_info: {ctx._auth_info}")

    print("\n🔍 Testing validate_agent_context_or_error...")

    try:
        agent_context = await validate_agent_context_or_error(ctx, None)
        print(f"✅ Agent context: {agent_context}")

        print("\n🔍 Testing create_session with MockContext...")
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="Mock test session"
        )
        print(f"Session result: {session_result}")

        if session_result.get("success"):
            session_id = session_result["session_id"]
            print(f"✅ Session created: {session_id}")

            print("\n🔍 Testing add_message with MockContext...")
            message_result = await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content="Mock test message",
                visibility="public",
            )
            print(f"Message result: {message_result}")

        else:
            print("❌ Session creation failed")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_mockcontext())
