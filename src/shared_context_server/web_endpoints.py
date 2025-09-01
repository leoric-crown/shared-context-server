"""
Web UI endpoints for the Shared Context MCP Server.

Provides dashboard functionality, session viewer, memory browser, and static file serving
for the web-based administration interface.

All endpoints are registered as custom routes with the FastMCP server instance.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request

# Set up logging
import logging

from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)

from . import __version__
from .config import get_config
from .core_server import mcp, static_dir, templates
from .dashboard_auth import dashboard_auth
from .database import get_db_connection

logger = logging.getLogger(__name__)


# ============================================================================
# WEB UI ENDPOINTS
# ============================================================================


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@mcp.custom_route("/ui/login", methods=["GET", "POST"])
async def login(request: Request) -> HTMLResponse | RedirectResponse:
    """
    Admin login page and authentication handler.
    """
    if request.method == "GET":
        # Show login form
        return templates.TemplateResponse(request, "login.html", {"request": request})

    # Handle login form submission
    form = await request.form()
    password = str(form.get("password", ""))

    if dashboard_auth.verify_password(password):
        # Authentication successful - redirect to dashboard
        response = RedirectResponse("/ui/", status_code=302)
        dashboard_auth.set_auth_cookie(response)
        logger.info("Dashboard login successful")
        return response
    # Authentication failed - show error
    logger.warning("Dashboard login failed - invalid password")
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "error": "Invalid password. Please try again."},
    )


@mcp.custom_route("/ui/logout", methods=["POST"])
async def logout(_request: Request) -> RedirectResponse:
    """
    Logout endpoint to clear authentication.
    """
    response = RedirectResponse("/ui/login", status_code=302)
    dashboard_auth.clear_auth_cookie(response)
    logger.info("Dashboard logout")
    return response


def require_auth(request: Request) -> RedirectResponse | None:
    """
    Check authentication and redirect to login if not authenticated.
    Returns None if authenticated, RedirectResponse if not.
    """
    if not dashboard_auth.is_authenticated(request):
        return RedirectResponse("/ui/login", status_code=302)
    return None


# ============================================================================
# REDIRECT HANDLERS
# ============================================================================


@mcp.custom_route("/ui", methods=["GET"])
async def ui_redirect(_request: Request) -> RedirectResponse:
    """Redirect /ui to /ui/ for consistent routing."""
    return RedirectResponse("/ui/", status_code=301)


# ============================================================================
# WEB UI ENDPOINTS (PROTECTED)
# ============================================================================


@mcp.custom_route("/ui/", methods=["GET"])
async def dashboard(request: Request) -> HTMLResponse | RedirectResponse:
    """
    Main dashboard displaying active sessions with real-time updates.
    ADMIN ACCESS: Shows all session data including admin_only content.
    """
    # Check authentication
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect
    try:
        from .config import get_config

        config = get_config()

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            if hasattr(conn, "row_factory"):
                # Row factory handled by SQLAlchemy connection wrapper
                pass
                pass

            # Get active sessions with message counts, memory counts, and participant counts
            cursor = await conn.execute("""
                SELECT s.*,
                       COUNT(DISTINCT m.id) as message_count,
                       COUNT(DISTINCT am.id) as memory_count,
                       COUNT(DISTINCT m.sender) as participant_count,
                       MAX(m.timestamp) as last_activity,
                       CASE
                           WHEN MAX(m.timestamp) IS NOT NULL THEN MAX(m.timestamp)
                           ELSE s.created_at
                       END as sort_timestamp
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                LEFT JOIN agent_memory am ON s.id = am.session_id
                    AND (am.expires_at IS NULL OR am.expires_at > unixepoch('now'))
                WHERE s.is_active = 1
                GROUP BY s.id
                ORDER BY sort_timestamp DESC
                LIMIT 50
            """)

            sessions = [dict(row) for row in await cursor.fetchall()]

        # Determine external websocket port for UI (supports Docker port mapping)
        external_websocket_port = int(
            os.getenv("EXTERNAL_WEBSOCKET_PORT", config.mcp_server.websocket_port)
        )

        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "request": request,
                "sessions": sessions,
                "total_sessions": len(sessions),
                "websocket_port": external_websocket_port,
                "admin_access": True,  # Dashboard has full admin access
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
async def session_view(request: Request) -> HTMLResponse | RedirectResponse:
    """
    Individual session message viewer with real-time updates.
    ADMIN ACCESS: Shows ALL messages including admin_only visibility.
    """
    # Check authentication
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect
    session_id = request.path_params["session_id"]

    try:
        from .config import get_config

        config = get_config()

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            if hasattr(conn, "row_factory"):
                # Row factory handled by SQLAlchemy connection wrapper
                pass

            # Get session information with last activity and participant count
            cursor = await conn.execute(
                """
                SELECT s.*,
                       MAX(m.timestamp) as last_activity,
                       COUNT(DISTINCT m.sender) as participant_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                WHERE s.id = ?
                GROUP BY s.id
                """,
                (session_id,),
            )
            session = await cursor.fetchone()

            if not session:
                return HTMLResponse(
                    "<html><body><h1>Session Not Found</h1></body></html>",
                    status_code=404,
                )

            # Get ALL messages for this session (admin access - no visibility filtering)
            cursor = await conn.execute(
                """
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """,
                (session_id,),
            )

            messages = [dict(row) for row in await cursor.fetchall()]

            # Get session-scoped memory entries for this session
            memory_cursor = await conn.execute(
                """
                SELECT agent_id, key, value, created_at, updated_at, expires_at
                FROM agent_memory
                WHERE session_id = ?
                AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY created_at DESC
            """,
                (session_id,),
            )

            session_memory = [dict(row) for row in await memory_cursor.fetchall()]

        # Determine external websocket port for UI (supports Docker port mapping)
        external_websocket_port = int(
            os.getenv("EXTERNAL_WEBSOCKET_PORT", config.mcp_server.websocket_port)
        )

        return templates.TemplateResponse(
            request,
            "session_view.html",
            {
                "request": request,
                "session": dict(session),
                "messages": messages,
                "session_memory": session_memory,
                "session_id": session_id,
                "websocket_port": external_websocket_port,
                "admin_access": True,  # Dashboard has full admin access
            },
        )

    except Exception as e:
        logger.exception(f"Session view failed for {session_id}")

        return HTMLResponse(
            f"<html><body><h1>Session View Error</h1><p>Type: {type(e).__name__}</p><p>Error: {e}</p></body></html>",
            status_code=500,
        )


@mcp.custom_route("/ui/memory", methods=["GET"])
async def memory_dashboard(request: Request) -> HTMLResponse | RedirectResponse:
    """
    Memory dashboard displaying memory entries based on scope parameter.
    Supports scope filtering: global, session, or all (default).
    ADMIN ACCESS: Shows all memory entries.
    """
    # Check authentication
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect
    try:
        # Get scope parameter with default to 'all' for better user experience
        scope = request.query_params.get("scope", "all")

        # Validate scope parameter
        if scope not in ["global", "session", "all"]:
            scope = "all"  # fallback to safe default

        async with get_db_connection() as conn:
            # Set row factory for dict-like access
            if hasattr(conn, "row_factory"):
                # Row factory handled by SQLAlchemy connection wrapper
                pass

            # Build query based on scope parameter
            # Note: expires_at is stored as Unix timestamp, so we compare against unixepoch('now')
            if scope == "global":
                where_clause = "WHERE session_id IS NULL AND (expires_at IS NULL OR expires_at > unixepoch('now'))"
                scope_label = "Global"
            elif scope == "session":
                where_clause = "WHERE session_id IS NOT NULL AND (expires_at IS NULL OR expires_at > unixepoch('now'))"
                scope_label = "Session-Scoped"
            else:  # scope == 'all'
                where_clause = (
                    "WHERE (expires_at IS NULL OR expires_at > unixepoch('now'))"
                )
                scope_label = "All"

            # Execute query with dynamic WHERE clause
            base_query = f"""
                SELECT agent_id, key, value, created_at, updated_at, session_id, expires_at
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
                "total_count": all_count,
                "admin_access": True,  # Dashboard has full admin access
            },
        )

    except Exception as e:
        logger.exception("Memory dashboard failed to load")

        return HTMLResponse(
            f"<html><body><h1>Memory Dashboard Error</h1><p>Type: {type(e).__name__}</p><p>Error: {e}</p></body></html>",
            status_code=500,
        )


