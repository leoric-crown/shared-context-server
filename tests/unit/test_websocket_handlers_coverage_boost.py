"""
Coverage boost tests for websocket_handlers module.

Tests WebSocket manager functionality and notification system for significant coverage gains.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.shared_context_server.websocket_handlers import (
    WebSocketManager,
    _notify_websocket_server,
    websocket_manager,
)


class TestWebSocketManagerCoverageBoost:
    """High-impact tests for WebSocket manager functionality."""

    def test_websocket_manager_singleton(self):
        """Test that websocket_manager is properly instantiated."""
        assert isinstance(websocket_manager, WebSocketManager)
        assert websocket_manager.active_connections == {}

    @pytest.mark.asyncio
    async def test_connect_new_session(self):
        """Test connecting WebSocket to new session."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        session_id = "test_session_1"

        await manager.connect(mock_websocket, session_id)

        mock_websocket.accept.assert_called_once()
        assert session_id in manager.active_connections
        assert mock_websocket in manager.active_connections[session_id]

    @pytest.mark.asyncio
    async def test_connect_existing_session(self):
        """Test connecting WebSocket to existing session."""
        manager = WebSocketManager()
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        session_id = "test_session_1"

        # First connection
        await manager.connect(mock_websocket1, session_id)
        # Second connection to same session
        await manager.connect(mock_websocket2, session_id)

        assert len(manager.active_connections[session_id]) == 2
        assert mock_websocket1 in manager.active_connections[session_id]
        assert mock_websocket2 in manager.active_connections[session_id]

    def test_disconnect_from_session(self):
        """Test disconnecting WebSocket from session."""
        manager = WebSocketManager()
        mock_websocket = Mock()
        session_id = "test_session_1"

        # Setup connection first
        manager.active_connections[session_id] = {mock_websocket}

        # Disconnect
        manager.disconnect(mock_websocket, session_id)

        assert session_id not in manager.active_connections  # Session cleaned up

    def test_disconnect_partial_session(self):
        """Test disconnecting one WebSocket when multiple exist in session."""
        manager = WebSocketManager()
        mock_websocket1 = Mock()
        mock_websocket2 = Mock()
        session_id = "test_session_1"

        # Setup multiple connections
        manager.active_connections[session_id] = {mock_websocket1, mock_websocket2}

        # Disconnect one
        manager.disconnect(mock_websocket1, session_id)

        assert session_id in manager.active_connections  # Session still exists
        assert mock_websocket1 not in manager.active_connections[session_id]
        assert mock_websocket2 in manager.active_connections[session_id]

    def test_disconnect_nonexistent_session(self):
        """Test disconnecting from nonexistent session doesn't crash."""
        manager = WebSocketManager()
        mock_websocket = Mock()

        # Should not crash
        manager.disconnect(mock_websocket, "nonexistent_session")

    @pytest.mark.asyncio
    async def test_broadcast_to_session(self):
        """Test broadcasting message to all WebSockets in session."""
        manager = WebSocketManager()
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        session_id = "test_session_1"
        test_message = {"type": "test", "content": "hello"}

        # Setup connections
        manager.active_connections[session_id] = {mock_websocket1, mock_websocket2}

        with patch.object(
            manager, "_send_message_safe", new_callable=AsyncMock
        ) as mock_send:
            await manager.broadcast_to_session(session_id, test_message)

        # Should send to both websockets
        assert mock_send.call_count == 2
        mock_send.assert_any_call(mock_websocket1, test_message, session_id)
        mock_send.assert_any_call(mock_websocket2, test_message, session_id)

    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_session(self):
        """Test broadcasting to nonexistent session doesn't crash."""
        manager = WebSocketManager()
        test_message = {"type": "test", "content": "hello"}

        # Should not crash
        await manager.broadcast_to_session("nonexistent_session", test_message)

    @pytest.mark.asyncio
    async def test_send_message_safe_success(self):
        """Test _send_message_safe sends message successfully."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        session_id = "test_session"
        test_message = {"type": "test", "content": "hello"}

        await manager._send_message_safe(mock_websocket, test_message, session_id)

        mock_websocket.send_json.assert_called_once_with(test_message)

    @pytest.mark.asyncio
    async def test_send_message_safe_handles_exception(self):
        """Test _send_message_safe handles WebSocket send exceptions."""
        manager = WebSocketManager()
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("WebSocket error")
        session_id = "test_session"
        test_message = {"type": "test", "content": "hello"}

        # Setup connection to be disconnected
        manager.active_connections[session_id] = {mock_websocket}

        await manager._send_message_safe(mock_websocket, test_message, session_id)

        # Should disconnect the websocket
        assert session_id not in manager.active_connections


class TestWebSocketNotificationSystem:
    """Tests for WebSocket notification system."""

    @pytest.mark.asyncio
    @patch("src.shared_context_server.websocket_handlers.get_config")
    async def test_notify_websocket_server_disabled(self, mock_get_config):
        """Test WebSocket notification when WebSocket is disabled."""
        # Mock config with WebSocket disabled
        mock_config = Mock()
        mock_config.websocket.enabled = False
        mock_get_config.return_value = mock_config

        session_id = "test_session"
        message_data = {"type": "new_message", "content": "test"}

        # Should not crash when disabled (simple coverage test)
        await _notify_websocket_server(session_id, message_data)
