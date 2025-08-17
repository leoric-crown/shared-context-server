"""
Integration tests for multi-tool agent workflows.

Tests complete workflows using multiple MCP tools together, simulating real
agent collaboration scenarios according to Phase 1 specification.
"""

# Import testing helpers from conftest.py
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.append(str(Path(__file__).parent.parent))
from conftest import MockContext, call_fastmcp_tool

from shared_context_server.server import (
    add_message,
    create_session,
    get_messages,
    get_session,
)


class TestCompleteAgentWorkflow:
    """Test complete agent collaboration workflows."""

    @pytest.fixture
    def agent1_context(self):
        """Mock context for first agent."""
        return MockContext("alice_session", "agent_alice")

    @pytest.fixture
    def agent2_context(self):
        """Mock context for second agent."""
        return MockContext("bob_session", "agent_bob")

    # Database fixtures now provided by conftest.py - no need for hardcoded mocks

    @pytest.mark.asyncio
    async def test_complete_collaboration_workflow(
        self, agent1_context, agent2_context, test_db_manager
    ):
        """Test a complete agent collaboration workflow."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # Use the real test database instead of hardcoded mocks
            @asynccontextmanager
            async def mock_get_db_connection():
                async with test_db_manager.get_connection() as conn:
                    yield conn

            mock_db_conn.side_effect = mock_get_db_connection

            # Step 1: Agent Alice creates a session
            session_result = await call_fastmcp_tool(
                create_session,
                agent1_context,
                purpose="Agent collaboration testing",
                metadata={"test": "integration"},
            )

            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # Step 2: Alice adds an initial message
            alice_message = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="Hello, I'm Alice. Starting our collaboration project.",
                visibility="public",
                metadata={"agent": "alice", "role": "coordinator"},
            )

            assert alice_message["success"] is True

            # Step 3: Bob joins the session and adds a response
            bob_message = await call_fastmcp_tool(
                add_message,
                agent2_context,
                session_id=session_id,
                content="Hi Alice! I'm Bob, ready to collaborate.",
                visibility="public",
                metadata={"agent": "bob", "role": "contributor"},
            )

            assert bob_message["success"] is True

            # Step 4: Alice retrieves the session to see Bob's message
            session_view = await call_fastmcp_tool(
                get_session,
                agent1_context,
                session_id=session_id,
            )

            assert session_view["success"] is True
            assert len(session_view["messages"]) == 2

            # Verify both messages are present (order may vary)
            messages = session_view["messages"]
            message_contents = [msg["content"] for msg in messages]
            message_senders = [msg["sender"] for msg in messages]

            assert (
                "Hello, I'm Alice. Starting our collaboration project."
                in message_contents
            )
            assert "Hi Alice! I'm Bob, ready to collaborate." in message_contents
            assert "agent_alice" in message_senders
            assert "agent_bob" in message_senders

            # Step 5: Bob retrieves messages to confirm his view
            bob_view = await call_fastmcp_tool(
                get_messages,
                agent2_context,
                session_id=session_id,
                limit=10,
                offset=0,
            )

            assert bob_view["success"] is True
            assert len(bob_view["messages"]) == 2

    @pytest.mark.asyncio
    async def test_error_handling_workflow(
        self, agent1_context, agent2_context, test_db_manager
    ):
        """Test error handling in agent workflows."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            # Use the real test database instead of hardcoded mocks
            @asynccontextmanager
            async def mock_get_db_connection():
                async with test_db_manager.get_connection() as conn:
                    yield conn

            mock_db_conn.side_effect = mock_get_db_connection

            # Test 1: Try to add message to non-existent session
            invalid_message = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id="non-existent-session",
                content="This should fail",
                visibility="public",
            )

            assert invalid_message["success"] is False
            assert "SESSION_NOT_FOUND" in invalid_message.get("code", "")

            # Test 2: Try to retrieve non-existent session
            invalid_session = await call_fastmcp_tool(
                get_session,
                agent1_context,
                session_id="non-existent-session",
            )

            assert invalid_session["success"] is False
            assert "SESSION_NOT_FOUND" in invalid_session.get("code", "")

    @pytest.mark.asyncio
    async def test_concurrent_agent_access(
        self, agent1_context, agent2_context, test_db_manager
    ):
        """Test concurrent agent access to the same session."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            # Use the real test database instead of hardcoded mocks
            @asynccontextmanager
            async def mock_get_db_connection():
                async with test_db_manager.get_connection() as conn:
                    yield conn

            mock_db_conn.side_effect = mock_get_db_connection

            # Create session with agent 1
            session_result = await call_fastmcp_tool(
                create_session,
                agent1_context,
                purpose="Concurrent access test",
                metadata={"test": "concurrent"},
            )

            session_id = session_result["session_id"]

            # Both agents try to add messages simultaneously (simulated)
            alice_message = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="Alice's message",
                visibility="public",
            )

            bob_message = await call_fastmcp_tool(
                add_message,
                agent2_context,
                session_id=session_id,
                content="Bob's concurrent message",
                visibility="public",
            )

            # Both operations should succeed
            assert alice_message["success"] is True
            assert bob_message["success"] is True

            # Verify both messages are stored
            session_view = await call_fastmcp_tool(
                get_session,
                agent1_context,
                session_id=session_id,
            )

            assert session_view["success"] is True
            assert len(session_view["messages"]) == 2

            # Check message content exists in session
            message_contents = [msg["content"] for msg in session_view["messages"]]
            assert "Alice's message" in message_contents
            assert "Bob's concurrent message" in message_contents
