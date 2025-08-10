"""
Shared Context MCP Server.

A centralized memory store enabling multiple AI agents (Claude, Gemini, etc.)
to collaborate on complex tasks through shared conversational context.
"""

__version__ = "1.0.0"
__author__ = "Shared Context Server Team"

from .config import get_config, load_config
from .models import (
    AgentMemoryModel,
    MessageModel,
    MessageType,
    MessageVisibility,
    SessionModel,
)

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
