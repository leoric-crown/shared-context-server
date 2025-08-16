"""
Tests for environment detection and configuration functions in database.py.

These tests target uncovered utility functions to improve coverage.
"""

import os
import sys
from unittest.mock import patch

from src.shared_context_server.database import _is_testing_environment


class TestEnvironmentDetection:
    """Test environment detection functions."""

    def test_is_testing_environment_with_pytest(self):
        """Test detection when pytest is in sys.modules."""
        # pytest should already be in modules when running tests
        assert _is_testing_environment() is True

    def test_is_testing_environment_without_pytest(self):
        """Test detection without pytest in modules."""
        # Mock sys.modules without pytest
        original_modules = sys.modules.copy()

        # Remove pytest from modules temporarily
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        try:
            # Test without any environment variables
            with patch.dict(os.environ, {}, clear=True):
                result = _is_testing_environment()
                assert result is False
        finally:
            # Restore original modules
            sys.modules.update(original_modules)

    def test_is_testing_environment_with_ci(self):
        """Test detection with CI environment variable."""
        # Remove pytest from modules temporarily
        original_modules = sys.modules.copy()
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        try:
            with patch.dict(os.environ, {"CI": "true"}, clear=True):
                result = _is_testing_environment()
                assert result is True
        finally:
            sys.modules.update(original_modules)

    def test_is_testing_environment_with_github_actions(self):
        """Test detection with GITHUB_ACTIONS environment variable."""
        original_modules = sys.modules.copy()
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        try:
            with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
                result = _is_testing_environment()
                assert result is True
        finally:
            sys.modules.update(original_modules)

    def test_is_testing_environment_with_pytest_current_test(self):
        """Test detection with PYTEST_CURRENT_TEST environment variable."""
        original_modules = sys.modules.copy()
        if "pytest" in sys.modules:
            del sys.modules["pytest"]

        try:
            with patch.dict(
                os.environ, {"PYTEST_CURRENT_TEST": "test_example.py"}, clear=True
            ):
                result = _is_testing_environment()
                assert result is True
        finally:
            sys.modules.update(original_modules)
