#!/usr/bin/env python3
"""
Command Line Interface for Shared Context MCP Server.

THIN WRAPPER: This module serves as the legacy entry point, redirecting
core functionality to the modular cli/main.py implementation while preserving
backward compatibility and essential bootstrap logic.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

# Import centralized color infrastructure
from ..cli.utils import Colors

# Configure logging before importing other modules
# Skip logging configuration during pytest runs to avoid I/O capture conflicts
if "pytest" not in sys.modules and "PYTEST_CURRENT_TEST" not in os.environ:
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


def generate_client_config(
    client: str,
    host: str,
    port: int,
    scope: str = "local",
    copy_behavior: str = "no_copy",
) -> None:
    """
    Generate MCP client configuration with modern UX.

    Args:
        client: MCP client type (claude, cursor, windsurf, vscode, claude-desktop, gemini, codex, qwen, kiro)
        host: Server host address
        port: Server port number
        scope: Configuration scope for Claude Code (user, project, local, dynamic)
        copy_behavior: Clipboard behavior ("copy", "prompt", "no_copy")

    Generates properly formatted configuration for the specified MCP client,
    displays it with syntax highlighting, and optionally copies to clipboard.
    """
    # Validate scope usage - only Claude Code supports scope
    if scope != "local" and client not in ["claude"]:
        print(
            f"Warning: --scope/-s flag is only supported for Claude Code, ignoring for {client}"
        )
        scope = "local"

    server_url = f"http://{host}:{port}/mcp/"

    # Get API key from environment for display
    api_key = os.getenv("API_KEY", "").strip()
    api_key_display = api_key if api_key else "YOUR_API_KEY_HERE"

    # Generate configuration based on client type
    if client == "claude":
        config_text = _generate_claude_config(server_url, api_key_display, scope)
    elif client == "claude-desktop":
        config_text = _generate_claude_desktop_config(server_url, api_key_display)
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
    elif client == "kiro":
        config_text = _generate_kiro_config(server_url, api_key_display)
    else:
        raise ValueError(f"Unsupported client type: {client}")

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
    _handle_clipboard(config_text, copy_behavior, Colors)

    print()


def _generate_http_json_config(
    server_url: str, api_key: str, server_name: str = "shared-context-server"
) -> str:
    """Generate standard HTTP JSON configuration object for HTTP-based MCP clients."""
    return f'''"{server_name}": {{
  "url": "{server_url}",
  "headers": {{
    "X-API-Key": "{api_key}"
  }}
}}'''


def _generate_claude_config(server_url: str, api_key: str, scope: str) -> str:
    """Generate Claude Code configuration with proper scope."""
    scope_flag = f" -s {scope}" if scope != "local" else ""

    # For HTTP servers, Claude Code requires add-json with proper JSON structure
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


def _generate_claude_desktop_config(server_url: str, api_key: str) -> str:
    """Generate Claude Desktop configuration using mcp-proxy."""
    # Detect mcp-proxy location - common locations
    import shutil
    from pathlib import Path

    mcp_proxy_path = shutil.which("mcp-proxy")
    if not mcp_proxy_path:
        common_paths = [
            "/usr/local/bin/mcp-proxy",
            "~/.local/bin/mcp-proxy",
            "~/.cargo/bin/mcp-proxy",
        ]
        for path in common_paths:
            expanded_path = Path(path).expanduser()
            if expanded_path.exists():
                mcp_proxy_path = str(expanded_path)
                break

    if not mcp_proxy_path:
        mcp_proxy_path = "mcp-proxy"

    config_object = f'''"shared-context-server": {{
  "command": "{mcp_proxy_path}",
  "args": ["--transport=streamablehttp", "{server_url}", "--headers", "X-API-Key", "{api_key}"]
}}'''

    return f"""Add to Claude Desktop configuration:

{Colors.GREEN}{config_object}{Colors.NC}

{Colors.BLUE}Configuration file location:{Colors.NC}
{Colors.YELLOW}Claude Desktop → Settings → Developer → Edit Config{Colors.NC}

