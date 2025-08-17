"""
WebSocket handlers and real-time communication infrastructure.

Provides WebSocket connection management, notification broadcasting,
and real-time updates for the shared context system.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from starlette.websockets import WebSocket, WebSocketDisconnect

from .config import get_config

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================


class WebSocketManager:
    """Manager for WebSocket connections and session-based broadcasting."""

    def __init__(self) -> None:
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """Remove a WebSocket connection and cleanup empty sessions."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_to_session(self, session_id: str, message: dict) -> None:
        """Broadcast a message to all WebSocket connections for a session."""
        if session_id in self.active_connections:
            # Extract WebSocket list to avoid performance overhead in loop
            websockets = list(self.active_connections[session_id])
            for websocket in websockets:
                await self._send_message_safe(websocket, message, session_id)

    async def _send_message_safe(
        self, websocket: WebSocket, message: dict, session_id: str
    ) -> None:
        """Safely send message to WebSocket, disconnect on error."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket, session_id)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# ============================================================================
# WEBSOCKET NOTIFICATION SYSTEM
# ============================================================================


async def _notify_websocket_server(
    session_id: str, message_data: dict[str, Any]
) -> None:
    """Notify WebSocket server of new message via HTTP bridge."""
    try:
        config = get_config()
        ws_host = config.mcp_server.websocket_host
        ws_port = config.mcp_server.websocket_port

        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(
                f"http://{ws_host}:{ws_port}/broadcast/{session_id}", json=message_data
            )
            response.raise_for_status()
            logger.debug(f"WebSocket broadcast triggered for session {session_id}")
    except Exception as e:
        logger.debug(f"WebSocket broadcast failed (non-critical): {e}")


# Public alias for notification function
notify_websocket_server = _notify_websocket_server


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================


async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time session updates.
    """
    # Extract session_id from WebSocket path
    path_params = websocket.path_params
    session_id = path_params.get("session_id")

    if not session_id:
        await websocket.close(code=1008, reason="Missing session_id")
        return

    await websocket_manager.connect(websocket, session_id)

    try:
        while True:
            # Wait for messages (client heartbeat or disconnect)
            data = await websocket.receive_text()

            # Handle client heartbeat
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.warning(f"WebSocket error for session {session_id}: {e}")
        websocket_manager.disconnect(websocket, session_id)


# ============================================================================
# MCPSOCK WEBSOCKET SUPPORT
# ============================================================================

# Import mcpsock for proper WebSocket support
try:
    from mcpsock import WebSocketServer as MCPWebSocketServer

    MCPSOCK_AVAILABLE = True
    logger.info("mcpsock package available - WebSocket support enabled")
except ImportError:
    MCPSOCK_AVAILABLE = False
    logger.warning("mcpsock package not available - WebSocket support disabled")

# Create WebSocket server instance for real-time updates
if MCPSOCK_AVAILABLE:
    # Create a WebSocket server router for real-time session updates
    websocket_router = MCPWebSocketServer()

    @websocket_router.initialize()  # type: ignore[misc]
    async def websocket_initialize(
        _websocket: Any, session_id: str | None = None
    ) -> dict[str, Any]:
        """Initialize WebSocket connection with session metadata."""
        return {"status": "connected", "session_id": session_id}

    @websocket_router.tool("subscribe")  # type: ignore[misc]
    async def websocket_subscribe(_websocket: Any, session_id: str) -> dict[str, str]:
        """Subscribe to session updates via WebSocket."""
        return {"status": "subscribed", "session_id": session_id}

    @websocket_router.tool("get_updates")  # type: ignore[misc]
    async def websocket_get_updates(_websocket: Any, session_id: str) -> dict[str, Any]:
        """Get real-time updates for a session."""
        return {"session_id": session_id, "updates": []}

    # Register WebSocket tools with FastMCP if available
    logger.info("WebSocket tools registered for real-time session updates")

else:
    websocket_router = None
    logger.info("WebSocket support disabled - mcpsock not available")

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "websocket_manager",
    "websocket_endpoint",
    "notify_websocket_server",
    "websocket_router",
    "MCPSOCK_AVAILABLE",
]
