#!/usr/bin/env python3
"""
Core setup functionality for the shared context server.

This module provides the core key generation and setup logic
used by both the CLI interface and the standalone setup script.
"""

import base64
import re
import secrets
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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


def print_color(color: str, *args: Any, **kwargs: Any) -> None:
    """Print with color formatting"""
    message = " ".join(str(arg) for arg in args)
    print(f"{color}{message}{Colors.NC}", **kwargs)


def _raise_docker_error(return_code: int) -> None:
    """Helper function to raise Docker-related errors."""
    msg = f"Docker command failed with code {return_code}"
    raise subprocess.CalledProcessError(return_code, "docker --version", msg)


def _check_docker_conflicts(
    docker_compose_content: str,
) -> tuple[str, bool, dict[int, int]]:
    """
    Check for Docker container/volume conflicts and resolve them if found.

    Returns (potentially_modified_content, conflicts_found, port_mappings)
    Only modifies names if actual conflicts are detected.
    port_mappings: dict mapping original_port -> resolved_port
    """
    try:
        # Check if Docker is available
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, check=True, timeout=5
        )
        if result.returncode != 0:
            _raise_docker_error(result.returncode)
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        print_color(
            Colors.YELLOW, "   ⚠️  Docker not available - skipping conflict check"
        )
        print_color(
            Colors.YELLOW,
            "   💡 Install Docker to enable automatic conflict resolution",
        )
        return docker_compose_content, False, {}

    # Extract container, volume names, and ports from compose content
    container_names = _extract_container_names(docker_compose_content)
    volume_names = _extract_volume_names(docker_compose_content)
    port_mappings = _extract_port_mappings(docker_compose_content)

    # Check for conflicts
    container_conflicts = _check_container_conflicts(container_names)
    volume_conflicts = _check_volume_conflicts(volume_names)
    port_conflicts = _check_port_conflicts(port_mappings)

    if not container_conflicts and not volume_conflicts and not port_conflicts:
        print_color(Colors.GREEN, "   ✅ No Docker conflicts detected")
        return docker_compose_content, False, {}

    print_color(
        Colors.YELLOW, "   ⚠️  Docker conflicts detected, generating unique names..."
    )
    if container_conflicts:
        print_color(
            Colors.YELLOW,
            f"     • Conflicting containers: {', '.join(container_conflicts)}",
        )
    if volume_conflicts:
        print_color(
            Colors.YELLOW, f"     • Conflicting volumes: {', '.join(volume_conflicts)}"
        )
    if port_conflicts:
        conflict_ports = [str(port) for port in port_conflicts]
        print_color(
            Colors.YELLOW, f"     • Conflicting ports: {', '.join(conflict_ports)}"
        )

    # Generate unique suffix and resolve conflicts
    unique_suffix = str(int(time.time()))[-6:]
    content, resolved_ports = _resolve_conflicts(
        docker_compose_content,
        container_conflicts,
        volume_conflicts,
        port_conflicts,
        unique_suffix,
    )

    return content, True, resolved_ports


def _extract_container_names(compose_content: str) -> list[str]:
    """Extract container names from docker-compose content"""
    container_pattern = r'container_name:\s+["\']?([^"\'\n]+)["\']?'
    return re.findall(container_pattern, compose_content)


def _extract_volume_names(compose_content: str) -> list[str]:
    """Extract volume names from docker-compose content"""
    # Look for named volumes in the volumes section
    volume_pattern = r"^volumes:\s*$(.*?)^(?:\w|\Z)"
    volume_section_match = re.search(
        volume_pattern, compose_content, re.MULTILINE | re.DOTALL
    )

    if not volume_section_match:
        # Try simpler pattern for volumes section
        lines = compose_content.split("\n")
        in_volumes = False
        volume_names = []

        for line in lines:
            if re.match(r"^volumes:\s*$", line):
                in_volumes = True
                continue
            if in_volumes:
                # Check if we've hit another top-level section
                if re.match(
                    r"^[a-zA-Z_][a-zA-Z0-9_]*:\s*$", line
                ) and not line.startswith(" "):
                    break
                # Extract volume name (2-space indent, not 4-space)
                match = re.match(r"^  ([a-zA-Z_][a-zA-Z0-9_-]+):\s*$", line)
                if match:
                    volume_names.append(match.group(1))

        return volume_names

    volume_names = []
    volume_content = volume_section_match.group(1)
    name_pattern = r"^  ([a-zA-Z_][a-zA-Z0-9_-]+):\s*$"  # Only 2-space indent

    for line in volume_content.split("\n"):
        match = re.match(name_pattern, line)
        if match:
            volume_names.append(match.group(1))

    return volume_names


