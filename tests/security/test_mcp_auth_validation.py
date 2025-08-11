"""
MCP-based authentication and authorization validation tests.

Tests that verify proper authentication and authorization enforcement
within the MCP protocol framework:
- Admin permission enforcement for admin_only messages
- Agent isolation for private/agent_only messages
- Context-based authentication validation
- Permission-based access controls
"""

import pytest

from shared_context_server.auth import AuthInfo
from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestMCPAuthValidation:
    """MCP-compatible authentication validation tests."""

    @pytest.fixture
    def admin_ctx(self):
        """Create test context with admin permissions."""
        ctx = MockContext(session_id="admin_test", agent_id="admin-agent")
        ctx._auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="admin-agent",
            agent_type="admin",
            permissions=["read", "write", "admin"],
            authenticated=True,
            auth_method="jwt",
            token_id="admin_token_123",
        )
        return ctx

    @pytest.fixture
    def user_ctx(self):
        """Create test context with regular user permissions."""
        ctx = MockContext(session_id="user_test", agent_id="regular-user")
        ctx._auth_info = AuthInfo(
            jwt_validated=True,
            agent_id="regular-user",
            agent_type="claude",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="jwt",
            token_id="user_token_456",
        )
        return ctx

    @pytest.mark.asyncio
    async def test_admin_only_message_creation_requires_admin(
        self, test_db_manager, admin_ctx, user_ctx
    ):
        """Test that only admins can create admin_only messages."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Admin creates session
            session_result = await call_fastmcp_tool(
                server.create_session, admin_ctx, purpose="Admin security test"
            )
            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # Admin can create admin_only message
            admin_msg_result = await call_fastmcp_tool(
                server.add_message,
                admin_ctx,
                session_id=session_id,
                content="Admin-only secret message",
                visibility="admin_only",
            )
            assert admin_msg_result["success"] is True

            # Regular user CANNOT create admin_only message
            user_msg_result = await call_fastmcp_tool(
                server.add_message,
                user_ctx,
                session_id=session_id,
                content="Attempted admin message",
                visibility="admin_only",
            )
            assert user_msg_result["success"] is False
            assert "admin" in user_msg_result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_admin_only_message_visibility_filtering(
        self, test_db_manager, admin_ctx, user_ctx
    ):
        """Test that admin_only messages are only visible to admins."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Admin creates session and adds both public and admin_only messages
            session_result = await call_fastmcp_tool(
                server.create_session, admin_ctx, purpose="Visibility test"
            )
            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # Add public message
            public_msg = await call_fastmcp_tool(
                server.add_message,
                admin_ctx,
                session_id=session_id,
                content="Public message everyone can see",
                visibility="public",
            )
            assert public_msg["success"] is True

            # Add admin_only message
            admin_msg = await call_fastmcp_tool(
                server.add_message,
                admin_ctx,
                session_id=session_id,
                content="Secret admin information",
                visibility="admin_only",
            )
            assert admin_msg["success"] is True

            # Admin can see both messages
            admin_messages = await call_fastmcp_tool(
                server.get_messages, admin_ctx, session_id=session_id, limit=10
            )
            assert admin_messages["success"] is True
            admin_msg_contents = [msg["content"] for msg in admin_messages["messages"]]
            assert "Public message everyone can see" in admin_msg_contents
            assert "Secret admin information" in admin_msg_contents

            # Regular user can only see public message
            user_messages = await call_fastmcp_tool(
                server.get_messages, user_ctx, session_id=session_id, limit=10
            )
            assert user_messages["success"] is True
            user_msg_contents = [msg["content"] for msg in user_messages["messages"]]
            assert "Public message everyone can see" in user_msg_contents
            assert "Secret admin information" not in user_msg_contents

    @pytest.mark.asyncio
    async def test_agent_isolation_private_messages(self, test_db_manager):
        """Test that private messages are only visible to their sender."""
        from shared_context_server import server

        # Create two different user contexts
        agent1_ctx = MockContext(session_id="isolation_test", agent_id="agent-1")
        agent1_ctx._auth_info = AuthInfo(
            agent_id="agent-1",
            agent_type="claude",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="jwt",
        )

        agent2_ctx = MockContext(session_id="isolation_test", agent_id="agent-2")
        agent2_ctx._auth_info = AuthInfo(
            agent_id="agent-2",
            agent_type="gemini",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="jwt",
        )

        with patch_database_connection(test_db_manager):
            # Agent 1 creates session and private message
            session_result = await call_fastmcp_tool(
                server.create_session, agent1_ctx, purpose="Agent isolation test"
            )
            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # Agent 1 adds private message
            private_msg = await call_fastmcp_tool(
                server.add_message,
                agent1_ctx,
                session_id=session_id,
                content="Agent 1 private message",
                visibility="private",
            )
            assert private_msg["success"] is True

            # Agent 1 adds public message
            public_msg = await call_fastmcp_tool(
                server.add_message,
                agent1_ctx,
                session_id=session_id,
                content="Public message from Agent 1",
                visibility="public",
            )
            assert public_msg["success"] is True

            # Agent 1 can see both messages
            agent1_messages = await call_fastmcp_tool(
                server.get_messages, agent1_ctx, session_id=session_id, limit=10
            )
            assert agent1_messages["success"] is True
            agent1_contents = [msg["content"] for msg in agent1_messages["messages"]]
            assert "Agent 1 private message" in agent1_contents
            assert "Public message from Agent 1" in agent1_contents

            # Agent 2 can only see public message
            agent2_messages = await call_fastmcp_tool(
                server.get_messages, agent2_ctx, session_id=session_id, limit=10
            )
            assert agent2_messages["success"] is True
            agent2_contents = [msg["content"] for msg in agent2_messages["messages"]]
            assert "Agent 1 private message" not in agent2_contents
            assert "Public message from Agent 1" in agent2_contents

    @pytest.mark.asyncio
    async def test_agent_memory_isolation(self, test_db_manager):
        """Test that agent memory is properly isolated between agents."""
        from shared_context_server import server

        # Create two different agent contexts
        agent1_ctx = MockContext(session_id="memory_test", agent_id="memory-agent-1")
        agent2_ctx = MockContext(session_id="memory_test", agent_id="memory-agent-2")

        with patch_database_connection(test_db_manager):
            # Agent 1 sets memory
            set_result = await call_fastmcp_tool(
                server.set_memory,
                agent1_ctx,
                key="secret_data",
                value={"password": "agent1_secret", "config": "private_settings"},
            )
            assert set_result["success"] is True

            # Agent 1 can retrieve its own memory
            get_result_1 = await call_fastmcp_tool(
                server.get_memory, agent1_ctx, key="secret_data"
            )
            assert get_result_1["success"] is True
            assert get_result_1["value"]["password"] == "agent1_secret"

            # Agent 2 CANNOT access Agent 1's memory
            get_result_2 = await call_fastmcp_tool(
                server.get_memory, agent2_ctx, key="secret_data"
            )
            assert get_result_2["success"] is False
            assert "not found" in get_result_2.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_context_authentication_validation(self, test_db_manager):
        """Test that agent context is properly validated for authentication."""
        from shared_context_server import server

        # Create context with minimal authentication
        minimal_ctx = MockContext(session_id="auth_test", agent_id="minimal-agent")
        minimal_ctx._auth_info = AuthInfo(
            agent_id="minimal-agent",
            agent_type="generic",
            permissions=["read"],  # Only read permission
            authenticated=True,
            auth_method="api_key",
        )

        with patch_database_connection(test_db_manager):
            # Agent with read-only permissions can create sessions
            # (create_session doesn't require write permission in current implementation)
            session_result = await call_fastmcp_tool(
                server.create_session, minimal_ctx, purpose="Minimal auth test"
            )
            # This should succeed as create_session doesn't enforce write permission
            assert session_result["success"] is True

            session_id = session_result["session_id"]

            # Agent can retrieve session info (read permission)
            get_result = await call_fastmcp_tool(
                server.get_session, minimal_ctx, session_id=session_id
            )
            assert get_result["success"] is True

    @pytest.mark.asyncio
    async def test_search_permission_filtering(
        self, test_db_manager, admin_ctx, user_ctx
    ):
        """Test that search results respect permission-based filtering."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Admin creates session with mixed visibility messages
            session_result = await call_fastmcp_tool(
                server.create_session, admin_ctx, purpose="Search filtering test"
            )
            session_id = session_result["session_id"]

            # Add messages with different visibility levels
            messages_to_add = [
                ("Public searchable message", "public"),
                ("Admin searchable secret", "admin_only"),
                ("Private admin note", "private"),
            ]

            for content, visibility in messages_to_add:
                await call_fastmcp_tool(
                    server.add_message,
                    admin_ctx,
                    session_id=session_id,
                    content=content,
                    visibility=visibility,
                )

            # Admin search sees all messages
            admin_search = await call_fastmcp_tool(
                server.search_context,
                admin_ctx,
                session_id=session_id,
                query="searchable",
            )
            assert admin_search["success"] is True
            admin_found = [
                result["message"]["content"] for result in admin_search["results"]
            ]
            assert "Public searchable message" in str(admin_found)
            assert "Admin searchable secret" in str(admin_found)

            # User search only sees public messages
            user_search = await call_fastmcp_tool(
                server.search_context,
                user_ctx,
                session_id=session_id,
                query="searchable",
            )
            assert user_search["success"] is True
            user_found = [
                result["message"]["content"] for result in user_search["results"]
            ]
            assert "Public searchable message" in str(user_found)
            assert "Admin searchable secret" not in str(user_found)
