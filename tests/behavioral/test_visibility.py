"""
Behavioral tests for message visibility controls.

Tests visibility enforcement and agent isolation according to Phase 1 specification.
Ensures proper security boundaries between agents and sessions.

Modernized to use isolated_db fixture and real database operations instead of legacy mock patterns.
"""

# Import testing helpers from conftest.py
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.append(str(Path(__file__).parent.parent))
from conftest import call_fastmcp_tool, MockContext
from tests.fixtures.database import (
    DatabaseTestManager,
    patch_database_for_test,
)

from shared_context_server.server import (
    add_message,
    create_session,
    get_messages,
    get_session,
)


class TestVisibilityControls:
    """Test message visibility and agent isolation behaviors."""

    @pytest.fixture
    def alice_context(self):
        """Alice agent context."""
        return MockContext("alice_session", "alice")

    @pytest.fixture
    def bob_context(self):
        """Bob agent context."""
        return MockContext("bob_session", "bob")

    @pytest.fixture
    def charlie_context(self):
        """Charlie agent context (same type as Alice)."""
        return MockContext("charlie_session", "charlie")

    @pytest.fixture
    async def visibility_test_session(self, isolated_db: DatabaseTestManager):
        """Create a test session for visibility testing with real database operations."""
        
        with patch_database_for_test(isolated_db):
            # Create test session
            ctx = MockContext("visibility_test_agent")
            session_result = await call_fastmcp_tool(
                create_session, ctx, purpose="Visibility testing session"
            )
            session_id = session_result["session_id"]
            
            return session_id, isolated_db

    @pytest.mark.asyncio
    async def test_public_message_visibility(
        self, alice_context, bob_context, visibility_test_session
    ):
        """Test that public messages are visible to all agents."""

        session_id, db_manager = visibility_test_session

        with patch_database_for_test(db_manager):
            # Alice creates session and adds public message
            session_result = await call_fastmcp_tool(
                create_session,
                alice_context,
                purpose="Public message test",
                metadata={"test": "visibility"},
            )
            alice_session_id = session_result["session_id"]

            message_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=alice_session_id,
                content="This is a public announcement",
                visibility="public",
                metadata={"importance": "high"},
            )
            assert message_result["success"] is True

            # Bob should be able to see the public message
            bob_messages = await call_fastmcp_tool(
                get_messages, bob_context, session_id=alice_session_id
            )

            assert bob_messages["success"] is True
            assert len(bob_messages["messages"]) == 1
            assert (
                bob_messages["messages"][0]["content"]
                == "This is a public announcement"
            )
            assert (
                bob_messages["messages"][0]["sender"] == "alice"
            )  # Uses agent_id from MockContext
            assert bob_messages["messages"][0]["visibility"] == "public"

            # Bob can also see the session details
            session_view = await call_fastmcp_tool(
                get_session, bob_context, session_id=alice_session_id
            )
            assert session_view["success"] is True
            assert len(session_view["messages"]) == 1

    @pytest.mark.asyncio
    async def test_private_message_isolation(
        self, alice_context, bob_context, visibility_test_session
    ):
        """Test that private messages are only visible to their sender."""

        session_id, db_manager = visibility_test_session

        with patch_database_for_test(db_manager):

            # Alice creates session
            session_result = await call_fastmcp_tool(
                create_session,
                alice_context,
                purpose="Private message test",
                metadata={"test": "privacy"},
            )
            session_id = session_result["session_id"]

            # Alice adds a private message
            private_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="This is Alice's private thought",
                visibility="private",
                metadata={"confidential": True},
            )
            assert private_result["success"] is True

            # Alice adds a public message for comparison
            public_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="This is Alice's public message",
                visibility="public",
            )
            assert public_result["success"] is True

            # Alice should see both messages
            alice_messages = await call_fastmcp_tool(
                get_messages, alice_context, session_id=session_id
            )
            assert alice_messages["success"] is True
            assert len(alice_messages["messages"]) == 2

            message_contents = [msg["content"] for msg in alice_messages["messages"]]
            assert "This is Alice's private thought" in message_contents
            assert "This is Alice's public message" in message_contents

            # Bob should only see the public message
            bob_messages = await call_fastmcp_tool(
                get_messages, bob_context, session_id=session_id
            )

            assert bob_messages["success"] is True
            assert len(bob_messages["messages"]) == 1
            assert (
                bob_messages["messages"][0]["content"]
                == "This is Alice's public message"
            )
            assert bob_messages["messages"][0]["visibility"] == "public"

            # Verify Bob cannot see Alice's private message
            bob_message_contents = [msg["content"] for msg in bob_messages["messages"]]
            assert "This is Alice's private thought" not in bob_message_contents

    @pytest.mark.asyncio
    async def test_agent_only_message_behavior(
        self, alice_context, bob_context, charlie_context, visibility_test_session
    ):
        """Test agent_only message visibility (Phase 1 implementation)."""

        session_id, db_manager = visibility_test_session

        with patch_database_for_test(db_manager):

            # Alice creates session
            session_result = await call_fastmcp_tool(
                create_session,
                alice_context,
                purpose="Agent-only message test",
                metadata={"test": "agent-only"},
            )
            session_id = session_result["session_id"]

            # Alice adds agent_only message
            agent_only_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="Internal developer note",
                visibility="agent_only",
                metadata={"internal": True},
            )
            assert agent_only_result["success"] is True

            # Alice should see her own agent_only message
            alice_messages = await call_fastmcp_tool(
                get_messages, alice_context, session_id=session_id
            )
            assert alice_messages["success"] is True
            assert len(alice_messages["messages"]) == 1
            assert alice_messages["messages"][0]["content"] == "Internal developer note"

            # Bob (different agent) should not see Alice's agent_only message
            bob_messages = await call_fastmcp_tool(
                get_messages, bob_context, session_id=session_id
            )
            assert bob_messages["success"] is True
            assert len(bob_messages["messages"]) == 0

            # Charlie (same agent type) behavior depends on Phase 1 implementation
            # For Phase 1, agent_only behaves like private (sender only)
            charlie_messages = await call_fastmcp_tool(
                get_messages, charlie_context, session_id=session_id
            )
            assert charlie_messages["success"] is True
            # In Phase 1, Charlie shouldn't see Alice's agent_only message
            assert len(charlie_messages["messages"]) == 0

    @pytest.mark.asyncio
    async def test_mixed_visibility_scenarios(
        self, alice_context, bob_context, visibility_test_session
    ):
        """Test complex scenarios with multiple visibility levels."""

        session_id, db_manager = visibility_test_session

        with patch_database_for_test(db_manager):

            # Alice creates session
            session_result = await call_fastmcp_tool(
                create_session,
                alice_context,
                purpose="Mixed visibility test",
                metadata={"test": "mixed"},
            )
            session_id = session_result["session_id"]

            # Alice adds messages with different visibility levels
            messages_added = []

            # 1. Public message
            public_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="Public: Project kick-off meeting",
                visibility="public",
            )
            messages_added.append(("public", "Public: Project kick-off meeting"))

            # 2. Private message
            private_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="Private: Need to review Alice's code quality",
                visibility="private",
            )
            messages_added.append(
                ("private", "Private: Need to review Alice's code quality")
            )

            # 3. Agent-only message
            agent_only_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="Agent-only: Technical debt in authentication module",
                visibility="agent_only",
            )
            messages_added.append(
                ("agent_only", "Agent-only: Technical debt in authentication module")
            )

            assert all(
                result["success"]
                for result in [public_result, private_result, agent_only_result]
            )

            # Bob joins and adds his own messages
            await call_fastmcp_tool(
                add_message,
                bob_context,
                session_id=session_id,
                content="Public: I can help with testing",
                visibility="public",
            )
            messages_added.append(("public", "Public: I can help with testing"))

            await call_fastmcp_tool(
                add_message,
                bob_context,
                session_id=session_id,
                content="Private: Alice's code looks good to me",
                visibility="private",
            )
            messages_added.append(("private", "Private: Alice's code looks good to me"))

            # Now test what each agent can see

            # Alice's view: should see her own messages + Bob's public messages
            alice_view = await call_fastmcp_tool(
                get_messages, alice_context, session_id=session_id
            )
            assert alice_view["success"] is True

            alice_contents = [msg["content"] for msg in alice_view["messages"]]

            # Alice should see:
            # - Her public message
            # - Her private message
            # - Her agent_only message
            # - Bob's public message
            # Alice should NOT see:
            # - Bob's private message

            assert "Public: Project kick-off meeting" in alice_contents
            assert "Private: Need to review Alice's code quality" in alice_contents
            assert (
                "Agent-only: Technical debt in authentication module" in alice_contents
            )
            assert "Public: I can help with testing" in alice_contents
            assert "Private: Alice's code looks good to me" not in alice_contents

            # Bob's view: should see his own messages + Alice's public messages
            bob_view = await call_fastmcp_tool(
                get_messages, bob_context, session_id=session_id
            )
            assert bob_view["success"] is True

            bob_contents = [msg["content"] for msg in bob_view["messages"]]

            # Bob should see:
            # - Alice's public message
            # - His public message
            # - His private message
            # Bob should NOT see:
            # - Alice's private message
            # - Alice's agent_only message

            assert "Public: Project kick-off meeting" in bob_contents
            assert "Public: I can help with testing" in bob_contents
            assert "Private: Alice's code looks good to me" in bob_contents
            assert "Private: Need to review Alice's code quality" not in bob_contents
            assert (
                "Agent-only: Technical debt in authentication module"
                not in bob_contents
            )

    @pytest.mark.asyncio
    async def test_visibility_filter_parameter(
        self, alice_context, bob_context, visibility_test_session
    ):
        """Test the visibility_filter parameter in get_messages."""

        session_id, db_manager = visibility_test_session

        with patch_database_for_test(db_manager):

            # Alice creates session and adds mixed messages
            session_result = await call_fastmcp_tool(
                create_session,
                alice_context,
                purpose="Visibility filter test",
                metadata={"test": "filter"},
            )
            session_id = session_result["session_id"]

            # Add different types of messages
            await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="Public msg 1",
                visibility="public",
            )
            await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="Private msg 1",
                visibility="private",
            )
            await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="Public msg 2",
                visibility="public",
            )

            # Test filtering for public messages only
            public_only = await call_fastmcp_tool(
                get_messages,
                alice_context,
                session_id=session_id,
                visibility_filter="public",
            )

            assert public_only["success"] is True
            assert len(public_only["messages"]) == 2
            assert all(msg["visibility"] == "public" for msg in public_only["messages"])
            assert all(
                "Public msg" in msg["content"] for msg in public_only["messages"]
            )

            # Test filtering for private messages only
            private_only = await call_fastmcp_tool(
                get_messages,
                alice_context,
                session_id=session_id,
                visibility_filter="private",
            )

            assert private_only["success"] is True
            assert len(private_only["messages"]) == 1
            assert private_only["messages"][0]["visibility"] == "private"
            assert "Private msg 1" in private_only["messages"][0]["content"]

            # Test no filter (should respect normal visibility rules)
            all_accessible = await call_fastmcp_tool(
                get_messages, alice_context, session_id=session_id
            )

            assert all_accessible["success"] is True
            assert (
                len(all_accessible["messages"]) == 3
            )  # Alice can see all her messages

    @pytest.mark.asyncio
    async def test_session_isolation_security(
        self, alice_context, bob_context, visibility_test_session
    ):
        """Test that agents cannot access messages from sessions they shouldn't see."""

        session_id, db_manager = visibility_test_session

        with patch_database_for_test(db_manager):

            # Alice creates a private session
            alice_session = await call_fastmcp_tool(
                create_session,
                alice_context,
                purpose="Alice's private planning session",
                metadata={"confidential": True},
            )
            alice_session_id = alice_session["session_id"]

            # Alice adds sensitive information
            await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=alice_session_id,
                content="SENSITIVE: Database passwords need updating",
                visibility="private",
            )

            await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=alice_session_id,
                content="TODO: Security audit findings",
                visibility="public",  # Even public messages in this session
            )

            # Bob creates his own session
            bob_session = await call_fastmcp_tool(
                create_session,
                bob_context,
                purpose="Bob's testing session",
                metadata={"type": "testing"},
            )
            bob_session_id = bob_session["session_id"]

            await call_fastmcp_tool(
                add_message,
                bob_context,
                session_id=bob_session_id,
                content="Test plan for new features",
                visibility="public",
            )

            # Security test: Bob should not be able to see Alice's private messages
            # even if he knows the session ID
            bob_view_alice_session = await call_fastmcp_tool(
                get_messages, bob_context, session_id=alice_session_id
            )

            # Bob should be able to access the session but only see public messages
            assert bob_view_alice_session["success"] is True
            bob_accessible = [
                msg["content"] for msg in bob_view_alice_session["messages"]
            ]

            # Bob should NOT see Alice's private message
            assert "SENSITIVE: Database passwords need updating" not in bob_accessible
            # Bob SHOULD see Alice's public message (if the session allows cross-agent access)
            assert "TODO: Security audit findings" in bob_accessible

            # Verification: Alice should see all her own messages
            alice_view = await call_fastmcp_tool(
                get_messages, alice_context, session_id=alice_session_id
            )
            alice_accessible = [msg["content"] for msg in alice_view["messages"]]

            assert "SENSITIVE: Database passwords need updating" in alice_accessible
            assert "TODO: Security audit findings" in alice_accessible