def _extract_port_mappings(compose_content: str) -> list[int]:
    """Extract host port mappings from docker-compose content"""
    # Look for port mappings in various formats
    port_patterns = [
        r'^\s*-\s*["\']?\$\{[^}]+:-(\d+)\}:\$\{[^}]+:-\d+\}["\']?\s*$',  # ${VAR:-PORT}:${VAR:-PORT} format
        r'^\s*-\s*["\']?\$\{[^}]+:-(\d+)\}(?::\d+)?["\']?\s*$',  # ${VAR:-PORT}:PORT format
        r'^\s*-\s*["\']?(\d+)(?::\d+)?["\']?\s*$',  # Direct port format
    ]
    ports = []

    lines = compose_content.split("\n")
    in_ports_section = False

    for line in lines:
        # Check if we're in a ports section
        if re.match(r"^\s+ports:\s*$", line):
            in_ports_section = True
            continue
        if in_ports_section:
            # Check if we've left the ports section (new key at same or lower indent)
            if re.match(
                r"^\s+[a-zA-Z_][a-zA-Z0-9_]*:\s*", line
            ) and not line.strip().startswith("- "):
                in_ports_section = False
            else:
                # Try each pattern
                for pattern in port_patterns:
                    match = re.match(pattern, line)
                    if match:
                        port = int(match.group(1))
                        if port not in ports:  # Avoid duplicates
                            ports.append(port)
                        break

    return ports


def _check_port_conflicts(port_list: list[int]) -> list[int]:
    """Check which ports are already in use (cross-platform)"""
    if not port_list:
        return []

    conflicting_ports = []

    for port in port_list:
        # Check both TCP and UDP (most services use TCP)
        for protocol in [socket.SOCK_STREAM, socket.SOCK_DGRAM]:
            try:
                # Try to bind to the port
                sock = socket.socket(socket.AF_INET, protocol)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", port))
                sock.close()
            except OSError:  # noqa: PERF203
                # Port is in use or permission denied
                if port not in conflicting_ports:
                    conflicting_ports.append(port)
                break  # Don't check UDP if TCP failed

    return conflicting_ports


