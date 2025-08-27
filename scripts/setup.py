#!/usr/bin/env python3
"""
Shared Context Server - Key Generation Script
Generates secure API keys and JWT tokens for development and deployment

Note: This script is maintained for backward compatibility and demo mode.
For general use, prefer the integrated CLI: `scs setup`
"""

import argparse
import sys
from pathlib import Path

# Import shared functionality
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
try:
    from shared_context_server.setup_core import (
        Colors,
        create_env_file,
        export_keys,
        generate_keys,
        print_color,
        show_docker_commands,
        show_security_notes,
        show_uvx_commands,
    )
except ImportError as e:
    print(f"❌ Could not import setup core module: {e}")
    print("Make sure you're running from the repository root directory")
    sys.exit(1)


def display_keys(keys: dict[str, str]) -> None:
    """Display generated keys"""
    print_color(Colors.BLUE, "📋 Generated Keys:")
    print()
    for key, value in keys.items():
        print_color(Colors.YELLOW, f"{key}={value}")
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


def show_local_commands(_keys: dict[str, str]) -> None:
    """Display local development commands"""
    print_color(Colors.BLUE, "💻 Local Development:")
    print()
    print_color(Colors.YELLOW, "Start development server:")
    print_color(Colors.GREEN, "   make dev")
    print()


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
