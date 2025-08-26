#!/usr/bin/env python3
"""
Command Line Interface for Shared Context MCP Server.

This module provides the main CLI entry point for production use,
supporting both STDIO and HTTP transports with proper configuration
management for system deployment.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import sys
from typing import Any

# Import uvloop conditionally for better performance
try:
    import uvloop

    UVLOOP_AVAILABLE = True
except ImportError:
    uvloop = None  # type: ignore[assignment]
    UVLOOP_AVAILABLE = False

# Configure logging - use environment LOG_LEVEL if available
import os

from .. import __version__
from ..config import get_config, load_config

# Check if we're running client-config command or version to suppress logging
client_config_mode = len(sys.argv) >= 2 and sys.argv[1] == "client-config"
version_mode = "--version" in sys.argv

log_level = (
    logging.CRITICAL
    if client_config_mode or version_mode
    else getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)
    ],  # Use stderr to avoid interfering with STDIO transport
)

logger = logging.getLogger(__name__)

# Import server components
try:
    from ..server import initialize_server, server

    SERVER_AVAILABLE = True
except ImportError:
    SERVER_AVAILABLE = False
    logger.exception("Server components not available")


class ProductionServer:
    """Production MCP server with transport selection."""

    def __init__(self) -> None:
        self.config = None
        self.server = None

    async def start_stdio_server(self) -> None:
        """Start server with STDIO transport."""
        logger.info("Starting Shared Context MCP Server (STDIO)")

        if not SERVER_AVAILABLE:
            logger.error("Server components not available")
            sys.exit(1)

        try:
            # Initialize server components
            await initialize_server()

            # Log version information just before starting MCP server
            logger.info(
                f"✅ Shared Context MCP Server v{__version__} initialized successfully"
            )

            # Run server with STDIO transport
            await server.run_stdio_async()
        except Exception:
            logger.exception("STDIO server failed")
            sys.exit(1)

    async def start_http_server(self, host: str, port: int) -> None:
        """Start server with HTTP transport and WebSocket server."""
        logger.info(f"Starting Shared Context MCP Server (HTTP) on {host}:{port}")

        if not SERVER_AVAILABLE:
            logger.error("Server components not available")
            sys.exit(1)

        try:
            # Initialize server components
            await initialize_server()

            # Import config after server initialization
            from ..config import get_config

            config = get_config()

            # Start WebSocket server if enabled
            websocket_task = None
            if config.mcp_server.websocket_enabled:
                ws_host = config.mcp_server.websocket_host
                ws_port = config.mcp_server.websocket_port
                logger.info(f"Starting WebSocket server on ws://{ws_host}:{ws_port}")

                try:
                    from ..websocket_server import start_websocket_server

                    websocket_task = asyncio.create_task(
                        start_websocket_server(host=ws_host, port=ws_port)
                    )
                except ImportError:
                    logger.warning("WebSocket server dependencies not available")
                except Exception:
                    logger.exception("Failed to start WebSocket server")
            else:
                logger.info(
                    "WebSocket server disabled via config (WEBSOCKET_ENABLED=false)"
                )

            # Use FastMCP's native Streamable HTTP transport
            # mcp-proxy will bridge this to SSE for Claude MCP CLI compatibility
            # Configure uvicorn to use the modern websockets-sansio implementation
            # to avoid deprecation warnings from the legacy websockets API
            uvicorn_config = {"ws": "websockets-sansio"}

            # Log version information just before starting MCP server
            logger.info(
                f"✅ Shared Context MCP Server v{__version__} initialized successfully"
            )

            # Run HTTP server (this will block)
            try:
                await server.run_http_async(
                    host=host, port=port, uvicorn_config=uvicorn_config
                )
            finally:
                # Clean up WebSocket server if it was started
                if websocket_task and not websocket_task.done():
                    logger.info("Stopping WebSocket server...")
                    websocket_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await websocket_task

        except ImportError:
            logger.exception(
                "HTTP server dependencies not available - FastAPI and uvicorn are core dependencies"
            )
            sys.exit(1)
        except Exception:
            logger.exception("HTTP server failed")
            sys.exit(1)


def parse_arguments() -> Any:
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Shared Context MCP Server - Multi-agent coordination and shared memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport Options:
  STDIO (default):  Direct process communication (recommended for Claude Desktop)
  HTTP:            Web server for team/remote access

Examples:
  shared-context-server                          # Start with STDIO (default)
  shared-context-server --transport http        # Start HTTP server on localhost:23456
  shared-context-server --transport http --host 0.0.0.0 --port 9000  # Custom HTTP config

Claude Desktop Integration:
  claude mcp add shared-context-server shared-context-server
        """,
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    # Load config to get proper defaults

    try:
        config = get_config()
        default_host = config.mcp_server.http_host
        default_port = config.mcp_server.http_port
    except Exception:
        # Fallback to hardcoded defaults if config loading fails
        default_host = "localhost"
        default_port = 23456

    parser.add_argument(
        "--host",
        default=default_host,
        help=f"HTTP host address (default: {default_host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help=f"HTTP port (default: {default_port})",
    )
    parser.add_argument(
        "--config", type=str, help="Path to configuration file (.env format)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--version", action="version", version=f"shared-context-server {__version__}"
    )

    # Add subcommands for Docker workflow
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Client configuration command
    client_parser = subparsers.add_parser(
        "client-config", help="Generate MCP client configuration"
    )
    client_parser.add_argument(
        "client",
        choices=["claude", "cursor", "windsurf", "vscode", "generic"],
        help="MCP client type",
    )
    # Get default host and port from config/environment
    try:
        config = get_config()
        default_client_port = config.mcp_server.http_port
        # For client config, we need the externally accessible hostname, not the server bind address
        default_client_host = os.getenv("CLIENT_HOST") or os.getenv(
            "MCP_CLIENT_HOST", "localhost"
        )
    except Exception:
        # Fallback to environment variables or hardcoded defaults
        default_client_host = os.getenv("CLIENT_HOST") or os.getenv(
            "MCP_CLIENT_HOST", "localhost"
        )
        default_client_port = int(os.getenv("HTTP_PORT", "23456"))

    client_parser.add_argument(
        "--host",
        default=default_client_host,
        help=f"Server host (default: {default_client_host})",
    )
    client_parser.add_argument(
        "--port",
        type=int,
        default=default_client_port,
        help=f"Server port (default: {default_client_port})",
    )

    # Status command
    subparsers.add_parser("status", help="Show server status and connected clients")

    return parser.parse_args()


