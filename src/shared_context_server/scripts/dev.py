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
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import SharedContextServerConfig

# Import uvloop conditionally
try:
    import uvloop

    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

from ..config import get_config, load_config

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
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

    def __init__(self) -> None:
        self.config: SharedContextServerConfig | None = None
        self.running = False
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

            if self.config.mcp_server.mcp_transport == "http":
                logger.info(
                    f"HTTP server: http://{self.config.mcp_server.http_host}:{self.config.mcp_server.http_port}"
                )
            else:
                logger.info("MCP server running on stdio transport")

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

        def signal_handler(signum: int, _frame: Any) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Unix-specific signals
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, signal_handler)

    async def shutdown(self) -> None:
        """Gracefully shutdown the development server."""
        if not self.running:
            return

        logger.info("Shutting down development server...")
        self.running = False

        try:
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


async def start_dev_server() -> None:
    """Start the development server."""
    dev_server = DevelopmentServer()
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
            uvloop.install()
            logger.info("Using uvloop for enhanced async performance")
        else:
            logger.info("uvloop not available, using default asyncio")

        asyncio.run(start_dev_server())

    except KeyboardInterrupt:
        logger.info("Development server interrupted by user")
        sys.exit(0)
    except Exception:
        logger.exception("Development server failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
