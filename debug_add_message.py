#!/usr/bin/env python3
"""Debug script to understand add_message failures."""

import asyncio
import sys

# Add src to path
sys.path.insert(0, "src")

from shared_context_server.server import add_message, create_session
from tests.conftest import call_fastmcp_tool


async def debug_add_message():
    """Debug add_message behavior."""

    # Create a test agent context
    test_agent = {
        "agent_id": "debug_agent",
        "agent_type": "claude",
        "permissions": ["read", "write"],
        "api_key": "test_key",
    }

    print("🔍 Creating test session...")

    # Create session first
    session_result = await call_fastmcp_tool(
        create_session, test_agent, purpose="Debug session"
    )

    print(f"Session creation result: {session_result}")

    if not session_result.get("success"):
        print("❌ Session creation failed!")
        return

    session_id = session_result["session_id"]
    print(f"✅ Session created: {session_id}")

    print("\n🔍 Testing add_message...")

    # Test add_message
    message_result = await call_fastmcp_tool(
        add_message,
        test_agent,
        session_id=session_id,
        content="Debug test message",
        visibility="public",
    )

    print(f"Message result: {message_result}")

    if message_result.get("success"):
        print("✅ add_message succeeded!")
    else:
        print("❌ add_message failed!")
        if "error" in message_result:
            print(f"Error: {message_result['error']}")
        if "code" in message_result:
            print(f"Code: {message_result['code']}")
        if "context" in message_result:
            print(f"Context: {message_result['context']}")


if __name__ == "__main__":
    asyncio.run(debug_add_message())
