"""
CLI Utilities - Unified color infrastructure and shared CLI helpers.

This module consolidates color functionality previously duplicated across
setup_core.py and cli.py, providing a single source of truth for CLI styling.
"""


class Colors:
    """Centralized ANSI color definitions eliminating duplication."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color


def print_color(text: str, color: str = "default", end: str = "\n") -> None:
    """
    Unified color printing helper.

    Args:
        text: Text to print
        color: Color code or "default" for no color
        end: String appended after the text (default: newline)
    """
    if color == "default" or color == Colors.NC:
        print(text, end=end)
    else:
        print(f"{color}{text}{Colors.NC}", end=end)


def get_colors_with_fallback() -> type[Colors]:
    """
    Get Colors class with consistent interface.

    This replaces the _get_colors() function pattern used in cli.py
    and provides a consistent way to access color definitions.

    Returns:
        Colors class for consistent styling across CLI components
    """
    return Colors
