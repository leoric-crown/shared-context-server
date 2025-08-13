"""
Behavioral tests for WebSocket bridge functionality.

Tests the HTTP bridge between MCP server and WebSocket server that enables
real-time message broadcasting across the dual-server architecture.
"""

import inspect
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic.fields import FieldInfo

from shared_context_server import server, websocket_server
from shared_context_server.auth import AuthInfo


def extract_field_defaults(fastmcp_tool: Any) -> dict[str, Any]:
    """Extract actual default values from FastMCP tool function."""
    defaults: dict[str, Any] = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for param_name, param in sig.parameters.items():
        if param_name == "ctx":  # Skip context parameter
            continue

        if isinstance(param.default, FieldInfo):
            defaults[param_name] = param.default.default
        elif param.default is not inspect.Parameter.empty:
            defaults[param_name] = param.default

    return defaults


async def call_fastmcp_tool(fastmcp_tool: Any, ctx: Any, **kwargs: Any) -> Any:
    """Call a FastMCP tool function with proper default handling."""
    defaults = extract_field_defaults(fastmcp_tool)
    call_args = {**defaults, **kwargs}

    # Call the function with context as first parameter
    return await fastmcp_tool.fn(ctx, **call_args)


class MockContext:
    """Mock context for testing FastMCP tools."""

    def __init__(
        self,
        session_id: str = "test_session",
        agent_id: str = "test_agent_bridge",
        agent_type: str = "claude",
    ) -> None:
        self.session_id = session_id
        # Store auth info in the same way as real FastMCP context
        self._auth_info = AuthInfo(
            agent_id=agent_id,
            agent_type=agent_type,
            permissions=["read", "write"],
            authenticated=True,
        )
        # Also keep auth for backward compatibility
        self.auth = self._auth_info


@pytest.fixture
def test_agent():
    """Create test agent context."""
    return MockContext("test_session", "test-agent-bridge", "claude")


