"""
Real-time WebSocket Server for Shared Context Server.

This module provides WebSocket support using the mcpsock package to enable
real-time updates for the Web UI. It runs as a separate FastAPI server that
integrates with the main MCP server.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

try:
    from mcpsock import WebSocketServer as MCPWebSocketServer

    MCPSOCK_AVAILABLE = True
except ImportError:
    MCPSOCK_AVAILABLE = False

from .database import get_db_connection
from .database_manager import CompatibleRow
from .server import websocket_manager

logger = logging.getLogger(__name__)

# ============================================================================
# WEBSOCKET SERVER SETUP
# ============================================================================

if MCPSOCK_AVAILABLE:
    # Create FastAPI app for WebSocket server
    websocket_app = FastAPI(title="Shared Context WebSocket Server")

    # Create mcpsock WebSocket server
    ws_router = MCPWebSocketServer()

    @ws_router.initialize()
    async def ws_initialize(_websocket: WebSocket, session_id: Optional[str] = None):
        """Initialize WebSocket connection."""
        logger.info(f"WebSocket connection initialized for session: {session_id}")
        return {
            "status": "connected",
            "session_id": session_id,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    @ws_router.tool("subscribe")
    async def subscribe_to_session(session_id: str) -> dict[str, Any]:
        """Subscribe to real-time updates for a session."""
        logger.info(f"Client subscribed to session: {session_id}")
        return {"status": "subscribed", "session_id": session_id}

    @ws_router.tool("get_messages")
    async def get_session_messages(
        session_id: str, since_id: Optional[int] = None
    ) -> dict[str, Any]:
        """Get messages for a session, optionally since a specific message ID."""
        try:
            async with get_db_connection() as conn:
                # Set row factory for dict-like access
                if hasattr(conn, "row_factory"):
                    conn.row_factory = CompatibleRow

                # Build query
                query = """
                    SELECT * FROM messages
                    WHERE session_id = ?
                    AND visibility IN ('public', 'private', 'agent_only')
                """
                params = [session_id]

                if since_id:
                    query += " AND id > ?"
                    params.append(since_id)

                query += " ORDER BY timestamp ASC LIMIT 50"

                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                messages = [dict(row) for row in rows]

                return {
                    "session_id": session_id,
                    "messages": messages,
                    "count": len(messages),
                    "since_id": since_id,
                }

        except Exception as e:
            logger.exception(f"Failed to get messages for session {session_id}")
            return {
                "error": str(e),
                "session_id": session_id,
                "messages": [],
                "count": 0,
            }

    @ws_router.tool("get_session_info")
    async def get_session_info(session_id: str) -> dict[str, Any]:
        """Get basic session information."""
        try:
            async with get_db_connection() as conn:
                # Set row factory for dict-like access
                if hasattr(conn, "row_factory"):
                    conn.row_factory = CompatibleRow

                cursor = await conn.execute(
                    "SELECT * FROM sessions WHERE id = ?", (session_id,)
                )
                session = await cursor.fetchone()

                if not session:
                    return {"error": "Session not found", "session_id": session_id}

                return {
                    "session_id": session_id,
                    "session": dict(session),
                    "status": "active" if session["is_active"] else "inactive",
                }

        except Exception as e:
            logger.exception(f"Failed to get session info for {session_id}")
            return {"error": str(e), "session_id": session_id}

    # Register MCP WebSocket endpoint for AI agents
    @websocket_app.websocket("/mcp/{session_id}")
    async def mcp_websocket_endpoint(websocket: WebSocket, session_id: str):
        """MCP WebSocket endpoint for AI agents using mcpsock."""
        await ws_router.handle_websocket(websocket, session_id=session_id)

    # Register plain WebSocket endpoint for Web UI
    @websocket_app.websocket("/ws/{session_id}")
    async def web_ui_websocket_endpoint(websocket: WebSocket, session_id: str):
        """Plain WebSocket endpoint for Web UI real-time updates."""
        import json

        await websocket.accept()

        try:
            # Add to websocket manager without calling accept again
            websocket_manager.active_connections.setdefault(session_id, set()).add(
                websocket
            )
            logger.info(f"Web UI WebSocket client connected to session: {session_id}")

            # Keep connection alive and handle messages
            try:
                while True:
                    data = await websocket.receive_text()

                    # Handle JSON messages from web UI
                    try:
                        message = json.loads(data)
                        message_type = message.get("type")

                        if message_type == "subscribe":
                            await websocket.send_json(
                                {
                                    "type": "subscribed",
                                    "session_id": session_id,
                                    "status": "success",
                                }
                            )
                        elif message_type == "ping":
                            await websocket.send_json({"type": "pong"})
                        else:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "message": f"Unknown message type: {message_type}",
                                }
                            )

                    except json.JSONDecodeError:
                        # Handle plain text messages for backward compatibility
                        if data == "ping":
                            await websocket.send_text("pong")
                        elif data.startswith("subscribe:"):
                            await websocket.send_json(
                                {
                                    "type": "subscribed",
                                    "session_id": session_id,
                                    "status": "success",
                                }
                            )
                        else:
                            await websocket.send_json(
                                {"type": "error", "message": "Unknown command"}
                            )

            except WebSocketDisconnect:
                pass  # Client disconnected normally

        except Exception:
            logger.exception("Web UI WebSocket error occurred")
        finally:
            websocket_manager.disconnect(websocket, session_id)
            logger.info(
                f"Web UI WebSocket client disconnected from session: {session_id}"
            )

    @websocket_app.post("/broadcast/{session_id}")
    async def trigger_broadcast(
        session_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """HTTP endpoint to trigger WebSocket broadcast from MCP server."""
        try:
            await websocket_manager.broadcast_to_session(session_id, request)
            logger.debug(f"Successfully broadcasted to session {session_id}")
            return {"success": True, "session_id": session_id}
        except Exception as e:
            logger.warning(f"Failed to broadcast to session {session_id}: {e}")
            return {"success": False, "error": str(e)}

    @websocket_app.get("/health")
    async def websocket_health():
        """Health check for WebSocket server."""
        return {
            "status": "healthy",
            "websocket_support": True,
            "endpoints": {
                "web_ui": "/ws/{session_id}",
                "mcp_agents": "/mcp/{session_id}",
                "broadcast": "/broadcast/{session_id}",
            },
            "mcpsock_version": "0.1.5",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    logger.info(
        "WebSocket server configured with dual support: Web UI (/ws/) + MCP agents (/mcp/)"
    )

else:
    # Fallback WebSocket server without mcpsock
    websocket_app = FastAPI(title="Shared Context WebSocket Server (Fallback)")

    @websocket_app.websocket("/ws/{session_id}")
    async def websocket_fallback(websocket: WebSocket, session_id: str):
        """Fallback WebSocket endpoint without mcpsock."""
        await websocket.accept()

        try:
            # Add to websocket manager without calling accept again
            websocket_manager.active_connections.setdefault(session_id, set()).add(
                websocket
            )
            logger.info(f"WebSocket client connected to session: {session_id}")

            # Keep connection alive and handle messages
            try:
                while True:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text("pong")
                    elif data.startswith("subscribe:"):
                        await websocket.send_json(
                            {
                                "type": "subscribed",
                                "session_id": session_id,
                                "status": "success",
                            }
                        )
                    else:
                        await websocket.send_json(
                            {"type": "error", "message": "Unknown command"}
                        )
            except WebSocketDisconnect:
                pass  # Client disconnected normally

        except Exception:
            logger.exception("WebSocket error occurred")
        finally:
            websocket_manager.disconnect(websocket, session_id)
            logger.info(f"WebSocket client disconnected from session: {session_id}")

    @websocket_app.post("/broadcast/{session_id}")
    async def trigger_broadcast_fallback(
        session_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """HTTP endpoint to trigger WebSocket broadcast from MCP server (fallback mode)."""
        try:
            await websocket_manager.broadcast_to_session(session_id, request)
            logger.debug(f"Successfully broadcasted to session {session_id}")
            return {"success": True, "session_id": session_id}
        except Exception as e:
            logger.warning(f"Failed to broadcast to session {session_id}: {e}")
            return {"success": False, "error": str(e)}

    @websocket_app.get("/health")
    async def websocket_health_fallback():
        """Health check for fallback WebSocket server."""
        return {
            "status": "healthy",
            "websocket_support": True,
            "endpoints": {
                "web_ui": "/ws/{session_id}",
                "broadcast": "/broadcast/{session_id}",
            },
            "mcpsock_available": False,
            "mode": "fallback",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    logger.warning("WebSocket server using fallback mode (no mcpsock)")


# ============================================================================
# SERVER RUNNER
# ============================================================================


async def start_websocket_server(host: str = "127.0.0.1", port: int = 8080):
    """Start the WebSocket server."""
    logger.info(f"Starting WebSocket server on {host}:{port}")
    try:
        config = uvicorn.Config(
            app=websocket_app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,  # Reduce log noise
            ws="websockets-sansio",  # Use modern websockets Sans-I/O implementation
        )
        server = uvicorn.Server(config)
        await server.serve()
    except OSError as e:
        if e.errno == 48:  # Address already in use
            logger.exception(
                f"Port {port} is already in use. Please check for other services using this port."
            )
        else:
            logger.exception(f"Failed to bind to {host}:{port}")
        raise
    except Exception:
        logger.exception("WebSocket server failed to start")
        raise


def run_websocket_server(host: str = "127.0.0.1", port: int = 8080):
    """Run the WebSocket server (synchronous)."""
    asyncio.run(start_websocket_server(host, port))


if __name__ == "__main__":
    # Run the WebSocket server directly
    run_websocket_server()