def run_with_optimal_loop(coro: Any) -> Any:
    """Run coroutine with optimal event loop (uvloop if available)."""
    if UVLOOP_AVAILABLE:
        import uvloop

        logger.debug("Using uvloop for enhanced async performance")
        return uvloop.run(coro)
    logger.debug("Using default asyncio event loop")
    return asyncio.run(coro)


async def run_server_stdio() -> None:
    """Run server with STDIO transport."""
    if not SERVER_AVAILABLE:
        logger.error("Server components not available")
        sys.exit(1)

    production_server = ProductionServer()
    await production_server.start_stdio_server()


async def run_server_http(host: str, port: int) -> None:
    """Run server with HTTP transport."""
    if not SERVER_AVAILABLE:
        logger.error("Server components not available")
        sys.exit(1)

    production_server = ProductionServer()
    await production_server.start_http_server(host, port)


def generate_client_config(client: str, host: str, port: int) -> None:
    """Generate MCP client configuration."""
    server_url = f"http://{host}:{port}/mcp/"

    # Get API key from environment for display
    api_key = os.getenv("API_KEY", "").strip()
    api_key_display = api_key if api_key else "YOUR_API_KEY_HERE"

    configs = {
        "claude": f"""Add to Claude Code MCP configuration:
claude mcp add-json shared-context-server '{{
  "type": "http",
  "url": "{server_url}",
  "headers": {{
    "X-API-Key": "{api_key_display}"
  }}
}}'""",
        "cursor": f"""Add to Cursor settings.json:
{{
  "mcp.servers": {{
    "shared-context-server": {{
      "type": "http",
      "url": "{server_url}",
      "headers": {{
        "X-API-Key": "{api_key_display}"
      }}
    }}
  }}
}}""",
        "windsurf": f"""Add to Windsurf MCP configuration:
{{
  "shared-context-server": {{
    "type": "http",
    "url": "{server_url}",
    "headers": {{
      "X-API-Key": "{api_key_display}"
    }}
  }}
}}""",
        "vscode": f"""Add to VS Code settings.json:
{{
  "mcp.servers": {{
    "shared-context-server": {{
      "type": "http",
      "url": "{server_url}",
      "headers": {{
        "X-API-Key": "{api_key_display}"
      }}
    }}
  }}
}}""",
        "generic": f"""Generic MCP client configuration:
Type: http
URL: {server_url}
Headers: X-API-Key: {api_key_display}""",
    }

    print(f"\n=== {client.upper()} MCP Client Configuration ===\n")
    print(configs[client])
    print(f"\nServer URL: {server_url}")

    if api_key_display == "YOUR_API_KEY_HERE":
        print(
            "⚠️  SECURITY: Replace 'YOUR_API_KEY_HERE' with your actual API_KEY from server environment"
        )
        print(
            "   You can find the API_KEY in your server's .env file or environment variables"
        )
    else:
        print(
            f"✅ Using API_KEY from server environment (first 8 chars: {api_key[:8]}...)"
        )

    print()