class TestWebSocketBridge:
    """Test WebSocket bridge functionality between servers."""

    @pytest.mark.asyncio
    async def test_websocket_bridge_broadcast_endpoint(self, test_agent):
        """Test that WebSocket server broadcast endpoint works."""
        # Test with real WebSocket app
        client = TestClient(websocket_server.websocket_app)

        test_message = {
            "type": "new_message",
            "data": {
                "id": 123,
                "sender": "test-agent",
                "sender_type": "claude",
                "content": "Test bridge message",
                "visibility": "public",
                "timestamp": "2025-01-13T12:00:00Z",
                "metadata": {},
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
    async def test_websocket_bridge_broadcast_error_handling(self, test_agent):
        """Test broadcast endpoint error handling."""
        client = TestClient(websocket_server.websocket_app)

        test_message = {"type": "test", "data": {}}

        # Mock websocket_manager to raise exception
        with patch.object(
            websocket_server.websocket_manager,
            "broadcast_to_session",
            side_effect=Exception("Connection failed"),
        ):
            response = client.post("/broadcast/test-session-error", json=test_message)

            assert response.status_code == 200
            result = response.json()
            assert result["success"] is False
            assert "Connection failed" in result["error"]

    @pytest.mark.asyncio
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

        # Mock httpx client
        with patch(
            "shared_context_server.server.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.raise_for_status = Mock(return_value=None)
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Call the notification function
            await server._notify_websocket_server(
                "test-session-http", test_message_data
            )

            # Verify HTTP client was used correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "broadcast/test-session-http" in call_args[0][0]
            assert call_args[1]["json"] == test_message_data

    @pytest.mark.asyncio
    async def test_http_notification_error_handling(self, test_agent):
        """Test HTTP notification handles errors gracefully."""
        test_message_data = {"type": "test", "data": {}}

        # Mock httpx to raise exception
        with patch(
            "shared_context_server.server.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("HTTP timeout")

            # Should not raise exception (graceful handling)
            try:
                await server._notify_websocket_server(
                    "test-session-error", test_message_data
                )
            except Exception:
                pytest.fail("HTTP notification should handle errors gracefully")

    @pytest.mark.asyncio
    async def test_add_message_triggers_http_bridge(self, test_db_manager, test_agent):
        """Test that add_message MCP tool triggers HTTP bridge notification."""

        with patch("shared_context_server.server.get_db_connection") as mock_db_conn:
            # Use the real test database instead of hardcoded mocks
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

            # Mock both WebSocket manager and HTTP notification
            with (
                patch.object(
                    server.websocket_manager,
                    "broadcast_to_session",
                    new_callable=AsyncMock,
                ) as mock_ws_broadcast,
                patch.object(
                    server, "_notify_websocket_server", new_callable=AsyncMock
                ) as mock_http_notify,
            ):
                # Call add_message
                result = await call_fastmcp_tool(
                    server.add_message,
                    test_agent,
                    session_id="bridge-test-session",
                    content="Test message for bridge",
                    visibility="public",
                )

            # Verify success - print detailed result for debugging
            print(f"add_message result: {result}")
            if not result.get("success"):
                print(f"Error details: {result}")
                pytest.fail(f"add_message failed: {result}")
            assert result["success"] is True
            message_id = result["message_id"]

            # Verify both WebSocket and HTTP notifications were called
            # Note: broadcast_to_session may be called multiple times (session update + new message)
            assert mock_ws_broadcast.call_count >= 1
            mock_http_notify.assert_called_once()

            # Check the HTTP notification call arguments
            http_call_args = mock_http_notify.call_args
            assert http_call_args[0][0] == "bridge-test-session"  # session_id

            message_data = http_call_args[0][1]
            assert message_data["type"] == "new_message"
            assert message_data["data"]["id"] == message_id
            assert message_data["data"]["sender"] == "test-agent-bridge"
            assert message_data["data"]["content"] == "Test message for bridge"
            assert message_data["data"]["visibility"] == "public"

    @pytest.mark.asyncio
    async def test_websocket_bridge_end_to_end_integration(
        self, test_db_manager, test_agent
    ):
        """Integration test: MCP message triggers WebSocket broadcast via HTTP bridge."""

        with patch("shared_context_server.server.get_db_connection") as mock_db_conn:
            # Use the real test database instead of hardcoded mocks
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
                        "e2e-test-session",
                        "End-to-end test",
                        "test-agent-bridge",
                        "2025-01-13T12:00:00Z",
                        True,
                    ),
                )
                await conn.commit()

            # Mock the WebSocket manager on both sides
            with (
                patch.object(
                    server.websocket_manager,
                    "broadcast_to_session",
                    new_callable=AsyncMock,
                ),
                patch.object(
                    websocket_server.websocket_manager,
                    "broadcast_to_session",
                    new_callable=AsyncMock,
                ) as mock_ws_server_ws,
            ):
                # Mock HTTP client to actually call WebSocket server
                async def mock_http_post(url, **kwargs):
                    # Extract session_id from URL
                    session_id = url.split("/broadcast/")[1]
                    message_data = kwargs["json"]

                    # Simulate the WebSocket server receiving and processing the broadcast
                    await websocket_server.websocket_manager.broadcast_to_session(
                        session_id, message_data
                    )

                    # Return mock response with proper sync setup for raise_for_status
                    mock_response = Mock()
                    mock_response.raise_for_status = Mock(return_value=None)
                    return mock_response

                with patch(
                    "shared_context_server.server.httpx.AsyncClient"
                ) as mock_client_class:
                    mock_client = AsyncMock()
                    mock_client.post.side_effect = mock_http_post
                    mock_client_class.return_value.__aenter__.return_value = mock_client

                    # Add message via MCP tool
                    result = await call_fastmcp_tool(
                        server.add_message,
                        test_agent,
                        session_id="e2e-test-session",
                        content="End-to-end bridge test message",
                        visibility="public",
                    )

                    # Verify message was added successfully
                    assert result["success"] is True
                    message_id = result["message_id"]

                    # Verify MCP server's websocket_manager was called
                    # Note: May be called multiple times (session update + new message)
                    # Use the actual mock that was applied to the websocket_manager
                    actual_mock = cast(
                        "AsyncMock", server.websocket_manager.broadcast_to_session
                    )
                    assert actual_mock.call_count >= 1

                    # Verify HTTP client was used
                    mock_client.post.assert_called_once()

                    # Verify WebSocket server's websocket_manager was called via HTTP bridge
                    # Note: May be called multiple times due to both HTTP bridge and session updates
                    assert mock_ws_server_ws.call_count >= 1

                    # Verify the message data passed through the bridge correctly
                    bridge_call_args = mock_ws_server_ws.call_args
                    assert bridge_call_args[0][0] == "e2e-test-session"
                    message_data = bridge_call_args[0][1]
                    assert message_data["type"] == "new_message"
                    assert message_data["data"]["id"] == message_id
                    assert (
                        message_data["data"]["content"]
                        == "End-to-end bridge test message"
                    )

    @pytest.mark.asyncio
    async def test_websocket_bridge_graceful_degradation(
        self, test_db_manager, test_agent
    ):
        """Test that MCP operations work even when WebSocket server is unavailable."""

        with patch("shared_context_server.server.get_db_connection") as mock_db_conn:
            # Use the real test database instead of hardcoded mocks
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

    @pytest.mark.asyncio
    async def test_websocket_server_health_includes_broadcast_endpoint(self):
        """Test that WebSocket server health check includes broadcast endpoint."""
        client = TestClient(websocket_server.websocket_app)

        response = client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "endpoints" in health_data
        assert "broadcast" in health_data["endpoints"]
        assert "/broadcast/{session_id}" in health_data["endpoints"]["broadcast"]
