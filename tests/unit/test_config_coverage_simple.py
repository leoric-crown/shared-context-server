"""
Simple test coverage improvements for config.py.

This module focuses on testing simple utility functions in config.py
to improve overall test coverage with minimal complexity.
"""

import os
from pathlib import Path
from unittest.mock import patch

from shared_context_server.config import (
    get_default_data_directory,
    get_default_database_path,
)


class TestConfigUtilities:
    """Test simple config utility functions."""

    @patch("os.name", "posix")
    @patch.dict(os.environ, {"XDG_DATA_HOME": "/custom/data"})
    def test_get_default_data_directory_xdg_data_home(self):
        """Test data directory with XDG_DATA_HOME set."""
        with patch("pathlib.Path.mkdir"):
            result = get_default_data_directory()
            assert result == "/custom/data/shared-context-server"

    @patch("os.name", "posix")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_default_data_directory_no_xdg(self):
        """Test data directory without XDG_DATA_HOME."""
        with (
            patch("pathlib.Path.home", return_value=Path("/home/user")),
            patch("pathlib.Path.mkdir"),
        ):
            result = get_default_data_directory()
            assert result == "/home/user/.local/share/shared-context-server"

    @patch("os.name", "other")
    def test_get_default_data_directory_fallback(self):
        """Test data directory fallback for other OS."""
        with (
            patch("pathlib.Path.home", return_value=Path("/home/user")),
            patch("pathlib.Path.mkdir"),
        ):
            result = get_default_data_directory()
            assert result == "/home/user/.shared-context-server"

    def test_get_default_database_path_development_env(self):
        """Test database path in development environment."""
        with patch("pathlib.Path.exists", return_value=True):
            result = get_default_database_path()
            assert result == "./chat_history.db"

    def test_get_default_database_path_production_env(self):
        """Test database path in production environment."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch(
                "shared_context_server.config.get_default_data_directory",
                return_value="/data/shared-context",
            ),
        ):
            result = get_default_database_path()
            assert result == "/data/shared-context/chat_history.db"
