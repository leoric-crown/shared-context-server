"""
Status Utilities Module - Health monitoring and status reporting.

This module provides server status monitoring and health check functionality
extracted from the monolithic cli.py for better modularity and testing.
"""

import os
from typing import Any

import requests


def get_server_status(
    host: str | None = None,
    port: int | None = None,
    detailed: bool = False,  # noqa: ARG001
) -> dict[str, Any]:
    """
    Server status with optional detailed metrics.

    Args:
        host: Server host (defaults to config/environment)
        port: Server port (defaults to config/environment)
        detailed: Include detailed metrics if available

    Returns:
        Dictionary containing server status information
    """
    # Get default host and port from config/environment if not provided
    if host is None or port is None:
        try:
            from ..config import get_config

            config = get_config()
            port = port or config.mcp_server.http_port
            # For status check, use client-accessible hostname
            host = (
                host
                or os.getenv("CLIENT_HOST")
                or os.getenv("MCP_CLIENT_HOST", "localhost")
            )
        except Exception:
            host = (
                host
                or os.getenv("CLIENT_HOST")
                or os.getenv("MCP_CLIENT_HOST", "localhost")
            )
            port = port or int(os.getenv("HTTP_PORT", "23456"))

    status = {
        "host": host,
        "port": port,
        "server_running": False,
        "health_status": "unknown",
        "mcp_endpoint": "unknown",
    }

    try:
        # Check health endpoint
        health_url = f"http://{host}:{port}/health"
        response = requests.get(health_url, timeout=5)

        if response.status_code == 200:
            status["server_running"] = True
            status["health_status"] = "healthy"
            status["health_data"] = response.json()

            # Try to get MCP endpoint info
            try:
                requests.get(f"http://{host}:{port}/mcp/", timeout=5)
                status["mcp_endpoint"] = "available"
            except Exception:
                status["mcp_endpoint"] = "not_accessible"
        else:
            status["health_status"] = f"failed_{response.status_code}"

    except requests.exceptions.ConnectionError:
        status["health_status"] = "connection_failed"
    except Exception as e:
        status["health_status"] = f"error_{str(e)}"

    return status


def format_status_output(status_data: dict, format_type: str = "text") -> str:
    """
    Format status data for CLI output.

    Args:
        status_data: Status information from get_server_status
        format_type: Output format - "text" or "json"

    Returns:
        Formatted status string
    """
    if format_type == "json":
        import json

        return json.dumps(status_data, indent=2)

    # Text format
    lines = []

    host = status_data.get("host", "unknown")
    port = status_data.get("port", "unknown")

    if status_data.get("server_running", False):
        lines.append(f"✅ Server is running at http://{host}:{port}")

        health_data = status_data.get("health_data", {})
        if health_data:
            lines.append(f"✅ Health check: {health_data}")

        mcp_status = status_data.get("mcp_endpoint", "unknown")
        if mcp_status == "available":
            lines.append("✅ MCP endpoint: Available")
        else:
            lines.append("⚠️  MCP endpoint: Not accessible")
    else:
        health_status = status_data.get("health_status", "unknown")
        if health_status == "connection_failed":
            lines.append(f"❌ Cannot connect to server at http://{host}:{port}")
            lines.append(
                "   Make sure the server is running with 'docker compose up -d'"
            )
        elif health_status.startswith("failed_"):
            status_code = health_status.split("_")[1]
            lines.append(f"❌ Server health check failed: {status_code}")
        else:
            lines.append(f"❌ Error checking server status: {health_status}")

    return "\n".join(lines)


def check_service_health() -> dict[str, bool]:
    """
    Service health checks and availability.

    Returns:
        Dictionary mapping service names to health status
    """
    health = {}

    # Check if server components are available
    try:
        from ..server import initialize_server, server  # noqa: F401

        health["server_components"] = True
    except ImportError:
        health["server_components"] = False

    # Check database connectivity
    try:
        from ..database import get_db_connection  # noqa: F401

        health["database"] = True
    except ImportError:
        health["database"] = False

    # Check configuration loading
    try:
        from ..config import get_config

        get_config()
        health["configuration"] = True
    except Exception:
        health["configuration"] = False

    return health


def show_status_interactive(host: str | None = None, port: int | None = None) -> None:
    """Show server status with interactive CLI output."""
    status = get_server_status(host, port)
    output = format_status_output(status, "text")
    print(output)
