"""
Unit tests for session management tools.

Tests the create_session and get_session tools according to Phase 1 specification.
"""

# Import testing helpers from conftest.py
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from unittest.mock import AsyncMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent))
from conftest import MockContext, call_fastmcp_tool

from shared_context_server.session_tools import create_session, get_session


class TestCreateSession:
    """Test create_session tool functionality."""

    @pytest.fixture
    def mock_context(self):
        """Mock MCP context for testing."""
        return MockContext("test_session", "test_agent")

    @pytest.mark.asyncio
    async def test_create_session_success(self, mock_context):
        """Test successful session creation."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:
            # Setup mocks
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.lastrowid = 123
            mock_conn.execute.return_value = mock_cursor
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            # Test session creation
            result = await call_fastmcp_tool(
                create_session,
                mock_context,
                purpose="Test session",
                metadata={"test": True},
            )

            # Debug: Print actual result
            print(f"DEBUG: result = {result}")

            # Verify results
            assert result["success"] is True
            assert "session_id" in result
            assert result["session_id"].startswith("session_")
            assert result["created_by"] == "test_agent"
            assert "created_at" in result

            # Verify database calls
            mock_conn.execute.assert_any_call(
                """
                INSERT INTO sessions (id, purpose, created_by, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    result["session_id"],
                    "Test session",
                    "test_agent",
                    '{"test":true}',
                    mock.ANY,
                    mock.ANY,
                ),
            )
            mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_empty_purpose(self, mock_context):
        """Test session creation with empty purpose fails."""

        # No patches needed with direct context passing
        result = await call_fastmcp_tool(
            create_session, mock_context, purpose="   ", metadata=None
        )

        assert result["success"] is False
        assert result["code"] == "INVALID_INPUT"
        assert "empty" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_create_session_database_error(self, mock_context):
        """Test session creation with database error."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_db_conn.side_effect = Exception("Database connection failed")

            result = await call_fastmcp_tool(
                create_session, mock_context, purpose="Test session"
            )

            assert result["success"] is False
            assert result["code"] in ["SESSION_CREATION_FAILED", "DATABASE_UNAVAILABLE"]
            assert (
                "database temporarily unavailable" in result["error"].lower()
                or "database connection failed" in result["error"].lower()
            )


class TestGetSession:
    """Test get_session tool functionality."""

    @pytest.fixture
    def mock_context(self):
        """Mock MCP context for testing."""
        return MockContext("test_session", "test_agent")

    @pytest.fixture
    def mock_session_row(self):
        """Mock session database row."""
        return {
            "id": "session_abc123",
            "purpose": "Test session",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
            "created_by": "test_agent",
            "metadata": '{"test": true}',
        }

    @pytest.fixture
    def mock_message_rows(self):
        """Mock message database rows."""
        return [
            {
                "id": 1,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "Hello world",
                "visibility": "public",
                "metadata": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parent_message_id": None,
            },
            {
                "id": 2,
                "session_id": "session_abc123",
                "sender": "other_agent",
                "content": "Public response",
                "visibility": "public",
                "metadata": '{"type": "response"}',
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parent_message_id": 1,
            },
        ]

    @pytest.mark.asyncio
    async def test_get_session_success(
        self, mock_context, mock_session_row, mock_message_rows
    ):
        """Test successful session retrieval."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()

            # Setup database responses
            mock_cursor.fetchone.side_effect = [mock_session_row]  # Session query
            mock_cursor.fetchall.return_value = mock_message_rows  # Messages query
            mock_conn.execute.return_value = mock_cursor
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                get_session, mock_context, session_id="session_abc123"
            )

            # Verify results
            assert result["success"] is True
            assert result["session"]["id"] == "session_abc123"
            assert result["session"]["purpose"] == "Test session"
            assert len(result["messages"]) == 2
            assert result["message_count"] == 2

            # Verify database queries
            assert mock_conn.execute.call_count == 2  # Session + messages queries

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, mock_context):
        """Test session retrieval when session doesn't exist."""

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone.return_value = None  # Session not found
            mock_conn.execute.return_value = mock_cursor
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                get_session, mock_context, session_id="session_nonexistent"
            )

            assert result["success"] is False
            assert result["code"] == "SESSION_NOT_FOUND"
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_session_visibility_filtering(
        self, mock_context, mock_session_row
    ):
        """Test that private messages are filtered correctly."""

        mixed_messages = [
            {
                "id": 1,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "My private message",
                "visibility": "private",
                "metadata": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parent_message_id": None,
            },
            {
                "id": 2,
                "session_id": "session_abc123",
                "sender": "other_agent",
                "content": "Other agent private message",
                "visibility": "private",
                "metadata": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parent_message_id": None,
            },
            {
                "id": 3,
                "session_id": "session_abc123",
                "sender": "test_agent",
                "content": "Public message",
                "visibility": "public",
                "metadata": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parent_message_id": None,
            },
        ]

        with (
            patch(
                "shared_context_server.session_tools.get_db_connection"
            ) as mock_db_conn,
        ):
            # No mcp context patches needed
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()

            # Setup responses
            mock_cursor.fetchone.return_value = mock_session_row
            mock_cursor.fetchall.return_value = [
                mixed_messages[0],
                mixed_messages[2],
            ]  # Only accessible messages
            mock_conn.execute.return_value = mock_cursor
            mock_db_conn.return_value.__aenter__.return_value = mock_conn

            result = await call_fastmcp_tool(
                get_session, mock_context, session_id="session_abc123"
            )

            # Should only see own private message and public messages
            assert result["success"] is True
            assert len(result["messages"]) == 2

            # Verify visibility query includes correct conditions
            visibility_query_call = mock_conn.execute.call_args_list[
                1
            ]  # Second call is messages
            query_args = visibility_query_call[0]
            assert "visibility = 'public'" in query_args[0]
            assert "visibility = 'private' AND sender = ?" in query_args[0]
            assert "test_agent" in query_args[1]  # Agent ID parameter