def _find_available_port(start_port: int, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
            sock.close()
            return port
        except OSError:  # noqa: PERF203
            continue

    # Fallback if no port found
    return start_port


def _check_container_conflicts(container_names: list[str]) -> list[str]:
    """Check which container names are already in use"""
    if not container_names:
        return []

    try:
        # Get list of existing containers (both running and stopped)
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        existing_containers = (
            set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        )

        return [name for name in container_names if name in existing_containers]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # If we can't check, assume no conflicts (safer than failing)
        return []


def _check_volume_conflicts(volume_names: list[str]) -> list[str]:
    """Check which volume names are already in use"""
    if not volume_names:
        return []

    try:
        # Get list of existing volumes
        result = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        existing_volumes = (
            set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        )

        return [name for name in volume_names if name in existing_volumes]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # If we can't check, assume no conflicts (safer than failing)
        return []


def _resolve_conflicts(
    compose_content: str,
    container_conflicts: list[str],
    volume_conflicts: list[str],
    port_conflicts: list[int],
    unique_suffix: str,
) -> tuple[str, dict[int, int]]:
    """Resolve conflicts by adding unique suffixes to conflicting names"""
    content = compose_content

    # Resolve container name conflicts
    for container_name in container_conflicts:
        container_pattern = (
            rf'(\s+container_name:\s+)(["\']?)({re.escape(container_name)})(["\']?)'
        )

        def replace_container(match: re.Match[str]) -> str:
            prefix = match.group(1)
            quote_start = match.group(2)
            name = match.group(3)
            quote_end = match.group(4)
            new_name = f"{name}_scs_{unique_suffix}"
            return f"{prefix}{quote_start}{new_name}{quote_end}"

        content = re.sub(container_pattern, replace_container, content)

    # Resolve volume conflicts
    for volume_name in volume_conflicts:
        # Replace in volumes section
        volume_def_pattern = rf"^(\s+)({re.escape(volume_name)})(:)"
        content = re.sub(
            volume_def_pattern,
            rf"\1{volume_name}_scs_{unique_suffix}\3",
            content,
            flags=re.MULTILINE,
        )

        # Replace volume references in services
        volume_ref_pattern = rf"(\s+- )({re.escape(volume_name)})(:.*)"
        content = re.sub(
            volume_ref_pattern, rf"\1{volume_name}_scs_{unique_suffix}\3", content
        )

    # Resolve port conflicts by shifting to alternative ports
    port_mappings = {}
    for port in port_conflicts:
        # Find available port starting from conflicting port + 1000
        new_port = _find_available_port(port + 1000)
        port_mappings[port] = new_port
        print_color(Colors.GREEN, f"     → Port {port} → {new_port}")

        # Replace port mappings in various formats
        port_patterns = [
            # ${VAR:-PORT}:${VAR:-PORT} format - replace both occurrences
            (
                rf'(\s*-\s*["\']?\$\{{[^}}]+:-){port}(\}}:\$\{{[^}}]+:-){port}(\}}["\']?\s*)',
                rf"\g<1>{new_port}\g<2>{new_port}\g<3>",
            ),
            # ${VAR:-PORT}:PORT format
            (
                rf'(\s*-\s*["\']?\$\{{[^}}]+:-){port}(\}}:\d+["\']?\s*)',
                rf"\g<1>{new_port}\g<2>",
            ),
            # ${VAR:-PORT} format
            (
                rf'(\s*-\s*["\']?\$\{{[^}}]+:-){port}(\}}["\']?\s*)',
                rf"\g<1>{new_port}\g<2>",
            ),
            # Direct "PORT:PORT" format
            (rf'(\s*-\s*["\']?){port}(:\d+["\']?\s*)', rf"\g<1>{new_port}\g<2>"),
            # Direct "PORT" format
            (rf'(\s*-\s*["\']?){port}(["\']?\s*)$', rf"\g<1>{new_port}\g<2>"),
        ]

        for pattern, replacement in port_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    return content, port_mappings


def _generate_unique_volumes(docker_compose_content: str) -> str:
    """
    Legacy function name - now performs intelligent conflict checking.

    Checks for actual Docker conflicts and only modifies names when necessary.
    """
    content, _conflicts_found, _port_mappings = _check_docker_conflicts(
        docker_compose_content
    )
    return content


def print_diff(old_content: str, new_content: str) -> None:
    """Print a simple diff between two file contents"""
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    # Simple line-by-line comparison
    max_lines = max(len(old_lines), len(new_lines))
    changes_found = False

    for i in range(max_lines):
        old_line = old_lines[i] if i < len(old_lines) else None
        new_line = new_lines[i] if i < len(new_lines) else None

        if old_line != new_line:
            changes_found = True
            if old_line is not None:
                print_color(Colors.RED, f"  - {old_line}")
            if new_line is not None:
                print_color(Colors.GREEN, f"  + {new_line}")

    if not changes_found:
        print_color(Colors.GREEN, "  (No changes detected)")
    print()


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


def export_keys(keys: dict[str, str], format_type: str) -> None:
    """Export keys in various formats"""
    if format_type == "json":
        import json

        print(json.dumps(keys, indent=2))
    elif format_type == "yaml":
        try:
            import yaml  # type: ignore[import-untyped]

            print(yaml.dump(keys, default_flow_style=False))
        except ImportError:
            print("❌ PyYAML not installed. Install with: pip install pyyaml")
    elif format_type == "export":
        for key, value in keys.items():
            print(f"export {key}='{value}'")
    elif format_type == "docker-env":
        for key, value in keys.items():
            print(f"-e {key}='{value}' \\")


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
            .startswith(("your-", "replace-", "change-", "REPLACE_WITH"))
            for pattern in sensitive_patterns
        )
    except Exception:
        return False


