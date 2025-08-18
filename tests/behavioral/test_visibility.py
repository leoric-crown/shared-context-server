"""
Behavioral tests for message visibility controls.

Tests visibility enforcement and agent isolation according to Phase 1 specification.
Ensures proper security boundaries between agents and sessions.
"""

# FastMCP testing helpers (inlined for simplicity)
import inspect
from unittest.mock import AsyncMock, patch

import pytest
from pydantic.fields import FieldInfo

from shared_context_server.auth import AuthInfo
from shared_context_server.server import (
    add_message,
    create_session,
    get_messages,
    get_session,
)


def extract_field_defaults(fastmcp_tool):
    """Extract actual default values from FastMCP tool function."""
    from pydantic_core import PydanticUndefined
    defaults = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for param_name, param in sig.parameters.items():
        if param_name == "ctx":  # Skip context parameter
            continue
        if isinstance(param.default, FieldInfo):
            # Only include if it has a real default value (not required)
            if param.default.default is not PydanticUndefined:
                defaults[param_name] = param.default.default
        elif param.default != inspect.Parameter.empty:
            defaults[param_name] = param.default
    return defaults


async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """Call FastMCP tool with proper default handling."""
    defaults = extract_field_defaults(fastmcp_tool)
    # kwargs should override defaults, not the other way around
    call_args = {**defaults, **kwargs}
    
    # Pass ctx as keyword argument to avoid positional conflicts with exclude_args
    return await fastmcp_tool.fn(ctx=ctx, **call_args)