@mcp.custom_route("/ui/health", methods=["GET"])
async def health_dashboard(request: Request) -> HTMLResponse | RedirectResponse:
    """
    Health dashboard displaying system status in a user-friendly format.
    """
    # Check authentication
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect

    try:
        # Import here to avoid circular imports
        from .database import health_check as db_health_check

        # Check database connectivity
        db_status = await db_health_check()

        # Get configuration information
        config = get_config()

        # Get activity statistics from database
        activity_stats = {}
        try:
            async with get_db_connection() as conn:
                # Count total sessions
                sessions_cursor = await conn.execute(
                    "SELECT COUNT(*) as count FROM sessions"
                )
                sessions_row = await sessions_cursor.fetchone()
                activity_stats["total_sessions"] = (
                    sessions_row["count"] if sessions_row else 0
                )

                # Count total messages
                messages_cursor = await conn.execute(
                    "SELECT COUNT(*) as count FROM messages"
                )
                messages_row = await messages_cursor.fetchone()
                activity_stats["total_messages"] = (
                    messages_row["count"] if messages_row else 0
                )

                # Count memory entries (non-expired)
                memory_cursor = await conn.execute(
                    "SELECT COUNT(*) as count FROM agent_memory WHERE expires_at IS NULL OR expires_at > unixepoch('now')"
                )
                memory_row = await memory_cursor.fetchone()
                activity_stats["memory_entries"] = (
                    memory_row["count"] if memory_row else 0
                )
        except Exception as e:
            logger.warning(f"Failed to get activity stats: {e}")
            activity_stats = {
                "total_sessions": 0,
                "total_messages": 0,
                "memory_entries": 0,
            }

        # Use external websocket port and client host for display
        external_websocket_port = int(
            os.getenv("EXTERNAL_WEBSOCKET_PORT", config.mcp_server.websocket_port)
        )
        client_host = os.getenv("MCP_CLIENT_HOST", config.mcp_server.http_host)

        health_data = {
            "status": "healthy" if db_status["status"] == "healthy" else "unhealthy",
            "timestamp": db_status["timestamp"],
            "database": db_status,
            "server": "shared-context-server",
            "version": __version__,
            "config": {
                "websocket_port": external_websocket_port,
                "websocket_host": client_host,
            },
            "activity_stats": activity_stats,
        }

        return templates.TemplateResponse(
            request,
            "health.html",
            {
                "request": request,
                "health_data": health_data,
                "admin_access": True,  # Health dashboard has full admin access
            },
        )

    except Exception as e:
        logger.exception("Health dashboard failed to load")

        error_data = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return templates.TemplateResponse(
            request,
            "health.html",
            {
                "request": request,
                "health_data": error_data,
                "admin_access": True,
            },
            status_code=500,
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


@mcp.custom_route("/ui/static/scs-logo.svg", methods=["GET"])
async def serve_logo_svg(_request: Request) -> Response:
    """Serve SVG logo file for the Web UI."""
    svg_file = static_dir / "scs-logo.svg"
    if svg_file.exists():
        return FileResponse(svg_file, media_type="image/svg+xml")
    return Response("Logo SVG Not Found", status_code=404)


# ============================================================================
# CLIENT CONFIGURATION PAGE
# ============================================================================


@mcp.custom_route("/ui/client-config", methods=["GET"])
async def client_config(request: Request) -> HTMLResponse | RedirectResponse:
    """Serve a markdown-rendered page with MCP client configuration for all clients."""
    # Require admin auth for now (contains API key hints); adjust if needed
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect

    try:
        # Determine client-facing host and port
        config = get_config()
        client_host = os.getenv("MCP_CLIENT_HOST", config.mcp_server.http_host)
        external_http_port = int(
            os.getenv("EXTERNAL_HTTP_PORT", str(config.mcp_server.http_port))
        )

        # Generate markdown to a temp file using existing CLI helper
        import tempfile
        from pathlib import Path

        # Local import to avoid circular imports at module load time
        from .scripts.cli import generate_all_client_configs

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "client-config.md"
            # Reuse CLI generator to produce clean Markdown
            # SECURITY: Do not embed API key in admin UI output by default.
            # Temporarily replace API_KEY in environment for generation.
            original_api_key = os.environ.get("API_KEY")
            try:
                os.environ["API_KEY"] = "YOUR_API_KEY_HERE"
                generate_all_client_configs(
                    client_host, external_http_port, str(out_path)
                )
            finally:
                if original_api_key is not None:
                    os.environ["API_KEY"] = original_api_key
                else:
                    os.environ.pop("API_KEY", None)
            raw_content = out_path.read_text(encoding="utf-8")

        # Transform the generated text into Markdown with per-client code blocks
        import re

        lines = raw_content.splitlines()
        md_parts: list[str] = []
        md_parts.append("# MCP Client Configurations\n")
        md_parts.append(
            "Below are ready-to-copy configurations for all supported MCP clients.\n"
        )

        content = "\n".join(lines)
        pattern = re.compile(r"^===\s+(.*?)\s+===$", re.M)
        sections = list(pattern.finditer(content))

        def _slugify(s: str) -> str:
            s = s.strip().lower()
            s = re.sub(r"[^a-z0-9\s-]", "", s)
            s = re.sub(r"\s+", "-", s)
            s = re.sub(r"-+", "-", s)
            return s  # noqa: RET504

        def _prettify_title(raw: str) -> str:
            """Convert all-caps section headers to nicer titles.

            Applies known mappings for acronyms/brands, otherwise uses title-case.
            """
            base = raw.strip().lower()
            mapping = {
                "claude code": "Claude Code",
                "cursor ide": "Cursor IDE",
                "windsurf ide": "Windsurf IDE",
                "vs code": "VS Code",
                "vscode": "VS Code",
                "claude desktop": "Claude Desktop",
                "gemini cli": "Gemini CLI",
                "codex cli": "Codex CLI",
                "qwen cli": "Qwen CLI",
                "kiro ide": "Kiro IDE",
            }
            if base in mapping:
                return mapping[base]
            # Fallback: simple title case
            return base.title()

        toc: list[tuple[str, str]] = []

        if sections:
            for idx, match in enumerate(sections):
                raw_title = match.group(1).strip()
                title = _prettify_title(raw_title)
                anchor = _slugify(title)
                start = match.end()
                end = (
                    sections[idx + 1].start()
                    if idx + 1 < len(sections)
                    else len(content)
                )
                body = content[start:end].strip("\n")

                toc.append((title, anchor))

                md_parts.append(f'\n<a id="{anchor}"></a>\n## {title}\n')
                md_parts.append("```text")
                md_parts.append(body.strip())
                md_parts.append("```")

            if toc:
                toc_md = ["\n## Table of Contents\n"]
                for t, a in toc:
                    toc_md.append(f"- [{t}](#{a})")
                # Insert after the intro (after 2 initial md_parts entries)
                md_parts.insert(2, "\n".join(toc_md))
        else:
            # Fallback: show the entire content as a code block
            md_parts.append("```text")
            md_parts.append(content.strip())
            md_parts.append("```")

        md_content = "\n".join(md_parts)

        # Render page; client-side will convert Markdown → HTML via marked.js
        return templates.TemplateResponse(
            "client_config.html",
            {
                "request": request,
                "markdown_content": md_content,
                "admin_access": True,
            },
        )
    except Exception as e:
        logger.exception("Failed to generate client configuration page")
        return HTMLResponse(f"<h1>Error</h1><pre>{str(e)}</pre>", status_code=500)


@mcp.custom_route("/ui/api-key", methods=["GET"])
async def reveal_api_key(request: Request) -> JSONResponse | RedirectResponse:
    """Admin-protected endpoint that returns the server API key.

    The client page uses this to temporarily reveal the key for copy convenience.
    """
    # Require admin auth
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect

    try:
        config = get_config()
        api_key = os.getenv("API_KEY") or getattr(config.security, "api_key", None)
        if not api_key:
            return JSONResponse({"error": "API key not configured"}, status_code=404)

        logger.info("Admin requested API key reveal (60-second client window)")
        return JSONResponse({"api_key": api_key, "ttl_seconds": 60})
    except Exception as e:
        logger.exception("Failed to provide API key")
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/ui/static/favicon/favicon.ico", methods=["GET"])
async def serve_favicon_ico(_request: Request) -> Response:
    """Serve favicon.ico file for the Web UI."""
    favicon_file = static_dir / "favicon" / "favicon.ico"
    if favicon_file.exists():
        return FileResponse(favicon_file, media_type="image/x-icon")
    return Response("Favicon Not Found", status_code=404)


@mcp.custom_route("/ui/static/favicon/favicon-32x32.png", methods=["GET"])
async def serve_favicon_32(_request: Request) -> Response:
    """Serve 32x32 favicon PNG file for the Web UI."""
    favicon_file = static_dir / "favicon" / "favicon-32x32.png"
    if favicon_file.exists():
        return FileResponse(favicon_file, media_type="image/png")
    return Response("Favicon 32x32 Not Found", status_code=404)


@mcp.custom_route("/ui/static/favicon/favicon-16x16.png", methods=["GET"])
async def serve_favicon_16(_request: Request) -> Response:
    """Serve 16x16 favicon PNG file for the Web UI."""
    favicon_file = static_dir / "favicon" / "favicon-16x16.png"
    if favicon_file.exists():
        return FileResponse(favicon_file, media_type="image/png")
    return Response("Favicon 16x16 Not Found", status_code=404)


@mcp.custom_route("/ui/static/favicon/apple-touch-icon.png", methods=["GET"])
async def serve_apple_touch_icon(_request: Request) -> Response:
    """Serve Apple touch icon file for the Web UI."""
    icon_file = static_dir / "favicon" / "apple-touch-icon.png"
    if icon_file.exists():
        return FileResponse(icon_file, media_type="image/png")
    return Response("Apple Touch Icon Not Found", status_code=404)


@mcp.custom_route("/ui/static/favicon/site.webmanifest", methods=["GET"])
async def serve_webmanifest(_request: Request) -> Response:
    """Serve web manifest file for the Web UI."""
    manifest_file = static_dir / "favicon" / "site.webmanifest"
    if manifest_file.exists():
        return FileResponse(manifest_file, media_type="application/manifest+json")
    return Response("Web Manifest Not Found", status_code=404)


# Note: WebSocket connections are handled by the separate WebSocket server on port 8080
# Real-time WebSocket support is implemented in websocket_handlers module
