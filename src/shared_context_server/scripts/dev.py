"""
Development server script for Shared Context MCP Server.

This script provides a hot-reload development server with:
- FastMCP server initialization and lifecycle management
- Configuration validation and environment setup
- Database initialization and health checks
- Structured logging and error handling
- Hot reload support for development
"""

from __future__ import annotations

import asyncio
import logging
import signal
import subprocess  # noqa: TC003
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import SharedContextServerConfig

# Check uvloop availability without importing
try:
    import importlib.util

    UVLOOP_AVAILABLE = importlib.util.find_spec("uvloop") is not None
except ImportError:
    UVLOOP_AVAILABLE = False

from ..config import get_config, load_config

# Configure logging first - both console and file
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_file = Path("logs/dev-server.log")

# Ensure logs directory exists
log_file.parent.mkdir(exist_ok=True)

# Configure logging with both console and rotating file handlers
# Get log level from environment or use INFO as default
log_level = logging.INFO
try:
    from ..config import get_config

    config = get_config()
    log_level = getattr(logging, config.operational.log_level.upper(), logging.INFO)
except Exception:
    # Fallback to environment variable if config loading fails
    import os

    env_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, env_log_level, logging.INFO)

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB max size
            backupCount=5,  # Keep 5 backup files
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger(__name__)

# Import server components conditionally to handle missing dependencies
try:
    from ..server import initialize_server, shutdown_server

    SERVER_AVAILABLE = True
except ImportError as e:
    SERVER_AVAILABLE = False
    logger.warning(f"Server components not available: {e}")

# ============================================================================
# DEVELOPMENT SERVER
# ============================================================================


