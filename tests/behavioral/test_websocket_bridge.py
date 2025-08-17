"""
Simplified behavioral tests for WebSocket bridge functionality.

Focuses on core functionality without complex mocking.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from shared_context_server import server, websocket_server
from tests.conftest import MockContext, call_fastmcp_tool


@pytest.fixture
def test_agent():
    """Create test agent context."""
    return MockContext("test_session", "test-agent-bridge")


class TestWebSocketBridgeSimplified:
    """Simplified WebSocket bridge tests focusing on core functionality."""

    @pytest.mark.asyncio
    async def test_websocket_bridge_broadcast_endpoint(self, test_agent):
        """Test that WebSocket server broadcast endpoint works."""
        client = TestClient(websocket_server.websocket_app)

        test_message = {
            "type": "new_message",
            "data": {
                "id": 123,
                "sender": "test-agent",
                "content": "Test bridge message",
                "timestamp": "2025-01-13T12:00:00Z",
            },
        }

        # Mock websocket_manager to avoid actual WebSocket connections
        with patch.object(
            websocket_server.websocket_manager,
            "broadcast_to_session",
            new_callable=AsyncMock,
        ) as mock_broadcast:
            response = client.post("/broadcast/test-session-123", json=test_message)

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is True
            assert result["session_id"] == "test-session-123"

            # Verify broadcast was called
            mock_broadcast.assert_called_once_with("test-session-123", test_message)

    @pytest.mark.asyncio
    @pytest.mark.no_websocket_mock
    async def test_http_notification_function(self, test_agent):
        """Test the HTTP notification function directly."""
        test_message_data = {
            "type": "new_message",
            "data": {
                "id": 456,
                "sender": "test-agent",
                "content": "Direct HTTP test",
                "timestamp": "2025-01-13T12:00:00Z",
            },
        }

        # Import the original function to test it directly (bypassing global mock)
        from shared_context_server.server import _notify_websocket_server

        # Mock httpx client
        with patch(
            "shared_context_server.server.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status = Mock(return_value=None)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Call the notification function directly (bypassing global mock)
            await _notify_websocket_server("test-session-http", test_message_data)

            # Verify HTTP client was used correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "broadcast/test-session-http" in call_args[0][0]
            assert call_args[1]["json"] == test_message_data

    @pytest.mark.asyncio
    async def test_add_message_triggers_http_bridge(self, test_db_manager, test_agent):
        """Test that add_message MCP tool triggers HTTP bridge notification."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:

            @asynccontextmanager
            async def mock_get_db_connection():
                async with test_db_manager.get_connection() as conn:
                    yield conn

            mock_db_conn.side_effect = mock_get_db_connection

            # Create test session
            async with test_db_manager.get_connection() as conn:
                await conn.execute(
                    "INSERT INTO sessions (id, purpose, created_by, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
                    (
                        "bridge-test-session",
                        "Bridge test",
                        "test-agent-bridge",
                        "2025-01-13T12:00:00Z",
                        True,
                    ),
                )
                await conn.commit()

            # Mock HTTP notification - this is what we're testing
            mock_http_notify = AsyncMock()
            with patch(
                "shared_context_server.session_tools.get_websocket_imports",
                return_value={
                    "notify_websocket_server": mock_http_notify,
                    "available": True,
                },
            ):
                # Call add_message
                result = await call_fastmcp_tool(
                    server.add_message,
                    test_agent,
                    session_id="bridge-test-session",
                    content="Test message for bridge",
                    visibility="public",
                )

                # Verify success
                assert result["success"] is True
                message_id = result["message_id"]

                # Verify HTTP notification was called
                mock_http_notify.assert_called_once()

                # Check the HTTP notification call arguments
                http_call_args = mock_http_notify.call_args
                assert http_call_args[0][0] == "bridge-test-session"  # session_id

                message_data = http_call_args[0][1]
                assert message_data["type"] == "new_message"
                assert message_data["data"]["id"] == message_id
                assert message_data["data"]["sender"] == "test-agent-bridge"
                assert message_data["data"]["content"] == "Test message for bridge"

    @pytest.mark.asyncio
    async def test_websocket_bridge_graceful_degradation(
        self, test_db_manager, test_agent
    ):
        """Test that MCP operations work even when WebSocket server is unavailable."""

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_db_conn:

            @asynccontextmanager
            async def mock_get_db_connection():
                async with test_db_manager.get_connection() as conn:
                    yield conn

            mock_db_conn.side_effect = mock_get_db_connection

            # Create test session
            async with test_db_manager.get_connection() as conn:
                await conn.execute(
                    "INSERT INTO sessions (id, purpose, created_by, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
                    (
                        "degradation-test-session",
                        "Graceful degradation test",
                        "test-agent-bridge",
                        "2025-01-13T12:00:00Z",
                        True,
                    ),
                )
                await conn.commit()

            # Mock HTTP client to simulate WebSocket server being down
            with patch(
                "shared_context_server.server.httpx.AsyncClient"
            ) as mock_client_class:
                mock_client_class.side_effect = httpx.ConnectError("Connection refused")

                # Add message - should succeed despite HTTP bridge failure
                result = await call_fastmcp_tool(
                    server.add_message,
                    test_agent,
                    session_id="degradation-test-session",
                    content="Message during WebSocket server downtime",
                    visibility="public",
                )

                # Verify message was still added successfully
                assert result["success"] is True
                assert "message_id" in result

                # Verify message was stored in database
                async with test_db_manager.get_connection() as conn:
                    cursor = await conn.execute(
                        "SELECT content FROM messages WHERE id = ?",
                        (result["message_id"],),
                    )
                    message_content = await cursor.fetchone()
                    assert message_content is not None
                    assert (
                        message_content[0] == "Message during WebSocket server downtime"
                    )