Full structure example:
{{
  "mcpServers": {{
    {config_object}
  }}
}}

{Colors.YELLOW}Note: Ensure mcp-proxy is installed:{Colors.NC}
npm install -g @modelcontextprotocol/proxy

{Colors.YELLOW}If mcp-proxy path differs, update the "command" field accordingly{Colors.NC}"""


def _generate_cursor_config(server_url: str, api_key: str) -> str:
    """Generate Cursor IDE configuration."""
    config_object = _generate_http_json_config(server_url, api_key)

    return f"""Configuration to add to Cursor IDE:

{Colors.GREEN}{config_object}{Colors.NC}

Add this configuration to your Cursor IDE MCP settings."""


def _generate_windsurf_config(server_url: str, api_key: str) -> str:
    """Generate Windsurf configuration."""
    # Windsurf uses "serverUrl" instead of "url"
    config_object = _generate_http_json_config(server_url, api_key).replace(
        '"url":', '"serverUrl":'
    )

    return f"""Add to Windsurf MCP configuration:

{Colors.GREEN}{{
  {config_object}
}}{Colors.NC}"""


def _generate_vscode_config(server_url: str, api_key: str) -> str:
    """Generate VS Code configuration."""
    return f"""Configuration for VS Code:

{Colors.GREEN}{{
  "shared-context-server": {{
    "url": "{server_url}",
    "headers": {{
      "X-API-Key": "{api_key}"
    }},
    "type": "http"
  }}
}}{Colors.NC}"""


def _generate_gemini_config(server_url: str, api_key: str) -> str:
    """Generate Gemini CLI configuration."""
    # Extract server name from URL for Gemini CLI command
    server_name = "shared-context-server"

    return f"""Command to add to Gemini CLI:

{Colors.GREEN}gemini mcp add {server_name} {server_url} -t http -H "X-API-Key: {api_key}"{Colors.NC}

{Colors.BLUE}Transport:{Colors.NC} HTTP (StreamableHTTPClientTransport)
{Colors.BLUE}Authentication:{Colors.NC} X-API-Key header

Gemini CLI supports direct HTTP transport for MCP servers.
After running the command above, the server will be available for Gemini sessions."""


def _generate_codex_config(server_url: str, api_key: str) -> str:
    """Generate Codex CLI configuration using mcp-proxy."""
    return f"""Configuration for Codex CLI:

{Colors.GREEN}[mcp_servers.shared-context-server]
command = "mcp-proxy"
args = ["--transport=streamablehttp", "-H", "X-API-Key", "{api_key}", "{server_url}"]{Colors.NC}

{Colors.BLUE}Transport:{Colors.NC} Streamable HTTP via mcp-proxy
{Colors.BLUE}Authentication:{Colors.NC} X-API-Key header

Add the above configuration to your Codex CLI TOML config file.

You'll need mcp-proxy installed. If you don't have it:

{Colors.YELLOW}npm install -g @modelcontextprotocol/proxy{Colors.NC}

{Colors.YELLOW}Note: mcp-proxy bridges HTTP transport for Codex CLI compatibility{Colors.NC}"""


def _generate_qwen_config(server_url: str, api_key: str) -> str:
    """Generate Qwen CLI configuration."""
    return f"""Configuration for Qwen CLI:

Add to ~/.qwen/settings.json:

{Colors.GREEN}{{
  "mcpServers": {{
    "shared-context-server": {{
      "httpUrl": "{server_url}",
      "headers": {{
        "X-API-Key": "{api_key}"
      }}
    }}
  }}
}}{Colors.NC}

{Colors.BLUE}Transport:{Colors.NC} HTTP (StreamableHTTPClientTransport)
{Colors.BLUE}Authentication:{Colors.NC} X-API-Key header

