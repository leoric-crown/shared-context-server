"""
Unit tests for comprehensive session lifecycle operations in the server.

Tests session management operations including create_session, get_session,
add_message, get_messages with comprehensive visibility controls, edge cases,
and multi-agent scenarios.
"""

import json
from datetime import datetime, timezone

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestSessionLifecycle:
    """Test comprehensive session lifecycle operations."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    async def test_session_complete_lifecycle(self, server_with_db, test_db_manager):
        """Test complete session lifecycle from creation to message handling."""
        ctx = MockContext(agent_id="lifecycle_agent")

        # 1. Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="Lifecycle test session",
            metadata={"test": "lifecycle", "phase": "creation"},
        )

        assert create_result["success"] is True
        session_id = create_result["session_id"]
        assert session_id.startswith("session_")
        assert create_result["created_by"] == "lifecycle_agent"

        # 2. Get empty session
        get_result = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        assert get_result["success"] is True
        assert get_result["session"]["id"] == session_id
        assert get_result["session"]["purpose"] == "Lifecycle test session"
        assert len(get_result["messages"]) == 0
        assert get_result["message_count"] == 0

        # 3. Add messages with different visibility levels
        messages_to_add = [
            {"content": "Public message 1", "visibility": "public"},
            {"content": "Private message 1", "visibility": "private"},
            {"content": "Agent-only message 1", "visibility": "agent_only"},
            {"content": "Public message 2", "visibility": "public"},
        ]

        for msg_data in messages_to_add:
            add_result = await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=msg_data["content"],
                visibility=msg_data["visibility"],
                metadata={"order": len(messages_to_add)},
            )
            assert add_result["success"] is True

        # 4. Get session with messages
        get_result = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        assert get_result["success"] is True
        assert len(get_result["messages"]) == 4  # All messages visible to sender
        assert get_result["message_count"] == 4

        # 5. Get messages with pagination
        paginated_result = await call_fastmcp_tool(
            server_with_db.get_messages, ctx, session_id=session_id, limit=2, offset=0
        )

        assert paginated_result["success"] is True
        assert len(paginated_result["messages"]) == 2
        assert paginated_result["count"] == 2
        assert paginated_result["has_more"] is True

        # 6. Get remaining messages
        remaining_result = await call_fastmcp_tool(
            server_with_db.get_messages, ctx, session_id=session_id, limit=2, offset=2
        )

        assert remaining_result["success"] is True
        assert len(remaining_result["messages"]) == 2
        assert remaining_result["count"] == 2
        assert remaining_result["has_more"] is False

    async def test_session_visibility_isolation(self, server_with_db, test_db_manager):
        """Test that session visibility controls work correctly between agents."""
        agent1_ctx = MockContext(agent_id="agent_1")
        agent2_ctx = MockContext(agent_id="agent_2")

        # Agent 1 creates session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session,
            agent1_ctx,
            purpose="Multi-agent visibility test",
        )
        session_id = create_result["session_id"]

        # Agent 1 adds messages with different visibility
        messages = [
            {"content": "Public from agent 1", "visibility": "public"},
            {"content": "Private from agent 1", "visibility": "private"},
            {"content": "Agent-only from agent 1", "visibility": "agent_only"},
        ]

        for msg in messages:
            await call_fastmcp_tool(
                server_with_db.add_message,
                agent1_ctx,
                session_id=session_id,
                content=msg["content"],
                visibility=msg["visibility"],
            )

        # Agent 2 adds messages
        agent2_messages = [
            {"content": "Public from agent 2", "visibility": "public"},
            {"content": "Private from agent 2", "visibility": "private"},
        ]

        for msg in agent2_messages:
            await call_fastmcp_tool(
                server_with_db.add_message,
                agent2_ctx,
                session_id=session_id,
                content=msg["content"],
                visibility=msg["visibility"],
            )

        # Test Agent 1's view
        agent1_view = await call_fastmcp_tool(
            server_with_db.get_session, agent1_ctx, session_id=session_id
        )

        agent1_contents = [msg["content"] for msg in agent1_view["messages"]]

        # Agent 1 should see: all public + own private/agent_only
        assert "Public from agent 1" in agent1_contents
        assert "Public from agent 2" in agent1_contents
        assert "Private from agent 1" in agent1_contents
        assert "Agent-only from agent 1" in agent1_contents
        assert (
            "Private from agent 2" not in agent1_contents
        )  # Can't see other's private

        # Test Agent 2's view
        agent2_view = await call_fastmcp_tool(
            server_with_db.get_session, agent2_ctx, session_id=session_id
        )

        agent2_contents = [msg["content"] for msg in agent2_view["messages"]]

        # Agent 2 should see: all public + own private/agent_only
        assert "Public from agent 1" in agent2_contents
        assert "Public from agent 2" in agent2_contents
        assert "Private from agent 2" in agent2_contents
        assert (
            "Private from agent 1" not in agent2_contents
        )  # Can't see other's private
        assert (
            "Agent-only from agent 1" not in agent2_contents
        )  # Can't see other's agent_only

    async def test_session_message_threading(self, server_with_db, test_db_manager):
        """Test message threading functionality."""
        ctx = MockContext(agent_id="thread_agent")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Threading test"
        )
        session_id = create_result["session_id"]

        # Add root message
        root_result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Root message",
            visibility="public",
        )
        root_message_id = root_result["message_id"]

        # Add threaded replies
        reply1_result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Reply 1 to root",
            visibility="public",
            parent_message_id=root_message_id,
        )

        reply2_result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Reply 2 to root",
            visibility="public",
            parent_message_id=root_message_id,
        )

        # Add nested reply
        nested_reply_result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Nested reply",
            visibility="public",
            parent_message_id=reply1_result["message_id"],
        )

        # Verify threading structure
        session_result = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        messages = session_result["messages"]
        assert len(messages) == 4

        # Find messages and verify parent relationships
        message_map = {msg["id"]: msg for msg in messages}

        root_msg = message_map[root_message_id]
        reply1_msg = message_map[reply1_result["message_id"]]
        reply2_msg = message_map[reply2_result["message_id"]]
        nested_msg = message_map[nested_reply_result["message_id"]]

        assert root_msg["parent_message_id"] is None
        assert reply1_msg["parent_message_id"] == root_message_id
        assert reply2_msg["parent_message_id"] == root_message_id
        assert nested_msg["parent_message_id"] == reply1_result["message_id"]

    async def test_session_metadata_handling(self, server_with_db, test_db_manager):
        """Test comprehensive metadata handling in sessions and messages."""
        ctx = MockContext(agent_id="metadata_agent")

        # Test session metadata
        complex_metadata = {
            "project": "test_project",
            "tags": ["urgent", "backend", "api"],
            "config": {"timeout": 30, "retry_count": 3, "debug": True},
            "participants": ["agent_1", "agent_2", "human_user"],
            "created_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        create_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="Metadata handling test",
            metadata=complex_metadata,
        )
        session_id = create_result["session_id"]

        # Verify session metadata
        session_result = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        stored_metadata = session_result["session"]["metadata"]
        if isinstance(stored_metadata, str):
            stored_metadata = json.loads(stored_metadata)

        assert stored_metadata["project"] == "test_project"
        assert stored_metadata["tags"] == ["urgent", "backend", "api"]
        assert stored_metadata["config"]["timeout"] == 30

        # Test message metadata
        message_metadata = {
            "importance": "high",
            "source": "automated_system",
            "processing_time": 0.125,
            "references": ["doc_1", "doc_2"],
        }

        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Message with metadata",
            visibility="public",
            metadata=message_metadata,
        )

        # Verify message metadata
        updated_session = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        message = updated_session["messages"][0]
        msg_metadata = message["metadata"]
        if isinstance(msg_metadata, str):
            msg_metadata = json.loads(msg_metadata)

        assert msg_metadata["importance"] == "high"
        assert msg_metadata["processing_time"] == 0.125
        assert msg_metadata["references"] == ["doc_1", "doc_2"]

    async def test_session_edge_cases(self, server_with_db, test_db_manager):
        """Test session operations with edge cases."""
        ctx = MockContext(agent_id="edge_case_agent")

        # Test session with minimal data
        minimal_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="x",  # Single character
        )
        assert minimal_result["success"] is True

        # Test session with maximum purpose length
        max_purpose = "a" * 1000  # Assuming reasonable maximum
        max_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose=max_purpose
        )
        assert max_result["success"] is True

        # Test unicode content
        unicode_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="Test with unicode: 🚀 世界 🌍 测试",
        )
        assert unicode_result["success"] is True
        session_id = unicode_result["session_id"]

        # Add unicode message
        unicode_msg_result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Unicode message: 🎉 Hello 世界! Testing émojis and spëcial chars 🔥",
            visibility="public",
        )
        assert unicode_msg_result["success"] is True

        # Verify unicode is preserved
        session_data = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        assert "🚀 世界 🌍" in session_data["session"]["purpose"]
        assert "🎉 Hello 世界!" in session_data["messages"][0]["content"]

    async def test_session_nonexistent_operations(
        self, server_with_db, test_db_manager
    ):
        """Test operations on nonexistent sessions."""
        ctx = MockContext(agent_id="nonexistent_agent")
        fake_session_id = "session_nonexistent123"

        # Test get_session on nonexistent session
        get_result = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=fake_session_id
        )
        assert get_result["success"] is False
        assert "not found" in get_result["error"].lower()
        assert get_result["code"] == "SESSION_NOT_FOUND"

        # Test add_message to nonexistent session
        add_result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=fake_session_id,
            content="Message to nowhere",
            visibility="public",
        )
        assert add_result["success"] is False
        assert "not found" in add_result["error"].lower()
        assert add_result["code"] == "SESSION_NOT_FOUND"

        # Test get_messages from nonexistent session
        get_msgs_result = await call_fastmcp_tool(
            server_with_db.get_messages, ctx, session_id=fake_session_id
        )
        assert get_msgs_result["success"] is False

    async def test_session_agent_context_extraction(
        self, server_with_db, test_db_manager
    ):
        """Test that agent context is properly extracted in session operations."""
        # Test with different context configurations
        contexts = [
            MockContext(session_id="test1", agent_id="explicit_agent"),
            MockContext(session_id="test2"),  # Will derive agent_id from session
        ]

        for ctx in contexts:
            # Create session
            create_result = await call_fastmcp_tool(
                server_with_db.create_session, ctx, purpose="Context extraction test"
            )

            assert create_result["success"] is True
            assert "created_by" in create_result

            # The created_by should be either the explicit agent_id or derived from session
            created_by = create_result["created_by"]
            if hasattr(ctx, "agent_id") and ctx.agent_id:
                assert created_by == ctx.agent_id
            else:
                # Should be derived from session_id
                assert created_by.startswith("agent_")

    async def test_session_message_ordering(self, server_with_db, test_db_manager):
        """Test that messages are properly ordered by timestamp."""
        ctx = MockContext(agent_id="order_agent")

        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Message ordering test"
        )
        session_id = create_result["session_id"]

        # Add messages with small delays to ensure different timestamps
        import asyncio

        message_contents = []

        for i in range(5):
            content = f"Message {i}"
            message_contents.append(content)

            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=content,
                visibility="public",
            )
            await asyncio.sleep(0.01)  # Small delay to ensure timestamp differences

        # Get messages and verify ordering
        get_result = await call_fastmcp_tool(
            server_with_db.get_messages, ctx, session_id=session_id, limit=10
        )

        retrieved_contents = [msg["content"] for msg in get_result["messages"]]

        # Messages should be in chronological order (ASC in get_messages)
        assert retrieved_contents == message_contents

        # get_session should return messages in reverse chronological order (DESC)
        session_result = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        session_contents = [msg["content"] for msg in session_result["messages"]]
        assert session_contents == list(reversed(message_contents))

    async def test_session_visibility_filtering(self, server_with_db, test_db_manager):
        """Test get_messages with visibility filtering."""
        ctx = MockContext(agent_id="filter_agent")

        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Visibility filter test"
        )
        session_id = create_result["session_id"]

        # Add messages with different visibility
        visibilities = ["public", "private", "agent_only", "public", "private"]
        for i, visibility in enumerate(visibilities):
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=f"{visibility} message {i}",
                visibility=visibility,
            )

        # Test public filter
        public_result = await call_fastmcp_tool(
            server_with_db.get_messages,
            ctx,
            session_id=session_id,
            visibility_filter="public",
        )

        public_messages = [msg["content"] for msg in public_result["messages"]]
        assert len(public_messages) == 2
        assert all("public" in content for content in public_messages)

        # Test private filter
        private_result = await call_fastmcp_tool(
            server_with_db.get_messages,
            ctx,
            session_id=session_id,
            visibility_filter="private",
        )

        private_messages = [msg["content"] for msg in private_result["messages"]]
        assert len(private_messages) == 2
        assert all("private" in content for content in private_messages)

        # Test agent_only filter
        agent_only_result = await call_fastmcp_tool(
            server_with_db.get_messages,
            ctx,
            session_id=session_id,
            visibility_filter="agent_only",
        )

        agent_only_messages = [msg["content"] for msg in agent_only_result["messages"]]
        assert len(agent_only_messages) == 1
        assert "agent_only" in agent_only_messages[0]

    async def test_session_concurrent_operations(self, server_with_db, test_db_manager):
        """Test concurrent session operations."""
        import asyncio

        base_ctx = MockContext(agent_id="concurrent_agent")

        # Create session first
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, base_ctx, purpose="Concurrent test"
        )
        session_id = create_result["session_id"]

        # Define concurrent operations
        async def add_message(content: str, visibility: str = "public"):
            return await call_fastmcp_tool(
                server_with_db.add_message,
                base_ctx,
                session_id=session_id,
                content=content,
                visibility=visibility,
            )

        async def get_session():
            return await call_fastmcp_tool(
                server_with_db.get_session, base_ctx, session_id=session_id
            )

        # Run concurrent operations
        tasks = [
            add_message("Concurrent message 1"),
            add_message("Concurrent message 2", "private"),
            add_message("Concurrent message 3"),
            get_session(),
            add_message("Concurrent message 4", "agent_only"),
            get_session(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should succeed (no exceptions)
        for result in results:
            assert not isinstance(result, Exception)
            if "success" in result:
                assert result["success"] is True

        # Verify final state
        final_result = await call_fastmcp_tool(
            server_with_db.get_session, base_ctx, session_id=session_id
        )

        assert len(final_result["messages"]) == 4  # All 4 messages added