def create_env_file(
    keys: dict[str, str],
    force: bool = False,
    demo: bool = False,
    include_octocode: bool = True,
) -> Optional[tuple[str, bool]]:
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

    if env_file.exists() and has_sensitive_keys(env_file):
        if demo:
            # Demo mode: Allow overwrite with confirmation (demo keys aren't critical)
            if not force:
                print_color(
                    Colors.RED, "🚨 WARNING: .env contains existing API keys/tokens!"
                )
                print_color(
                    Colors.YELLOW, "   Previous keys will be permanently replaced."
                )
                print()

                # Ask for confirmation unless force is specified
                try:
                    response = (
                        input("Continue and replace existing keys? [y/N]: ")
                        .strip()
                        .lower()
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
                        Colors.YELLOW,
                        "Operation cancelled. Your existing keys are safe.",
                    )
                    return None
            else:
                # Force mode: just show a notice but continue
                print_color(Colors.YELLOW, "🔄 Force mode: Replacing existing keys...")
                print()
        else:
            # Regular mode: Always use .env.generated for safety unless --force
            if not force:
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
            else:
                # Force mode for regular setup: allow overwrite
                print_color(Colors.YELLOW, "🔄 Force mode: Replacing existing keys...")
                print()
    elif env_file.exists() and not demo and not force:
        # File exists but no sensitive keys detected
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
        create_mcp_json_file(keys, http_port, include_octocode)

    print()

    # Return info about whether we used a fallback filename
    generated_fallback = target_file.name.endswith(".generated")
    return str(target_file), generated_fallback


def create_mcp_json_file(
    keys: dict[str, str], http_port: str, include_octocode: bool = True
) -> None:
    """Create MCP JSON configuration file for Claude Code"""
    demo_dir = Path("examples/demos/multi-expert-optimization")
    if not demo_dir.exists():
        print_color(Colors.RED, f"❌ Demo directory not found: {demo_dir}")
        return

    mcp_json_file = demo_dir / ".mcp.json"

    # Base configuration with shared-context-server
    mcp_config = {
        "mcpServers": {
            "scs-demo": {
                "type": "http",
                "url": f"http://localhost:{http_port}/mcp/",
                "headers": {"X-API-Key": keys["API_KEY"]},
            }
        }
    }

    # Conditionally add octocode if npm/npx is available
    if include_octocode:
        mcp_config["mcpServers"]["octocode"] = {
            "command": "npx",
            "args": ["-y", "octocode-mcp"],
        }

    import json

    mcp_json_file.write_text(json.dumps(mcp_config, indent=2))

    if include_octocode:
        print_color(Colors.GREEN, f"✅ MCP configuration saved to {mcp_json_file}")
    else:
        print_color(
            Colors.GREEN,
            f"✅ MCP configuration saved to {mcp_json_file} (limited - octocode excluded)",
        )
        print_color(
            Colors.YELLOW,
            "   💡 Install npm/npx to enable octocode MCP server features",
        )


