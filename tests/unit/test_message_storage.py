"""
Unit tests for message storage tools.

Tests the add_message and get_messages tools according to Phase 1 specification.
"""

# Import testing helpers from conftest.py
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent))
from conftest import MockContext, call_fastmcp_tool

from shared_context_server.server import add_message, get_messages


class TestAddMessage:
    """Test add_message tool functionality."""

    @pytest.fixture
    def mock_context(self):
        """Mock MCP context for testing."""
        return MockContext("test_session", "test_agent")

    @pytest.mark.asyncio
    async def test_add_message_success(self, mock_context):
        """Test successful message addition."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
            patch(
                "shared_context_server.session_tools.validate_agent_context_or_error"
            ) as mock_validate,
        ):
            # Mock validation to return successful agent context
            mock_validate.return_value = {
                "agent_id": "test_agent",
                "agent_type": "test",
                "permissions": ["read", "write"],
            }

            # Setup mocks
            mock_conn = AsyncMock()

            # Create separate cursors for different calls
            session_cursor = AsyncMock()
            session_cursor.fetchone.return_value = {
                "id": "session_abc123"
            }  # Session exists

            insert_cursor = AsyncMock()
            insert_cursor.lastrowid = 123  # Message ID

            audit_cursor = AsyncMock()

            # Set up execute to return different cursors for different queries
            def mock_execute(query, params=None):
                if "SELECT id FROM sessions" in query:
                    return session_cursor
                if "INSERT INTO messages" in query:
                    return insert_cursor
                if "INSERT INTO audit_log" in query:
                    return audit_cursor
                return AsyncMock()

            mock_conn.execute.side_effect = mock_execute
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            # Test message addition
            result = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id="session_abc123",
                content="Hello world",
                visibility="public",
                metadata={"test": True},
                parent_message_id=None,
            )

            # Verify results
            assert result["success"] is True
            assert result["message_id"] == 123
            assert "timestamp" in result

            # Verify database calls
            assert (
                mock_conn.execute.call_count >= 2
            )  # Session check + insert (audit log may or may not be called depending on config)
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message_invalid_visibility(self, mock_context):
        """Test message addition with invalid visibility level."""

        # No patches needed with direct context passing
        result = await call_fastmcp_tool(
            add_message,
            mock_context,
            session_id="session_abc123",
            content="Hello world",
            visibility="invalid_visibility",
        )

        assert result["success"] is False
        assert result["code"] == "INVALID_VISIBILITY"

    @pytest.mark.asyncio
    async def test_add_message_session_not_found(self, mock_context):
        """Test message addition when session doesn't exist."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = None  # Session doesn't exist
            mock_conn.execute.return_value = mock_cursor
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id="session_nonexistent",
                content="Hello world",
            )

            assert result["success"] is False
            assert result["code"] == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_message_empty_content(self, mock_context):
        """Test message addition with empty content."""

        # No patches needed with direct context passing
        result = await call_fastmcp_tool(
            add_message,
            mock_context,
            session_id="session_abc123",
            content="   ",  # Empty after sanitization
            visibility="public",
        )

        assert result["success"] is False
        assert result["code"] == "INVALID_INPUT"
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_add_message_with_threading(self, mock_context):
        """Test message addition with parent message ID."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = {"id": "session_abc123"}
            mock_cursor.lastrowid = 124
            mock_conn.execute.return_value = mock_cursor
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                add_message,
                mock_context,
                session_id="session_abc123",
                content="Reply message",
                visibility="public",
                parent_message_id=123,
            )

            assert result["success"] is True
            assert result["message_id"] == 124

            # Verify parent_message_id was included in INSERT
            insert_call = mock_conn.execute.call_args_list[1]  # Second call is INSERT
            assert 123 in insert_call[0][1]  # parent_message_id in parameters


class TestGetMessages:
    """Test get_messages tool functionality."""

    @pytest.fixture
    def mock_context(self):
        """Mock MCP context for testing."""
        return MockContext("test_session", "test_agent")

    @pytest.fixture
    def mock_message_rows(self):
        """Mock message database rows with different visibility levels."""
        return [
            {
                "id": 1,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "Public message",
                "visibility": "public",
                "metadata": None,
                "timestamp": "2025-01-01T10:00:00+00:00",
                "parent_message_id": None,
            },
            {
                "id": 2,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "Private message",
                "visibility": "private",
                "metadata": '{"private": true}',
                "timestamp": "2025-01-01T10:01:00+00:00",
                "parent_message_id": None,
            },
            {
                "id": 3,
                "session_id": "session_abc123",
                "sender": "other_agent",
                "content": "Another public message",
                "visibility": "public",
                "metadata": None,
                "timestamp": "2025-01-01T10:02:00+00:00",
                "parent_message_id": 1,
            },
        ]

    @pytest.mark.asyncio
    async def test_get_messages_success(self, mock_context, mock_message_rows):
        """Test successful message retrieval."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()

            # Set up row factory like real connection
            mock_conn.row_factory = None

            # Track execute call count to return different results for count vs select
            call_count = [0]

            async def mock_execute(query, params):
                call_count[0] += 1
                mock_cursor = AsyncMock()

                if "SELECT COUNT(*)" in query:
                    # First call: COUNT query - return count of messages (3)
                    mock_cursor.fetchone.return_value = [3]
                    return mock_cursor
                if "SELECT id FROM sessions" in query:
                    # Session existence check - return valid session
                    mock_cursor.fetchone.return_value = {"id": "session_abc123"}
                    return mock_cursor
                # Second call: SELECT query - return message rows
                mock_cursor.fetchall.return_value = mock_message_rows
                return mock_cursor

            mock_conn.execute.side_effect = mock_execute
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                get_messages, mock_context, session_id="session_abc123"
            )

            # Debug output to understand what's failing
            if result.get("success") is not True:
                print(f"get_messages failed: {result}")

            assert result["success"] is True
            assert result["count"] == 3
            assert len(result["messages"]) == 3
            assert result["has_more"] is False  # Less than limit

    @pytest.mark.asyncio
    async def test_get_messages_pagination(self, mock_context, mock_message_rows):
        """Test message retrieval with pagination."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()

            # Set up row factory like real connection
            mock_conn.row_factory = None

            # Track execute call count to return different results for count vs select
            limited_rows = mock_message_rows[:2]

            async def mock_execute(query, params):
                mock_cursor = AsyncMock()

                if "SELECT COUNT(*)" in query:
                    # COUNT query - return total count (3), but only 2 will be returned due to limit
                    mock_cursor.fetchone.return_value = [3]
                    return mock_cursor
                if "SELECT id FROM sessions" in query:
                    # Session existence check - return valid session
                    mock_cursor.fetchone.return_value = {"id": "session_abc123"}
                    return mock_cursor
                # SELECT query - return limited rows for pagination test
                mock_cursor.fetchall.return_value = limited_rows
                return mock_cursor

            mock_conn.execute.side_effect = mock_execute
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                get_messages,
                mock_context,
                session_id="session_abc123",
                limit=2,
                offset=0,
            )

            assert result["success"] is True
            assert result["count"] == 2
            assert result["has_more"] is True  # Reached limit, might have more

            # Verify query parameters
            query_call = mock_conn.execute.call_args
            assert 2 in query_call[0][1]  # limit parameter
            assert 0 in query_call[0][1]  # offset parameter

    @pytest.mark.asyncio
    async def test_get_messages_visibility_filtering(self, mock_context):
        """Test message visibility filtering works correctly."""

        # Mock messages with different senders and visibility
        mixed_messages = [
            {
                "id": 1,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "My public message",
                "visibility": "public",
                "metadata": None,
                "timestamp": "2025-01-01T10:00:00+00:00",
                "parent_message_id": None,
            },
            {
                "id": 2,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "My private message",
                "visibility": "private",
                "metadata": None,
                "timestamp": "2025-01-01T10:01:00+00:00",
                "parent_message_id": None,
            },
            # Note: Other agent's private message should not be returned by query
        ]

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()

            # Set up row factory like real connection
            mock_conn.row_factory = None

            async def mock_execute(query, params):
                mock_cursor = AsyncMock()

                if "SELECT COUNT(*)" in query:
                    # COUNT query - return count of mixed messages (2)
                    mock_cursor.fetchone.return_value = [2]
                    return mock_cursor
                if "SELECT id FROM sessions" in query:
                    # Session existence check - return valid session
                    mock_cursor.fetchone.return_value = {"id": "session_abc123"}
                    return mock_cursor
                # SELECT query - return mixed messages
                mock_cursor.fetchall.return_value = mixed_messages
                return mock_cursor

            mock_conn.execute.side_effect = mock_execute
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                get_messages, mock_context, session_id="session_abc123"
            )

            assert result["success"] is True
            assert len(result["messages"]) == 2

            # Verify visibility conditions in query
            query_call = mock_conn.execute.call_args
            query = query_call[0][0]
            params = query_call[0][1]

            assert "visibility = 'public'" in query
            assert "visibility = 'private' AND sender = ?" in query
            assert "test_agent" in params

    @pytest.mark.asyncio
    async def test_get_messages_with_filter(self, mock_context):
        """Test message retrieval with visibility filter."""

        public_messages = [
            {
                "id": 1,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "Public message 1",
                "visibility": "public",
                "metadata": None,
                "timestamp": "2025-01-01T10:00:00+00:00",
                "parent_message_id": None,
            }
        ]

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()

            # Set up row factory like real connection
            mock_conn.row_factory = None

            async def mock_execute(query, params):
                mock_cursor = AsyncMock()

                if "SELECT COUNT(*)" in query:
                    # COUNT query - return count of public messages (1)
                    mock_cursor.fetchone.return_value = [1]
                    return mock_cursor
                if "SELECT id FROM sessions" in query:
                    # Session existence check - return valid session
                    mock_cursor.fetchone.return_value = {"id": "session_abc123"}
                    return mock_cursor
                # SELECT query - return public messages only
                mock_cursor.fetchall.return_value = public_messages
                return mock_cursor

            mock_conn.execute.side_effect = mock_execute
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                get_messages,
                mock_context,
                session_id="session_abc123",
                visibility_filter="public",
            )

            assert result["success"] is True
            assert len(result["messages"]) == 1

            # Verify filter was applied - check SQL query contains visibility filter
            query_call = mock_conn.execute.call_args
            query = query_call[0][0]  # First argument is the SQL query
            params = query_call[0][1]  # Second argument is parameters

            # For public filter, query should contain "visibility = 'public'" and params should be [session_id, limit, offset]
            assert "visibility = 'public'" in query
            assert params == ["session_abc123", 50, 0]  # Default limit and offset

    @pytest.mark.asyncio
    async def test_get_messages_database_error(self, mock_context):
        """Test message retrieval with database error."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_db_conn.side_effect = Exception("Database connection failed")

            result = await call_fastmcp_tool(
                get_messages, mock_context, session_id="session_abc123"
            )

            assert result["success"] is False
            assert result["code"] in [
                "MESSAGE_RETRIEVAL_FAILED",
                "DATABASE_UNAVAILABLE",
            ]
            assert (
                "database connection failed" in result["error"].lower()
                or "database temporarily unavailable" in result["error"].lower()
            )
