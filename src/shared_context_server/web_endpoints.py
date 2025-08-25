"""
Web UI endpoints for the Shared Context MCP Server.

Provides dashboard functionality, session viewer, memory browser, and static file serving
for the web-based administration interface.

All endpoints are registered as custom routes with the FastMCP server instance.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request

# Set up logging
import logging

from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response

from .config import get_config
from .core_server import mcp, static_dir, templates
from .database import get_db_connection

logger = logging.getLogger(__name__)


# ============================================================================
# WEB UI ENDPOINTS
# ============================================================================


@mcp.custom_route("/ui/", methods=["GET"])
async def dashboard(request: Request) -> HTMLResponse:
    """
    Main dashboard displaying active sessions with real-time updates.
    """
    try:
        from .config import get_config

        config = get_config()

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            if hasattr(conn, "row_factory"):
                # Row factory handled by SQLAlchemy connection wrapper
                pass
                pass

            # Get active sessions with message counts and memory counts
            cursor = await conn.execute("""
                SELECT s.*,
                       COUNT(DISTINCT m.id) as message_count,
                       COUNT(DISTINCT am.id) as memory_count,
                       MAX(m.timestamp) as last_activity
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                LEFT JOIN agent_memory am ON s.id = am.session_id
                    AND (am.expires_at IS NULL OR am.expires_at > datetime('now'))
                WHERE s.is_active = 1
                GROUP BY s.id
                ORDER BY last_activity DESC, s.created_at DESC
                LIMIT 50
            """)

            sessions = [dict(row) for row in await cursor.fetchall()]

        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "request": request,
                "sessions": sessions,
                "total_sessions": len(sessions),
                "websocket_port": config.mcp_server.websocket_port,
            },
        )

    except Exception as e:
        logger.exception("Dashboard failed to load")

        # Get database configuration info for debugging
        database_url = os.getenv("DATABASE_URL", "not_set")
        ci_env = bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))

        logger.info(f"Environment: DATABASE_URL={database_url}, CI={ci_env}")

        return HTMLResponse(
            f"<html><body><h1>Dashboard Error</h1><p>Type: {type(e).__name__}</p><p>Error: {e}</p></body></html>",
            status_code=500,
        )


@mcp.custom_route("/ui/sessions/{session_id}", methods=["GET"])
async def session_view(request: Request) -> HTMLResponse:
    """
    Individual session message viewer with real-time updates.
    """
    session_id = request.path_params["session_id"]

    try:
        from .config import get_config

        config = get_config()

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            if hasattr(conn, "row_factory"):
                # Row factory handled by SQLAlchemy connection wrapper
                pass

            # Get session information
            cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await cursor.fetchone()

            if not session:
                return HTMLResponse(
                    "<html><body><h1>Session Not Found</h1></body></html>",
                    status_code=404,
                )

            # Get messages for this session (showing all public + visible private/agent_only)
            cursor = await conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                AND visibility IN ('public', 'private', 'agent_only')
                ORDER BY timestamp ASC
            """,
                (session_id,),
            )

            messages = [dict(row) for row in await cursor.fetchall()]

            # Get session-scoped memory entries for this session
            memory_cursor = await conn.execute(
                """
                SELECT agent_id, key, value, created_at, updated_at
                FROM agent_memory
                WHERE session_id = ?
                ORDER BY created_at DESC
            """,
                (session_id,),
            )

            session_memory = [dict(row) for row in await memory_cursor.fetchall()]

        return templates.TemplateResponse(
            request,
            "session_view.html",
            {
                "request": request,
                "session": dict(session),
                "messages": messages,
                "session_memory": session_memory,
                "session_id": session_id,
                "websocket_port": config.mcp_server.websocket_port,
            },
        )

    except Exception as e:
        logger.exception(f"Session view failed for {session_id}")

        return HTMLResponse(
            f"<html><body><h1>Session View Error</h1><p>Type: {type(e).__name__}</p><p>Error: {e}</p></body></html>",
            status_code=500,
        )


@mcp.custom_route("/ui/memory", methods=["GET"])
async def memory_dashboard(request: Request) -> HTMLResponse:
    """
    Memory dashboard displaying memory entries based on scope parameter.
    Supports scope filtering: global (default), session, or all.
    """
    try:
        # Get scope parameter with default to 'global' for backward compatibility
        scope = request.query_params.get("scope", "global")

        # Validate scope parameter
        if scope not in ["global", "session", "all"]:
            scope = "global"  # fallback to safe default

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            if hasattr(conn, "row_factory"):
                # Row factory handled by SQLAlchemy connection wrapper
                pass

            # Build query based on scope parameter
            if scope == "global":
                where_clause = "WHERE session_id IS NULL"
                scope_label = "Global"
            elif scope == "session":
                where_clause = "WHERE session_id IS NOT NULL"
                scope_label = "Session-Scoped"
            else:  # scope == 'all'
                where_clause = ""
                scope_label = "All"

            # Execute query with dynamic WHERE clause
            base_query = f"""
                SELECT agent_id, key, value, created_at, updated_at, session_id
                FROM agent_memory
                {where_clause}
                ORDER BY created_at DESC
                LIMIT 50
            """

            cursor = await conn.execute(base_query)
            memory_entries = [dict(row) for row in await cursor.fetchall()]

            # Get counts for each scope for statistics
            global_cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM agent_memory WHERE session_id IS NULL"
            )
            global_row = await global_cursor.fetchone()
            global_count = global_row["count"] if global_row else 0

            session_cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM agent_memory WHERE session_id IS NOT NULL"
            )
            session_row = await session_cursor.fetchone()
            session_count = session_row["count"] if session_row else 0

            all_count = global_count + session_count

        return templates.TemplateResponse(
            request,
            "memory.html",
            {
                "request": request,
                "memory_entries": memory_entries,
                "total_entries": len(memory_entries),
                "current_scope": scope,
                "scope_label": scope_label,
                "global_count": global_count,
                "session_count": session_count,
                "all_count": all_count,
            },
        )

    except Exception as e:
        logger.exception("Memory dashboard failed to load")

        return HTMLResponse(
            f"<html><body><h1>Memory Dashboard Error</h1><p>Type: {type(e).__name__}</p><p>Error: {e}</p></body></html>",
            status_code=500,
        )


@mcp.custom_route("/ui/config", methods=["GET"])
async def ui_config(_request: Request) -> JSONResponse:
    """
    Frontend configuration endpoint for WebSocket port and other settings.
    """

    config = get_config()

    return JSONResponse(
        {
            "websocket_port": config.mcp_server.websocket_port,
            "websocket_host": config.mcp_server.websocket_host,
        }
    )


# ============================================================================
# STATIC FILE SERVING
# ============================================================================


@mcp.custom_route("/ui/static/css/style.css", methods=["GET"])
async def serve_css(_request: Request) -> Response:
    """Serve CSS file for the Web UI."""
    css_file = static_dir / "css" / "style.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css")
    return Response("CSS Not Found", status_code=404)


@mcp.custom_route("/ui/static/js/app.js", methods=["GET"])
async def serve_js(_request: Request) -> Response:
    """Serve JavaScript file for the Web UI."""
    js_file = static_dir / "js" / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    return Response("JS Not Found", status_code=404)


# Note: WebSocket connections are handled by the separate WebSocket server on port 8080
# Real-time WebSocket support is implemented in websocket_handlers module