def fetch_docker_compose_files() -> tuple[bool, dict[int, int]]:
    """Fetch essential docker-compose file from GitHub repository for repository-free setup"""
    github_base_url = (
        "https://raw.githubusercontent.com/leoric-crown/shared-context-server/main"
    )
    # Only fetch the essential production docker-compose.yml for repository-free setup
    docker_files = ["docker-compose.yml"]

    print_color(Colors.YELLOW, "📦 Fetching Docker configuration files from GitHub...")

    # Track port mappings from conflict resolution
    resolved_port_mappings = {}

    # Try to create SSL context that handles certificate issues
    ssl_context = None
    try:
        ssl_context = ssl.create_default_context()
    except Exception:
        # If SSL context creation fails, try unverified context
        try:
            ssl_context = ssl._create_unverified_context()
            print_color(
                Colors.YELLOW,
                "   ⚠️  Using unverified SSL context due to certificate issues",
            )
        except Exception:
            pass

    success_count = 0
    for file_name in docker_files:
        downloaded = False

        # Try multiple approaches for each file
        for attempt, (context, desc) in enumerate(
            [
                (ssl_context, "with SSL verification"),
                (
                    ssl._create_unverified_context()
                    if hasattr(ssl, "_create_unverified_context")
                    else None,
                    "without SSL verification",
                ),
            ]
        ):
            if downloaded or context is None:
                continue

            try:
                url = f"{github_base_url}/{file_name}"
                if attempt == 0:
                    print_color(Colors.YELLOW, f"   • Downloading {file_name}...")
                else:
                    print_color(Colors.YELLOW, f"   • Retrying {file_name} {desc}...")

                request = urllib.request.Request(
                    url, headers={"User-Agent": "shared-context-server-setup/1.0"}
                )

                with urllib.request.urlopen(request, context=context) as response:
                    content = response.read().decode("utf-8")

                # For repository-free setup, resolve conflicts
                if file_name == "docker-compose.yml":
                    # Resolve any conflicts and capture port mappings
                    content, _conflicts_found, port_mappings = _check_docker_conflicts(
                        content
                    )
                    resolved_port_mappings.update(port_mappings)
                    print_color(
                        Colors.YELLOW,
                        "   ⚙️  Checking for Docker conflicts and resolving if needed...",
                    )

                Path(file_name).write_text(content)
                print_color(Colors.GREEN, f"   ✅ {file_name} downloaded successfully")
                success_count += 1
                downloaded = True

            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print_color(
                        Colors.YELLOW, f"   ⚠️  {file_name} not found (optional file)"
                    )
                    break  # Don't retry 404s
                if attempt == 1:  # Last attempt
                    print_color(
                        Colors.RED,
                        f"   ❌ Failed to download {file_name}: HTTP {e.code}",
                    )
            except Exception as e:
                if attempt == 1:  # Last attempt
                    print_color(
                        Colors.RED, f"   ❌ Failed to download {file_name}: {e}"
                    )

    print()
    if success_count > 0:
        print_color(
            Colors.GREEN,
            f"✅ Downloaded {success_count}/{len(docker_files)} Docker configuration files",
        )
        return True, resolved_port_mappings
    print_color(Colors.RED, "❌ Failed to download Docker configuration files")
    print_color(Colors.YELLOW, "💡 Manual alternative:")
    print_color(
        Colors.GREEN,
        f"   curl -L {github_base_url}/docker-compose.yml -o docker-compose.yml",
    )
    print_color(
        Colors.GREEN,
        f"   curl -L {github_base_url}/docker-compose.dev.yml -o docker-compose.dev.yml",
    )
    return False, {}


def is_shared_context_repo() -> bool:
    """Check if we're in the shared-context-server repository"""

    # Primary: Check pyproject.toml contents for definitive identification
    pyproject_file = Path("pyproject.toml")
    if pyproject_file.exists():
        try:
            content = pyproject_file.read_text()
            if 'name = "shared-context-server"' in content:
                return True
        except Exception:
            pass  # If we can't read it, continue with other checks

    # Secondary: Check .git directory metadata
    git_dir = Path(".git")
    if git_dir.exists():
        # Check git config for remote URL
        try:
            git_config = git_dir / "config"
            if git_config.exists():
                config_content = git_config.read_text()
                if "shared-context-server" in config_content.lower():
                    return True
        except Exception:
            pass

        # Fallback: Try git command if available
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip().lower()
                if "shared-context-server" in remote_url:
                    return True
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.CalledProcessError,
        ):
            pass

    return False


def _update_env_with_resolved_ports(
    port_mappings: dict[int, int], env_file: Path | None = None
) -> None:
    """Update .env file with resolved port mappings from conflict resolution"""
    if not port_mappings:
        return

    # Default to .env if no specific file provided
    if env_file is None:
        env_file = Path(".env")

    if not env_file.exists():
        return

    try:
        content = env_file.read_text()
        updated = False

        # Update HTTP_PORT if it was remapped
        if 23456 in port_mappings:
            new_http_port = port_mappings[23456]
            content = re.sub(
                r"^HTTP_PORT=.*$",
                f"HTTP_PORT={new_http_port}",
                content,
                flags=re.MULTILINE,
            )
            updated = True

        # Update WEBSOCKET_PORT if it was remapped
        if 34567 in port_mappings:
            new_ws_port = port_mappings[34567]
            content = re.sub(
                r"^WEBSOCKET_PORT=.*$",
                f"WEBSOCKET_PORT={new_ws_port}",
                content,
                flags=re.MULTILINE,
            )
            updated = True

        if updated:
            env_file.write_text(content)
            print_color(
                Colors.GREEN, f"   ✅ Updated {env_file.name} with resolved ports"
            )
            for old_port, new_port in port_mappings.items():
                port_name = (
                    "HTTP_PORT"
                    if old_port == 23456
                    else "WEBSOCKET_PORT"
                    if old_port == 34567
                    else f"PORT_{old_port}"
                )
                print_color(
                    Colors.GREEN, f"     → {port_name}: {old_port} → {new_port}"
                )

    except Exception as e:
        print_color(Colors.YELLOW, f"   ⚠️  Could not update {env_file.name}: {e}")