def show_status(host: str | None = None, port: int | None = None) -> None:
    """Show server status."""
    import requests

    # Get default host and port from config/environment if not provided
    if host is None or port is None:
        try:
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

    try:
        # Check health endpoint
        health_url = f"http://{host}:{port}/health"
        response = requests.get(health_url, timeout=5)

        if response.status_code == 200:
            print(f"✅ Server is running at http://{host}:{port}")
            print(f"✅ Health check: {response.json()}")

            # Try to get MCP endpoint info
            try:
                requests.get(f"http://{host}:{port}/mcp/", timeout=5)
                print("✅ MCP endpoint: Available")
            except Exception:
                print("⚠️  MCP endpoint: Not accessible")

        else:
            print(f"❌ Server health check failed: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at http://{host}:{port}")
        print("   Make sure the server is running with 'docker compose up -d'")
    except Exception as e:
        print(f"❌ Error checking server status: {e}")


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown in containers."""

    def signal_handler(signum: int, _frame: Any) -> None:
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name}, initiating graceful shutdown...")
        sys.exit(0)

    # Handle SIGTERM (Docker stop) and SIGINT (Ctrl+C)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Handle SIGHUP for configuration reload (if needed)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, signal_handler)


def main() -> None:
    """Main CLI entry point."""
    args = parse_arguments()

    # Handle subcommands first
    if hasattr(args, "command") and args.command:
        if args.command == "client-config":
            generate_client_config(args.client, args.host, args.port)
            return
        if args.command == "status":
            show_status()
            return

    # Setup signal handlers for container environments
    setup_signal_handlers()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Load configuration
    try:
        if args.config:
            load_config(args.config)
        get_config()
        logger.info("Configuration loaded successfully")
    except Exception:
        logger.exception("Failed to load configuration")
        sys.exit(1)

    # Start server based on transport with optimal event loop
    try:
        if args.transport == "stdio":
            run_with_optimal_loop(run_server_stdio())
        elif args.transport == "http":
            run_with_optimal_loop(run_server_http(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception:
        logger.exception("Server failed to start")
        sys.exit(1)


if __name__ == "__main__":
    main()
