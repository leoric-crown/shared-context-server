"""
CLI Module for Shared Context Server.

This module provides modular CLI functionality extracted from the monolithic cli.py.
Following the architectural refactoring to improve maintainability and testing.
"""

# Export main interfaces for internal use
from .utils import Colors, print_color

__all__ = ["Colors", "print_color"]
