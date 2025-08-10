#!/usr/bin/env python3
"""
Command Line Interface for Shared Context MCP Server.

This module provides the main CLI entry point for production use,
supporting both STDIO and HTTP transports with proper configuration
management for pipx installation and system deployment.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import NoReturn

# Import uvloop conditionally for better performance
try:
    import uvloop

    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

from ..config import get_config, load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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

    async def start_stdio_server(self) -> NoReturn:
        """Start server with STDIO transport."""
        logger.info("Starting Shared Context MCP Server (STDIO)")

        if not SERVER_AVAILABLE:
            logger.error("Server components not available")
            sys.exit(1)

        try:
            # Initialize server components
            await initialize_server()

            # Run server with STDIO transport
            await server.run_stdio_async()
        except Exception:
            logger.exception("STDIO server failed")
            sys.exit(1)

    async def start_http_server(self, host: str, port: int) -> NoReturn:
        """Start server with HTTP transport."""
        logger.info(f"Starting Shared Context MCP Server (HTTP) on {host}:{port}")

        if not SERVER_AVAILABLE:
            logger.error("Server components not available")
            sys.exit(1)

        try:
            # Import HTTP server components
            import uvicorn

            # Initialize server components
            await initialize_server()

            # Run with uvicorn using FastMCP's built-in HTTP support
            try:
                await server.run_http_async(host=host, port=port)
            except AttributeError:
                # Fallback to FastAPI integration if FastMCP doesn't have run_http_async
                logger.info("Using FastAPI integration for HTTP server")

                from fastapi import FastAPI
                from fastmcp.server.fastapi import FastMCPServer

                # Create FastAPI app with MCP server
                app = FastAPI(
                    title="Shared Context MCP Server",
                    description="Multi-agent shared context and memory coordination server",
                    version="1.0.0",
                )

                # Add MCP server to FastAPI
                mcp_server = FastMCPServer(server)
                mcp_server.add_to_app(app)

                # Add health check endpoint
                @app.get("/health")
                async def health_check():
                    return {"status": "healthy", "server": "shared-context-mcp"}

                # Run with uvicorn
                config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
                uvicorn_server = uvicorn.Server(config)
                await uvicorn_server.serve()

        except ImportError:
            logger.exception(
                "HTTP server dependencies not available - FastAPI and uvicorn are core dependencies"
            )
            sys.exit(1)
        except Exception:
            logger.exception("HTTP server failed")
            sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
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
  shared-context-server --transport http        # Start HTTP server on localhost:8000
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
    parser.add_argument(
        "--host", default="localhost", help="HTTP host address (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="HTTP port (default: 8000)"
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
        "--version", action="version", version="shared-context-server 1.0.0"
    )

    args = parser.parse_args()

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

    # Create production server
    production_server = ProductionServer()

    # Use uvloop for better performance if available
    if UVLOOP_AVAILABLE:
        uvloop.install()
        logger.debug("Using uvloop for enhanced async performance")

    # Start server based on transport
    try:
        if args.transport == "stdio":
            asyncio.run(production_server.start_stdio_server())
        elif args.transport == "http":
            asyncio.run(production_server.start_http_server(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception:
        logger.exception("Server failed to start")
        sys.exit(1)


if __name__ == "__main__":
    main()
