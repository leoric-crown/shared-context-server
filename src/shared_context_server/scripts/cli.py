#!/usr/bin/env python3
"""
Command Line Interface for Shared Context MCP Server.

This module provides the main CLI entry point for production use,
supporting both STDIO and HTTP transports with proper configuration
management for system deployment.
"""
# ruff: noqa: TRY400 - Using logger.error in exception handlers for clean user-facing messages

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

# Check if we're running commands that should suppress config validation logging
client_config_mode = len(sys.argv) >= 2 and sys.argv[1] == "client-config"
version_mode = "--version" in sys.argv
setup_mode = len(sys.argv) >= 2 and sys.argv[1] == "setup"

log_level = (
    logging.CRITICAL
    if client_config_mode or version_mode or setup_mode
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


async def validate_startup_configuration() -> None:
    """
    Validate critical configuration requirements at startup.

    This ensures the server fails fast with helpful error messages
    if essential configuration is missing, rather than waiting for
    the first authentication request to fail.
    """
    import os

    logger.info("Validating startup configuration...")

    # Check JWT encryption key (required for authentication)
    jwt_encryption_key = os.getenv("JWT_ENCRYPTION_KEY")
    if not jwt_encryption_key:
        logger.error("")
        logger.error("🔐 CONFIGURATION ERROR: Missing JWT encryption key")
        logger.error("")
        logger.error("JWT_ENCRYPTION_KEY is required for secure authentication.")
        logger.error("The server cannot start without this key.")
        logger.error("")
        logger.error("Quick fixes:")
        logger.error("  1. Generate secure keys:")
        logger.error("     scs setup")
        logger.error("")
        logger.error("  2. Copy the generated configuration:")
        logger.error("     cp .env.generated .env")
        logger.error("")
        logger.error("  3. Or set the environment variable:")
        logger.error("     export JWT_ENCRYPTION_KEY='your-fernet-key-here'")
        logger.error("")
        sys.exit(1)

    # Validate JWT encryption key format (should be a valid Fernet key)
    try:
        from cryptography.fernet import Fernet

        Fernet(jwt_encryption_key.encode())
    except Exception:
        # Intentionally using logger.error() for clean user-facing messages
        # without technical stack traces
        logger.error("")
        logger.error("🔐 CONFIGURATION ERROR: Invalid JWT encryption key format")
        logger.error("")
        logger.error("JWT_ENCRYPTION_KEY must be a valid Fernet key.")
        logger.error("")
        logger.error("Quick fix:")
        logger.error("  scs setup")
        logger.error("  cp .env.generated .env")
        logger.error("")
        sys.exit(1)

    logger.info("✅ Startup configuration validation completed")


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
            logger.error("")
            logger.error("🔐 CONFIGURATION ERROR: Missing JWT encryption key")
            logger.error("")
            logger.error(
                "The server requires JWT_ENCRYPTION_KEY for secure token management."
            )
            logger.error("Quick fixes:")
            logger.error("")
            logger.error("  1. Generate secure keys:")
            logger.error("     scs setup")
            logger.error("")
            logger.error("  2. Copy the generated configuration:")
            logger.error("     cp .env.generated .env")
            logger.error("")
            logger.error("  3. Or set the environment variable directly:")
            logger.error("     export JWT_ENCRYPTION_KEY='your-generated-key'")
            logger.error("")
            sys.exit(1)

        # JWT Secret Key issues
        if "JWT_SECRET_KEY" in error_message:
            logger.error("")
            logger.error("🔐 CONFIGURATION ERROR: Missing JWT secret key")
            logger.error("")
            logger.error("The server requires JWT_SECRET_KEY for token signing.")
            logger.error("Quick fix:")
            logger.error("  scs setup")
            logger.error("")
            sys.exit(1)

        # Database permission/lock issues
        if (
            "database is locked" in error_message.lower()
            or "permission denied" in error_message.lower()
        ):
            logger.error("")
            logger.error("💾 DATABASE ERROR: Unable to access database file")
            logger.error("")
            logger.error("Common causes and fixes:")
            logger.error("  • Another server instance running:")
            logger.error("    → Check: lsof -i :23456")
            logger.error("    → Kill: pkill -f shared-context-server")
            logger.error("")
            logger.error("  • File permissions issue:")
            logger.error("    → Check: ls -la chat_history.db*")
            logger.error("    → Fix: chmod 664 chat_history.db*")
            logger.error("")
            logger.error("  • Stale lock files:")
            logger.error("    → Clean: rm chat_history.db-wal chat_history.db-shm")
            logger.error("")
            sys.exit(1)

        # Generic database initialization failure with helpful guidance
        logger.error("")
        logger.error("💥 DATABASE INITIALIZATION FAILED")
        logger.error("")
        logger.error("Common fixes (try in order):")
        logger.error("")
        logger.error("  1. Ensure authentication keys are configured:")
        logger.error("     scs setup")
        logger.error("     cp .env.generated .env")
        logger.error("")
        logger.error("  2. Check database file permissions:")
        logger.error("     ls -la chat_history.db*")
        logger.error("")
        logger.error("  3. Verify no other server instances are running:")
        logger.error("     lsof -i :23456")
        logger.error("")
        logger.error("  4. Clean up stale database locks:")
        logger.error("     rm -f chat_history.db-wal chat_history.db-shm")
        logger.error("")
        logger.error(f"Technical details: {e}")
        logger.error("")
        sys.exit(1)


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

            # Run server with STDIO transport (no banner for MCP Inspector compatibility)
            await server.run_stdio_async(show_banner=False)
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
  HTTP (default):   Web server for multi-client access (recommended for shared coordination)
  STDIO:            Direct process communication (legacy, single-client only)

Examples:
  shared-context-server                          # Start with HTTP (default)
  shared-context-server --transport http --host 0.0.0.0 --port 9000  # Custom HTTP config
  shared-context-server --transport stdio       # Start with STDIO for legacy compatibility

Claude Code Integration:
  claude mcp add shared-context-server shared-context-server
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
        default_transport = "stdio"
        default_host = "localhost"
        default_port = 23456

    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default=default_transport,
        help=f"Transport protocol (default: {default_transport}, from MCP_TRANSPORT env var)",
    )

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
        choices=[
            "claude",
            "cursor",
            "windsurf",
            "vscode",
            "gemini",
            "codex",
            "qwen",
            "generic",
        ],
        help="MCP client type",
    )

    # Scope support (Claude Code pattern)
    client_parser.add_argument(
        "-s",
        "--scope",
        choices=["user", "project", "local"],
        default="local",
        help="Configuration scope: user (global), project (shared), or local (default)",
    )

    # Clipboard integration
    client_parser.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Copy configuration to clipboard without confirmation",
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

    # Setup command
    setup_parser = subparsers.add_parser(
        "setup",
        help="Setup keys and configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  scs setup                    # Basic setup: generate keys, create .env, show deployment options
  scs setup docker            # Generate keys + show Docker commands only
  scs setup uvx                # Generate keys + show uvx commands only
  scs setup demo               # Show demo setup guidance (requires repo context)
  scs setup export json       # Create .env file + export keys as JSON to stdout
  scs setup export yaml       # Create .env file + export keys as YAML to stdout
  scs setup export env        # Create .env file + export as shell variables to stdout
  scs setup export docker-env # Create .env file + export as Docker -e flags to stdout
  scs setup --force           # Overwrite existing .env file if it exists

Notes:
  - Without arguments: Creates .env file and shows both Docker and uvx deployment options
  - With deployment type: Creates .env file and shows specific deployment commands
  - With 'export': Creates .env file and exports keys to stdout in specified format
        """,
    )
    setup_parser.add_argument(
        "deployment",
        nargs="?",
        choices=["docker", "uvx", "demo", "export"],
        help="Deployment type: 'docker', 'uvx', 'demo', or 'export'",
    )
    setup_parser.add_argument(
        "format",
        nargs="?",
        choices=["json", "yaml", "env", "docker-env"],
        help="Export format (only used with 'export' deployment): 'json', 'yaml', 'env', or 'docker-env'",
    )
    setup_parser.add_argument(
        "--force", action="store_true", help="Overwrite existing .env file"
    )

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


def generate_client_config(
    client: str, host: str, port: int, scope: str = "local", copy: bool = False
) -> None:
    """Generate MCP client configuration with modern UX."""
    # Import setup utilities for consistent formatting
    try:
        from ..setup_core import Colors
    except ImportError:
        # Fallback colors if import fails
        class Colors:  # type: ignore[no-redef]
            RED = "\033[0;31m"
            GREEN = "\033[0;32m"
            YELLOW = "\033[1;33m"
            BLUE = "\033[0;34m"
            BOLD = "\033[1m"
            NC = "\033[0m"

    server_url = f"http://{host}:{port}/mcp/"

    # Get API key from environment for display
    api_key = os.getenv("API_KEY", "").strip()
    api_key_display = api_key if api_key else "YOUR_API_KEY_HERE"

    # Generate configuration based on client type
    if client == "claude":
        config_text = _generate_claude_config(server_url, api_key_display, scope)
    elif client == "cursor":
        config_text = _generate_cursor_config(server_url, api_key_display)
    elif client == "windsurf":
        config_text = _generate_windsurf_config(server_url, api_key_display)
    elif client == "vscode":
        config_text = _generate_vscode_config(server_url, api_key_display)
    elif client == "gemini":
        config_text = _generate_gemini_config(server_url, api_key_display)
    elif client == "codex":
        config_text = _generate_codex_config(server_url, api_key_display)
    elif client == "qwen":
        config_text = _generate_qwen_config(server_url, api_key_display)
    else:  # generic
        config_text = _generate_generic_config(server_url, api_key_display)

    # Display the configuration
    print(
        f"\n{Colors.BLUE}=== {client.upper()} MCP Client Configuration ==={Colors.NC}\n"
    )
    print(config_text)

    # Show API key status
    if api_key_display == "YOUR_API_KEY_HERE":
        print(
            f"\n{Colors.YELLOW}⚠️  SECURITY: Replace 'YOUR_API_KEY_HERE' with your actual API_KEY{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}   You can find the API_KEY in your server's .env file{Colors.NC}"
        )
    else:
        print(
            f"\n{Colors.GREEN}✅ Using API_KEY from server environment (first 8 chars: {api_key[:8]}...){Colors.NC}"
        )

    # Handle clipboard integration
    _handle_clipboard(config_text, copy, Colors)

    print()


def _generate_claude_config(server_url: str, api_key: str, scope: str) -> str:
    """Generate Claude Code configuration with proper scope."""
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            NC = "\033[0m"

    scope_flag = f" -s {scope}" if scope != "local" else ""

    # For HTTP servers, Claude Code requires add-json with proper JSON structure
    # Format JSON with proper indentation for readability
    json_config = f'''{{
  "type": "http",
  "url": "{server_url}",
  "headers": {{
    "X-API-Key": "{api_key}"
  }}
}}'''

    return f"""Command to add to Claude Code:

{Colors.GREEN}claude mcp add-json shared-context-server{scope_flag} '{json_config}'{Colors.NC}

Scope: {scope}
  • user: Global configuration (available in all projects)
  • project: Project-specific configuration (shared via .mcp.json)
  • local: Local configuration (current project only)"""


def _generate_cursor_config(server_url: str, api_key: str) -> str:
    """Generate Cursor configuration object for insertion."""
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            NC = "\033[0m"

    config_object = f'''"shared-context-server": {{
  "url": "{server_url}",
  "headers": {{
    "X-API-Key": "{api_key}"
  }}
}}'''

    return f"""Insert the following object into your mcpServers section:

{Colors.GREEN}{config_object}{Colors.NC}

Configuration locations:
  • Global: ~/.cursor/mcp.json (all projects)
  • Project: .cursor/mcp.json (project-specific)

Full structure example:
{{
  "mcpServers": {{
    {config_object}
  }}
}}"""


def _generate_windsurf_config(server_url: str, api_key: str) -> str:
    """Generate Windsurf configuration."""
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            NC = "\033[0m"

    return f"""Add to Windsurf MCP configuration:

{Colors.GREEN}{{
  "shared-context-server": {{
    "url": "{server_url}",
    "headers": {{
      "X-API-Key": "{api_key}"
    }}
  }}
}}{Colors.NC}"""


def _generate_vscode_config(server_url: str, api_key: str) -> str:
    """Generate VS Code configuration."""
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            NC = "\033[0m"

    return f"""Add to VS Code settings.json:

{Colors.GREEN}{{
  "mcp.servers": {{
    "shared-context-server": {{
      "url": "{server_url}",
      "headers": {{
        "X-API-Key": "{api_key}"
      }}
    }}
  }}
}}{Colors.NC}"""


def _generate_gemini_config(server_url: str, api_key: str) -> str:
    """Generate Gemini CLI configuration."""
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            NC = "\033[0m"

    # Extract server name from URL for Gemini CLI command
    server_name = "shared-context-server"

    return f"""Command to add to Gemini CLI:

{Colors.GREEN}gemini mcp add {server_name} {server_url} -t http -H "X-API-Key: {api_key}"{Colors.NC}

Configuration details:
  • Server name: {server_name}
  • Transport type: http
  • URL: {server_url}
  • Authentication: X-API-Key header"""


def _generate_codex_config(server_url: str, api_key: str) -> str:
    """Generate Codex CLI configuration with mcp-proxy bridge."""
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            YELLOW = "\033[1;33m"
            NC = "\033[0m"

    return f"""Add to ~/.codex/config.toml:

{Colors.GREEN}[mcp_servers.shared-context-server]
command = "mcp-proxy"
args = ["--transport=streamablehttp", "-H", "X-API-Key", "{api_key}", "{server_url}"]{Colors.NC}

{Colors.YELLOW}Prerequisites:{Colors.NC}
  1. Install mcp-proxy: {Colors.GREEN}uv tool install mcp-proxy{Colors.NC}
  2. Verify installation: {Colors.GREEN}mcp-proxy --version{Colors.NC}

Configuration details:
  • Codex CLI only supports STDIO transport
  • mcp-proxy bridges HTTP MCP servers to STDIO
  • Server URL: {server_url}
  • Authentication: X-API-Key header via mcp-proxy"""


def _generate_qwen_config(server_url: str, api_key: str) -> str:
    """Generate Qwen CLI configuration for MCP servers.

    Args:
        server_url: The MCP server URL
        api_key: API key for authentication (included for consistency with other generators)
    """
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            YELLOW = "\033[1;33m"
            BLUE = "\033[0;34m"
            NC = "\033[0m"

    return f"""Add to ~/.qwen/settings.json:

{Colors.GREEN}{{
  "mcpServers": {{
    "shared-context-server": {{
      "httpUrl": "{server_url}",
      "timeout": 30000
    }}
  }}
}}{Colors.NC}

{Colors.YELLOW}Authentication Setup:{Colors.NC}
  Add X-API-Key header with value: {api_key}
  (see Qwen CLI documentation for header configuration)

{Colors.BLUE}Interactive Setup (Alternative):{Colors.NC}
  1. Launch Qwen CLI: {Colors.GREEN}qwen{Colors.NC}
  2. Run setup command: {Colors.GREEN}/setup-mcp{Colors.NC}
  3. Use MCP management: {Colors.GREEN}/mcp{Colors.NC}

Configuration details:
  • File location: ~/.qwen/settings.json
  • Transport: Direct HTTP (StreamableHTTPClientTransport)
  • Server URL: {server_url}
  • Timeout: 30 seconds
  • Authentication: X-API-Key header (configuration needed)"""


def _generate_generic_config(server_url: str, api_key: str) -> str:
    """Generate generic MCP configuration."""
    # Import colors for this function
    try:
        from ..setup_core import Colors
    except ImportError:

        class Colors:  # type: ignore[no-redef]
            GREEN = "\033[0;32m"
            NC = "\033[0m"

    return f"""Generic MCP client configuration:

{Colors.GREEN}Type: http
URL: {server_url}
Headers: X-API-Key: {api_key}{Colors.NC}"""


def _handle_clipboard(content: str, copy: bool, Colors: Any) -> None:
    """Handle clipboard integration with user confirmation."""
    # Try to import clipboard functionality
    clipboard_available = False
    try:
        import pyperclip  # type: ignore[import-untyped]

        clipboard_available = True
    except ImportError:
        pass

    if not clipboard_available:
        return

    # Extract the actual command/config from the formatted text
    clipboard_content = _extract_clipboard_content(content)

    if copy:
        # Auto-copy without confirmation
        try:
            pyperclip.copy(clipboard_content)
            print(f"\n{Colors.GREEN}✅ Copied to clipboard{Colors.NC}")
        except Exception:
            print(f"\n{Colors.YELLOW}⚠️  Failed to copy to clipboard{Colors.NC}")
    else:
        # Ask for confirmation
        try:
            response = (
                input(f"\n{Colors.YELLOW}Copy to clipboard? [y/N]: {Colors.NC}")
                .strip()
                .lower()
            )
            if response in ["y", "yes"]:
                pyperclip.copy(clipboard_content)
                print(f"{Colors.GREEN}✅ Copied to clipboard{Colors.NC}")
        except (KeyboardInterrupt, EOFError):
            print()  # Clean exit on Ctrl+C


def _extract_clipboard_content(formatted_text: str) -> str:
    """Extract the actual command/config from formatted display text."""
    import re

    # Remove ANSI color codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    clean_text = ansi_escape.sub("", formatted_text)

    # For Claude Code, extract the command line (including add-json)
    if "claude mcp add" in clean_text:
        lines = clean_text.split("\n")
        for line in lines:
            if line.strip().startswith("claude mcp add"):
                return line.strip()

    # For Gemini CLI, extract the command line
    if "gemini mcp add" in clean_text:
        lines = clean_text.split("\n")
        for line in lines:
            if line.strip().startswith("gemini mcp add"):
                return line.strip()

    # For Codex CLI, extract the TOML configuration block
    if "[mcp_servers.shared-context-server]" in clean_text:
        lines = clean_text.split("\n")
        in_toml_block = False
        toml_lines: list[str] = []
        for line in lines:
            if "[mcp_servers.shared-context-server]" in line:
                in_toml_block = True
            if in_toml_block:
                # Stop at empty line or next section
                if line.strip() == "" and len(toml_lines) > 1:
                    break
                if (
                    line.strip().startswith("[")
                    and "[mcp_servers.shared-context-server]" not in line
                ):
                    break
                # Skip prerequisite/description lines that start with bullet points or explanatory text
                if not line.strip().startswith("•") and not line.strip().startswith(
                    "Configuration details"
                ):
                    toml_lines.append(line)
        return "\n".join(toml_lines).strip()

    # For Qwen CLI, extract the JSON mcpServers configuration
    if '"httpUrl"' in clean_text and '"mcpServers"' in clean_text:
        lines = clean_text.split("\n")
        in_json_block = False
        json_lines = []
        brace_count = 0
        for line in lines:
            if line.strip().startswith("{") and not in_json_block:
                in_json_block = True
                json_lines.append(line)
                brace_count += line.count("{") - line.count("}")
            elif in_json_block:
                json_lines.append(line)
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0 and len(json_lines) > 1:
                    break
        return "\n".join(json_lines).strip()

    # For Cursor and others, extract the JSON object
    if '"shared-context-server"' in clean_text:
        # Extract just the object that needs to be inserted
        lines = clean_text.split("\n")
        in_object = False
        object_lines = []
        for line in lines:
            if '"shared-context-server":' in line:
                in_object = True
            if in_object:
                object_lines.append(line)
                if line.strip() == "}" and len(
                    [
                        line_content
                        for line_content in object_lines
                        if "{" in line_content
                    ]
                ) == len(
                    [
                        line_content
                        for line_content in object_lines
                        if "}" in line_content
                    ]
                ):
                    break
        return "\n".join(object_lines)

    # Fallback: return cleaned text
    return clean_text.strip()


def run_setup_command(
    deployment: str | None, format_type: str | None, force: bool
) -> None:
    """Run setup command with integrated setup functionality."""
    from ..setup_core import (
        Colors,
        _apply_demo_configuration,
        check_demo_dependencies,
        create_env_file,
        export_keys,
        generate_keys,
        show_dependency_error,
        show_docker_commands,
        show_security_notes,
        show_uvx_commands,
    )

    # Validate argument combinations
    if format_type and deployment != "export":
        print(
            f"{Colors.RED}❌ Error: Format argument '{format_type}' can only be used with 'export' deployment.{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}   Did you mean: scs setup export {format_type}?{Colors.NC}"
        )
        print()
        sys.exit(1)

    # Generate keys first
    keys = generate_keys()

    # Handle different deployment types
    if deployment == "export":
        # For export, create .env file first, then export to stdout
        result = create_env_file(keys, force, demo=False)
        if not result:
            sys.exit(1)

        export_format = format_type or "json"
        if export_format == "env":
            export_format = "export"
        export_keys(keys, export_format)
        return

    # For all other cases, create env file unless it's demo mode handled specially
    used_generated = False
    if deployment != "demo":
        result = create_env_file(keys, force, demo=False)
        if not result:
            sys.exit(1)
        _, used_generated = result

    # Show specific commands based on deployment type
    if deployment == "docker":
        show_docker_commands(keys, demo=False)
    elif deployment == "uvx":
        show_uvx_commands(keys, demo=False)
    elif deployment == "demo":
        # Handle demo mode - create demo files in current directory

        print(
            f"\n{Colors.BLUE}🎪 Setting up demo environment in current directory{Colors.NC}"
        )
        print()

        # Check demo dependencies (npm/npx for octocode MCP server)
        deps_available, missing_deps = check_demo_dependencies()
        if not deps_available:
            show_dependency_error(missing_deps)
            print(
                f"{Colors.YELLOW}💡 You can still run the demo with a limited MCP configuration.{Colors.NC}"
            )
            print(
                f"{Colors.YELLOW}   The shared-context-server will work, but octocode features won't be available.{Colors.NC}"
            )
            print()
            if not force:
                try:
                    response = (
                        input("Continue with limited demo setup? [y/N]: ")
                        .strip()
                        .lower()
                    )
                    if response not in ["y", "yes"]:
                        print(f"{Colors.YELLOW}Demo setup cancelled.{Colors.NC}")
                        return
                    print()
                except (KeyboardInterrupt, EOFError):
                    print()
                    print(f"{Colors.YELLOW}Demo setup cancelled.{Colors.NC}")
                    return
            else:
                print(
                    f"{Colors.YELLOW}🔄 Force mode: Continuing with limited demo setup...{Colors.NC}"
                )
                print()

        # Use standard setup flow with demo-specific port defaults
        result = create_env_file(keys, force, demo=False)
        if not result:
            sys.exit(1)

        env_file_path, used_generated = result

        # Apply demo-specific configuration to the .env file
        _apply_demo_configuration(env_file_path, keys, deps_available)

        print(f"{Colors.BLUE}🎪 Demo Environment Setup Complete!{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}Next steps:{Colors.NC}")
        print(f"{Colors.YELLOW}1. Start the server:{Colors.NC}")
        print(
            f"{Colors.GREEN}   scs{Colors.NC}  {Colors.BLUE}# Uses demo configuration automatically{Colors.NC}"
        )
        print()
        print(f"{Colors.YELLOW}2. Configure MCP clients:{Colors.NC}")
        print(f"{Colors.GREEN}   Option A: Use pre-generated config:{Colors.NC}")
        print(f"{Colors.GREEN}   claude --mcp-config .mcp.json{Colors.NC}")
        print()
        print(f"{Colors.GREEN}   Option B: Add to your existing config:{Colors.NC}")
        print(f"{Colors.GREEN}   scs client-config claude -s user --copy{Colors.NC}")
        print()
        print(
            f"{Colors.YELLOW}3. You're ready for multi-expert collaboration!{Colors.NC}"
        )
        print(
            f"{Colors.BLUE}   • Server running with demo-specific configuration{Colors.NC}"
        )
        print(f"{Colors.BLUE}   • MCP client configured for Claude Code{Colors.NC}")
        print(
            f"{Colors.BLUE}   • {('Octocode MCP included' if deps_available else 'Limited MCP setup (octocode unavailable)')}{Colors.NC}"
        )
        print()
        print(f"{Colors.GREEN}💡 Demo database: demo_chat_history.db{Colors.NC}")
        print(f"{Colors.GREEN}💡 MCP config: .mcp.json{Colors.NC}")
        return
    else:
        # Default: show both main deployment methods
        show_docker_commands(keys, demo=False)
        show_uvx_commands(keys, demo=False)

    # Show security notes and completion message
    show_security_notes()

    # Add client configuration instructions for all deployment types
    print()
    print(
        f"{Colors.YELLOW}📋 After starting your server, configure MCP clients:{Colors.NC}"
    )
    print(
        f"{Colors.GREEN}   scs client-config claude -s user --copy{Colors.NC}    {Colors.BLUE}# Claude Code (global){Colors.NC}"
    )
    print(
        f"{Colors.GREEN}   scs client-config cursor --copy{Colors.NC}            {Colors.BLUE}# Cursor IDE{Colors.NC}"
    )
    print()
    print(
        f"{Colors.YELLOW}💡 Scope options for Claude Code: -s user (global) | -s project | -s local{Colors.NC}"
    )

    if used_generated:
        print(
            f"{Colors.GREEN}{Colors.BOLD}🎉 Setup complete! Configuration saved safely to .env.generated{Colors.NC}"
        )
        print()
        print(f"{Colors.YELLOW}📋 Next steps to use your new configuration:{Colors.NC}")
        print(f"{Colors.GREEN}   1. Review the generated configuration:{Colors.NC}")
        print(f"{Colors.GREEN}      cat .env.generated{Colors.NC}")
        print(
            f"{Colors.GREEN}   2. Update your .env file with the new keys:{Colors.NC}"
        )
        print(
            f"{Colors.GREEN}      • Copy individual keys from .env.generated to .env{Colors.NC}"
        )
        print(
            f"{Colors.GREEN}      • Or replace entirely: cp .env.generated .env{Colors.NC}"
        )
        print()
        print(
            f"{Colors.YELLOW}💡 Your server will use the new keys once you update .env{Colors.NC}"
        )
    else:
        print(
            f"{Colors.GREEN}{Colors.BOLD}🎉 Setup complete! Your shared-context-server is ready to use.{Colors.NC}"
        )

        # Add client configuration instructions
        print()
        print(f"{Colors.YELLOW}📋 Next steps:{Colors.NC}")
        print(
            f"{Colors.GREEN}   1. Start the server: `shared-context-server` or `scs`{Colors.NC}"
        )
        print(
            f"{Colors.GREEN}   2. Configure MCP clients (commands shown above){Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}   3. Start collaborating with multi-agent workflows!{Colors.NC}"
        )


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
            generate_client_config(
                args.client, args.host, args.port, args.scope, args.copy
            )
            return
        if args.command == "status":
            show_status()
            return
        if args.command == "setup":
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
        run_with_optimal_loop(validate_startup_configuration())
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


if __name__ == "__main__":
    main()
