"""
Test coverage for dashboard authentication behavior.

This module tests the dashboard authentication flows including password
verification, session token creation/validation, and request authentication.
Focus is on behavior-first testing with time mocking for session timeouts.
"""

import hashlib
import hmac
import os
from unittest.mock import MagicMock, patch

from shared_context_server.dashboard_auth import DashboardAuth


class TestDashboardAuthBehavior:
    """Test dashboard authentication behavior with focus on flows."""

    def test_init_with_admin_password(self):
        """Test initialization when admin password is set."""
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "test_password"}, clear=False):
            auth = DashboardAuth()
            assert auth.admin_password == "test_password"
            assert auth.secret_key is not None
            assert len(auth.secret_key) > 0

    def test_init_without_admin_password(self):
        """Test initialization when no admin password is set."""
        with patch.dict(os.environ, {}, clear=True):
            auth = DashboardAuth()
            assert auth.admin_password is None
            assert auth.secret_key is not None

    def test_init_with_custom_dashboard_secret(self):
        """Test initialization with custom dashboard secret."""
        with patch.dict(os.environ, {"DASHBOARD_SECRET": "custom_secret"}, clear=False):
            auth = DashboardAuth()
            assert auth.secret_key == "custom_secret"

    def test_generate_secret_creates_unique_values(self):
        """Test that _generate_secret creates unique values."""
        auth = DashboardAuth()
        secret1 = auth._generate_secret()
        secret2 = auth._generate_secret()

        assert secret1 != secret2
        assert len(secret1) > 20  # URL-safe base64 should be substantial
        assert len(secret2) > 20

    def test_is_auth_required_with_password(self):
        """Test authentication requirement when password is set."""
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "test_password"}, clear=False):
            auth = DashboardAuth()
            assert auth.is_auth_required() is True

    def test_is_auth_required_without_password(self):
        """Test authentication requirement when no password is set."""
        with patch.dict(os.environ, {}, clear=True):
            auth = DashboardAuth()
            assert auth.is_auth_required() is False

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        with patch.dict(
            os.environ, {"ADMIN_PASSWORD": "correct_password"}, clear=False
        ):
            auth = DashboardAuth()
            assert auth.verify_password("correct_password") is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        with patch.dict(
            os.environ, {"ADMIN_PASSWORD": "correct_password"}, clear=False
        ):
            auth = DashboardAuth()
            assert auth.verify_password("wrong_password") is False

    def test_verify_password_no_password_required(self):
        """Test password verification when no password is required."""
        with patch.dict(os.environ, {}, clear=True):
            auth = DashboardAuth()
            assert auth.verify_password("any_password") is True

    def test_verify_password_empty_string(self):
        """Test password verification with empty string."""
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "test_password"}, clear=False):
            auth = DashboardAuth()
            assert auth.verify_password("") is False

    @patch("time.time")
    def test_create_session_token_format(self, mock_time):
        """Test session token creation format."""
        mock_time.return_value = 1690000000.0  # Fixed timestamp

        with patch.dict(
            os.environ,
            {"ADMIN_PASSWORD": "test", "DASHBOARD_SECRET": "test_secret"},
            clear=False,
        ):
            auth = DashboardAuth()
            token = auth.create_session_token()

            # Token should have timestamp:signature format
            parts = token.split(":")
            assert len(parts) == 2
            assert parts[0] == "1690000000"  # Timestamp as string
            assert len(parts[1]) == 64  # SHA256 hex digest

    @patch("time.time")
    def test_create_session_token_signature_validity(self, mock_time):
        """Test that session token signature is correctly generated."""
        mock_time.return_value = 1690000000.0

        with patch.dict(os.environ, {"DASHBOARD_SECRET": "test_secret"}, clear=False):
            auth = DashboardAuth()
            token = auth.create_session_token()

            timestamp_str, signature = token.split(":", 1)

            # Manually calculate expected signature
            expected_signature = hmac.new(
                b"test_secret", timestamp_str.encode(), hashlib.sha256
            ).hexdigest()

            assert signature == expected_signature

    @patch("time.time")
    def test_verify_session_token_valid_fresh(self, mock_time):
        """Test verification of valid, fresh session token."""
        # Create token at time 1690000000
        mock_time.return_value = 1690000000.0

        with patch.dict(os.environ, {"DASHBOARD_SECRET": "test_secret"}, clear=False):
            auth = DashboardAuth()
            token = auth.create_session_token()

            # Verify token 1 hour later (well within 24h timeout)
            mock_time.return_value = 1690000000.0 + 3600  # +1 hour
            assert auth.verify_session_token(token) is True

    @patch("time.time")
    def test_verify_session_token_expired(self, mock_time):
        """Test verification of expired session token."""
        # Create token at time 1690000000
        mock_time.return_value = 1690000000.0

        with patch.dict(os.environ, {"DASHBOARD_SECRET": "test_secret"}, clear=False):
            auth = DashboardAuth()
            token = auth.create_session_token()

            # Verify token 25 hours later (beyond 24h timeout)
            mock_time.return_value = 1690000000.0 + (25 * 60 * 60)  # +25 hours
            assert auth.verify_session_token(token) is False

    def test_verify_session_token_invalid_format(self):
        """Test verification of malformed session tokens."""
        auth = DashboardAuth()

        # Various invalid formats
        assert auth.verify_session_token("invalid") is False
        assert auth.verify_session_token("") is False
        assert auth.verify_session_token("timestamp_only") is False
        assert auth.verify_session_token(":signature_only") is False
        assert auth.verify_session_token("not:a:valid:timestamp:123") is False

    def test_verify_session_token_invalid_timestamp(self):
        """Test verification with non-numeric timestamp."""
        auth = DashboardAuth()

        # Invalid timestamp formats
        assert auth.verify_session_token("not_a_number:signature") is False
        assert auth.verify_session_token("123.456:signature") is False

    @patch("time.time")
    def test_verify_session_token_wrong_signature(self, mock_time):
        """Test verification with correct format but wrong signature."""
        mock_time.return_value = 1690000000.0

        with patch.dict(os.environ, {"DASHBOARD_SECRET": "test_secret"}, clear=False):
            auth = DashboardAuth()

            # Create a token with wrong signature
            fake_token = "1690000000:wrong_signature"
            assert auth.verify_session_token(fake_token) is False

    @patch("time.time")
    def test_verify_session_token_different_secret(self, mock_time):
        """Test verification fails when secret key changes."""
        mock_time.return_value = 1690000000.0

        # Create token with one secret
        with patch.dict(os.environ, {"DASHBOARD_SECRET": "secret1"}, clear=False):
            auth1 = DashboardAuth()
            token = auth1.create_session_token()

        # Try to verify with different secret
        mock_time.return_value = 1690000000.0 + 3600  # +1 hour
        with patch.dict(os.environ, {"DASHBOARD_SECRET": "secret2"}, clear=False):
            auth2 = DashboardAuth()
            assert auth2.verify_session_token(token) is False

    def test_is_authenticated_no_auth_required(self):
        """Test authentication check when no auth is required."""
        with patch.dict(os.environ, {}, clear=True):
            auth = DashboardAuth()

            # Mock request - content doesn't matter when no auth required
            mock_request = MagicMock()
            assert auth.is_authenticated(mock_request) is True

    def test_is_authenticated_no_cookie(self):
        """Test authentication check when no session cookie is present."""
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "test"}, clear=False):
            auth = DashboardAuth()

            mock_request = MagicMock()
            mock_request.cookies.get.return_value = None

            assert auth.is_authenticated(mock_request) is False
            mock_request.cookies.get.assert_called_once_with(DashboardAuth.COOKIE_NAME)

    @patch("time.time")
    def test_is_authenticated_valid_cookie(self, mock_time):
        """Test authentication check with valid session cookie."""
        mock_time.return_value = 1690000000.0

        with patch.dict(
            os.environ,
            {"ADMIN_PASSWORD": "test", "DASHBOARD_SECRET": "test_secret"},
            clear=False,
        ):
            auth = DashboardAuth()
            token = auth.create_session_token()

            mock_request = MagicMock()
            mock_request.cookies.get.return_value = token

            # Check authentication 1 hour later
            mock_time.return_value = 1690000000.0 + 3600
            assert auth.is_authenticated(mock_request) is True

    @patch("time.time")
    def test_is_authenticated_expired_cookie(self, mock_time):
        """Test authentication check with expired session cookie."""
        mock_time.return_value = 1690000000.0

        with patch.dict(
            os.environ,
            {"ADMIN_PASSWORD": "test", "DASHBOARD_SECRET": "test_secret"},
            clear=False,
        ):
            auth = DashboardAuth()
            token = auth.create_session_token()

            mock_request = MagicMock()
            mock_request.cookies.get.return_value = token

            # Check authentication 25 hours later (expired)
            mock_time.return_value = 1690000000.0 + (25 * 60 * 60)
            assert auth.is_authenticated(mock_request) is False

    def test_is_authenticated_invalid_cookie(self):
        """Test authentication check with invalid session cookie."""
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "test"}, clear=False):
            auth = DashboardAuth()

            mock_request = MagicMock()
            mock_request.cookies.get.return_value = "invalid_token"

            assert auth.is_authenticated(mock_request) is False

    def test_session_constants(self):
        """Test that session constants have expected values."""
        assert DashboardAuth.COOKIE_NAME == "scs_dashboard_auth"
        assert DashboardAuth.SESSION_TIMEOUT == 24 * 60 * 60  # 24 hours in seconds

    def test_hmac_compare_digest_usage(self):
        """Test that password verification uses timing-safe comparison."""
        with patch.dict(os.environ, {"ADMIN_PASSWORD": "test_password"}, clear=False):
            auth = DashboardAuth()

            # Patch hmac.compare_digest to verify it's being called
            with patch(
                "shared_context_server.dashboard_auth.hmac.compare_digest"
            ) as mock_compare:
                mock_compare.return_value = True

                result = auth.verify_password("test_password")

                assert result is True
                mock_compare.assert_called_once_with("test_password", "test_password")

    @patch("shared_context_server.dashboard_auth.logger")
    def test_warning_logged_when_no_password(self, mock_logger):
        """Test that warning is logged when ADMIN_PASSWORD is not set."""
        with patch.dict(os.environ, {}, clear=True):
            DashboardAuth()

            mock_logger.warning.assert_called_once_with(
                "ADMIN_PASSWORD not set - dashboard will be accessible without authentication"
            )

    def test_edge_case_empty_admin_password(self):
        """Test behavior when ADMIN_PASSWORD is set to empty string."""
        with patch.dict(os.environ, {"ADMIN_PASSWORD": ""}, clear=False):
            auth = DashboardAuth()

            # Empty string should be falsy, so auth not required
            assert auth.is_auth_required() is False
            assert auth.verify_password("anything") is True

    @patch("time.time")
    def test_session_timeout_boundary(self, mock_time):
        """Test session timeout at exact boundary."""
        mock_time.return_value = 1690000000.0

        with patch.dict(os.environ, {"DASHBOARD_SECRET": "test_secret"}, clear=False):
            auth = DashboardAuth()
            token = auth.create_session_token()

            # Test exactly at timeout boundary (condition is >, so this is still valid)
            mock_time.return_value = 1690000000.0 + DashboardAuth.SESSION_TIMEOUT
            assert auth.verify_session_token(token) is True

            # Test just past timeout boundary
            mock_time.return_value = 1690000000.0 + DashboardAuth.SESSION_TIMEOUT + 1
            assert auth.verify_session_token(token) is False
