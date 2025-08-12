"""
Shared Context MCP Server.

A centralized memory store enabling multiple AI agents (Claude, Gemini, etc.)
to collaborate on complex tasks through shared conversational context.
"""

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
    """Get version from pyproject.toml."""
    try:
        # Try to find pyproject.toml - look up the directory tree
        current_path = Path(__file__).parent
        for _ in range(5):  # Look up to 5 levels
            pyproject_path = current_path / "pyproject.toml"
            if pyproject_path.exists():
                content = pyproject_path.read_text(encoding="utf-8")
                # Simple parsing - find version = "x.y.z" line
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("version = "):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
            current_path = current_path.parent

        # Fallback version if pyproject.toml not found
        return "1.0.2"
    except Exception:
        # Fallback in case of any errors
        return "1.0.2"


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
