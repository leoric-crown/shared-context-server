"""
CLI Module for Shared Context Server.

This module provides modular CLI functionality extracted from the monolithic cli.py.
Following the architectural refactoring to improve maintainability and testing.
"""

# Export CLI utilities without shadowing the 'main' submodule
# Note: Do NOT export a name 'main' here; it would mask the
# 'shared_context_server.cli.main' submodule and break test patching
# (particularly on Python 3.10) where targets like
# 'shared_context_server.cli.main.ProductionServer' are expected
# to resolve to the submodule.
from .utils import Colors, print_color

__all__ = ["Colors", "print_color"]
