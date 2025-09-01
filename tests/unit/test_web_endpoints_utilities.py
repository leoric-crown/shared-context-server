"""
Test coverage for web endpoints utility functions.

This module tests the utility functions in web_endpoints.py that support
the web dashboard functionality. Focus is on behavior-first testing of
authentication helpers and route utilities.
"""

from unittest.mock import Mock, patch

from shared_context_server.web_endpoints import require_auth


class TestWebEndpointsUtilities:
    """Test web endpoints utility functions with behavior-first approach."""

    # =============================================================================
    # AUTHENTICATION UTILITIES
    # =============================================================================

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    def test_require_auth_authenticated_user_returns_none(self, mock_dashboard_auth):
        """Test require_auth returns None for authenticated users."""
        # Mock authenticated user
        mock_dashboard_auth.is_authenticated.return_value = True
        mock_request = Mock()

        result = require_auth(mock_request)

        assert result is None
        mock_dashboard_auth.is_authenticated.assert_called_once_with(mock_request)

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    def test_require_auth_unauthenticated_user_returns_redirect(
        self, mock_dashboard_auth
    ):
        """Test require_auth returns redirect for unauthenticated users."""
        # Mock unauthenticated user
        mock_dashboard_auth.is_authenticated.return_value = False
        mock_request = Mock()

        result = require_auth(mock_request)

        assert result is not None
        assert hasattr(result, "headers")  # RedirectResponse has headers
        assert result.headers["location"] == "/ui/login"
        assert result.status_code == 302
        mock_dashboard_auth.is_authenticated.assert_called_once_with(mock_request)

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    def test_require_auth_handles_none_request(self, mock_dashboard_auth):
        """Test require_auth handles None request gracefully."""
        # Mock dashboard_auth to handle None request
        mock_dashboard_auth.is_authenticated.return_value = False

        result = require_auth(None)

        assert result is not None
        assert result.headers["location"] == "/ui/login"
        assert result.status_code == 302
        mock_dashboard_auth.is_authenticated.assert_called_once_with(None)

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    def test_require_auth_preserves_request_object(self, mock_dashboard_auth):
        """Test require_auth passes request object correctly to is_authenticated."""
        mock_dashboard_auth.is_authenticated.return_value = True
        mock_request = Mock()
        mock_request.headers = {"User-Agent": "test-agent"}

        result = require_auth(mock_request)

        assert result is None
        # Verify the exact request object was passed
        mock_dashboard_auth.is_authenticated.assert_called_once_with(mock_request)

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    def test_require_auth_behavior_consistent_multiple_calls(self, mock_dashboard_auth):
        """Test require_auth behavior is consistent across multiple calls."""
        mock_request = Mock()

        # Test authenticated state
        mock_dashboard_auth.is_authenticated.return_value = True
        result1 = require_auth(mock_request)
        result2 = require_auth(mock_request)

        assert result1 is None
        assert result2 is None

        # Test unauthenticated state
        mock_dashboard_auth.is_authenticated.return_value = False
        result3 = require_auth(mock_request)
        result4 = require_auth(mock_request)

        assert result3 is not None and result3.headers["location"] == "/ui/login"
        assert result4 is not None and result4.headers["location"] == "/ui/login"
