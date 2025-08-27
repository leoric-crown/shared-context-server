#!/usr/bin/env python3
"""
Shared Context Server - Key Generation Script
Generates secure API keys and JWT tokens for development and deployment
"""

import argparse
import base64
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("❌ Missing cryptography package. Install with: pip install cryptography")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color


def print_color(color: str, *args, **kwargs) -> None:
    """Print with color formatting"""
    message = " ".join(str(arg) for arg in args)
    print(f"{color}{message}{Colors.NC}", **kwargs)


def generate_keys() -> dict[str, str]:
    """Generate secure keys for the application"""
    print_color(Colors.YELLOW, "🔑 Generating secure keys...")
    print()

    # Generate API key (32 bytes, base64 encoded)
    api_key = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
    print_color(Colors.GREEN, "✅ API_KEY generated (32 bytes, base64 encoded)")

    # Generate JWT secret key (32 bytes, base64 encoded)
    jwt_secret = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
    print_color(Colors.GREEN, "✅ JWT_SECRET_KEY generated (32 bytes, base64 encoded)")

    # Generate JWT encryption key (Fernet key)
    jwt_encryption = Fernet.generate_key().decode("utf-8")
    print_color(Colors.GREEN, "✅ JWT_ENCRYPTION_KEY generated (Fernet key)")
    print()

    return {
        "API_KEY": api_key,
        "JWT_SECRET_KEY": jwt_secret,
        "JWT_ENCRYPTION_KEY": jwt_encryption,
    }


def display_keys(keys: dict[str, str]) -> None:
    """Display generated keys"""
    print_color(Colors.BLUE, "📋 Generated Keys:")
    print()
    for key, value in keys.items():
        print_color(Colors.YELLOW, f"{key}={value}")
    print()


def create_env_file(keys: dict[str, str], force: bool = False) -> Optional[str]:
    """Create .env file with generated keys"""
    env_file = Path(".env")
    target_file = env_file

    if env_file.exists() and not force:
        target_file = Path(".env.generated")
        print_color(
            Colors.YELLOW,
            f"⚠️  .env file already exists. Creating {target_file.name} instead.",
        )

    env_content = f"""# Shared Context MCP Server - Generated Configuration
# Generated on {datetime.now().isoformat()}

# ============================================================================
# 🔒 SECURITY KEYS - Generated automatically
# ============================================================================

API_KEY={keys["API_KEY"]}
JWT_SECRET_KEY={keys["JWT_SECRET_KEY"]}
JWT_ENCRYPTION_KEY={keys["JWT_ENCRYPTION_KEY"]}

# ============================================================================
# ⚙️ BASIC CONFIG - Usually defaults work fine
# ============================================================================

# Database location
DATABASE_PATH=./chat_history.db

# Server configuration
HTTP_PORT=23456
LOG_LEVEL=INFO
ENVIRONMENT=development
DEBUG=false

# MCP client connection (hostname clients use to reach server)
MCP_CLIENT_HOST=localhost
# Server transport configuration
MCP_TRANSPORT=http

# CORS origins (use * for development, restrict for production)
CORS_ORIGINS=*

# WebSocket port (for real-time updates)
WEBSOCKET_PORT=34567
"""

    target_file.write_text(env_content)
    print_color(Colors.GREEN, f"✅ Configuration saved to {target_file.name}")
    print()
    return str(target_file)


def show_docker_commands(keys: dict[str, str]) -> None:
    """Display Docker deployment commands"""
    print_color(Colors.BLUE, "🐳 Docker Compose Commands (Recommended):")
    print()
    print_color(Colors.YELLOW, "# 🚀 Production (pre-built image from GHCR):")
    print("make docker")
    print("# OR: docker compose up -d")
    print()
    print_color(Colors.YELLOW, "# 🔧 Development (with hot reload):")
    print("make dev-docker")
    print("# OR: docker compose -f docker-compose.dev.yml up -d")
    print()
    print_color(Colors.YELLOW, "# 🏗️ Production (build locally):")
    print("make docker-local")
    print(
        "# OR: docker compose -f docker-compose.yml -f docker-compose.local.yml up -d"
    )
    print()
    print_color(Colors.BLUE, "🐳 Raw Docker Commands:")
    print()
    print_color(Colors.YELLOW, "# Quick start with environment variables:")
    print("docker run -d --name shared-context-server \\")
    print("  -p 23456:23456 \\")
    print(f'  -e API_KEY="{keys["API_KEY"]}" \\')
    print(f'  -e JWT_SECRET_KEY="{keys["JWT_SECRET_KEY"]}" \\')
    print(f'  -e JWT_ENCRYPTION_KEY="{keys["JWT_ENCRYPTION_KEY"]}" \\')
    print("  ghcr.io/leoric-crown/shared-context-server:latest")
    print()
    print_color(Colors.YELLOW, "# Or with .env file:")
    print("docker run -d --name shared-context-server \\")
    print("  -p 23456:23456 --env-file .env \\")
    print("  ghcr.io/leoric-crown/shared-context-server:latest")
    print()


