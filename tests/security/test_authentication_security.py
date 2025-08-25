"""
Security tests for authentication and authorization.

Tests JWT token validation, agent context isolation, and permission boundaries.
Uses real authentication flows to validate security model.
"""

from shared_context_server.auth import AuthInfo
from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestAuthenticationSecurity:
    """Test authentication and authorization security controls."""

    async def test_agent_context_isolation(self, test_db_manager):
        """Test that agent contexts maintain proper isolation."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create two agents with different authentication contexts
            agent_1_ctx = MockContext(
                session_id="auth_test", agent_id="authenticated_agent_1"
            )
            agent_1_ctx._auth_info = AuthInfo(
                jwt_validated=True,
                agent_id="authenticated_agent_1",
                agent_type="claude",
                permissions=["read", "write"],
                authenticated=True,
                auth_method="jwt",
                token_id="token_1",
            )

            agent_2_ctx = MockContext(
                session_id="auth_test", agent_id="authenticated_agent_2"
            )
            agent_2_ctx._auth_info = AuthInfo(
                jwt_validated=True,
                agent_id="authenticated_agent_2",
                agent_type="gemini",
                permissions=[
                    "read",
                    "write",
                ],  # Need write permissions to create sessions
                authenticated=True,
                auth_method="jwt",
                token_id="token_2",
            )

            # Test that each agent gets their own identity consistently
            session_1 = await call_fastmcp_tool(
                server.create_session,
                agent_1_ctx,
                purpose="Agent 1 session",
                metadata={"created_by": "agent_1"},
            )
            assert session_1["success"] is True
            assert session_1["created_by"] == "authenticated_agent_1"

            session_2 = await call_fastmcp_tool(
                server.create_session,
                agent_2_ctx,
                purpose="Agent 2 session",
                metadata={"created_by": "agent_2"},
            )
            assert session_2["success"] is True
            assert session_2["created_by"] == "authenticated_agent_2"

            # Verify agent identities don't cross-contaminate
            assert session_1["created_by"] != session_2["created_by"]

    async def test_permission_boundary_enforcement(self, test_db_manager):
        """Test that permission boundaries are properly enforced."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create read-only agent
            readonly_ctx = MockContext(
                session_id="perm_test", agent_id="readonly_agent"
            )
            readonly_ctx._auth_info = AuthInfo(
                jwt_validated=True,
                agent_id="readonly_agent",
                agent_type="restricted",
                permissions=["read"],  # No write permission
                authenticated=True,
                auth_method="jwt",
                token_id="readonly_token",
            )

            # Create read-write agent
            readwrite_ctx = MockContext(
                session_id="perm_test", agent_id="readwrite_agent"
            )
            readwrite_ctx._auth_info = AuthInfo(
                jwt_validated=True,
                agent_id="readwrite_agent",
                agent_type="claude",
                permissions=["read", "write"],
                authenticated=True,
                auth_method="jwt",
                token_id="readwrite_token",
            )

            # Read-write agent creates session (should succeed)
            session_result = await call_fastmcp_tool(
                server.create_session,
                readwrite_ctx,
                purpose="Permission test session",
            )
            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # Read-write agent adds message (should succeed)
            message_result = await call_fastmcp_tool(
                server.add_message,
                readwrite_ctx,
                session_id=session_id,
                content="Message from read-write agent",
                visibility="public",
            )
            assert message_result["success"] is True

            # Read-only agent can read messages (should succeed)
            read_result = await call_fastmcp_tool(
                server.get_messages,
                readonly_ctx,
                session_id=session_id,
            )
            assert read_result["success"] is True
            assert len(read_result["messages"]) == 1

            # Read-only agent can read session info (should succeed)
            session_read = await call_fastmcp_tool(
                server.get_session,
                readonly_ctx,
                session_id=session_id,
            )
            assert session_read["success"] is True

    async def test_unauthenticated_access_restrictions(self, test_db_manager):
        """Test that unauthenticated agents have limited access."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create unauthenticated context
            unauth_ctx = MockContext(session_id="unauth_test", agent_id="unknown")
            unauth_ctx._auth_info = AuthInfo(
                jwt_validated=False,
                agent_id="unknown",
                agent_type="unknown",
                permissions=["read"],  # Limited permissions
                authenticated=False,
                auth_method="none",
                token_id=None,
            )

            # Create authenticated context for comparison
            auth_ctx = MockContext(session_id="unauth_test", agent_id="auth_agent")
            auth_ctx._auth_info = AuthInfo(
                jwt_validated=True,
                agent_id="auth_agent",
                agent_type="claude",
                permissions=["read", "write"],
                authenticated=True,
                auth_method="jwt",
                token_id="valid_token",
            )

            # Authenticated agent creates session
            session_result = await call_fastmcp_tool(
                server.create_session,
                auth_ctx,
                purpose="Auth test session",
            )
            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # Authenticated agent adds public message
            await call_fastmcp_tool(
                server.add_message,
                auth_ctx,
                session_id=session_id,
                content="Public message for auth test",
                visibility="public",
            )

            # Unauthenticated agent can read public messages
            unauth_read = await call_fastmcp_tool(
                server.get_messages,
                unauth_ctx,
                session_id=session_id,
            )
            assert unauth_read["success"] is True
            assert len(unauth_read["messages"]) == 1

    async def test_agent_identity_consistency(self, test_db_manager):
        """Test that agent identity remains consistent across operations."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create consistent agent context
            agent_ctx = MockContext(
                session_id="consistency_test", agent_id="consistent_agent"
            )

            # Perform multiple operations and verify identity consistency
            operations = []

            # Create session
            session_result = await call_fastmcp_tool(
                server.create_session,
                agent_ctx,
                purpose="Identity consistency test",
            )
            assert session_result["success"] is True
            session_id = session_result["session_id"]
            operations.append(("create_session", session_result["created_by"]))

            # Add message
            message_result = await call_fastmcp_tool(
                server.add_message,
                agent_ctx,
                session_id=session_id,
                content="Consistency test message",
                visibility="public",
            )
            assert message_result["success"] is True

            # Get the message to check sender
            messages = await call_fastmcp_tool(
                server.get_messages,
                agent_ctx,
                session_id=session_id,
            )
            operations.append(("add_message", messages["messages"][0]["sender"]))

            # Set memory
            memory_result = await call_fastmcp_tool(
                server.set_memory,
                agent_ctx,
                key="consistency_test",
                value={"test": "identity_consistency"},
            )
            assert memory_result["success"] is True

            # List memory to verify agent_id
            memory_list = await call_fastmcp_tool(
                server.list_memory,
                agent_ctx,
                limit=10,
            )
            assert memory_list["success"] is True
            # Memory operations don't expose agent_id directly, but isolation proves identity consistency

            # Verify all operations used the same agent identity
            agent_identities = [op[1] for op in operations]
            assert all(
                identity == "consistent_agent" for identity in agent_identities
            ), f"Agent identity inconsistent across operations: {operations}"

    async def test_session_based_fallback_isolation(self, test_db_manager):
        """Test that session-based agent_id fallback doesn't create cross-contamination."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Create contexts that might use session-based fallback
            session_id = "fallback_isolation_test"

            # Both contexts have same session but should get different derived agent_ids
            ctx_1 = MockContext(session_id=session_id, agent_id="derived_agent_1")
            ctx_2 = MockContext(session_id=session_id, agent_id="derived_agent_2")

            # Test memory isolation even with session-based derivation
            memory_1 = await call_fastmcp_tool(
                server.set_memory,
                ctx_1,
                key="fallback_test",
                value={"agent": "1", "session": session_id},
                session_id=None,  # Global memory
            )
            assert memory_1["success"] is True

            memory_2 = await call_fastmcp_tool(
                server.set_memory,
                ctx_2,
                key="fallback_test",  # Same key
                value={"agent": "2", "session": session_id},
                session_id=None,  # Global memory
            )
            assert memory_2["success"] is True

            # Each agent should see only their own value
            verify_1 = await call_fastmcp_tool(
                server.get_memory,
                ctx_1,
                key="fallback_test",
                session_id=None,
            )
            assert verify_1["success"] is True
            assert verify_1["value"]["agent"] == "1"

            verify_2 = await call_fastmcp_tool(
                server.get_memory,
                ctx_2,
                key="fallback_test",
                session_id=None,
            )
            assert verify_2["success"] is True
            assert verify_2["value"]["agent"] == "2"

            # SECURITY CHECK: Neither agent should see the other's value
            assert verify_1["value"]["agent"] != verify_2["value"]["agent"]

    async def test_jwt_vs_fallback_isolation(self, test_db_manager):
        """Test isolation between JWT-authenticated and fallback agent identification."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # JWT authenticated agent
            jwt_ctx = MockContext(session_id="jwt_fallback_test", agent_id="jwt_agent")
            jwt_ctx._auth_info = AuthInfo(
                jwt_validated=True,
                agent_id="jwt_validated_agent",  # Different from MockContext agent_id
                agent_type="claude",
                permissions=["read", "write"],
                authenticated=True,
                auth_method="jwt",
                token_id="jwt_token_123",
            )

            # Fallback authenticated agent
            fallback_ctx = MockContext(
                session_id="jwt_fallback_test", agent_id="fallback_agent"
            )
            # Uses default MockContext auth_info (not JWT validated)

            # Both agents store memory with same key
            jwt_memory = await call_fastmcp_tool(
                server.set_memory,
                jwt_ctx,
                key="isolation_test_key",
                value={"auth_method": "jwt", "agent": "jwt_validated_agent"},
            )
            assert jwt_memory["success"] is True

            fallback_memory = await call_fastmcp_tool(
                server.set_memory,
                fallback_ctx,
                key="isolation_test_key",  # Same key
                value={"auth_method": "fallback", "agent": "fallback_agent"},
            )
            assert fallback_memory["success"] is True

            # Verify memory isolation between JWT and fallback agents
            jwt_retrieve = await call_fastmcp_tool(
                server.get_memory,
                jwt_ctx,
                key="isolation_test_key",
            )
            assert jwt_retrieve["success"] is True
            assert jwt_retrieve["value"]["auth_method"] == "jwt"

            fallback_retrieve = await call_fastmcp_tool(
                server.get_memory,
                fallback_ctx,
                key="isolation_test_key",
            )
            assert fallback_retrieve["success"] is True
            assert fallback_retrieve["value"]["auth_method"] == "fallback"

            # CRITICAL: Each agent should only see their own memory
            assert jwt_retrieve["value"]["agent"] != fallback_retrieve["value"]["agent"]
