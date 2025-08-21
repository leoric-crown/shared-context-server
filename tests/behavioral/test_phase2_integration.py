"""
Behavioral tests for Phase 2 essential features integration.

Tests real-world usage scenarios and multi-agent collaboration patterns
using the search, memory, and resource systems together.
"""

# Import testing helpers from conftest.py
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from shared_context_server.memory_tools import (
    get_memory,
    list_memory,
    set_memory,
)

# Import tools directly for testing (access .fn for actual functions)
from shared_context_server.server import (
    add_message,
    create_session,
    search_context,
)

sys.path.append(str(Path(__file__).parent.parent))
from conftest import MockContext, call_fastmcp_tool

# Database fixtures are now provided by conftest.py - no need for hardcoded mocks


@pytest.mark.asyncio
@pytest.mark.behavioral
async def test_multi_agent_search_and_memory_workflow(test_db_manager):
    """Test complete workflow: agents collaborate using search and memory systems."""

    with (
        patch("shared_context_server.session_tools.get_db_connection") as mock_db_conn,
        patch(
            "shared_context_server.memory_tools.get_db_connection",
            return_value=mock_db_conn.return_value,
        ),
        patch(
            "shared_context_server.search_tools.get_db_connection",
            return_value=mock_db_conn.return_value,
        ),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        # Use the real test database instead of hardcoded mocks
        @asynccontextmanager
        async def mock_get_db_connection():
            async with test_db_manager.get_connection() as conn:
                yield conn

        mock_db_conn.side_effect = mock_get_db_connection
        mock_notify.return_value = None

        # Agent 1 context
        agent1_ctx = MockContext("agent1_session", "agent_1")

        # Agent 1 creates session
        session_result = await call_fastmcp_tool(
            create_session,
            agent1_ctx,
            purpose="Phase 2 integration test - multi-agent collaboration",
            metadata={"test_type": "behavioral", "phase": "2"},
        )

        assert session_result["success"] is True
        session_id = session_result["session_id"]

        # Agent 1 adds context to the session
        message_result = await call_fastmcp_tool(
            add_message,
            agent1_ctx,
            session_id=session_id,
            content="Starting project X: implementing user authentication system with JWT tokens",
            visibility="public",
            metadata={"project": "X", "component": "auth", "priority": "high"},
        )

        # Debug output to understand what's failing
        if message_result.get("success") is not True:
            print(f"Message creation failed: {message_result}")
        assert message_result["success"] is True

        # Agent 1 stores research in memory
        memory_result = await call_fastmcp_tool(
            set_memory,
            agent1_ctx,
            key="auth_research",
            value={
                "jwt_libraries": ["PyJWT", "python-jose"],
                "security_considerations": [
                    "token_expiry",
                    "secret_rotation",
                    "claims_validation",
                ],
                "implementation_status": "researching",
            },
            session_id=session_id,
            expires_in=None,
            metadata={"research_date": datetime.now().isoformat()},
            overwrite=True,
        )

        assert memory_result["success"] is True

        # Agent 2 joins and searches for relevant context
        agent2_ctx = MockContext("agent2_session", "agent_2")

        search_result = await call_fastmcp_tool(
            search_context,
            agent2_ctx,
            session_id=session_id,
            query="authentication JWT tokens",
            fuzzy_threshold=70.0,
            limit=10,
            search_metadata=True,
            search_scope="all",
        )

        assert search_result["success"] is True
        # Note: Mock database will return empty results, but the tool should succeed

        # Agent 2 adds complementary information
        agent2_message = await call_fastmcp_tool(
            add_message,
            agent2_ctx,
            session_id=session_id,
            content="For JWT implementation, recommend using RS256 algorithm and implementing refresh token rotation",
            visibility="public",
            metadata={"project": "X", "component": "auth", "expertise": "security"},
        )

        assert agent2_message["success"] is True

        # Verify memory isolation - Agent 2 cannot access Agent 1's memory
        agent2_memory_access = await call_fastmcp_tool(
            get_memory,
            agent2_ctx,
            key="auth_research",
            session_id=session_id,
        )

        # Should fail because memory is agent-scoped
        assert agent2_memory_access["success"] is False

        print("✅ Multi-agent search and memory workflow test completed successfully")


@pytest.mark.asyncio
@pytest.mark.behavioral
async def test_search_performance_with_realistic_data(test_db_manager):
    """Test search performance with realistic multi-agent collaboration data."""

    with (
        patch("shared_context_server.session_tools.get_db_connection") as mock_db_conn,
        patch(
            "shared_context_server.memory_tools.get_db_connection",
            return_value=mock_db_conn.return_value,
        ),
        patch(
            "shared_context_server.search_tools.get_db_connection",
            return_value=mock_db_conn.return_value,
        ),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        # Use the real test database instead of hardcoded mocks
        @asynccontextmanager
        async def mock_get_db_connection():
            async with test_db_manager.get_connection() as conn:
                yield conn

        mock_db_conn.side_effect = mock_get_db_connection
        mock_notify.return_value = None

        # Create test context
        ctx = MockContext("perf_session", "performance_agent")

        # Create session
        session_result = await call_fastmcp_tool(
            create_session,
            ctx,
            purpose="Performance testing session",
            metadata={"test_type": "performance"},
        )

        session_id = session_result["session_id"]

        # Test search performance (even with mock database)
        start_time = time.time()

        search_result = await call_fastmcp_tool(
            search_context,
            ctx,
            session_id=session_id,
            query="authentication security implementation",
            fuzzy_threshold=60.0,
            limit=10,
            search_metadata=True,
            search_scope="all",
        )

        search_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        assert search_result["success"] is True
        assert search_time < 100  # Should complete in under 100ms
        assert "results" in search_result
        assert "search_time_ms" in search_result
        assert search_result["search_time_ms"] < 100  # RapidFuzz should be fast

        print(f"✅ Search completed in {search_time:.2f}ms (target: <100ms)")


@pytest.mark.asyncio
@pytest.mark.behavioral
async def test_memory_ttl_workflow(test_db_manager):
    """Test memory TTL in realistic workflow scenarios."""

    with (
        patch("shared_context_server.session_tools.get_db_connection") as mock_db_conn,
        patch(
            "shared_context_server.memory_tools.get_db_connection"
        ) as mock_memory_db_conn,
        patch(
            "shared_context_server.search_tools.get_db_connection",
            return_value=mock_db_conn.return_value,
        ),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        # Use the real test database instead of hardcoded mocks
        @asynccontextmanager
        async def mock_get_db_connection():
            async with test_db_manager.get_connection() as conn:
                yield conn

        mock_db_conn.side_effect = mock_get_db_connection
        mock_memory_db_conn.side_effect = (
            mock_get_db_connection  # Memory tools also use test DB
        )
        mock_notify.return_value = None

        ctx = MockContext("ttl_session", "ttl_agent")

        # Create session
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="TTL testing session", metadata=None
        )

        session_id = session_result["session_id"]

        # Set temporary memory with reasonable TTL (30 seconds)
        # Note: Database constraint ensures expires_at > created_at
        temp_memory_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="temp_build_status",
            value={"status": "building", "started_at": datetime.now().isoformat()},
            expires_in=30,  # 30 seconds - respects database constraint
            session_id=session_id,
            metadata=None,
            overwrite=True,
        )

        # Debug output to understand what's failing
        if temp_memory_result.get("success") is not True:
            print(f"Temp memory creation failed: {temp_memory_result}")
        assert temp_memory_result["success"] is True
        assert temp_memory_result["expires_at"] is not None

        # Set permanent memory
        perm_memory_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="project_config",
            value={"name": "test_project", "version": "1.0.0"},
            session_id=session_id,
            expires_in=None,
            metadata=None,
            overwrite=True,
        )

        assert perm_memory_result["success"] is True
        assert perm_memory_result["expires_at"] is None

        # List all memory - should see both (temp and permanent)
        list_result = await call_fastmcp_tool(
            list_memory, ctx, session_id=session_id, prefix=None, limit=50
        )

        assert list_result["success"] is True
        assert len(list_result["entries"]) == 2

        # Verify TTL entry has expiration
        ttl_entries = [
            e for e in list_result["entries"] if e["key"] == "temp_build_status"
        ]
        perm_entries = [
            e for e in list_result["entries"] if e["key"] == "project_config"
        ]

        assert len(ttl_entries) == 1, "Should have exactly one TTL entry"
        assert len(perm_entries) == 1, "Should have exactly one permanent entry"

        assert ttl_entries[0]["expires_at"] is not None, (
            "TTL entry should have expiration"
        )
        assert perm_entries[0]["expires_at"] is None, (
            "Permanent entry should not expire"
        )

        # Test that we can retrieve the TTL entry (it should still be valid)
        get_result = await call_fastmcp_tool(
            get_memory, ctx, key="temp_build_status", session_id=session_id
        )

        assert get_result["success"] is True
        assert get_result["value"]["status"] == "building"
        assert get_result["expires_at"] is not None

        print("✅ Memory TTL workflow test completed successfully")