class MockContext:
    """Mock context for FastMCP testing."""

    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        # Set up authentication using AuthInfo pattern
        self._auth_info = AuthInfo(
            jwt_validated=False,
            agent_id=agent_id,
            agent_type="test",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="api_key",
            token_id=None,
        )

    # Backward compatibility properties for old attribute access
    @property
    def agent_id(self) -> str:
        return self._auth_info.agent_id

    @agent_id.setter
    def agent_id(self, value: str) -> None:
        self._auth_info.agent_id = value

    @property
    def agent_type(self) -> str:
        return self._auth_info.agent_type


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
    def mock_database_with_visibility(self):
        """Mock database that properly handles visibility filtering."""

        sessions = {}
        messages = {}
        message_id_counter = [1]

        async def mock_execute(query, params=()):
            nonlocal sessions, messages, message_id_counter

            if "INSERT INTO sessions" in query:
                session_id, purpose, created_by, metadata, created_at, updated_at = (
                    params
                )
                sessions[session_id] = {
                    "id": session_id,
                    "purpose": purpose,
                    "created_by": created_by,
                    "metadata": metadata,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "is_active": True,
                }
                return AsyncMock(lastrowid=None)

            if "SELECT * FROM sessions WHERE id = ?" in query:
                session_id = params[0]
                session = sessions.get(session_id)
                return AsyncMock(fetchone=AsyncMock(return_value=session))

            if "INSERT INTO messages" in query:
                (
                    session_id,
                    sender,
                    sender_type,
                    content,
                    visibility,
                    metadata,
                    parent_id,
                    timestamp,
                ) = params
                message_id = message_id_counter[0]
                message_id_counter[0] += 1

                messages[message_id] = {
                    "id": message_id,
                    "session_id": session_id,
                    "sender": sender,
                    "sender_type": sender_type,
                    "content": content,
                    "visibility": visibility,
                    "metadata": metadata,
                    "timestamp": timestamp,
                    "parent_message_id": parent_id,
                }
                return AsyncMock(lastrowid=message_id)

            if "SELECT id FROM sessions WHERE id = ?" in query:
                session_id = params[0]
                session = sessions.get(session_id)
                return AsyncMock(
                    fetchone=AsyncMock(
                        return_value={"id": session_id} if session else None
                    )
                )

            if "SELECT * FROM messages" in query:
                session_id = params[0]

                # New parameter format analysis
                # For visibility_filter queries:
                #   - public: (session_id, limit, offset)
                #   - private/agent_only: (session_id, agent_id, limit, offset)
                # For normal queries: (session_id, agent_id, agent_id, limit, offset)

                agent_id = None
                visibility_filter = None

                # Determine query type by analyzing the SQL and parameters
                if "visibility = 'public'" in query and len(params) == 3:
                    # Public visibility filter: no agent_id needed
                    visibility_filter = "public"
                elif (
                    "visibility = 'private'" in query
                    or "visibility = 'agent_only'" in query
                ) and len(params) == 4:
                    # Private or agent_only filter
                    agent_id = params[1]
                    if "private" in query:
                        visibility_filter = "private"
                    elif "agent_only" in query:
                        visibility_filter = "agent_only"
                elif len(params) == 5:
                    # Normal query without visibility filter: (session_id, agent_id, agent_id, limit, offset)
                    agent_id = params[1]  # Use first agent_id
                elif len(params) >= 2:
                    # Fallback case
                    agent_id = params[1]

                # Filter messages based on visibility rules
                filtered_messages = []
                for msg in messages.values():
                    if msg["session_id"] == session_id:
                        should_include = False

                        # First apply normal visibility rules
                        if msg["visibility"] == "public" or (
                            msg["visibility"] == "private" and msg["sender"] == agent_id
                        ):
                            should_include = True
                        elif msg["visibility"] == "agent_only":
                            # For Phase 1, agent_only behaves like private
                            # In Phase 2+, this would check agent_type
                            should_include = msg["sender"] == agent_id

                        # Then apply visibility_filter if provided
                        if should_include and visibility_filter:
                            should_include = msg["visibility"] == visibility_filter

                        if should_include:
                            filtered_messages.append(msg)

                # Sort by timestamp
                filtered_messages.sort(key=lambda x: x["timestamp"])
                return AsyncMock(fetchall=AsyncMock(return_value=filtered_messages))

            if "SELECT COUNT(*)" in query:
                # Handle count queries for pagination
                session_id = params[0]

                # Apply same filtering logic as SELECT * query to get accurate count
                agent_id = None
                visibility_filter = None

                # Determine query type by analyzing the SQL and parameters
                if "visibility = 'public'" in query and len(params) == 3:
                    visibility_filter = "public"
                elif (
                    "visibility = 'private'" in query
                    or "visibility = 'agent_only'" in query
                ) and len(params) == 4:
                    agent_id = params[1]
                    if "private" in query:
                        visibility_filter = "private"
                    elif "agent_only" in query:
                        visibility_filter = "agent_only"
                elif len(params) >= 2:
                    agent_id = params[1]

                # Count messages matching the criteria
                count = 0
                for msg in messages.values():
                    if msg["session_id"] == session_id:
                        should_include = False

                        # Apply normal visibility rules
                        if msg["visibility"] == "public" or (
                            msg["visibility"] == "private" and msg["sender"] == agent_id
                        ):
                            should_include = True
                        elif msg["visibility"] == "agent_only":
                            should_include = msg["sender"] == agent_id

                        # Apply visibility_filter if provided
                        if should_include and visibility_filter:
                            should_include = msg["visibility"] == visibility_filter

                        if should_include:
                            count += 1

                return AsyncMock(fetchone=AsyncMock(return_value=[count]))

            if "INSERT INTO audit_log" in query:
                return AsyncMock()

            return AsyncMock()

        mock_conn = AsyncMock()
        mock_conn.execute = mock_execute
        mock_conn.commit = AsyncMock()

        return mock_conn

    @pytest.mark.asyncio
    async def test_public_message_visibility(
        self, alice_context, bob_context, mock_database_with_visibility
    ):
        """Test that public messages are visible to all agents."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            mock_db_conn.return_value.__aenter__.return_value = (
                mock_database_with_visibility
            )

            # Alice creates session and adds public message
            session_result = await call_fastmcp_tool(
                create_session,
                alice_context,
                purpose="Public message test",
                metadata={"test": "visibility"},
            )
            session_id = session_result["session_id"]

            message_result = await call_fastmcp_tool(
                add_message,
                alice_context,
                session_id=session_id,
                content="This is a public announcement",
                visibility="public",
                metadata={"importance": "high"},
            )
            # Debug output to understand what's failing
            if message_result.get("success") is not True:
                print(f"Message creation failed: {message_result}")
            assert message_result["success"] is True

            # Bob should be able to see the public message
            bob_messages = await call_fastmcp_tool(
                get_messages, bob_context, session_id=session_id
            )

            # Debug output to understand what's failing
            if bob_messages.get("success") is not True:
                print(f"Bob get_messages failed: {bob_messages}")

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
                get_session, bob_context, session_id=session_id
            )
            assert session_view["success"] is True
            assert len(session_view["messages"]) == 1

    @pytest.mark.asyncio
    async def test_private_message_isolation(
        self, alice_context, bob_context, mock_database_with_visibility
    ):
        """Test that private messages are only visible to their sender."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            mock_db_conn.return_value.__aenter__.return_value = (
                mock_database_with_visibility
            )

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
        self, alice_context, bob_context, charlie_context, mock_database_with_visibility
    ):
        """Test agent_only message visibility (Phase 1 implementation)."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            mock_db_conn.return_value.__aenter__.return_value = (
                mock_database_with_visibility
            )

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
        self, alice_context, bob_context, mock_database_with_visibility
    ):
        """Test complex scenarios with multiple visibility levels."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            mock_db_conn.return_value.__aenter__.return_value = (
                mock_database_with_visibility
            )

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
        self, alice_context, bob_context, mock_database_with_visibility
    ):
        """Test the visibility_filter parameter in get_messages."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            mock_db_conn.return_value.__aenter__.return_value = (
                mock_database_with_visibility
            )

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
        self, alice_context, bob_context, mock_database_with_visibility
    ):
        """Test that agents cannot access messages from sessions they shouldn't see."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            mock_db_conn.return_value.__aenter__.return_value = (
                mock_database_with_visibility
            )

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
