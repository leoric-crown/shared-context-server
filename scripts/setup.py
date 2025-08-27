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


def has_sensitive_keys(file_path: Path) -> bool:
    """Check if file contains sensitive keys or tokens"""
    if not file_path.exists():
        return False

    try:
        content = file_path.read_text()
        sensitive_patterns = [
            "API_KEY=",
            "JWT_SECRET_KEY=",
            "JWT_ENCRYPTION_KEY=",
            "SECRET=",
            "TOKEN=",
            "_KEY=",
            "_SECRET=",
            "_TOKEN=",
        ]
        return any(
            pattern in content
            and not content.split(pattern, 1)[1]
            .strip()
            .startswith(("your-", "replace-", "change-"))
            for pattern in sensitive_patterns
        )
    except Exception:
        return False


def create_env_file(
    keys: dict[str, str], force: bool = False, demo: bool = False
) -> Optional[str]:
    """Create .env file with generated keys"""
    if demo:
        demo_dir = Path("examples/demos/multi-expert-optimization")
        if not demo_dir.exists():
            print_color(Colors.RED, f"❌ Demo directory not found: {demo_dir}")
            print_color(
                Colors.YELLOW, "   Make sure you're running from the repository root."
            )
            return None
        env_file = demo_dir / ".env"
    else:
        env_file = Path(".env")

    target_file = env_file

    if env_file.exists():
        if (force or demo) and has_sensitive_keys(env_file):
            print_color(
                Colors.RED, "🚨 WARNING: .env contains existing API keys/tokens!"
            )
            print_color(Colors.YELLOW, "   Previous keys will be permanently replaced.")
            print()

            # Ask for confirmation in all cases
            try:
                response = (
                    input("Continue and replace existing keys? [y/N]: ").strip().lower()
                )
                if response not in ["y", "yes"]:
                    print_color(
                        Colors.YELLOW,
                        "Operation cancelled. Your existing keys are safe.",
                    )
                    return None
                print()
            except (KeyboardInterrupt, EOFError):
                print()
                print_color(
                    Colors.YELLOW, "Operation cancelled. Your existing keys are safe."
                )
                return None
        elif not force and not demo:
            if has_sensitive_keys(env_file):
                print_color(
                    Colors.RED,
                    "🚨 WARNING: .env contains API keys/tokens that would be overwritten!",
                )
                print_color(
                    Colors.YELLOW,
                    "   Use --force to overwrite, or backup your existing .env file first.",
                )
                print_color(
                    Colors.YELLOW,
                    f"   Creating {Path('.env.generated').name} instead for safety.",
                )
                print()

            target_file = env_file.parent / ".env.generated"
            print_color(
                Colors.YELLOW,
                f"⚠️  .env file already exists. Creating {target_file} instead.",
            )

    # Configure ports based on demo mode
    if demo:
        http_port = "23432"
        websocket_port = "34543"
        database_path = "./demo_chat_history.db"
    else:
        http_port = "23456"
        websocket_port = "34567"
        database_path = "./chat_history.db"

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
DATABASE_PATH={database_path}

