"""
Security tests for message visibility controls.

Tests that message visibility levels (public, private, agent_only, admin_only) are properly enforced.
Uses real database connections and authentication contexts to validate security model.
"""

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestMessageVisibility:
    """Test message visibility security controls."""

    async def test_private_message_isolation(self, test_db_manager):
        """Test that private messages are only visible to their sender."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create session first
            agent_a_ctx = MockContext(session_id="visibility_test", agent_id="agent_a")
            agent_b_ctx = MockContext(session_id="visibility_test", agent_id="agent_b")

            session_result = await call_fastmcp_tool(
                server.create_session,
                agent_a_ctx,
                purpose="Message visibility security test",
                metadata={"test": "visibility"},
            )
            session_id = session_result["session_id"]

            # Agent A creates private message
            private_msg = await call_fastmcp_tool(
                server.add_message,
                agent_a_ctx,
                session_id=session_id,
                content="This is Agent A's private message - Agent B should NOT see this",
                visibility="private",
                metadata={"confidential": True},
            )
            assert private_msg["success"] is True

            # Agent A creates public message for comparison
            public_msg = await call_fastmcp_tool(
                server.add_message,
                agent_a_ctx,
                session_id=session_id,
                content="This is Agent A's public message - Agent B should see this",
                visibility="public",
            )
            assert public_msg["success"] is True

            # Agent A should see both messages
            agent_a_messages = await call_fastmcp_tool(
                server.get_messages,
                agent_a_ctx,
                session_id=session_id,
            )
            assert agent_a_messages["success"] is True
            assert len(agent_a_messages["messages"]) == 2

            a_contents = [msg["content"] for msg in agent_a_messages["messages"]]
            assert "private message" in " ".join(a_contents)
            assert "public message" in " ".join(a_contents)

            # CRITICAL SECURITY TEST: Agent B should only see public message
            agent_b_messages = await call_fastmcp_tool(
                server.get_messages,
                agent_b_ctx,
                session_id=session_id,
            )
            assert agent_b_messages["success"] is True
            assert len(agent_b_messages["messages"]) == 1  # Only public message

            b_contents = [msg["content"] for msg in agent_b_messages["messages"]]
            assert "public message" in " ".join(b_contents)
            assert "private message" not in " ".join(b_contents)  # SECURITY CHECK

    async def test_agent_only_message_isolation(self, test_db_manager):
        """Test that agent_only messages are properly filtered in Phase 1."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create session
            agent_a_ctx = MockContext(session_id="agent_only_test", agent_id="agent_a")
            agent_b_ctx = MockContext(session_id="agent_only_test", agent_id="agent_b")

            session_result = await call_fastmcp_tool(
                server.create_session,
                agent_a_ctx,
                purpose="Agent-only message test",
            )
            session_id = session_result["session_id"]

            # Agent A creates agent_only message
            agent_only_msg = await call_fastmcp_tool(
                server.add_message,
                agent_a_ctx,
                session_id=session_id,
                content="Agent A's agent_only message - should behave like private in Phase 1",
                visibility="agent_only",
                metadata={"internal": True},
            )
            assert agent_only_msg["success"] is True

            # Agent A should see their own agent_only message
            agent_a_messages = await call_fastmcp_tool(
                server.get_messages,
                agent_a_ctx,
                session_id=session_id,
            )
            assert agent_a_messages["success"] is True
            assert len(agent_a_messages["messages"]) == 1
            assert "agent_only message" in agent_a_messages["messages"][0]["content"]

            # SECURITY CHECK: Agent B should NOT see Agent A's agent_only message
            agent_b_messages = await call_fastmcp_tool(
                server.get_messages,
                agent_b_ctx,
                session_id=session_id,
            )
            assert agent_b_messages["success"] is True
            assert (
                len(agent_b_messages["messages"]) == 0
            )  # No messages visible to Agent B

    async def test_admin_only_message_protection(self, test_db_manager):
        """Test that admin_only messages require admin permissions."""
        from shared_context_server import server
        from shared_context_server.auth import AuthInfo

        with patch_database_connection(test_db_manager):
            # Create regular agent context (no admin permissions)
            regular_ctx = MockContext(session_id="admin_test", agent_id="regular_agent")

            # Create admin agent context
            admin_ctx = MockContext(session_id="admin_test", agent_id="admin_agent")
            admin_ctx._auth_info = AuthInfo(
                jwt_validated=True,  # Must use JWT for admin permissions
                agent_id="admin_agent",
                agent_type="admin",
                permissions=["read", "write", "admin"],  # Has admin permission
                authenticated=True,
                auth_method="jwt",  # Changed to JWT
                token_id="admin_jwt_token",
            )

            session_result = await call_fastmcp_tool(
                server.create_session,
                admin_ctx,
                purpose="Admin message test",
            )
            session_id = session_result["session_id"]

            # Regular agent attempts to create admin_only message (should fail)
            regular_admin_msg = await call_fastmcp_tool(
                server.add_message,
                regular_ctx,
                session_id=session_id,
                content="Regular agent attempting admin_only message",
                visibility="admin_only",
            )
            assert regular_admin_msg["success"] is False
            assert "Admin permission required" in regular_admin_msg["error"]
            assert regular_admin_msg["code"] == "PERMISSION_DENIED"

            # Admin agent creates admin_only message (should succeed)
            admin_msg = await call_fastmcp_tool(
                server.add_message,
                admin_ctx,
                session_id=session_id,
                content="Admin-only message - restricted access",
                visibility="admin_only",
            )
            if not admin_msg["success"]:
                print(f"Admin message creation failed: {admin_msg}")
            assert admin_msg["success"] is True

            # Regular agent should not see admin_only message
            regular_messages = await call_fastmcp_tool(
                server.get_messages,
                regular_ctx,
                session_id=session_id,
            )
            assert regular_messages["success"] is True
            assert len(regular_messages["messages"]) == 0

            # Admin agent should see their admin_only message
            admin_messages = await call_fastmcp_tool(
                server.get_messages,
                admin_ctx,
                session_id=session_id,
            )
            assert admin_messages["success"] is True
            assert len(admin_messages["messages"]) == 1
            assert "Admin-only message" in admin_messages["messages"][0]["content"]

    async def test_cross_session_message_isolation(self, test_db_manager):
        """Test that agents cannot see messages from sessions they're not part of."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Agent A creates session 1
            agent_a_ctx = MockContext(session_id="session_1", agent_id="agent_a")
            session_1_result = await call_fastmcp_tool(
                server.create_session,
                agent_a_ctx,
                purpose="Session 1 - Agent A's session",
            )
            session_1_id = session_1_result["session_id"]

            # Agent B creates session 2
            agent_b_ctx = MockContext(session_id="session_2", agent_id="agent_b")
            session_2_result = await call_fastmcp_tool(
                server.create_session,
                agent_b_ctx,
                purpose="Session 2 - Agent B's session",
            )
            session_2_id = session_2_result["session_id"]

            # Agent A adds message to session 1
            msg_1 = await call_fastmcp_tool(
                server.add_message,
                agent_a_ctx,
                session_id=session_1_id,
                content="Message in session 1 - should not leak to session 2",
                visibility="public",
            )
            assert msg_1["success"] is True

            # Agent B adds message to session 2
            msg_2 = await call_fastmcp_tool(
                server.add_message,
                agent_b_ctx,
                session_id=session_2_id,
                content="Message in session 2 - should not leak to session 1",
                visibility="public",
            )
            assert msg_2["success"] is True

            # SECURITY CHECK: Agent A should only see messages from session 1
            agent_a_session_1 = await call_fastmcp_tool(
                server.get_messages,
                agent_a_ctx,
                session_id=session_1_id,
            )
            assert agent_a_session_1["success"] is True
            assert len(agent_a_session_1["messages"]) == 1
            assert "session 1" in agent_a_session_1["messages"][0]["content"]

            # SECURITY CHECK: Agent B should only see messages from session 2
            agent_b_session_2 = await call_fastmcp_tool(
                server.get_messages,
                agent_b_ctx,
                session_id=session_2_id,
            )
            assert agent_b_session_2["success"] is True
            assert len(agent_b_session_2["messages"]) == 1
            assert "session 2" in agent_b_session_2["messages"][0]["content"]

    async def test_message_visibility_filter_parameter(self, test_db_manager):
        """Test that visibility_filter parameter properly filters messages."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            agent_ctx = MockContext(session_id="filter_test", agent_id="test_agent")

            session_result = await call_fastmcp_tool(
                server.create_session,
                agent_ctx,
                purpose="Visibility filter test",
            )
            session_id = session_result["session_id"]

            # Create messages with different visibility levels
            messages_data = [
                ("Public message 1", "public"),
                ("Private message 1", "private"),
                ("Public message 2", "public"),
                ("Private message 2", "private"),
            ]

            for content, visibility in messages_data:
                result = await call_fastmcp_tool(
                    server.add_message,
                    agent_ctx,
                    session_id=session_id,
                    content=content,
                    visibility=visibility,
                )
                assert result["success"] is True

            # Test filtering for public messages only
            public_only = await call_fastmcp_tool(
                server.get_messages,
                agent_ctx,
                session_id=session_id,
                visibility_filter="public",
            )
            assert public_only["success"] is True
            assert len(public_only["messages"]) == 2

            for msg in public_only["messages"]:
                assert msg["visibility"] == "public"
                assert "Public message" in msg["content"]

            # Test filtering for private messages only
            private_only = await call_fastmcp_tool(
                server.get_messages,
                agent_ctx,
                session_id=session_id,
                visibility_filter="private",
            )
            assert private_only["success"] is True
            assert len(private_only["messages"]) == 2

            for msg in private_only["messages"]:
                assert msg["visibility"] == "private"
                assert "Private message" in msg["content"]

            # Test no filter (should see all messages agent is authorized for)
            all_messages = await call_fastmcp_tool(
                server.get_messages,
                agent_ctx,
                session_id=session_id,
            )
            assert all_messages["success"] is True
            assert (
                len(all_messages["messages"]) == 4
            )  # Agent can see all their own messages

    async def test_message_search_respects_visibility(self, test_db_manager):
        """Test that search functionality respects message visibility controls."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create session with two agents
            agent_a_ctx = MockContext(session_id="search_test", agent_id="agent_a")
            agent_b_ctx = MockContext(session_id="search_test", agent_id="agent_b")

            session_result = await call_fastmcp_tool(
                server.create_session,
                agent_a_ctx,
                purpose="Search visibility test",
            )
            session_id = session_result["session_id"]

            # Agent A creates searchable messages with different visibility
            await call_fastmcp_tool(
                server.add_message,
                agent_a_ctx,
                session_id=session_id,
                content="Searchable public content about database optimization",
                visibility="public",
            )

            await call_fastmcp_tool(
                server.add_message,
                agent_a_ctx,
                session_id=session_id,
                content="Searchable private content about database secrets",
                visibility="private",
            )

            # Agent A should find both messages in search
            agent_a_search = await call_fastmcp_tool(
                server.search_context,
                agent_a_ctx,
                session_id=session_id,
                query="database",
                fuzzy_threshold=50.0,
            )
            assert agent_a_search["success"] is True
            assert len(agent_a_search["results"]) == 2

            # SECURITY CHECK: Agent B should only find public message in search
            agent_b_search = await call_fastmcp_tool(
                server.search_context,
                agent_b_ctx,
                session_id=session_id,
                query="database",
                fuzzy_threshold=50.0,
            )
            assert agent_b_search["success"] is True
            assert len(agent_b_search["results"]) == 1  # Only public message

            search_content = agent_b_search["results"][0]["message"]["content"]
            assert "public content" in search_content
            assert "secrets" not in search_content  # Private content should not appear
