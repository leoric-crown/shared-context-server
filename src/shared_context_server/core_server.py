"""
Core FastMCP server foundation and lifecycle management.

Provides the base FastMCP server instance, health check endpoint,
and essential server utilities for the shared context system.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request

from fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates

from . import __version__

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# FASTMCP SERVER FOUNDATION
# ============================================================================

# Initialize FastMCP server according to Phase 1 specification
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "shared-context-server"),
    version=__version__,
    instructions="Centralized memory store for multi-agent collaboration",
)

# ============================================================================
# WEB UI TEMPLATE CONFIGURATION
# ============================================================================

# Determine template and static file paths
current_dir = Path(__file__).parent
template_dir = current_dir / "templates"
static_dir = current_dir / "static"

# Ensure directories exist
template_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

# Initialize Jinja2 templates for HTML rendering
templates = Jinja2Templates(directory=str(template_dir))

# Export static_dir for use in other modules
__all__ = [
    "mcp",
    "templates",
    "static_dir",
    "health_check",
    "initialize_server",
    "shutdown_server",
]

# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """
    Health check endpoint for Docker containers and load balancers.

    Returns:
        JSONResponse: Health status with timestamp
    """
    try:
        # Import here to avoid circular imports
        from .database import health_check as db_health_check

        # Check database connectivity
        db_status = await db_health_check()

        return JSONResponse(
            {
                "status": "healthy"
                if db_status["status"] == "healthy"
                else "unhealthy",
                "timestamp": db_status["timestamp"],
                "database": db_status,
                "server": "shared-context-server",
                "version": __version__,
            }
        )
    except Exception as e:
        logger.exception("Health check failed")
        return JSONResponse(
            {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status_code=500,
        )


# ============================================================================
# SERVER LIFECYCLE MANAGEMENT
# ============================================================================


async def initialize_server() -> FastMCP:
    """
    Initialize the FastMCP server instance.

    Returns:
        FastMCP: Configured server instance
    """
    return mcp


async def shutdown_server() -> None:
    """
    Gracefully shutdown the server and cleanup resources.
    """
    logger.info("Shutting down shared context server")
    # Additional cleanup logic can be added here as needed


def _register_web_routes() -> None:
    """Register web UI routes by importing the web_endpoints module."""
    try:
        from . import web_endpoints  # noqa: F401

        logger.debug("Web UI routes registered successfully")
    except ImportError as e:
        logger.warning(f"Failed to register web UI routes: {e}")


def _register_mcp_components() -> None:
    """Register all MCP components including tools, resources, and prompts."""
    try:
        # Import all tool modules to register their @mcp.tool() decorated functions
        from . import (
            admin_tools,  # noqa: F401
            auth_tools,  # noqa: F401
            memory_tools,  # noqa: F401
            search_tools,  # noqa: F401
            session_tools,  # noqa: F401
        )

        logger.debug("MCP tools registered successfully")
    except ImportError as e:
        logger.warning(f"Failed to register MCP tools: {e}")

    try:
        # Import resource and prompt modules to register their decorators
        from . import (
            admin_resources,  # noqa: F401
            prompts,  # noqa: F401
            resources,  # noqa: F401
        )

        logger.debug("MCP resources and prompts registered successfully")
    except ImportError as e:
        logger.warning(f"Failed to register MCP resources and prompts: {e}")


# Register web routes and MCP components at module initialization
_register_web_routes()
_register_mcp_components()