def show_docker_commands(
    _keys: dict[str, str], demo: bool = False, fetch_files: bool = True
) -> None:
    """Display Docker deployment commands"""
    print_color(Colors.BLUE, "🐳 Docker Commands:")
    print()

    # Check if we're in the shared-context-server repository
    in_repo = is_shared_context_repo()
    fetched_files = False

    # Handle file fetching logic for repository-free setup
    compose_file = Path("docker-compose.yml")
    if not in_repo:
        # We're in repository-free mode
        if not compose_file.exists() and fetch_files and not demo:
            print_color(Colors.YELLOW, "Docker configuration not found locally.")
            success, port_mappings = fetch_docker_compose_files()
            if success:
                fetched_files = True
                # Update .env file with resolved ports if any conflicts were resolved
                _update_env_with_resolved_ports(port_mappings)
                print()
            else:
                print_color(
                    Colors.RED,
                    "Cannot proceed with Docker setup without configuration files.",
                )
                print_color(Colors.YELLOW, "Alternative: Use uvx deployment instead:")
                print_color(
                    Colors.GREEN,
                    "   uvx shared-context-server --transport http --port 23456",
                )
                print()
                return
        elif compose_file.exists() and fetch_files and not demo:
            # File exists from previous repository-free setup - offer to update
            print_color(
                Colors.YELLOW, "Existing docker-compose.yml found from previous setup."
            )
            print_color(
                Colors.YELLOW,
                "Would you like to update it with the latest version? [y/N]: ",
                end="",
            )
            try:
                response = input().strip().lower()
                if response in ["y", "yes"]:
                    # Save old content for diff
                    old_content = (
                        compose_file.read_text() if compose_file.exists() else ""
                    )

                    print_color(Colors.YELLOW, "Updating docker-compose.yml...")
                    success, port_mappings = fetch_docker_compose_files()
                    if success:
                        # Update .env file with resolved ports if any conflicts were resolved
                        _update_env_with_resolved_ports(port_mappings)
                        # Show diff if update was successful
                        new_content = (
                            compose_file.read_text() if compose_file.exists() else ""
                        )
                        if old_content != new_content:
                            print_color(
                                Colors.BLUE, "📋 Changes made to docker-compose.yml:"
                            )
                            print_diff(old_content, new_content)
                        else:
                            print_color(Colors.GREEN, "✅ File is already up to date")
                        fetched_files = True
                        print()
                    else:
                        print_color(
                            Colors.YELLOW, "Update failed, using existing file."
                        )
                        fetched_files = True
                        print()
                else:
                    print_color(Colors.GREEN, "Using existing docker-compose.yml")
                    fetched_files = True
                    print()
            except (KeyboardInterrupt, EOFError):
                print()
                print_color(Colors.GREEN, "Using existing docker-compose.yml")
                fetched_files = True
                print()
        elif compose_file.exists():
            # File exists but we're not fetching (demo mode or fetch disabled)
            fetched_files = True

    print_color(Colors.YELLOW, "Production (recommended):")
    print_color(Colors.GREEN, "   docker compose up -d")
    if not demo and in_repo:
        print_color(Colors.GREEN, "   # OR: make docker")
    print()

    # Show cleanup instructions
    if demo:
        print_color(Colors.YELLOW, "Stop and cleanup (removes containers and volumes):")
        print_color(Colors.GREEN, "   docker compose down -v")
        print()
    else:
        print_color(Colors.YELLOW, "Stop server:")
        print_color(Colors.GREEN, "   docker compose down")
        print()

    # Only show development options when in repository (has dev files)
    if not demo and in_repo:
        print_color(Colors.YELLOW, "Development with hot reload:")
        print_color(Colors.GREEN, "   docker compose -f docker-compose.dev.yml up -d")
        print_color(Colors.GREEN, "   # OR: make dev")
        print()
        print_color(Colors.YELLOW, "More options:")
        print_color(Colors.GREEN, "   make help")
        print()
    elif fetched_files and not in_repo:
        if compose_file.exists():
            print_color(
                Colors.YELLOW, "💡 Using docker-compose.yml for repository-free setup"
            )
            print_color(
                Colors.YELLOW, "   Use 'docker compose up -d' above to start the server"
            )
        print()


