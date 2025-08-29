"""
Simple dashboard authentication for admin access.

Provides basic password-based authentication for the web dashboard,
allowing access to admin_only messages and full system visibility.
"""

import hashlib
import hmac
import os
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

import logging

logger = logging.getLogger(__name__)


class DashboardAuth:
    """Simple session-based authentication for dashboard access."""

    # Session cookie name
    COOKIE_NAME = "scs_dashboard_auth"

    # Session timeout (24 hours)
    SESSION_TIMEOUT = 24 * 60 * 60

    def __init__(self) -> None:
        """Initialize dashboard authentication."""
        self.admin_password = os.getenv("ADMIN_PASSWORD")
        self.secret_key = os.getenv("DASHBOARD_SECRET", self._generate_secret())

        if not self.admin_password:
            logger.warning(
                "ADMIN_PASSWORD not set - dashboard will be accessible without authentication"
            )

    def _generate_secret(self) -> str:
        """Generate a secret key for session signing."""
        return secrets.token_urlsafe(32)

    def is_auth_required(self) -> bool:
        """Check if authentication is required for dashboard access."""
        return bool(self.admin_password)

    def verify_password(self, password: str) -> bool:
        """Verify admin password."""
        if not self.admin_password:
            return True  # No password required

        return hmac.compare_digest(password, self.admin_password)

    def create_session_token(self) -> str:
        """Create a signed session token."""
        # Simple token: timestamp + signature
        import time

        timestamp = str(int(time.time()))
        signature = hmac.new(
            self.secret_key.encode(), timestamp.encode(), hashlib.sha256
        ).hexdigest()

        return f"{timestamp}:{signature}"

    def verify_session_token(self, token: str) -> bool:
        """Verify session token is valid and not expired."""
        try:
            timestamp_str, signature = token.split(":", 1)
            timestamp = int(timestamp_str)

            # Check if token is expired
            import time

            if time.time() - timestamp > self.SESSION_TIMEOUT:
                return False

            # Verify signature
            expected_signature = hmac.new(
                self.secret_key.encode(), timestamp_str.encode(), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, IndexError):
            return False

    def is_authenticated(self, request: "Request") -> bool:
        """Check if request is authenticated."""
        if not self.is_auth_required():
            return True

        # Check session cookie
        token = request.cookies.get(self.COOKIE_NAME)
        if not token:
            return False

        return self.verify_session_token(token)

    def set_auth_cookie(self, response: "Response") -> None:
        """Set authentication cookie on response."""
        token = self.create_session_token()
        response.set_cookie(
            self.COOKIE_NAME,
            token,
            max_age=self.SESSION_TIMEOUT,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
        )

    def clear_auth_cookie(self, response: "Response") -> None:
        """Clear authentication cookie."""
        response.delete_cookie(self.COOKIE_NAME)


# Global dashboard auth instance
dashboard_auth = DashboardAuth()
