"""
End-to-end test of Phase 1 implementation.

Tests the complete Phase 1 workflow using the actual server tools.
"""

import asyncio

# Import testing helpers from conftest.py
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent))
from conftest import MockContext, call_fastmcp_tool

from shared_context_server.server import (
    add_message,
    create_session,
    get_messages,
    get_session,
    mcp,
)


class TestPhase1EndToEnd:
    """End-to-end tests for Phase 1 implementation."""

    @pytest.mark.asyncio
    async def test_complete_phase1_workflow(self, isolated_db):
        """Test the complete Phase 1 workflow end-to-end."""

        # Use isolated test database instead of production database
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Mock agent context
            mock_context = MockContext("test_session", "test_agent")

            # Step 1: Create a session
            session_result = await call_fastmcp_tool(
                create_session,
                mock_context,
                purpose="Phase 1 end-to-end test",
                metadata={"test": True, "phase": 1},
            )

            print(f"Session result: {session_result}")
            assert session_result["success"] is True
            assert "session_id" in session_result
            assert session_result["created_by"] == "test_agent"

            session_id = session_result["session_id"]

            # Step 2: Add a public message
            public_message = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id=session_id,
                content="This is a public test message",
                visibility="public",
                metadata={"message_type": "test"},
            )

            print(f"Public message result: {public_message}")
            assert public_message["success"] is True
            assert "message_id" in public_message

            # Step 3: Add a private message
            private_message = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id=session_id,
                content="This is a private test message",
                visibility="private",
                metadata={"confidential": True},
            )

            print(f"Private message result: {private_message}")
            assert private_message["success"] is True

            # Step 4: Retrieve session information
            session_info = await call_fastmcp_tool(
                get_session, mock_context, session_id=session_id
            )

            print(f"Session info: {session_info}")
            assert session_info["success"] is True
            assert session_info["session"]["id"] == session_id
            assert session_info["session"]["purpose"] == "Phase 1 end-to-end test"
            assert (
                len(session_info["messages"]) == 2
            )  # Should see both messages (same agent)

            # Step 5: Retrieve messages with pagination
            messages_result = await call_fastmcp_tool(
                get_messages, mock_context, session_id=session_id, limit=10, offset=0
            )

            print(f"Messages result: {messages_result}")
            assert messages_result["success"] is True
            assert messages_result["count"] == 2
            assert messages_result["has_more"] is False

            # Verify message content
            message_contents = [msg["content"] for msg in messages_result["messages"]]
            assert "This is a public test message" in message_contents
            assert "This is a private test message" in message_contents

            # Step 6: Test visibility filtering
            public_only = await call_fastmcp_tool(
                get_messages,
                mock_context,
                session_id=session_id,
                visibility_filter="public",
            )

            print(f"Public only result: {public_only}")
            assert public_only["success"] is True
            assert len(public_only["messages"]) == 1
            assert public_only["messages"][0]["visibility"] == "public"

            print("✅ Phase 1 end-to-end test completed successfully!")

    @pytest.mark.asyncio
    async def test_error_scenarios(self, isolated_db):
        """Test error handling scenarios."""

        # Use isolated test database instead of production database
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            mock_context = MockContext("test_session", "error_test_agent")

            # Test 1: Add message to non-existent session
            invalid_session = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id="session_nonexistent123",
                content="This should fail",
                visibility="public",
            )

            assert invalid_session["success"] is False
            assert invalid_session["code"] == "SESSION_NOT_FOUND"

            # Test 2: Invalid visibility level
            session_result = await call_fastmcp_tool(
                create_session, mock_context, purpose="Error test session"
            )
            session_id = session_result["session_id"]

            invalid_visibility = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id=session_id,
                content="Test message",
                visibility="invalid_visibility",
            )

            assert invalid_visibility["success"] is False
            assert invalid_visibility["code"] == "INVALID_VISIBILITY"

            # Test 3: Empty content
            empty_content = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id=session_id,
                content="   ",  # Empty after sanitization
                visibility="public",
            )

            assert empty_content["success"] is False
            assert empty_content["code"] == "INVALID_INPUT"

            print("✅ Error scenarios test completed successfully!")

    @pytest.mark.asyncio
    async def test_multi_agent_visibility(self, isolated_db):
        """Test message visibility between different agents."""

        # Use isolated test database instead of production database
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Agent 1 creates session and messages
            agent1_context = MockContext("visibility_session", "agent_alice")

            session_result = await call_fastmcp_tool(
                create_session, agent1_context, purpose="Multi-agent visibility test"
            )
            session_id = session_result["session_id"]

            # Alice adds public and private messages
            await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="Alice public message",
                visibility="public",
            )

            await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="Alice private message",
                visibility="private",
            )

            # Agent 2 tries to access messages
            agent2_context = MockContext("visibility_session", "agent_bob")

            messages_result = await call_fastmcp_tool(
                get_messages, agent2_context, session_id=session_id
            )

            # Bob should only see Alice's public message
            assert messages_result["success"] is True
            assert len(messages_result["messages"]) == 1
            assert messages_result["messages"][0]["content"] == "Alice public message"
            assert messages_result["messages"][0]["visibility"] == "public"

            # Verify Bob cannot see Alice's private message
            message_contents = [msg["content"] for msg in messages_result["messages"]]
            assert "Alice private message" not in message_contents

            # Agent 1 should see both messages
            alice_view = await call_fastmcp_tool(
                get_messages, agent1_context, session_id=session_id
            )

            assert alice_view["success"] is True
            assert len(alice_view["messages"]) == 2

            alice_contents = [msg["content"] for msg in alice_view["messages"]]
            assert "Alice public message" in alice_contents
            assert "Alice private message" in alice_contents

            print("✅ Multi-agent visibility test completed successfully!")

    def test_server_configuration(self):
        """Test server configuration and setup."""

        # Test FastMCP server instance
        assert mcp.name == "shared-context-server"

        # Test that all tools are registered
        # Note: FastMCP uses 'tool' attribute, not 'tools' for accessing individual tools
        # We need to check if the tools are available via the tool method
        expected_tools = [
            "create_session",
            "get_session",
            "add_message",
            "get_messages",
        ]

        # Try to access each expected tool to verify it's registered
        def _verify_tool_accessible(tool_name: str) -> None:
            try:
                tool = mcp.tool(tool_name)
                assert tool is not None, (
                    f"Tool {tool_name} not found in registered tools"
                )
            except Exception as e:
                raise AssertionError(f"Tool {tool_name} not accessible: {e}") from e

        for tool_name in expected_tools:
            _verify_tool_accessible(tool_name)

        print(f"✅ Server configured with all expected tools: {expected_tools}")


if __name__ == "__main__":
    # Run the main workflow test
    asyncio.run(TestPhase1EndToEnd().test_complete_phase1_workflow())