Qwen CLI supports direct HTTP transport for MCP servers.
The configuration uses the 'httpUrl' field for HTTP-based MCP connections."""


def _generate_kiro_config(server_url: str, api_key: str) -> str:
    """Generate Kiro IDE configuration using mcp-proxy."""
    # Detect mcp-proxy location - common locations
    import shutil
    from pathlib import Path

    mcp_proxy_path = shutil.which("mcp-proxy")
    if not mcp_proxy_path:
        common_paths = [
            "/usr/local/bin/mcp-proxy",
            "~/.local/bin/mcp-proxy",
            "~/.cargo/bin/mcp-proxy",
        ]
        for path in common_paths:
            expanded_path = Path(path).expanduser()
            if expanded_path.exists():
                mcp_proxy_path = str(expanded_path)
                break

    if not mcp_proxy_path:
        mcp_proxy_path = "mcp-proxy"

    config_object = f'''"shared-context-server": {{
  "command": "{mcp_proxy_path}",
  "args": [
    "--transport=streamablehttp",
    "{server_url}",
    "--headers",
    "X-API-Key",
    "{api_key}"
  ],
  "disabled": false
}}'''

    return f"""Configuration for Kiro IDE:

{Colors.GREEN}{config_object}{Colors.NC}

{Colors.BLUE}Configuration file locations:{Colors.NC}
{Colors.YELLOW}• Workspace: .kiro/settings/mcp.json{Colors.NC}
{Colors.YELLOW}• User: ~/.kiro/settings/mcp.json{Colors.NC}

Full structure example:
{{
  "mcpServers": {{
    {config_object}
  }}
}}

{Colors.BLUE}Setup via Command Palette:{Colors.NC}
{Colors.YELLOW}1. Open Command Palette (Cmd+Shift+P / Ctrl+Shift+P){Colors.NC}
{Colors.YELLOW}2. Search for "MCP" and select "Kiro: Open workspace MCP config (JSON)"{Colors.NC}
{Colors.YELLOW}3. Add the configuration above{Colors.NC}

{Colors.YELLOW}Note: Ensure mcp-proxy is installed:{Colors.NC}
npm install -g @modelcontextprotocol/proxy

{Colors.YELLOW}If mcp-proxy path differs, update the "command" field accordingly{Colors.NC}