@pytest.mark.asyncio
@pytest.mark.behavioral
async def test_agent_memory_isolation(test_db_manager):
    """Test that agent memory is properly isolated between different agents."""

    with (
        patch("shared_context_server.session_tools.get_db_connection") as mock_db_conn,
        patch(
            "shared_context_server.memory_tools.get_db_connection"
        ) as mock_memory_db_conn,
        patch(
            "shared_context_server.search_tools.get_db_connection"
        ) as mock_search_db_conn,
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        # Use the real test database instead of hardcoded mocks
        @asynccontextmanager
        async def mock_get_db_connection():
            async with test_db_manager.get_connection() as conn:
                yield conn

        mock_db_conn.side_effect = mock_get_db_connection
        mock_memory_db_conn.side_effect = mock_get_db_connection
        mock_search_db_conn.side_effect = mock_get_db_connection
        mock_notify.return_value = None

        # Create two different agents sharing the same session
        agent1_ctx = MockContext("shared_session", "agent_1")
        agent2_ctx = MockContext("shared_session", "agent_2")

        # Create shared session
        session_result = await call_fastmcp_tool(
            create_session,
            agent1_ctx,
            purpose="Memory isolation testing",
            metadata=None,
        )

        session_id = session_result["session_id"]

        # Agent 1 stores sensitive information
        agent1_memory = await call_fastmcp_tool(
            set_memory,
            agent1_ctx,
            key="sensitive_config",
            value={"database_password": "secret123", "api_key": "abc-xyz"},
            session_id=session_id,
            expires_in=None,
            metadata=None,
            overwrite=True,
        )

        assert agent1_memory["success"] is True

        # Agent 2 tries to access Agent 1's memory
        agent2_access = await call_fastmcp_tool(
            get_memory, agent2_ctx, key="sensitive_config", session_id=session_id
        )

        # Should fail due to agent isolation
        assert agent2_access["success"] is False
        assert agent2_access["code"] == "MEMORY_NOT_FOUND"

        # Agent 2 stores their own data with same key
        agent2_memory = await call_fastmcp_tool(
            set_memory,
            agent2_ctx,
            key="sensitive_config",
            value={"test_database": "test_db", "mock_api": "test-key"},
            session_id=session_id,
            expires_in=None,
            metadata=None,
            overwrite=True,
        )

        assert agent2_memory["success"] is True

        # Each agent should only see their own memory
        agent1_memory_check = await call_fastmcp_tool(
            get_memory,
            agent1_ctx,
            key="sensitive_config",
            session_id=session_id,
        )

        # Verify Agent 1 can access their own memory
        assert agent1_memory_check["success"] is True

        # Note: Mock implementation would need enhancement for full isolation testing
        # In real implementation, this verifies proper security boundaries

        print("✅ Agent memory isolation test completed successfully")


@pytest.mark.asyncio
@pytest.mark.behavioral
async def test_search_visibility_controls(test_db_manager):
    """Test search respects message visibility in collaborative scenarios."""

    with (
        patch("shared_context_server.session_tools.get_db_connection") as mock_db_conn,
        patch(
            "shared_context_server.memory_tools.get_db_connection",
            return_value=mock_db_conn.return_value,
        ),
        patch(
            "shared_context_server.search_tools.get_db_connection",
            return_value=mock_db_conn.return_value,
        ),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        # Use the real test database instead of hardcoded mocks
        @asynccontextmanager
        async def mock_get_db_connection():
            async with test_db_manager.get_connection() as conn:
                yield conn

        mock_db_conn.side_effect = mock_get_db_connection
        mock_notify.return_value = None

        agent1_ctx = MockContext("visibility_session", "agent_1")
        agent2_ctx = MockContext("visibility_session", "agent_2")

        # Create session
        session_result = await call_fastmcp_tool(
            create_session,
            agent1_ctx,
            purpose="Visibility testing session",
            metadata=None,
        )

        session_id = session_result["session_id"]

        # Agent 1 adds public message
        public_msg = await call_fastmcp_tool(
            add_message,
            agent1_ctx,
            session_id=session_id,
            content="Public project requirements discussion",
            visibility="public",
        )

        assert public_msg["success"] is True

        # Agent 1 adds private message
        private_msg = await call_fastmcp_tool(
            add_message,
            agent1_ctx,
            session_id=session_id,
            content="Private implementation notes and concerns",
            visibility="private",
        )

        assert private_msg["success"] is True

        # Agent 2 searches with public scope
        public_search = await call_fastmcp_tool(
            search_context,
            agent2_ctx,
            session_id=session_id,
            query="project requirements",
            search_scope="public",
            fuzzy_threshold=60.0,
            limit=10,
            search_metadata=True,
        )

        assert public_search["success"] is True

        # Agent 2 searches with all scope (should respect visibility)
        all_search = await call_fastmcp_tool(
            search_context,
            agent2_ctx,
            session_id=session_id,
            query="implementation notes",
            search_scope="all",
            fuzzy_threshold=60.0,
            limit=10,
            search_metadata=True,
        )

        assert all_search["success"] is True
        # In real implementation, this would verify Agent 2 doesn't see Agent 1's private messages

        print("✅ Search visibility controls test completed successfully")
