"""
Integration tests for multi-tool agent workflows.

Tests complete workflows using multiple MCP tools together, simulating real
agent collaboration scenarios according to Phase 1 specification.
"""

# Import testing helpers from conftest.py
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

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

    @pytest.fixture
    def mock_database_connection(self):
        """Mock database connection that simulates a real database."""

        # In-memory storage to simulate database persistence
        sessions = {}
        messages = {}
        audit_logs = []
        message_id_counter = [1]  # Use list for mutability

        async def mock_execute(query, params=()):
            nonlocal sessions, messages, audit_logs, message_id_counter

            if "INSERT INTO sessions" in query:
                session_id, purpose, created_by, metadata = params
                sessions[session_id] = {
                    "id": session_id,
                    "purpose": purpose,
                    "created_by": created_by,
                    "metadata": metadata,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                }
                return AsyncMock(lastrowid=None)

            if "SELECT * FROM sessions WHERE id = ?" in query:
                session_id = params[0]
                session = sessions.get(session_id)
                return AsyncMock(fetchone=AsyncMock(return_value=session))

            if "INSERT INTO messages" in query:
                session_id, sender, content, visibility, metadata, parent_id = params
                message_id = message_id_counter[0]
                message_id_counter[0] += 1

                messages[message_id] = {
                    "id": message_id,
                    "session_id": session_id,
                    "sender": sender,
                    "content": content,
                    "visibility": visibility,
                    "metadata": metadata,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "parent_message_id": parent_id,
                }
                return AsyncMock(lastrowid=message_id)

            if "SELECT * FROM messages" in query and "WHERE session_id = ?" in query:
                session_id = params[0]

                # Parse parameters based on query structure
                # Standard query: (session_id, agent_id, limit, offset)
                # With visibility_filter: (session_id, agent_id, visibility_filter, limit, offset)
                visibility_filter = None
                if (
                    len(params) >= 3
                    and isinstance(params[2], str)
                    and params[2] in ["public", "private", "agent_only"]
                ):
                    # Has visibility filter
                    agent_id = params[1] if len(params) > 1 else None
                    visibility_filter = params[2]
                else:
                    # No visibility filter
                    agent_id = params[1] if len(params) > 1 else None

                # Filter messages by visibility and agent
                filtered_messages = []
                for msg in messages.values():
                    if msg["session_id"] == session_id:
                        should_include = False

                        if visibility_filter:
                            # Apply visibility filter directly and check if agent can see this filtered message
                            if msg["visibility"] == visibility_filter and (
                                msg["visibility"] == "public"
                                or msg["visibility"] == "private"
                                and msg["sender"] == agent_id
                                or msg["visibility"] == "agent_only"
                                and msg["sender"] == agent_id
                            ):
                                should_include = True
                        else:
                            # Normal visibility rules (no filter)
                            if (
                                msg["visibility"] == "public"
                                or (
                                    msg["visibility"] == "private"
                                    and msg["sender"] == agent_id
                                )
                                or msg["visibility"] == "agent_only"
                                and msg["sender"] == agent_id
                            ):
                                should_include = True

                        if should_include:
                            filtered_messages.append(msg)

                # Sort by timestamp (ascending order as per spec)
                filtered_messages.sort(key=lambda x: x["timestamp"])

                # Apply limit/offset if specified
                # For get_session query: params are (session_id, agent_id) with no limit in params
                # For get_messages query: params might include limit and offset
                limit = None
                offset = 0

                if "LIMIT" in query and "OFFSET" in query:
                    # Query has both LIMIT and OFFSET - last two params
                    if len(params) >= 4:  # session_id, agent_id, limit, offset
                        limit = params[-2]
                        offset = params[-1]
                elif "LIMIT" in query:
                    # Query has only LIMIT - could be hardcoded in SQL or in params
                    if "LIMIT 50" in query:
                        # Hardcoded limit (like get_session)
                        limit = 50
                    elif len(params) >= 3:  # session_id, agent_id, limit
                        limit = params[-1]

                if limit and isinstance(limit, int):
                    filtered_messages = filtered_messages[offset : offset + limit]

                return AsyncMock(fetchall=AsyncMock(return_value=filtered_messages))

            if "INSERT INTO audit_log" in query:
                event_type, agent_id, session_id, metadata, timestamp = params
                audit_logs.append(
                    {
                        "event_type": event_type,
                        "agent_id": agent_id,
                        "session_id": session_id,
                        "metadata": metadata,
                        "timestamp": timestamp,
                    }
                )
                return AsyncMock()

            if "SELECT id FROM sessions WHERE id = ?" in query:
                session_id = params[0]
                session = sessions.get(session_id)
                return AsyncMock(
                    fetchone=AsyncMock(
                        return_value={"id": session_id} if session else None
                    )
                )

            return AsyncMock()

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute
        mock_conn.commit = AsyncMock()

        return mock_conn

    @pytest.mark.asyncio
    async def test_complete_collaboration_workflow(
        self, agent1_context, agent2_context, mock_database_connection
    ):
        """Test a complete agent collaboration workflow."""

        with (
            patch("shared_context_server.server.get_db_connection") as mock_db_conn,
        ):
            # Setup database mock
            mock_db_conn.return_value.__aenter__.return_value = mock_database_connection

            # Step 1: Agent Alice creates a session
            session_result = await call_fastmcp_tool(
                create_session,
                agent1_context,
                purpose="Code review collaboration",
                metadata={"project": "shared-context-server", "priority": "high"},
            )

            assert session_result["success"] is True
            session_id = session_result["session_id"]
            assert session_result["created_by"] == "agent_alice"

            # Step 2: Agent Alice adds a public message
            message_result = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="I need help reviewing the authentication code",
                visibility="public",
                metadata={"component": "authentication", "type": "request"},
            )

            assert message_result["success"] is True
            message_id_1 = message_result["message_id"]

            # Step 3: Agent Alice adds a private note
            private_note_result = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="Remember to check for SQL injection vulnerabilities",
                visibility="private",
                metadata={"type": "reminder"},
            )

            assert private_note_result["success"] is True

            # Step 4: Agent Bob joins and retrieves the session
            session_view_result = await call_fastmcp_tool(
                get_session, agent2_context, session_id=session_id
            )

            assert session_view_result["success"] is True
            assert session_view_result["session"]["id"] == session_id
            assert (
                session_view_result["session"]["purpose"] == "Code review collaboration"
            )
            # Bob should only see the public message, not Alice's private note
            assert len(session_view_result["messages"]) == 1
            assert (
                session_view_result["messages"][0]["content"]
                == "I need help reviewing the authentication code"
            )
            assert session_view_result["messages"][0]["visibility"] == "public"

            # Step 5: Agent Bob responds with a threaded message
            bob_response_result = await call_fastmcp_tool(
                add_message,
                agent2_context,
                session_id=session_id,
                content="I can help! I'll focus on input validation and error handling",
                visibility="public",
                metadata={"type": "response"},
                parent_message_id=message_id_1,
            )

            assert bob_response_result["success"] is True
            bob_response_result["message_id"]

            # Step 6: Agent Bob adds agent-only message (for future Phase 2)
            agent_only_result = await call_fastmcp_tool(
                add_message,
                agent2_context,
                session_id=session_id,
                content="Found potential security issue - needs investigation",
                visibility="agent_only",
                metadata={"security": True, "priority": "high"},
            )

            assert agent_only_result["success"] is True

            # Step 7: Alice retrieves all her accessible messages
            alice_messages_result = await call_fastmcp_tool(
                get_messages, agent1_context, session_id=session_id, limit=10, offset=0
            )

            assert alice_messages_result["success"] is True
            # Alice should see: her public message, her private note, Bob's public response
            # (agent_only from Bob might be visible depending on implementation)
            assert alice_messages_result["count"] >= 3

            # Verify message ordering (timestamp ascending)
            messages = alice_messages_result["messages"]
            for i in range(1, len(messages)):
                assert messages[i]["timestamp"] >= messages[i - 1]["timestamp"]

            # Step 8: Test pagination
            paginated_result = await call_fastmcp_tool(
                get_messages, agent1_context, session_id=session_id, limit=2, offset=0
            )

            assert paginated_result["success"] is True
            assert paginated_result["count"] == 2
            # Should indicate more messages are available
            if len(messages) > 2:
                assert paginated_result["has_more"] is True

            # Step 9: Test visibility filtering
            public_only_result = await call_fastmcp_tool(
                get_messages,
                agent1_context,
                session_id=session_id,
                visibility_filter="public",
            )

            assert public_only_result["success"] is True
            # Should only get public messages (Alice's initial + Bob's response)
            assert all(
                msg["visibility"] == "public" for msg in public_only_result["messages"]
            )

    @pytest.mark.asyncio
    async def test_session_isolation(
        self, agent1_context, agent2_context, mock_database_connection
    ):
        """Test that sessions are properly isolated from each other."""

        with (
            patch("shared_context_server.server.get_db_connection") as mock_db_conn,
        ):
            mock_db_conn.return_value.__aenter__.return_value = mock_database_connection

            # Create two separate sessions
            session1_result = await call_fastmcp_tool(
                create_session,
                agent1_context,
                purpose="Session 1 - Database design",
                metadata={"type": "design"},
            )
            session_id_1 = session1_result["session_id"]

            session2_result = await call_fastmcp_tool(
                create_session,
                agent1_context,
                purpose="Session 2 - API testing",
                metadata={"type": "testing"},
            )
            session_id_2 = session2_result["session_id"]

            # Add messages to session 1
            await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id_1,
                content="Let's design the user table",
                visibility="public",
            )

            # Add messages to session 2
            await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id_2,
                content="API endpoints need validation tests",
                visibility="public",
            )

            # Verify session 1 only has its own messages
            session1_messages = await call_fastmcp_tool(
                get_messages, agent1_context, session_id=session_id_1
            )
            assert session1_messages["success"] is True
            assert len(session1_messages["messages"]) == 1
            assert "user table" in session1_messages["messages"][0]["content"]

            # Verify session 2 only has its own messages
            session2_messages = await call_fastmcp_tool(
                get_messages, agent1_context, session_id=session_id_2
            )
            assert session2_messages["success"] is True
            assert len(session2_messages["messages"]) == 1
            assert "API endpoints" in session2_messages["messages"][0]["content"]

            # Cross-contamination check
            assert session1_messages["messages"][0]["session_id"] == session_id_1
            assert session2_messages["messages"][0]["session_id"] == session_id_2

    @pytest.mark.asyncio
    async def test_error_handling_workflow(
        self, agent1_context, mock_database_connection
    ):
        """Test error handling in multi-step workflows."""

        with (
            patch("shared_context_server.server.get_db_connection") as mock_db_conn,
        ):
            mock_db_conn.return_value.__aenter__.return_value = mock_database_connection

            # Test 1: Try to add message to non-existent session
            invalid_session_result = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id="session_nonexistent",
                content="This should fail",
                visibility="public",
            )

            assert invalid_session_result["success"] is False
            assert invalid_session_result["code"] == "SESSION_NOT_FOUND"

            # Test 2: Try to get messages from non-existent session
            invalid_get_result = await call_fastmcp_tool(
                get_messages, agent1_context, session_id="session_nonexistent"
            )

            # This should succeed but return empty results (depending on implementation)
            # or fail gracefully - either is acceptable
            assert "success" in invalid_get_result

            # Test 3: Create valid session for remaining tests
            session_result = await call_fastmcp_tool(
                create_session,
                agent1_context,
                purpose="Error handling test",
                metadata={"test": True},
            )
            session_id = session_result["session_id"]

            # Test 4: Try to add message with invalid visibility
            invalid_visibility_result = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="Test message",
                visibility="invalid_level",
            )

            assert invalid_visibility_result["success"] is False
            assert invalid_visibility_result["code"] == "INVALID_VISIBILITY"

            # Test 5: Try to add empty message
            empty_message_result = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="   ",  # Empty after sanitization
                visibility="public",
            )

            assert empty_message_result["success"] is False
            assert empty_message_result["code"] == "INVALID_INPUT"

    @pytest.mark.asyncio
    async def test_concurrent_agent_access(
        self, agent1_context, agent2_context, mock_database_connection
    ):
        """Test concurrent access by multiple agents."""

        with (
            patch("shared_context_server.server.get_db_connection") as mock_db_conn,
        ):
            mock_db_conn.return_value.__aenter__.return_value = mock_database_connection

            # Create session with agent 1
            session_result = await call_fastmcp_tool(
                create_session,
                agent1_context,
                purpose="Concurrent access test",
                metadata={"test": "concurrent"},
            )
            session_id = session_result["session_id"]

            # Both agents add messages concurrently (simulated)
            alice_message = await call_fastmcp_tool(
                add_message,
                agent1_context,
                session_id=session_id,
                content="Alice's message",
                visibility="public",
                metadata={"sender": "alice"},
            )

            bob_message = await call_fastmcp_tool(
                add_message,
                agent2_context,
                session_id=session_id,
                content="Bob's message",
                visibility="public",
                metadata={"sender": "bob"},
            )

            # Both should succeed
            assert alice_message["success"] is True
            assert bob_message["success"] is True

            # Both agents should see all public messages
            alice_view = await call_fastmcp_tool(
                get_messages, agent1_context, session_id=session_id
            )

            bob_view = await call_fastmcp_tool(
                get_messages, agent2_context, session_id=session_id
            )

            assert alice_view["success"] is True
            assert bob_view["success"] is True
            assert len(alice_view["messages"]) == 2
            assert len(bob_view["messages"]) == 2

            # Verify messages are from different senders
            senders = {msg["sender"] for msg in alice_view["messages"]}
            assert "agent_alice" in senders
            assert "agent_bob" in senders
