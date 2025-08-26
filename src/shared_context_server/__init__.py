"""
Shared Context MCP Server.

A centralized memory store enabling multiple AI agents (Claude, Gemini, etc.)
to collaborate on complex tasks through shared conversational context.
"""

from importlib.metadata import version as get_package_version
from pathlib import Path

from .config import get_config, load_config
from .models import (
    AgentMemoryModel,
    MessageModel,
    MessageType,
    MessageVisibility,
    SessionModel,
)

__author__ = "Shared Context Server Team"


def _get_version() -> str:
    """Get version from package metadata or Docker build."""
    try:
        # First, try Docker build version (for containerized environments)
        docker_version_file = Path("/app/version")
        if docker_version_file.exists():
            docker_version = docker_version_file.read_text(encoding="utf-8").strip()
            if docker_version:
                return docker_version

        # Standard approach: get version from installed package metadata
        return get_package_version("shared-context-server")
    except Exception:
        # Final fallback - should rarely be needed
        return "1.1.7"


__version__ = _get_version()

__all__ = [
    "__version__",
    "__author__",
    "get_config",
    "load_config",
    "SessionModel",
    "MessageModel",
    "AgentMemoryModel",
    "MessageVisibility",
    "MessageType",
]
