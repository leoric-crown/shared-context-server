"""
Security tests for agent memory isolation.

Tests that agents cannot access each other's private memory (both global and session-scoped).
Uses real database connections and authentication contexts to validate security model.
"""

import os
from unittest.mock import patch

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestAgentMemoryIsolation:
    """Test agent memory isolation security controls."""

    async def test_global_memory_isolation(self, test_db_manager):
        """Test that agents cannot access each other's global memory."""
        from shared_context_server import server

        # Set up API key to match MockContext
        with (
            patch.dict(
                os.environ,
                {
                    "API_KEY": "T34PEv/IEUoVx18/g+xOIk/zT4S/MaQUm0dlU9jQhXk=",
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ),
            patch_database_connection(test_db_manager),
        ):
            # Set up two different agent contexts
            agent_a_ctx = MockContext(session_id="test_session", agent_id="agent_a")
            agent_b_ctx = MockContext(session_id="test_session", agent_id="agent_b")

            # Agent A stores private global memory
            result_a = await call_fastmcp_tool(
                server.set_memory,
                agent_a_ctx,
                key="agent_a_secret",
                value={
                    "secret": "This is Agent A's private data",
                    "confidential": True,
                },
                session_id=None,  # Global memory
            )
            assert result_a["success"] is True

            # Agent B attempts to access Agent A's private memory
            result_b = await call_fastmcp_tool(
                server.get_memory,
                agent_b_ctx,
                key="agent_a_secret",
                session_id=None,  # Global memory
            )

            # CRITICAL SECURITY TEST: Agent B should NOT be able to access Agent A's memory
            assert result_b["success"] is False
            assert result_b["code"] == "MEMORY_NOT_FOUND"
            assert "not found" in result_b["error"].lower()

            # Verify Agent A can still access their own memory
            verify_a = await call_fastmcp_tool(
                server.get_memory,
                agent_a_ctx,
                key="agent_a_secret",
                session_id=None,
            )
            assert verify_a["success"] is True
            assert verify_a["value"]["secret"] == "This is Agent A's private data"

    async def test_session_scoped_memory_isolation(self, test_db_manager):
        """Test that agents cannot access each other's session-scoped memory."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Set up two different agent contexts in the same session
            agent_a_ctx = MockContext(session_id="memory_test", agent_id="agent_a")
            agent_b_ctx = MockContext(session_id="memory_test", agent_id="agent_b")

            # Create session first
            session_result = await call_fastmcp_tool(
                server.create_session,
                agent_a_ctx,
                purpose="Session-scoped memory isolation test",
            )
            session_id = session_result["session_id"]

            # Agent A stores session-scoped private memory
            result_a = await call_fastmcp_tool(
                server.set_memory,
                agent_a_ctx,
                key="session_secret",
                value={
                    "data": "Agent A's session-specific secret",
                    "session_id": session_id,
                },
                session_id=session_id,  # Session-scoped memory
            )
            if not result_a["success"]:
                print(f"Session memory set failed: {result_a}")
            assert result_a["success"] is True

            # Agent B attempts to access Agent A's session memory
            result_b = await call_fastmcp_tool(
                server.get_memory,
                agent_b_ctx,
                key="session_secret",
                session_id=session_id,
            )

            # CRITICAL SECURITY TEST: Agent B should NOT access Agent A's session memory
            assert result_b["success"] is False
            assert result_b["code"] == "MEMORY_NOT_FOUND"

            # Verify Agent A can still access their own session memory
            verify_a = await call_fastmcp_tool(
                server.get_memory,
                agent_a_ctx,
                key="session_secret",
                session_id=session_id,
            )
            assert verify_a["success"] is True
            assert verify_a["value"]["data"] == "Agent A's session-specific secret"

    async def test_cross_session_memory_isolation(self, test_db_manager):
        """Test that session-scoped memory is isolated between sessions."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Same agent in different sessions
            agent_ctx_s1 = MockContext(session_id="session_1", agent_id="test_agent")
            agent_ctx_s2 = MockContext(session_id="session_2", agent_id="test_agent")

            # Create sessions first
            session_1_result = await call_fastmcp_tool(
                server.create_session,
                agent_ctx_s1,
                purpose="Cross-session memory test - session 1",
            )
            session_1 = session_1_result["session_id"]

            session_2_result = await call_fastmcp_tool(
                server.create_session,
                agent_ctx_s2,
                purpose="Cross-session memory test - session 2",
            )
            session_2 = session_2_result["session_id"]

            # Store memory in session 1
            result_s1 = await call_fastmcp_tool(
                server.set_memory,
                agent_ctx_s1,
                key="cross_session_key",
                value={"session": "session_1_data"},
                session_id=session_1,
            )
            assert result_s1["success"] is True

            # Store memory in session 2 with same key
            result_s2 = await call_fastmcp_tool(
                server.set_memory,
                agent_ctx_s2,
                key="cross_session_key",
                value={"session": "session_2_data"},
                session_id=session_2,
            )
            assert result_s2["success"] is True

            # Verify session isolation: each session should have its own value
            verify_s1 = await call_fastmcp_tool(
                server.get_memory,
                agent_ctx_s1,
                key="cross_session_key",
                session_id=session_1,
            )
            assert verify_s1["success"] is True
            assert verify_s1["value"]["session"] == "session_1_data"

            verify_s2 = await call_fastmcp_tool(
                server.get_memory,
                agent_ctx_s2,
                key="cross_session_key",
                session_id=session_2,
            )
            assert verify_s2["success"] is True
            assert verify_s2["value"]["session"] == "session_2_data"

    async def test_memory_list_isolation(self, test_db_manager):
        """Test that agents can only list their own memory entries."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Set up two agents
            agent_a_ctx = MockContext(session_id="list_test", agent_id="agent_a")
            agent_b_ctx = MockContext(session_id="list_test", agent_id="agent_b")

            # Agent A stores multiple memory entries
            for i in range(3):
                await call_fastmcp_tool(
                    server.set_memory,
                    agent_a_ctx,
                    key=f"agent_a_key_{i}",
                    value={"agent": "a", "index": i},
                    session_id=None,  # Global memory
                )

            # Agent B stores different memory entries
            for i in range(2):
                await call_fastmcp_tool(
                    server.set_memory,
                    agent_b_ctx,
                    key=f"agent_b_key_{i}",
                    value={"agent": "b", "index": i},
                    session_id=None,  # Global memory
                )

            # Agent A lists their memory
            list_a = await call_fastmcp_tool(
                server.list_memory,
                agent_a_ctx,
                session_id=None,
                limit=10,
            )
            assert list_a["success"] is True
            assert len(list_a["entries"]) == 3

            # Verify all entries belong to Agent A
            for entry in list_a["entries"]:
                assert entry["key"].startswith("agent_a_key_")

            # Agent B lists their memory
            list_b = await call_fastmcp_tool(
                server.list_memory,
                agent_b_ctx,
                session_id=None,
                limit=10,
            )
            assert list_b["success"] is True
            assert len(list_b["entries"]) == 2

            # Verify all entries belong to Agent B
            for entry in list_b["entries"]:
                assert entry["key"].startswith("agent_b_key_")

    async def test_uat_reproduction_memory_isolation(self, test_db_manager):
        """Reproduce the exact UAT scenario that claimed memory isolation was broken."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Recreate UAT scenario exactly as described
            agent_1_ctx = MockContext(
                session_id="uat_test", agent_id="test-phase3-complete"
            )
            agent_2_ctx = MockContext(
                session_id="uat_test", agent_id="different-agent-test"
            )

            # Agent 1 stores private memory (as described in UAT)
            result_store = await call_fastmcp_tool(
                server.set_memory,
                agent_1_ctx,
                key="agent1_private_global",
                value={"secret": "this should be private to agent1"},
                session_id=None,  # Global memory
            )
            assert result_store["success"] is True

            # Agent 2 attempts to access Agent 1's private memory (UAT claimed this succeeded)
            result_access = await call_fastmcp_tool(
                server.get_memory,
                agent_2_ctx,
                key="agent1_private_global",
                session_id=None,
            )

            # CRITICAL SECURITY TEST: This should FAIL, not succeed as UAT claimed
            assert result_access["success"] is False
            assert result_access["code"] == "MEMORY_NOT_FOUND"

            # If this assertion fails, then the UAT finding is correct and we have a real vulnerability
            # If this assertion passes, then the UAT finding was a false positive

            print(f"UAT Reproduction Result: {result_access}")
            print("If success=False, UAT finding was a FALSE POSITIVE")
            print(
                "If success=True, UAT finding was CORRECT and we have a real vulnerability"
            )

    async def test_agent_context_derivation_security(self, test_db_manager):
        """Test that agent identity derivation doesn't create cross-contamination."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            # Test scenario where agents might get same derived IDs
            session_id = "context_derivation_test"

            # Create contexts that could potentially have ID collision
            agent_1_ctx = MockContext(session_id=session_id, agent_id="agent_1")
            agent_2_ctx = MockContext(session_id=session_id, agent_id="agent_2")

            # Store memory with each agent
            result_1 = await call_fastmcp_tool(
                server.set_memory,
                agent_1_ctx,
                key="collision_test",
                value={"owner": "agent_1"},
                session_id=None,
            )
            assert result_1["success"] is True

            result_2 = await call_fastmcp_tool(
                server.set_memory,
                agent_2_ctx,
                key="collision_test",
                value={"owner": "agent_2"},
                session_id=None,
            )
            assert result_2["success"] is True

            # Verify each agent can only see their own value
            verify_1 = await call_fastmcp_tool(
                server.get_memory,
                agent_1_ctx,
                key="collision_test",
                session_id=None,
            )
            assert verify_1["success"] is True
            assert verify_1["value"]["owner"] == "agent_1"

            verify_2 = await call_fastmcp_tool(
                server.get_memory,
                agent_2_ctx,
                key="collision_test",
                session_id=None,
            )
            assert verify_2["success"] is True
            assert verify_2["value"]["owner"] == "agent_2"