class DevelopmentServer:
    """Development server with hot reload and lifecycle management."""

    def __init__(self, enable_websocket: bool = True) -> None:
        self.config: SharedContextServerConfig | None = None
        self.running = False
        self.enable_websocket = enable_websocket
        self._shutdown_event = asyncio.Event()

    async def setup(self) -> None:
        """Setup the development environment."""
        logger.info("Setting up development environment...")

        try:
            # Load configuration
            self.config = get_config()
            assert self.config is not None
            logger.info(
                f"Configuration loaded for {self.config.development.environment} environment"
            )

            # Validate development settings
            if self.config.is_production():
                logger.warning("Running development server in production mode!")

            # Initialize server components if available
            if SERVER_AVAILABLE:
                await initialize_server()
                logger.info("Server components initialized successfully")
            else:
                logger.warning(
                    "Server components not available - skipping server initialization"
                )

        except Exception:
            logger.exception("Development setup failed")
            raise

    async def run(self) -> None:
        """Run the development server."""
        logger.info("Starting Shared Context MCP Development Server...")

        try:
            await self.setup()
            assert self.config is not None
            self.running = True

            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()

            logger.info("Development server is running...")
            logger.info(f"Server name: {self.config.mcp_server.mcp_server_name}")
            logger.info(f"Transport: {self.config.mcp_server.mcp_transport}")
            logger.info(f"📝 Logs: {log_file.resolve()} (tail -f {log_file})")
            logger.info("🔄 Log rotation: 10MB max size, 5 backup files")

            if self.config.mcp_server.mcp_transport == "http":
                logger.info(
                    f"HTTP server: http://{self.config.mcp_server.http_host}:{self.config.mcp_server.http_port}"
                )
            else:
                logger.info("MCP server running on stdio transport")

            # WebSocket server is now handled by the production CLI
            # Development server focuses on hot reload and development features
            if self.config.mcp_server.websocket_enabled:
                host = self.config.mcp_server.websocket_host
                port = self.config.mcp_server.websocket_port
                logger.info(
                    f"WebSocket server will be started by production CLI on ws://{host}:{port}"
                )
            else:
                logger.info(
                    "WebSocket server disabled via config (WEBSOCKET_ENABLED=false)"
                )

            # Start the actual FastMCP server with hot reload
            if self.config.mcp_server.mcp_transport == "http":
                await self._run_http_server_with_reload()
            else:
                await self._run_stdio_server()

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal...")
        except Exception:
            logger.exception("Development server error")
        finally:
            await self.shutdown()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum: int, _frame: object) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Unix-specific signals
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, signal_handler)

    async def _run_http_server_with_reload(self) -> None:
        """Run the FastMCP HTTP server with hot reload using watchdog."""
        if not SERVER_AVAILABLE:
            logger.warning("Server components not available - cannot start HTTP server")
            return

        try:
            import asyncio
            import os
            import subprocess
            import sys

            from watchdog.events import FileSystemEvent, FileSystemEventHandler
            from watchdog.observers import Observer

            project_root = Path.cwd()
            src_dir = project_root / "src" / "shared_context_server"

            logger.info("Starting FastMCP HTTP server with hot reload...")
            logger.info("🔥 Hot reload enabled - server will restart on file changes")
            logger.info(f"📁 Watching directory: {src_dir}")

            # Track server process
            server_process: subprocess.Popen[str] | None = None

            async def start_server() -> subprocess.Popen[str]:
                """Start the server process"""
                nonlocal server_process
                if server_process is not None:
                    server_process.terminate()
                    try:
                        await asyncio.wait_for(
                            asyncio.to_thread(server_process.wait), timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        server_process.kill()

                # Ensure config is available
                assert self.config is not None, "Configuration not initialized"

                # Start server with environment variables
                env = {
                    **dict(os.environ),
                    "MCP_TRANSPORT": "http",
                    "HTTP_PORT": str(self.config.mcp_server.http_port),
                    "HTTP_HOST": self.config.mcp_server.http_host,
                    "LOG_LEVEL": self.config.operational.log_level,
                }

                server_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "shared_context_server.scripts.cli",
                        "--transport",
                        "http",
                    ],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )

                logger.info(f"🚀 Server started with PID {server_process.pid}")

                # Start background task to capture subprocess output
                async def log_subprocess_output() -> None:
                    if server_process and server_process.stdout:
                        try:
                            while True:
                                line = await asyncio.to_thread(
                                    server_process.stdout.readline
                                )
                                if not line:
                                    break

                                line = line.rstrip()
                                if not line:
                                    continue

                                # Log each line immediately with appropriate level
                                if any(
                                    marker in line
                                    for marker in [
                                        "ERROR",
                                        "CRITICAL",
                                        "Exception",
                                        "Traceback",
                                        "Error:",
                                        "Failed",
                                        "failed",
                                    ]
                                ):
                                    logger.error(f"📤 Server: {line}")
                                elif "WARNING" in line:
                                    logger.warning(f"📤 Server: {line}")
                                elif any(
                                    marker in line
                                    for marker in ["INFO", "Starting", "Listening"]
                                ):
                                    logger.info(f"📤 Server: {line}")
                                else:
                                    logger.debug(f"📤 Server: {line}")

                        except Exception:
                            logger.debug("Subprocess output capture ended")

                asyncio.create_task(log_subprocess_output())
                return server_process

            class ReloadHandler(FileSystemEventHandler):
                """File system event handler for hot reload"""

                def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
                    self.last_reload: float = 0
                    self.debounce_time: float = (
                        1.5  # 1.5 second debounce for database compatibility
                    )
                    self.loop = loop

                def on_modified(self, event: FileSystemEvent) -> None:
                    if event.is_directory:
                        return

                    # Convert path to string if it's bytes
                    path_str = (
                        event.src_path.decode("utf-8")
                        if isinstance(event.src_path, bytes)
                        else str(event.src_path)
                    )

                    if not path_str.endswith(".py"):
                        return

                    import time

                    current_time = time.time()
                    if current_time - self.last_reload < self.debounce_time:
                        return

                    self.last_reload = current_time

                    logger.info(f"🔄 File changed: {path_str}")
                    logger.info("♻️  Restarting server...")

                    # Schedule server restart from thread-safe context
                    asyncio.run_coroutine_threadsafe(start_server(), self.loop)

            # Set up file watcher
            loop = asyncio.get_running_loop()
            event_handler = ReloadHandler(loop)
            observer = Observer()
            observer.schedule(event_handler, str(src_dir), recursive=True)
            observer.start()

            # Start initial server
            await start_server()

            try:
                # Keep the watcher running
                while not self._shutdown_event.is_set():
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down hot reload server...")
            finally:
                observer.stop()
                observer.join()
                if server_process:
                    server_process.terminate()
                    try:
                        await asyncio.wait_for(
                            asyncio.to_thread(server_process.wait), timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        server_process.kill()

        except Exception:
            logger.exception("Failed to start HTTP server with hot reload")
            raise

    async def _run_stdio_server(self) -> None:
        """Run the FastMCP stdio server (no hot reload for stdio)."""
        if not SERVER_AVAILABLE:
            logger.warning(
                "Server components not available - cannot start stdio server"
            )
            return

        try:
            from ..server import server

            logger.info("Starting FastMCP stdio server...")
            logger.warning("📝 Hot reload not available for stdio transport")

            # Start server on stdio
            await server.run_stdio_async(show_banner=True)

        except Exception:
            logger.exception("Failed to start stdio server")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown the development server."""
        if not self.running:
            return

        logger.info("Shutting down development server...")
        self.running = False

        try:
            # WebSocket server is managed by production CLI, not dev server

            if SERVER_AVAILABLE:
                await shutdown_server()
                logger.info("Development server shutdown completed")
            else:
                logger.info("No server components to shutdown")
        except Exception:
            logger.exception("Error during shutdown")


# ============================================================================
# CLI FUNCTIONS
# ============================================================================


async def start_dev_server(enable_websocket: bool = True) -> None:
    """Start the development server."""
    dev_server = DevelopmentServer(enable_websocket=enable_websocket)
    await dev_server.run()


def validate_environment() -> bool:
    """
    Validate the development environment setup.

    Returns:
        bool: True if environment is valid
    """
    logger.info("Validating development environment...")

    try:
        # Check configuration
        config = load_config()
        logger.info("✓ Configuration loaded successfully")

        # Check required environment variables
        if not config.security.api_key:
            logger.error("✗ API_KEY not set")
            return False
        logger.info("✓ API_KEY is configured")

        # Check database path accessibility
        db_path = Path(config.database.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Database path accessible: {db_path}")

        # Check development-specific settings
        if config.development.debug:
            logger.info("✓ Debug mode enabled")

        if config.development.dev_reset_database_on_start:
            logger.warning("⚠ Database reset on start is enabled")

        logger.info("Environment validation completed successfully")

    except Exception:
        logger.exception("✗ Environment validation failed")
        return False
    else:
        return True


def print_server_info() -> None:
    """Print server information and configuration."""
    try:
        config = get_config()

        print("\n" + "=" * 60)
        print("SHARED CONTEXT MCP SERVER - DEVELOPMENT INFO")
        print("=" * 60)
        print(f"Server Name: {config.mcp_server.mcp_server_name}")
        print(f"Version: {config.mcp_server.mcp_server_version}")
        print(f"Environment: {config.development.environment}")
        print(f"Transport: {config.mcp_server.mcp_transport}")

        if config.mcp_server.mcp_transport == "http":
            print(
                f"HTTP Address: http://{config.mcp_server.http_host}:{config.mcp_server.http_port}"
            )

        print(f"Database: {config.database.database_path}")
        print(f"Log Level: {config.operational.log_level}")
        print(f"Debug Mode: {config.development.debug}")
        print("=" * 60)

    except Exception:
        logger.exception("Failed to load server info")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main() -> None:
    """Main entry point for development server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Shared Context MCP Server Development Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m shared_context_server.scripts.dev              # Start development server
  python -m shared_context_server.scripts.dev --validate   # Validate environment
  python -m shared_context_server.scripts.dev --info       # Show server info
        """,
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate development environment and exit",
    )
    parser.add_argument(
        "--info", action="store_true", help="Show server information and exit"
    )
    parser.add_argument(
        "--config-file", type=str, help="Path to custom .env configuration file"
    )
    parser.add_argument(
        "--no-websocket",
        action="store_true",
        help="Disable WebSocket server (enabled by default)",
    )

    args = parser.parse_args()

    # Handle command line options
    if args.info:
        print_server_info()
        return

    if args.validate:
        valid = validate_environment()
        sys.exit(0 if valid else 1)

    # Load custom config file if specified
    if args.config_file:
        from ..config import load_config

        load_config(args.config_file)

    # Start development server
    try:
        # Use uvloop for better performance if available
        if UVLOOP_AVAILABLE:
            # Modern uvloop approach for Python 3.12+
            logger.info("Using uvloop for enhanced async performance")
            # uvloop.install() is deprecated - uvloop will be set up by run_http_async
        else:
            logger.info("uvloop not available, using default asyncio")

        asyncio.run(start_dev_server(enable_websocket=not args.no_websocket))

    except KeyboardInterrupt:
        logger.info("Development server interrupted by user")
        sys.exit(0)
    except Exception:
        logger.exception("Development server failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