# Server configuration
HTTP_PORT={http_port}
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
WEBSOCKET_PORT={websocket_port}
"""

    target_file.write_text(env_content)
    print_color(Colors.GREEN, f"✅ Configuration saved to {target_file}")

    # Create MCP JSON configuration for demo mode
    if demo:
        create_mcp_json_file(keys, http_port)

    print()

    # Return info about whether we used a fallback filename
    generated_fallback = target_file.name.endswith(".generated")
    return str(target_file), generated_fallback


def create_mcp_json_file(keys: dict[str, str], http_port: str) -> None:
    """Create MCP JSON configuration file for Claude Code"""
    demo_dir = Path("examples/demos/multi-expert-optimization")
    if not demo_dir.exists():
        print_color(Colors.RED, f"❌ Demo directory not found: {demo_dir}")
        return

    mcp_json_file = demo_dir / ".mcp.json"

    mcp_config = {
        "mcpServers": {
            "scs-demo": {
                "type": "http",
                "url": f"http://localhost:{http_port}/mcp/",
                "headers": {"X-API-Key": keys["API_KEY"]},
            },
            "octocode": {"command": "npx", "args": ["-y", "octocode-mcp"]},
        }
    }

    import json

    mcp_json_file.write_text(json.dumps(mcp_config, indent=2))
    print_color(Colors.GREEN, f"✅ MCP configuration saved to {mcp_json_file}")


def show_docker_commands(_keys: dict[str, str], demo: bool = False) -> None:
    """Display Docker deployment commands"""
    print_color(Colors.BLUE, "🐳 Docker Commands:")
    print()
    print_color(Colors.YELLOW, "Production (recommended):")
    print_color(Colors.GREEN, "   docker compose up -d")
    if not demo:
        print_color(Colors.GREEN, "   # OR: make docker")
    print()
    print_color(Colors.YELLOW, "Development with hot reload:")
    print_color(Colors.GREEN, "   docker compose -f docker-compose.dev.yml up -d")
    if not demo:
        print_color(Colors.GREEN, "   # OR: make dev")
    print()
    if not demo:
        print_color(Colors.YELLOW, "More options:")
        print_color(Colors.GREEN, "   make help")
        print()


def show_mcp_commands(keys: dict[str, str], demo: bool = False) -> None:
    """Display MCP client connection commands"""
    port = "23432" if demo else "23456"
    print_color(Colors.BLUE, "🔗 MCP Client Connection:")
    print()
    print_color(Colors.YELLOW, "Claude Code:")
    print_color(
        Colors.GREEN,
        f"   claude mcp add --transport http scs http://localhost:{port}/mcp/ \\",
    )
    print_color(Colors.GREEN, f'   --header "X-API-Key: {keys["API_KEY"]}"')
    print()
    print_color(Colors.YELLOW, "Gemini CLI:")
    print_color(
        Colors.GREEN, f"   gemini mcp add scs http://localhost:{port}/mcp -t http \\"
    )
    print_color(Colors.GREEN, f'   -H "X-API-Key: {keys["API_KEY"]}"')
    print()


def show_uvx_commands(keys: dict[str, str], demo: bool = False) -> None:
    """Display uvx testing commands"""
    port = "23432" if demo else "23456"
    print_color(Colors.BLUE, "📦 uvx Commands:")
    print()
    print_color(Colors.YELLOW, "Start server:")
    print()

    if demo:
        # Demo mode: needs env vars since running from subdirectory
        print_color(Colors.GREEN, f'   API_KEY="{keys["API_KEY"]}" \\')
        print_color(Colors.GREEN, f'   JWT_SECRET_KEY="{keys["JWT_SECRET_KEY"]}" \\')
        print_color(
            Colors.GREEN, f'   JWT_ENCRYPTION_KEY="{keys["JWT_ENCRYPTION_KEY"]}" \\'
        )
        print_color(
            Colors.GREEN, f"   uvx shared-context-server --transport http --port {port}"
        )
    else:
        # Regular mode: reads from .env automatically
        print_color(
            Colors.GREEN, f"   uvx shared-context-server --transport http --port {port}"
        )
        print_color(Colors.GREEN, "   # OR: make run")

    print()


def show_local_commands(_keys: dict[str, str]) -> None:
    """Display local development commands"""
    print_color(Colors.BLUE, "💻 Local Development:")
    print()
    print_color(Colors.YELLOW, "Start development server:")
    print_color(Colors.GREEN, "   make dev")
    print()


def show_security_notes() -> None:
    """Display security best practices"""
    print_color(Colors.BLUE, "🔒 Security Reminders:")
    print_color(
        Colors.YELLOW,
        "• Keep keys secure • Don't commit .env files • Use different keys per environment",
    )
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
        description="Setup and configure Shared Context MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup.py                    # Generate keys and show Docker setup
  python scripts/setup.py --docker-only      # Show only Docker commands
  python scripts/setup.py --demo --uvx       # Demo setup with uvx commands
  python scripts/setup.py --uvx              # Show only uvx commands
  python scripts/setup.py --export json      # Export as JSON
  python scripts/setup.py --no-file          # Don't create .env file
        """,
    )

    parser.add_argument(
        "--docker-only", action="store_true", help="Show only Docker commands"
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
        "--demo",
        action="store_true",
        help="Configure demo setup in examples/demos/multi-expert-optimization/ directory",
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

    if not args.quiet and not args.demo:
        display_keys(keys)

    # Create .env file unless disabled
    env_file_created = None
    used_fallback = False
    if not args.no_file:
        result = create_env_file(keys, args.force, args.demo)
        if result:
            env_file_created, used_fallback = result

    # Handle demo mode with focused output
    if args.demo:
        # Demo mode: show only relevant commands and concise next steps
        print_color(Colors.BLUE, "🎪 Multi-Expert Collaboration Demo Setup:")
        print()
        print_color(Colors.YELLOW, "Next steps:")
        print_color(Colors.YELLOW, "1. Navigate to demo directory:")
        print_color(Colors.GREEN, "   cd examples/demos/multi-expert-optimization/")

        if args.uvx:
            print_color(Colors.YELLOW, "2. Run the uvx command:")
            print()
            print_color(Colors.GREEN, f'   API_KEY="{keys["API_KEY"]}" \\')
            print_color(
                Colors.GREEN, f'   JWT_SECRET_KEY="{keys["JWT_SECRET_KEY"]}" \\'
            )
            print_color(
                Colors.GREEN, f'   JWT_ENCRYPTION_KEY="{keys["JWT_ENCRYPTION_KEY"]}" \\'
            )
            print_color(
                Colors.GREEN,
                "   uvx shared-context-server --transport http --port 23432",
            )
            print()
        else:
            print_color(Colors.YELLOW, "2. Start the server:")
            print_color(Colors.GREEN, "   uvx: Copy keys from .env and run uvx command")
            print_color(Colors.GREEN, "   Docker: docker compose up -d")

        print_color(Colors.YELLOW, "3. Start Claude Code:")
        print_color(Colors.GREEN, "   claude --mcp-config .mcp.json")
        print_color(Colors.YELLOW, "4. Follow demo instructions in README.md")
        print()
        print_color(Colors.GREEN, "✅ Demo setup ready!")
        return

    # Show commands based on arguments (non-demo mode)
    # Only show what was specifically requested
    if args.docker_only:
        show_docker_commands(keys, args.demo)
    elif args.uvx:
        show_uvx_commands(keys, args.demo)
    elif args.local:
        show_local_commands(keys)
    else:
        # Default: show both main deployment methods
        show_docker_commands(keys, args.demo)
        show_uvx_commands(keys, args.demo)

    if not args.quiet and not args.export:
        show_security_notes()

        # Show manual intervention notice if needed
        if used_fallback:
            print_color(
                Colors.YELLOW,
                f"⚠️  Manual step: Copy {env_file_created} to .env when ready",
            )
            print()

        print_color(
            Colors.GREEN,
            Colors.BOLD,
            "🎉 Setup complete! Your shared-context-server is ready to use.",
        )


if __name__ == "__main__":
    main()