def show_uvx_commands(keys: dict[str, str], demo: bool = False) -> None:
    """Display uvx testing commands"""
    # Check for port conflicts and resolve them
    default_http_port = 23432 if demo else 23456
    default_ws_port = 34532 if demo else 34567

    # Check which ports are actually in conflict
    conflicting_ports = _check_port_conflicts([default_http_port, default_ws_port])

    resolved_http_port = default_http_port
    resolved_ws_port = default_ws_port
    port_mappings = {}

    if conflicting_ports:
        print_color(
            Colors.YELLOW, "   ⚠️  Port conflicts detected, finding alternative ports..."
        )

        # Resolve HTTP port conflict
        if default_http_port in conflicting_ports:
            resolved_http_port = _find_available_port(default_http_port + 1000)
            port_mappings[default_http_port] = resolved_http_port
            print_color(
                Colors.GREEN,
                f"     → HTTP Port {default_http_port} → {resolved_http_port}",
            )

        # Resolve WebSocket port conflict
        if default_ws_port in conflicting_ports:
            resolved_ws_port = _find_available_port(default_ws_port + 1000)
            port_mappings[default_ws_port] = resolved_ws_port
            print_color(
                Colors.GREEN,
                f"     → WebSocket Port {default_ws_port} → {resolved_ws_port}",
            )

        # Update .env file with resolved ports (only for non-demo mode)
        if not demo and port_mappings:
            _update_env_with_resolved_ports(port_mappings)
            print()
    else:
        print_color(Colors.GREEN, "   ✅ No port conflicts detected")

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
            Colors.GREEN,
            f"   uvx shared-context-server --transport http --port {resolved_http_port}",
        )
    else:
        # Regular mode: reads configuration from .env automatically
        print_color(Colors.GREEN, "   uvx shared-context-server")
        print_color(Colors.GREEN, "   # OR: make run")

    print()


def check_demo_dependencies() -> tuple[bool, list[str]]:
    """Check if required dependencies for demo mode are available"""
    missing_deps = []

    # Check for npm
    try:
        subprocess.run(["npm", "--version"], capture_output=True, check=True, timeout=5)
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        missing_deps.append("npm")

    # Check for npx (usually comes with npm, but let's be thorough)
    try:
        subprocess.run(["npx", "--version"], capture_output=True, check=True, timeout=5)
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        missing_deps.append("npx")

    return len(missing_deps) == 0, missing_deps


def show_dependency_error(missing_deps: list[str]) -> None:
    """Display dependency installation instructions"""
    print_color(Colors.RED, "🚨 Missing Dependencies for Demo Mode:")
    print()

    if "npm" in missing_deps or "npx" in missing_deps:
        print_color(
            Colors.YELLOW, "The demo requires npm/npx for the octocode MCP server."
        )
        print_color(Colors.YELLOW, "Please install Node.js which includes npm:")
        print()
        print_color(Colors.GREEN, "📦 Installation options:")
        print_color(Colors.GREEN, "• Official installer: https://nodejs.org/")
        print_color(Colors.GREEN, "• Using Homebrew: brew install node")
        print_color(
            Colors.GREEN,
            "• Using nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash",
        )
        print()
        print_color(Colors.YELLOW, "After installation, verify with:")
        print_color(Colors.GREEN, "  npm --version")
        print_color(Colors.GREEN, "  npx --version")
        print()


def show_security_notes() -> None:
    """Display security best practices"""
    print_color(Colors.BLUE, "🔒 Security Reminders:")
    print_color(
        Colors.YELLOW,
        "• Keep keys secure • Don't commit .env files • Use different keys per environment",
    )
    print()