{Colors.BLUE}Transport:{Colors.NC} Streamable HTTP via mcp-proxy
{Colors.BLUE}Authentication:{Colors.NC} X-API-Key header"""


def _handle_clipboard(content: str, copy_behavior: str, Colors: Any) -> None:
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

    if copy_behavior == "copy":
        # Auto-copy without confirmation
        try:
            pyperclip.copy(clipboard_content)
            print(f"\n{Colors.GREEN}✅ Copied to clipboard{Colors.NC}")
        except Exception:
            print(f"\n{Colors.YELLOW}⚠️  Failed to copy to clipboard{Colors.NC}")
    elif copy_behavior == "prompt":
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

    # For Claude Code, extract the complete multi-line command
    if "claude mcp add" in clean_text:
        lines = clean_text.split("\n")
        command_started = False
        command_lines = []
        brace_count = 0

        for line in lines:
            original_line = line  # Keep original spacing
            line = line.strip()

            if line.startswith("claude mcp add"):
                command_started = True
                command_lines.append(line)
                # Check if the JSON starts on the same line
                if "'" in line:
                    json_part = line.split("'", 1)[1] if "'" in line else ""
                    brace_count += json_part.count("{") - json_part.count("}")
            elif command_started:
                if line:
                    command_lines.append(original_line.rstrip())  # Preserve indentation
                    brace_count += line.count("{") - line.count("}")
                    # End when we've closed all braces and hit the closing quote
                    if brace_count == 0 and line.endswith("}'"):
                        break

        if command_lines:
            return "\n".join(command_lines)

    # For Gemini CLI, extract just the command line
    if "gemini mcp add" in clean_text:
        lines = clean_text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("gemini mcp add"):
                return line_stripped

    # For Codex TOML, extract just the [mcp_servers.shared-context-server] block
    if "[mcp_servers.shared-context-server]" in clean_text:
        lines = clean_text.split("\n")
        toml_lines = []
        in_toml = False

        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith("[mcp_servers.shared-context-server]"):
                in_toml = True
                toml_lines.append(line_stripped)
            elif in_toml and line_stripped and not line_stripped.startswith("#"):
                # Continue collecting TOML content until we hit a blank line or comment
                if (
                    line_stripped.startswith("[")
                    and line_stripped != "[mcp_servers.shared-context-server]"
                ):
                    # Hit another section, stop
                    break
                toml_lines.append(line.rstrip())
            elif in_toml and not line_stripped:
                # Hit blank line, stop
                break

        if toml_lines:
            return "\n".join(toml_lines)

    # For JSON objects with "shared-context-server", extract with proper indentation
    if '"shared-context-server"' in clean_text:
        lines = clean_text.split("\n")
        in_object = False
        object_lines = []
        brace_count = 0

        for line in lines:
            if '"shared-context-server":' in line:
                in_object = True
                # Add proper indentation (2 spaces)
                object_lines.append(f"  {line.strip()}")
                brace_count += line.count("{") - line.count("}")
            elif in_object:
                stripped = line.strip()
                if stripped:
                    # Add proper indentation based on content
                    if stripped.startswith('"') or stripped.startswith("}"):
                        # Property or closing brace - 4 spaces
                        object_lines.append(f"    {stripped}")
                    else:
                        # Other content - 2 spaces
                        object_lines.append(f"  {stripped}")

                    brace_count += stripped.count("{") - stripped.count("}")

                    # Stop when braces are balanced
                    if brace_count == 0:
                        break

        if object_lines:
            return "\n".join(object_lines)

    # Fallback: return cleaned text
    return clean_text.strip()


def generate_all_client_configs(
    host: str, port: int, output_file: str | None = None
) -> None:
    """
    Generate all MCP client configurations at once.

    Args:
        host: Server host address
        port: Server port number
        output_file: Optional file path to save configurations. If None, displays to console.

    Generates configurations for all supported MCP clients (Claude Code, Cursor,
    Windsurf, VS Code, Claude Desktop, Gemini, Codex, Qwen, Kiro) in a single formatted
    output. Perfect for documentation, team sharing, or quick reference.
    """
    import os

    server_url = f"http://{host}:{port}/mcp/"

    # Get API key from environment for display
    api_key = os.getenv("API_KEY", "").strip()
    api_key_display = api_key if api_key else "YOUR_API_KEY_HERE"

    # Generate all configurations
    all_configs = []

    # Claude Code
    claude_config = _generate_claude_config(server_url, api_key_display, "user")
    all_configs.append(f"{Colors.BLUE}=== CLAUDE CODE ==={Colors.NC}\n{claude_config}")

    # Cursor
    cursor_config = _generate_cursor_config(server_url, api_key_display)
    all_configs.append(f"{Colors.BLUE}=== CURSOR IDE ==={Colors.NC}\n{cursor_config}")

    # Windsurf
    windsurf_config = _generate_windsurf_config(server_url, api_key_display)
    all_configs.append(
        f"{Colors.BLUE}=== WINDSURF IDE ==={Colors.NC}\n{windsurf_config}"
    )

    # VS Code
    vscode_config = _generate_vscode_config(server_url, api_key_display)
    all_configs.append(f"{Colors.BLUE}=== VS CODE ==={Colors.NC}\n{vscode_config}")

    # Claude Desktop
    claude_desktop_config = _generate_claude_desktop_config(server_url, api_key_display)
    all_configs.append(
        f"{Colors.BLUE}=== CLAUDE DESKTOP ==={Colors.NC}\n{claude_desktop_config}"
    )

    # Gemini
    gemini_config = _generate_gemini_config(server_url, api_key_display)
    all_configs.append(f"{Colors.BLUE}=== GEMINI CLI ==={Colors.NC}\n{gemini_config}")

    # Codex
    codex_config = _generate_codex_config(server_url, api_key_display)
    all_configs.append(f"{Colors.BLUE}=== CODEX CLI ==={Colors.NC}\n{codex_config}")

    # Qwen
    qwen_config = _generate_qwen_config(server_url, api_key_display)
    all_configs.append(f"{Colors.BLUE}=== QWEN CLI ==={Colors.NC}\n{qwen_config}")

    # Kiro IDE
    kiro_config = _generate_kiro_config(server_url, api_key_display)
    all_configs.append(f"{Colors.BLUE}=== KIRO IDE ==={Colors.NC}\n{kiro_config}")

    # Combine all configurations
    full_output = (
        f"\n{Colors.BOLD}🔧 ALL MCP CLIENT CONFIGURATIONS{Colors.NC}\n\n"
        + "\n\n".join(all_configs)
    )

    # Handle output - save to file or display to console
    if output_file:
        # Save to file (remove ANSI color codes for clean file output)
        import re
        from datetime import datetime
        from pathlib import Path

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        clean_output = ansi_escape.sub("", full_output)

        # Add metadata header for the file
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_header = f"""# MCP Client Configurations
# Generated: {timestamp}
# Server: http://{host}:{port}/mcp/
#
# This file contains configuration instructions for all supported MCP clients.
# Copy the relevant section for your MCP client and follow the instructions.

