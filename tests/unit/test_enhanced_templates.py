"""
Unit tests for Enhanced Message Templates.

Tests the paginated message template resource for parameter handling,
visibility filtering, and performance optimization.
"""

import json
from unittest.mock import AsyncMock, patch

from shared_context_server.admin_resources import (
    get_session_messages_paginated_resource,
)


class TestEnhancedMessageTemplates:
    """Test session://{session_id}/messages/{limit} template."""

    @patch("shared_context_server.admin_resources.get_db_connection")
    async def test_basic_paginated_messages(self, mock_get_db):
        """Test basic paginated message retrieval."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock session data
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = {
            "id": "test_session",
            "purpose": "Test session",
            "created_at": "2023-01-01T00:00:00Z",
        }

        # Mock message data
        mock_messages_cursor = AsyncMock()
        mock_messages_cursor.fetchall.return_value = [
            {
                "id": 1,
                "content": "Test message 1",
                "sender": "agent1",
                "visibility": "public",
                "timestamp": "2023-01-01T01:00:00Z",
            },
            {
                "id": 2,
                "content": "Test message 2",
                "sender": "agent2",
                "visibility": "public",
                "timestamp": "2023-01-01T01:01:00Z",
            },
        ]

        mock_conn.execute.side_effect = [mock_session_cursor, mock_messages_cursor]

        # Use create_resource method for template-based resources
        resource = await get_session_messages_paginated_resource.create_resource(
            "session://test_session/messages/10",
            {"session_id": "test_session", "limit": "10"},
        )

        assert str(resource.uri) == "session://test_session/messages/10"
        assert resource.name == "get_session_messages_paginated_resource"
        assert resource.mime_type == "text/plain"

        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)
        assert content["session_id"] == "test_session"
        assert content["pagination"]["requested_limit"] == 10
        assert content["pagination"]["total_messages_returned"] == 2
        assert len(content["messages"]) == 2

    @patch("shared_context_server.admin_resources.get_db_connection")
    async def test_limit_parameter_validation(self, mock_get_db):
        """Test limit parameter parsing and validation."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock minimal session and messages
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = {"id": "test", "purpose": "test"}

        mock_messages_cursor = AsyncMock()
        mock_messages_cursor.fetchall.return_value = []

        mock_conn.execute.side_effect = [mock_session_cursor, mock_messages_cursor]

        # Test various limit values
        test_cases = [
            ("50", 50),  # Normal case
            ("invalid", 50),  # Invalid string -> default
            ("0", 50),  # Zero -> default
            ("-5", 50),  # Negative -> default
            ("600", 500),  # Over max -> clamp to max
            ("100", 100),  # Valid within range
        ]

        for limit_input, expected_limit in test_cases:
            # Reset mocks
            mock_conn.execute.side_effect = [mock_session_cursor, mock_messages_cursor]

            # Use create_resource method for template-based resources
            resource = await get_session_messages_paginated_resource.create_resource(
                f"session://test/messages/{limit_input}",
                {"session_id": "test", "limit": limit_input},
            )

            # FastMCP resource templates return content via read() method
            resource_content = await resource.read()
            content = json.loads(resource_content)
            assert content["pagination"]["requested_limit"] == expected_limit

    @patch("shared_context_server.admin_resources.get_db_connection")
    async def test_visibility_filtering(self, mock_get_db):
        """Test message visibility filtering based on agent context."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock session
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = {
            "id": "test_session",
            "purpose": "Visibility test",
        }

        # Mock messages with different visibility levels
        mock_messages_cursor = AsyncMock()
        mock_messages_cursor.fetchall.return_value = [
            {
                "id": 1,
                "content": "Public message",
                "sender": "other_agent",
                "visibility": "public",
                "timestamp": "2023-01-01T01:00:00Z",
            },
            {
                "id": 2,
                "content": "Private message from requester",
                "sender": "requesting_agent",
                "visibility": "private",
                "timestamp": "2023-01-01T01:01:00Z",
            },
            {
                "id": 3,
                "content": "Private message from other",
                "sender": "other_agent",
                "visibility": "private",
                "timestamp": "2023-01-01T01:02:00Z",
            },
        ]

        mock_conn.execute.side_effect = [mock_session_cursor, mock_messages_cursor]

        # Mock context for requesting agent
        mock_ctx = type(
            "MockCtx", (), {"agent_id": "requesting_agent", "session_id": "ctx_session"}
        )()

        # Use create_resource method for template-based resources
        resource = await get_session_messages_paginated_resource.create_resource(
            "session://test_session/messages/50",
            {"session_id": "test_session", "limit": "50", "ctx": mock_ctx},
        )

        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)

        # Should include public message and own private message (2 total)
        assert content["pagination"]["total_messages_returned"] == 2
        assert content["pagination"]["messages_filtered_by_visibility"] == 1

        messages = content["messages"]
        message_contents = [msg["content"] for msg in messages]
        assert "Public message" in message_contents
        assert "Private message from requester" in message_contents
        assert "Private message from other" not in message_contents

    @patch("shared_context_server.admin_resources.get_db_connection")
    async def test_nonexistent_session(self, mock_get_db):
        """Test template with non-existent session."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock empty session result
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_session_cursor

        # Use create_resource method for template-based resources
        resource = await get_session_messages_paginated_resource.create_resource(
            "session://nonexistent/messages/10",
            {"session_id": "nonexistent", "limit": "10"},
        )

        assert str(resource.uri) == "session://nonexistent/messages/10"
        assert resource.name == "get_session_messages_paginated_resource"

        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)
        assert "error" in content
        assert "Session not found" in content["error"]

    @patch("shared_context_server.admin_resources.get_db_connection")
    async def test_database_error_handling(self, mock_get_db):
        """Test template handles database errors gracefully."""
        mock_get_db.side_effect = Exception("Database connection failed")

        # Use create_resource method for template-based resources
        resource = await get_session_messages_paginated_resource.create_resource(
            "session://error_session/messages/10",
            {"session_id": "error_session", "limit": "10"},
        )

        assert str(resource.uri) == "session://error_session/messages/10"
        assert resource.name == "get_session_messages_paginated_resource"

        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)
        assert "error" in content
        assert "Failed to retrieve session messages" in content["error"]
        assert "Database connection failed" in content["details"]

    async def test_context_fallback(self):
        """Test template with no context provided."""
        with patch(
            "shared_context_server.admin_resources.get_db_connection"
        ) as mock_get_db:
            mock_conn = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_conn

            # Mock minimal data
            mock_session_cursor = AsyncMock()
            mock_session_cursor.fetchone.return_value = {
                "id": "test",
                "purpose": "test",
            }

            mock_messages_cursor = AsyncMock()
            mock_messages_cursor.fetchall.return_value = [
                {
                    "id": 1,
                    "content": "Test message",
                    "sender": "current_agent",  # Should match fallback agent_id
                    "visibility": "public",
                    "timestamp": "2023-01-01T01:00:00Z",
                }
            ]

            mock_conn.execute.side_effect = [mock_session_cursor, mock_messages_cursor]

            # Use create_resource method for template-based resources
            resource = await get_session_messages_paginated_resource.create_resource(
                "session://test/messages/10",
                {
                    "session_id": "test",
                    "limit": "10",
                    "ctx": None,
                },  # No context provided
            )

            # FastMCP resource templates return content via read() method
            resource_content = await resource.read()
            content = json.loads(resource_content)
            assert content["metadata"]["retrieved_by"] == "current_agent"

    async def test_context_with_session_id_fallback(self):
        """Test template with context missing agent_id."""
        with patch(
            "shared_context_server.admin_resources.get_db_connection"
        ) as mock_get_db:
            mock_conn = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_conn

            # Mock data
            mock_session_cursor = AsyncMock()
            mock_session_cursor.fetchone.return_value = {
                "id": "test",
                "purpose": "test",
            }

            mock_messages_cursor = AsyncMock()
            mock_messages_cursor.fetchall.return_value = []

            mock_conn.execute.side_effect = [mock_session_cursor, mock_messages_cursor]

            # Mock context without agent_id
            mock_ctx = type("MockCtx", (), {"session_id": "ctx_session_12345678"})()

            # Use create_resource method for template-based resources
            resource = await get_session_messages_paginated_resource.create_resource(
                "session://test/messages/10",
                {"session_id": "test", "limit": "10", "ctx": mock_ctx},
            )

            # FastMCP resource templates return content via read() method
            resource_content = await resource.read()
            content = json.loads(resource_content)
            # Should use fallback based on session_id
            assert content["metadata"]["retrieved_by"] == "agent_ctx_sess"

    async def test_pagination_metadata(self):
        """Test pagination metadata accuracy."""
        with patch(
            "shared_context_server.admin_resources.get_db_connection"
        ) as mock_get_db:
            mock_conn = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_conn

            # Mock session
            mock_session_cursor = AsyncMock()
            mock_session_cursor.fetchone.return_value = {
                "id": "pagination_test",
                "purpose": "Pagination test session",
            }

            # Mock 5 messages, 3 visible to agent
            mock_messages_cursor = AsyncMock()
            mock_messages_cursor.fetchall.return_value = [
                {
                    "id": 1,
                    "content": "Msg 1",
                    "sender": "test_agent",
                    "visibility": "public",
                    "timestamp": "2023-01-01T01:00:00Z",
                },
                {
                    "id": 2,
                    "content": "Msg 2",
                    "sender": "other_agent",
                    "visibility": "private",
                    "timestamp": "2023-01-01T01:01:00Z",
                },
                {
                    "id": 3,
                    "content": "Msg 3",
                    "sender": "test_agent",
                    "visibility": "private",
                    "timestamp": "2023-01-01T01:02:00Z",
                },
                {
                    "id": 4,
                    "content": "Msg 4",
                    "sender": "test_agent",
                    "visibility": "public",
                    "timestamp": "2023-01-01T01:03:00Z",
                },
                {
                    "id": 5,
                    "content": "Msg 5",
                    "sender": "other_agent",
                    "visibility": "agent_only",
                    "timestamp": "2023-01-01T01:04:00Z",
                },
            ]

            mock_conn.execute.side_effect = [mock_session_cursor, mock_messages_cursor]

            mock_ctx = type("MockCtx", (), {"agent_id": "test_agent"})()

            # Use create_resource method for template-based resources
            resource = await get_session_messages_paginated_resource.create_resource(
                "session://pagination_test/messages/20",
                {"session_id": "pagination_test", "limit": "20", "ctx": mock_ctx},
            )

            # FastMCP resource templates return content via read() method
            resource_content = await resource.read()
            content = json.loads(resource_content)
            pagination = content["pagination"]

            assert pagination["requested_limit"] == 20
            assert pagination["total_messages_returned"] == 3  # Only visible messages
            assert pagination["messages_filtered_by_visibility"] == 2  # Hidden messages

    async def test_resource_uri_formatting(self):
        """Test resource URI formatting with various parameters."""
        test_cases = [
            ("session123", "10", "session://session123/messages/10"),
            (
                "long_session_id_456",
                "100",
                "session://long_session_id_456/messages/100",
            ),
            ("special-chars_789", "50", "session://special-chars_789/messages/50"),
        ]

        for session_id, limit, expected_uri in test_cases:
            with patch(
                "shared_context_server.admin_resources.get_db_connection"
            ) as mock_get_db:
                # Mock database error to get quick response
                mock_get_db.side_effect = Exception("Test error")

                # Use create_resource method for template-based resources
                resource = (
                    await get_session_messages_paginated_resource.create_resource(
                        expected_uri, {"session_id": session_id, "limit": limit}
                    )
                )

                assert str(resource.uri) == expected_uri