def show_mcp_commands(keys: dict[str, str]) -> None:
    """Display MCP client connection commands"""
    print_color(Colors.BLUE, "🔗 MCP Client Connection:")
    print()
    print_color(Colors.YELLOW, "# Claude Code:")
    print("claude mcp add --transport http scs http://localhost:23456/mcp/ \\")
    print(f'  --header "X-API-Key: {keys["API_KEY"]}"')
    print()
    print_color(Colors.YELLOW, "# Gemini CLI:")
    print("gemini mcp add scs http://localhost:23456/mcp -t http \\")
    print(f'  -H "X-API-Key: {keys["API_KEY"]}"')
    print()


def show_uvx_commands(keys: dict[str, str]) -> None:
    """Display uvx testing commands"""
    print_color(Colors.BLUE, "📦 uvx Commands (Testing Only):")
    print()
    print_color(Colors.YELLOW, "# Start server with generated API key:")
    print(f'API_KEY="{keys["API_KEY"]}" \\')
    print(f'JWT_SECRET_KEY="{keys["JWT_SECRET_KEY"]}" \\')
    print(f'JWT_ENCRYPTION_KEY="{keys["JWT_ENCRYPTION_KEY"]}" \\')
    print("uvx shared-context-server --transport http")
    print()


def show_local_commands(_keys: dict[str, str]) -> None:
    """Display local development commands"""
    print_color(Colors.BLUE, "💻 Local Development:")
    print()
    print_color(Colors.YELLOW, "# Using make (recommended):")
    print("make dev")
    print()
    print_color(Colors.YELLOW, "# Or directly with uv:")
    print("uv run python -m shared_context_server.scripts.dev")
    print()


def show_security_notes() -> None:
    """Display security best practices"""
    print_color(Colors.BLUE, "🔒 Security Notes:")
    print()
    print_color(Colors.YELLOW, "• Keep these keys secure and private")
    print_color(Colors.YELLOW, "• Don't commit .env files to version control")
    print_color(Colors.YELLOW, "• Regenerate keys for production deployments")
    print_color(Colors.YELLOW, "• Use different keys for different environments")
    print()


def export_keys(keys: dict[str, str], format_type: str) -> None:
    """Export keys in various formats"""
    if format_type == "json":
        import json

        print(json.dumps(keys, indent=2))
    elif format_type == "yaml":
        try:
            import yaml

            print(yaml.dump(keys, default_flow_style=False))
        except ImportError:
            print("❌ PyYAML not installed. Install with: pip install pyyaml")
    elif format_type == "export":
        for key, value in keys.items():
            print(f"export {key}='{value}'")
    elif format_type == "docker-env":
        for key, value in keys.items():
            print(f"-e {key}='{value}' \\")


def main() -> None:
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Generate secure keys for Shared Context MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_keys.py                    # Full interactive setup
  python scripts/generate_keys.py --docker-only      # Show only Docker commands
  python scripts/generate_keys.py --mcp-only        # Show only MCP client commands
  python scripts/generate_keys.py --export json     # Export as JSON
  python scripts/generate_keys.py --no-file         # Don't create .env file
        """,
    )

    parser.add_argument(
        "--docker-only", action="store_true", help="Show only Docker commands"
    )
    parser.add_argument(
        "--mcp-only", action="store_true", help="Show only MCP client commands"
    )
    parser.add_argument("--uvx", action="store_true", help="Include uvx commands")
    parser.add_argument(
        "--local", action="store_true", help="Include local development commands"
    )
    parser.add_argument("--no-file", action="store_true", help="Don't create .env file")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing .env file"
    )
    parser.add_argument(
        "--export",
        choices=["json", "yaml", "export", "docker-env"],
        help="Export keys in specified format",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress banner and decorative output",
    )

    args = parser.parse_args()

    if not args.quiet:
        print_color(
            Colors.BLUE, Colors.BOLD, "🔐 Shared Context Server - Key Generation"
        )
        print()

    # Generate keys
    keys = generate_keys()

    # Handle export format
    if args.export:
        export_keys(keys, args.export)
        return

    if not args.quiet:
        display_keys(keys)

    # Create .env file unless disabled
    if not args.no_file:
        create_env_file(keys, args.force)

    # Show commands based on arguments
    show_docker = not (args.mcp_only or args.export)
    show_mcp = not (args.docker_only or args.export)

    if args.docker_only or show_docker:
        show_docker_commands(keys)

    if args.mcp_only or show_mcp:
        show_mcp_commands(keys)

    if args.uvx:
        show_uvx_commands(keys)

    if args.local:
        show_local_commands(keys)

    if not args.quiet and not args.export:
        show_security_notes()
        print_color(
            Colors.GREEN,
            Colors.BOLD,
            "🎉 Setup complete! Your shared-context-server is ready to use.",
        )


if __name__ == "__main__":
    main()
