"""
CLI Main Orchestration Module - Core command coordination and execution.

This module contains the primary CLI orchestration logic extracted from the
monolithic cli.py, providing centralized command handling, argument parsing,
and server lifecycle management.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Import uvloop conditionally for better performance
try:
    import uvloop

    UVLOOP_AVAILABLE = True
except ImportError:
    uvloop = None  # type: ignore[assignment]
    UVLOOP_AVAILABLE = False

# Configure logging - use environment LOG_LEVEL if available

from .. import __version__
from ..config import get_config, load_config
from .startup_validation import validate_environment
from .status_utils import show_status_interactive
from .utils import Colors

# Import server components
try:
    from ..core_server import initialize_server

    SERVER_AVAILABLE = True
except ImportError:
    SERVER_AVAILABLE = False
    logging.getLogger(__name__).exception("Server components not available")

logger = logging.getLogger(__name__)


async def ensure_database_initialized() -> None:
    """
    Ensure database is properly initialized with all required tables.

    This function is idempotent - it checks if critical tables exist
    and only runs initialization if they're missing. This ensures
    fresh deployments work without requiring manual intervention.
    """
    try:
        from ..database import get_db_connection

        # Check if critical tables exist by trying to query them
        async with get_db_connection() as conn:
            # Try to query critical tables that must exist for the server to function
            critical_tables = ["sessions", "messages", "audit_log", "secure_tokens"]
            missing_tables = []

            # Check which tables exist by querying sqlite_master for all at once
            try:
                table_list = "', '".join(critical_tables)
                result = await conn.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('{table_list}')"
                )
                rows = await result.fetchall()
                existing_tables = {row[0] for row in rows}
                missing_tables = [
                    table for table in critical_tables if table not in existing_tables
                ]
            except Exception:
                # If query fails entirely, assume all tables are missing
                missing_tables = critical_tables.copy()

            if missing_tables:
                logger.info(f"Missing database tables detected: {missing_tables}")
                logger.info("Initializing database schema...")

                # Import and run database initialization using the WORKING SQLAlchemy manager
                # The database_manager version has broken schema path resolution in Docker
                from ..config import get_database_url
                from ..database_sqlalchemy import SimpleSQLAlchemyManager

                # Convert database URL to format expected by working manager
                database_url = get_database_url()
                if database_url.startswith("sqlite://"):
                    database_url = database_url.replace(
                        "sqlite://", "sqlite+aiosqlite://", 1
                    )

                sqlalchemy_manager = SimpleSQLAlchemyManager(database_url)
                await sqlalchemy_manager.initialize()

                logger.info("✅ Database schema initialized successfully")
            else:
                logger.debug("Database schema is already initialized")

    except Exception as e:
        logger.exception("Database initialization check failed")

        # Check for common configuration issues and provide helpful guidance
        # Note: Using logger.error() below for user-facing messages without stack traces
        error_message = str(e)

        # JWT/Authentication configuration issues
        if "JWT_ENCRYPTION_KEY" in error_message:
            logger.error("")  # noqa: TRY400
            logger.error("🔐 CONFIGURATION ERROR: Missing JWT encryption key")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            logger.error(  # noqa: TRY400
                "The server requires JWT_ENCRYPTION_KEY for secure token management."
            )
            logger.error("Quick fixes:")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            logger.error("  1. Generate secure keys:")  # noqa: TRY400
            logger.error("     scs setup")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            logger.error("  2. Copy the generated configuration:")  # noqa: TRY400
            logger.error("     cp .env.generated .env")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            logger.error("  3. Or set the environment variable:")  # noqa: TRY400
            logger.error("     export JWT_ENCRYPTION_KEY='your-fernet-key-here'")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            sys.exit(1)

        # Database/SQLite specific errors
        if "database is locked" in error_message.lower():
            logger.error("")  # noqa: TRY400
            logger.error("💾 DATABASE ERROR: Database is locked")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            logger.error(  # noqa: TRY400
                "Another process may be using the database, or a previous session didn't close cleanly."
            )
            logger.error("Quick fixes:")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            logger.error("  1. Stop any running shared-context-server instances")  # noqa: TRY400
            logger.error("  2. Check for lock files and remove if necessary")  # noqa: TRY400
            logger.error("  3. Try starting the server again")  # noqa: TRY400
            logger.error("")  # noqa: TRY400
            sys.exit(1)

        # Generic configuration issues
        logger.error("")  # noqa: TRY400
        logger.error("⚙️  CONFIGURATION ERROR: Server initialization failed")  # noqa: TRY400
        logger.error("")  # noqa: TRY400
        logger.error("This usually indicates a configuration issue.")  # noqa: TRY400
        logger.error("Quick diagnostic steps:")  # noqa: TRY400
        logger.error("")  # noqa: TRY400
        logger.error("  1. Check your .env file configuration:")  # noqa: TRY400
        logger.error("     cat .env")  # noqa: TRY400
        logger.error("")  # noqa: TRY400
        logger.error("  2. Regenerate configuration if needed:")  # noqa: TRY400
        logger.error("     scs setup")  # noqa: TRY400
        logger.error("")  # noqa: TRY400
        logger.error("  3. Check logs for more specific error details above")  # noqa: TRY400
        logger.error("")  # noqa: TRY400
        sys.exit(1)


class ProductionServer:
    """Production server lifecycle management with proper cleanup."""

    def __init__(self) -> None:
        self.config = None
        self.server = None
        self.server_instance: FastMCP | None = None

    async def start_http(self, host: str, port: int) -> None:
        """Start HTTP server with production configuration."""
        if not SERVER_AVAILABLE:
            logger.error("Server components not available")
            sys.exit(1)

        # Initialize server with proper configuration
        self.server_instance = await initialize_server()

        # Import config and server instance
        from ..config import get_config
        from ..server import server

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

        logger.info(f"Starting shared-context-server HTTP mode on {host}:{port}")
        logger.info(f"Dashboard will be available at: http://{host}:{port}/ui/")
        logger.info(f"Health check endpoint: http://{host}:{port}/health")
        logger.info(f"MCP endpoint: http://{host}:{port}/mcp/")

        # If running in a container with host port mappings, log external URLs too
        try:
            client_host = os.getenv("MCP_CLIENT_HOST", config.mcp_server.http_host)
            external_http_port = int(os.getenv("EXTERNAL_HTTP_PORT", str(port)))
            external_ws_port = (
                int(os.getenv("EXTERNAL_WEBSOCKET_PORT", str(ws_port)))
                if config.mcp_server.websocket_enabled
                else None
            )

            # Only log external mapping if it differs or explicitly set
            if str(external_http_port) != str(port) or os.getenv("EXTERNAL_HTTP_PORT"):
                logger.info(
                    "External (host) HTTP URL: "
                    f"http://{client_host}:{external_http_port}/"
                )
                logger.info(
                    "External (host) Dashboard: "
                    f"http://{client_host}:{external_http_port}/ui/"
                )
                logger.info(
                    "External (host) MCP endpoint: "
                    f"http://{client_host}:{external_http_port}/mcp/"
                )

            if external_ws_port is not None and (
                str(external_ws_port) != str(ws_port)
                or os.getenv("EXTERNAL_WEBSOCKET_PORT")
            ):
                logger.info(
                    f"External (host) WebSocket: ws://{client_host}:{external_ws_port}"
                )
        except Exception:
            logger.debug("External port mapping logging skipped")

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
        except ImportError:
            logger.exception(
                "HTTP server dependencies not available - FastAPI and uvicorn are core dependencies"
            )
            sys.exit(1)
        except Exception:
            logger.exception("HTTP server failed")
            sys.exit(1)
        finally:
            # Clean up WebSocket server if it was started
            if websocket_task and not websocket_task.done():
                logger.info("Stopping WebSocket server...")
                websocket_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await websocket_task

    async def start_stdio(self) -> None:
        """Start STDIO server for direct MCP communication."""
        if not SERVER_AVAILABLE:
            logger.error("Server components not available")
            sys.exit(1)

        try:
            logger.info("Starting shared-context-server STDIO mode")

            # Initialize server instance
            self.server_instance = await initialize_server()

            # For STDIO mode, delegate to existing server implementation
            # Import the server instance
            from ..server import server

            await server.run_stdio_async(show_banner=True)
        except Exception:
            logger.exception("Failed to start STDIO server")
            sys.exit(1)

    async def shutdown(self) -> None:
        """Graceful server shutdown."""
        if self.server_instance:
            logger.info("Shutting down server...")
            # Add any cleanup logic here
            self.server_instance = None


def parse_arguments() -> Any:
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Shared Context MCP Server - Multi-agent coordination and shared memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport Options:
  HTTP (default):   Web server for multi-client access (recommended for shared coordination)
  STDIO:            Direct process communication (legacy, single-client only)

Examples:
  shared-context-server                          # Start with HTTP (default)
  shared-context-server --transport http --host 0.0.0.0 --port 9000  # Custom HTTP config
  shared-context-server --transport stdio       # Start with STDIO for legacy compatibility

MCP Client Configuration:
  shared-context-server client-config claude -c # Generate Claude Code config and copy to clipboard
  shared-context-server client-config cursor    # Generate Cursor IDE config (prompts to copy)
  shared-context-server client-config all -o    # Save all client configs to default file (recommended)
        """,
    )

    # Load config to get proper defaults
    try:
        config = get_config()
        default_transport = config.mcp_server.mcp_transport.lower()
        default_host = config.mcp_server.http_host
        default_port = config.mcp_server.http_port
    except Exception:
        # Fallback to hardcoded defaults if config loading fails
        default_transport = "http"
        default_host = "localhost"
        default_port = 23456

    parser.add_argument(
        "--version", action="version", version=f"shared-context-server {__version__}"
    )

    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default=default_transport,
        help=f"Transport protocol (default: {default_transport})",
    )

    parser.add_argument(
        "--host",
        default=default_host,
        help=f"HTTP server host (default: {default_host})",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help=f"HTTP server port (default: {default_port})",
    )

    parser.add_argument(
        "--config", help="Path to configuration file (overrides default config loading)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Client configuration subcommand
    client_parser = subparsers.add_parser(
        "client-config",
        help="Generate MCP client configuration",
        description="Generate configuration for specific MCP clients with proper formatting and clipboard support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  scs client-config claude                    # Generate Claude Code config (prompts to copy)
  scs client-config claude -s user -c        # Generate Claude Code config for user scope, auto-copy
  scs client-config cursor -c                # Generate Cursor IDE config, auto-copy
  scs client-config all -o                   # Save ALL client configs to default file (recommended)
  scs client-config all -o custom.md        # Save ALL client configs to custom file
  scs client-config all                      # Display all client configs to console
  scs client-config vscode --host 0.0.0.0    # Generate VS Code config for custom host

Supported Clients:
  claude          Claude Code CLI (supports scopes: user, project, local, dynamic)
  cursor          Cursor IDE
  windsurf        Windsurf IDE
  vscode          Visual Studio Code
  claude-desktop  Claude Desktop app
  gemini          Gemini CLI
  codex           Codex CLI
  qwen            Qwen CLI
  kiro            Kiro IDE
  all             All supported clients (saves to file by default, perfect for documentation/sharing)
        """,
    )
    client_parser.add_argument(
        "client",
        choices=[
            "claude",
            "cursor",
            "windsurf",
            "vscode",
            "claude-desktop",
            "gemini",
            "codex",
            "qwen",
            "kiro",
            "all",
        ],
        help="MCP client type to generate configuration for, or 'all' for all clients",
    )
    client_parser.add_argument(
        "--host", help="Server host address (default: from config, usually localhost)"
    )
    client_parser.add_argument(
        "--port",
        type=int,
        help="Server port number (default: from config, usually 22456)",
    )
    client_parser.add_argument(
        "--scope",
        "-s",
        choices=["user", "project", "local", "dynamic"],
        default="local",
        help="Configuration scope for Claude Code only: user (global), project (shared via .mcp.json), local (current project), dynamic (runtime) - default: local",
    )
    client_parser.add_argument(
        "-c",
        "--copy",
        nargs="?",
        const="yes",
        default="prompt",
        help="Clipboard behavior: -c or -c yes (auto-copy), -c no (don't copy), no flag (prompt user) - default: prompt. Ignored when using -o/--output.",
    )
    client_parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        const="mcp-client-configurations.md",
        help="Save configurations to file (recommended for 'all' client type). Use -o with no argument to save to 'mcp-client-configurations.md', or -o filename.md to specify custom name. If not specified, displays to console.",
    )

    # Status subcommand
    status_parser = subparsers.add_parser("status", help="Show server status")
    status_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed status"
    )
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Setup subcommand
    setup_parser = subparsers.add_parser("setup", help="Setup and configuration")
    setup_parser.add_argument(
        "deployment",
        nargs="?",
        choices=["docker", "uvx", "demo", "export"],
        help="Deployment type",
    )
    setup_parser.add_argument(
        "format",
        nargs="?",
        choices=[
            "json",
            "yaml",
            "env",
            "docker-env",
            "claude",
            "cursor",
            "windsurf",
            "vscode",
            "claude-desktop",
            "gemini",
            "codex",
            "qwen",
            "kiro",
        ],
        help="Export format (only with 'export'): original formats (json, yaml, env, docker-env) or client configs (claude, cursor, windsurf, vscode, claude-desktop, gemini, codex, qwen, kiro)",
    )
    setup_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force overwrite existing configuration",
    )

    return parser.parse_args()


def run_with_optimal_loop(coro: Any) -> Any:
    """Run coroutine with optimal event loop (uvloop if available)."""
    if UVLOOP_AVAILABLE:
        # Use uvloop.run() directly instead of deprecated uvloop.install() + asyncio.run()
        return uvloop.run(coro)
    return asyncio.run(coro)


async def run_server_stdio() -> None:
    """Run server in STDIO mode."""
    server = ProductionServer()
    await server.start_stdio()


async def run_server_http(host: str, port: int) -> None:
    """Run server in HTTP mode."""
    server = ProductionServer()
    await server.start_http(host, port)


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown in container environments."""

    def signal_handler(signum: int, frame: Any) -> None:  # noqa: ARG001
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)

    # Handle common container signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Handle SIGHUP for configuration reload (if available on platform)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, signal_handler)


def main() -> None:
    """Main CLI entry point."""
    args = parse_arguments()

    # Handle subcommands first
    if hasattr(args, "command") and args.command:
        if args.command == "client-config":
            # Import client config generation
            from ..scripts.cli import generate_client_config

            # Parse copy argument based on the new logic:
            # No -c flag (default="prompt"): Prompt user
            # -c with no value (const="yes"): Copy without prompting
            # -c yes: Copy without prompting
            # -c no: Don't copy without prompting
            if args.copy == "prompt":
                # No -c flag was provided, prompt the user
                copy_behavior = "prompt"
            elif args.copy.lower() in ("yes", "y", "true", "1"):
                copy_behavior = "copy"
            else:  # "no", "n", "false", "0", etc.
                copy_behavior = "no_copy"

            # Get host and port with proper defaults
            host = args.host
            port = args.port
            if host is None or port is None:
                try:
                    config = get_config()
                    host = host or config.mcp_server.http_host
                    port = port or config.mcp_server.http_port
                except Exception:
                    host = host or "localhost"
                    port = port or 23456

            if args.client == "all":
                # Import all configs generation
                from ..scripts.cli import generate_all_client_configs

                # For 'all' client type, handle output file logic
                output_file = args.output
                if output_file is None:
                    # No -o flag provided, suggest using it
                    print(
                        f"\n{Colors.YELLOW}💡 Tip: Save all configurations to a file for easy sharing:{Colors.NC}"
                    )
                    print(
                        f"{Colors.GREEN}   scs client-config all -o{Colors.NC}                    {Colors.BLUE}# Saves to mcp-client-configurations.md{Colors.NC}"
                    )
                    print(
                        f"{Colors.GREEN}   scs client-config all -o custom.md{Colors.NC}          {Colors.BLUE}# Saves to custom filename{Colors.NC}"
                    )
                    print(f"{Colors.BLUE}Displaying to console...{Colors.NC}\n")
                    output_file = None  # Display to console
                # else: output_file is either the default filename (from const) or user-specified filename

                generate_all_client_configs(host, port, output_file)
            else:
                # Single client configs don't support output file (they're short enough for clipboard)
                if (
                    args.output is not None
                ):  # Check for None since empty string or filename both indicate -o was used
                    print(
                        f"\n{Colors.YELLOW}⚠️  Output file (-o) is only supported for 'all' client type{Colors.NC}"
                    )
                    print(
                        f"{Colors.YELLOW}   For single clients, use clipboard integration with -c flag{Colors.NC}"
                    )
                    print(
                        f"{Colors.BLUE}   For all clients: scs client-config all -o{Colors.NC}"
                    )
                    return

                generate_client_config(
                    args.client, host, port, args.scope, copy_behavior
                )
            return
        if args.command == "status":
            show_status_interactive(args.host, args.port)
            return
        if args.command == "setup":
            # Import setup command handling
            from ..scripts.cli import run_setup_command

            deployment = getattr(args, "deployment", None)
            format_type = getattr(args, "format", None)
            force = getattr(args, "force", False)
            run_setup_command(deployment, format_type, force)
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

    # Validate critical configuration before starting server
    try:
        run_with_optimal_loop(validate_environment())
    except Exception:
        logger.exception("Configuration validation failed")
        sys.exit(1)

    # Ensure database is initialized before starting server
    try:
        run_with_optimal_loop(ensure_database_initialized())
        logger.info("Database initialization check completed")
    except Exception:
        logger.exception("Database initialization failed")
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