"""

        try:
            output_path = Path(output_file)
            output_path.write_text(file_header + clean_output, encoding="utf-8")
            print(
                f"\n{Colors.GREEN}✅ All configurations saved to: {output_file}{Colors.NC}"
            )
            print(
                f"{Colors.BLUE}📄 File contains configurations for 9 MCP clients:{Colors.NC}"
            )
            print(
                f"{Colors.BLUE}   Claude Code, Cursor, Windsurf, VS Code, Claude Desktop,{Colors.NC}"
            )
            print(
                f"{Colors.BLUE}   Gemini CLI, Codex CLI, Qwen CLI, Kiro IDE{Colors.NC}"
            )

            # Show API key status
            if api_key_display == "YOUR_API_KEY_HERE":
                print(
                    f"\n{Colors.YELLOW}⚠️  SECURITY: Update API_KEY in the saved file{Colors.NC}"
                )
                print(
                    f"{Colors.YELLOW}   Replace 'YOUR_API_KEY_HERE' with your actual API_KEY from .env{Colors.NC}"
                )
            else:
                print(
                    f"\n{Colors.GREEN}✅ Using API_KEY from environment (first 8 chars: {api_key[:8]}...){Colors.NC}"
                )

            print(
                f"\n{Colors.BLUE}💡 Open the file to copy configurations for your MCP clients{Colors.NC}"
            )

        except Exception as e:
            print(f"\n{Colors.RED}❌ Failed to save file: {e}{Colors.NC}")
            print(
                f"{Colors.YELLOW}💡 Try a different filename or check file permissions{Colors.NC}"
            )
            print(
                f"{Colors.BLUE}   Example: scs client-config all -o ~/mcp-configs.md{Colors.NC}"
            )

            # Ask user if they want to see the output since file save failed
            try:
                response = (
                    input(
                        f"\n{Colors.YELLOW}Display configurations to console instead? [y/N]: {Colors.NC}"
                    )
                    .strip()
                    .lower()
                )
                if response in ["y", "yes"]:
                    print(f"\n{Colors.BLUE}Displaying configurations:{Colors.NC}")
                    print(full_output)
                else:
                    print(
                        f"{Colors.BLUE}Configurations not displayed. Try the file save again with a different path.{Colors.NC}"
                    )
            except (KeyboardInterrupt, EOFError):
                print(f"\n{Colors.BLUE}Configurations not displayed.{Colors.NC}")
    else:
        # Display to console
        print(full_output)

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

    print()


def run_setup_command(
    deployment: str | None, format_type: str | None, force: bool = False
) -> None:
    """Setup and configuration command handler."""
    from ..setup_core import (
        check_demo_dependencies,
        generate_keys,
        show_dependency_error,
        show_docker_commands,
        show_uvx_commands,
    )

    if format_type and deployment != "export":
        print(
            f"{Colors.RED}❌ Error: Format argument '{format_type}' can only be used with 'export' deployment.{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}   Did you mean: scs setup export {format_type}?{Colors.NC}"
        )
        sys.exit(1)

    # Handle export format specifically
    if deployment == "export" and format_type:
        # Handle original export formats (json, yaml, env, docker-env)
        if format_type in ["json", "yaml", "env", "docker-env"]:
            from ..setup_core import export_keys, generate_keys

            # Generate keys first for export
            keys = generate_keys()

            # Create .env file and export keys in specified format
            from ..setup_core import create_env_file

            result = create_env_file(keys, force, demo=False)
            if not result:
                sys.exit(1)

            # Export keys in requested format
            export_format = format_type
            if export_format == "env":
                export_format = "export"  # export_keys expects "export" not "env"
            export_keys(keys, export_format)
            return

        # Handle client configuration formats (claude, cursor, etc.)
        if format_type in [
            "claude",
            "cursor",
            "windsurf",
            "vscode",
            "claude-desktop",
            "gemini",
            "codex",
            "qwen",
            "kiro",
        ]:
            try:
                from ..config import get_config

                config = get_config()
                host = config.mcp_server.http_host
                port = config.mcp_server.http_port

                print(
                    f"\n{Colors.BLUE}Generating {format_type} configuration for export...{Colors.NC}"
                )
                generate_client_config(format_type, host, port, "local", "copy")
                return
            except Exception as e:
                print(f"{Colors.RED}❌ Error generating config: {e}{Colors.NC}")
                sys.exit(1)
        else:
            print(f"{Colors.RED}❌ Error: Unknown format '{format_type}'{Colors.NC}")
            print(
                f"{Colors.YELLOW}   Supported formats: json, yaml, env, docker-env, claude, cursor, windsurf, vscode, claude-desktop, gemini, codex, qwen, kiro{Colors.NC}"
            )
            sys.exit(1)

    # Handle demo setup
    if deployment == "demo":
        print(
            f"\n{Colors.BLUE}🎪 Setting up demo environment in current directory{Colors.NC}"
        )

        # Check demo dependencies
        deps_available = True
        try:
            deps_available, missing_deps = check_demo_dependencies()
            if not deps_available:
                show_dependency_error(missing_deps)
                raise SystemExit  # noqa: TRY301
        except SystemExit:
            deps_available = False
            if not force:
                print(
                    f"{Colors.YELLOW}💡 You can still run the demo with a limited MCP configuration.{Colors.NC}"
                )
                print(
                    f"{Colors.YELLOW}   The shared-context-server will work, but octocode features won't be available.{Colors.NC}"
                )

                try:
                    response = (
                        input(
                            f"\n{Colors.YELLOW}Continue with limited demo? [y/N]: {Colors.NC}"
                        )
                        .lower()
                        .strip()
                    )
                    if response not in ["y", "yes"]:
                        print(f"{Colors.YELLOW}Demo setup cancelled.{Colors.NC}")
                        return
                except (EOFError, KeyboardInterrupt):
                    print(f"{Colors.YELLOW}Demo setup cancelled.{Colors.NC}")
                    return
            else:
                print(
                    f"{Colors.YELLOW}🔄 Force mode: Continuing with limited demo setup...{Colors.NC}"
                )

        # Generate secure keys for demo
        keys = generate_keys()

        # Note: Demo environment creation simplified - function was removed during refactoring

        # Show completion message
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
        print()
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

    # Generate keys and handle different deployment types
    keys = generate_keys()

    if deployment == "docker":
        show_docker_commands(keys, demo=False)
    elif deployment == "uvx" or deployment is None:
        show_uvx_commands(keys, demo=False)

    # Note: Completion message handling simplified - function was removed during refactoring


def main() -> None:
    """
    Legacy CLI entry point - redirects to modular implementation.

    This thin wrapper preserves the original entry point while delegating
    core functionality to the modular cli/main.py implementation.
    """
    # Import and delegate to the main orchestration module
    from ..cli.main import main as cli_main

    # Execute the main CLI logic
    cli_main()


if __name__ == "__main__":
    main()
