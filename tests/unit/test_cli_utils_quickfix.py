"""
Quick coverage boost for CLI utils module.

Simple tests for utility functions to push coverage above the razor's edge.
"""

from unittest.mock import patch

from src.shared_context_server.cli.utils import (
    Colors,
    get_colors_with_fallback,
    print_color,
)


class TestCliUtilsQuickfix:
    """Quick coverage tests for CLI utility functions."""

    @patch("builtins.print")
    def test_print_color_with_default_color(self, mock_print):
        """Test print_color with default color (no coloring)."""
        print_color("test message", "default")
        mock_print.assert_called_once_with("test message", end="\n")

    @patch("builtins.print")
    def test_print_color_with_nc_color(self, mock_print):
        """Test print_color with NC color (no coloring)."""
        print_color("test message", Colors.NC)
        mock_print.assert_called_once_with("test message", end="\n")

    @patch("builtins.print")
    def test_print_color_with_actual_color(self, mock_print):
        """Test print_color with actual color code."""
        print_color("test message", Colors.RED)
        expected = f"{Colors.RED}test message{Colors.NC}"
        mock_print.assert_called_once_with(expected, end="\n")

    @patch("builtins.print")
    def test_print_color_with_custom_end(self, mock_print):
        """Test print_color with custom end parameter."""
        print_color("test message", "default", end="")
        mock_print.assert_called_once_with("test message", end="")

    def test_get_colors_with_fallback(self):
        """Test get_colors_with_fallback returns Colors class."""
        colors = get_colors_with_fallback()
        assert colors is Colors
        assert hasattr(colors, "RED")
        assert hasattr(colors, "GREEN")
        assert hasattr(colors, "NC")
