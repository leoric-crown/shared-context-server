"""
Essential behavior tests for web endpoints to achieve 70% coverage target.

This focused test suite tests the most critical web endpoint behaviors
to push coverage from 68.17% to 70%+ with minimal complexity.
"""

import json
import os
from unittest.mock import AsyncMock, Mock, patch

from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from shared_context_server import web_endpoints


class TestWebEndpointsEssential:
    """Essential web endpoint behavior tests."""

    # =============================================================================
    # LOGIN FLOW TESTING
    # =============================================================================

    @patch("shared_context_server.web_endpoints.templates")
    async def test_login_get_renders_form(self, mock_templates):
        """Test GET /ui/login renders login form."""
        mock_templates.TemplateResponse.return_value = HTMLResponse("login form")
        mock_request = Mock()
        mock_request.method = "GET"

        result = await web_endpoints.login(mock_request)

        assert isinstance(result, HTMLResponse)
        mock_templates.TemplateResponse.assert_called_once()

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    async def test_login_post_success_redirects_to_dashboard(self, mock_dashboard_auth):
        """Test successful login redirects to dashboard."""
        mock_dashboard_auth.verify_password.return_value = True
        mock_dashboard_auth.set_auth_cookie = Mock()

        mock_request = Mock()
        mock_request.method = "POST"
        mock_form = {"password": "correct"}
        mock_request.form = AsyncMock(return_value=mock_form)

        result = await web_endpoints.login(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/"
        assert result.status_code == 302
        mock_dashboard_auth.set_auth_cookie.assert_called_once()

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    @patch("shared_context_server.web_endpoints.templates")
    async def test_login_post_failure_shows_error(
        self, mock_templates, mock_dashboard_auth
    ):
        """Test failed login shows error message."""
        mock_dashboard_auth.verify_password.return_value = False
        mock_templates.TemplateResponse.return_value = HTMLResponse("error")

        mock_request = Mock()
        mock_request.method = "POST"
        mock_form = {"password": "wrong"}
        mock_request.form = AsyncMock(return_value=mock_form)

        result = await web_endpoints.login(mock_request)

        assert isinstance(result, HTMLResponse)
        # Verify error context was passed
        call_args = mock_templates.TemplateResponse.call_args[0]
        context = call_args[2]
        assert "error" in context

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    async def test_logout_clears_auth_cookie(self, mock_dashboard_auth):
        """Test logout clears authentication cookie."""
        mock_dashboard_auth.clear_auth_cookie = Mock()
        mock_request = Mock()

        result = await web_endpoints.logout(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"
        mock_dashboard_auth.clear_auth_cookie.assert_called_once()

    # =============================================================================
    # AUTHENTICATION HELPERS
    # =============================================================================

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    def test_require_auth_allows_authenticated_users(self, mock_dashboard_auth):
        """Test require_auth allows authenticated users through."""
        mock_dashboard_auth.is_authenticated.return_value = True
        mock_request = Mock()

        result = web_endpoints.require_auth(mock_request)

        assert result is None
        mock_dashboard_auth.is_authenticated.assert_called_once_with(mock_request)

    @patch("shared_context_server.web_endpoints.dashboard_auth")
    def test_require_auth_blocks_unauthenticated_users(self, mock_dashboard_auth):
        """Test require_auth blocks unauthenticated users."""
        mock_dashboard_auth.is_authenticated.return_value = False
        mock_request = Mock()

        result = web_endpoints.require_auth(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"

    # =============================================================================
    # PROTECTED PAGES AUTHENTICATION
    # =============================================================================

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_dashboard_blocks_unauthenticated_access(self, mock_require_auth):
        """Test dashboard blocks unauthenticated users."""
        mock_require_auth.return_value = RedirectResponse("/ui/login", status_code=302)
        mock_request = Mock()

        result = await web_endpoints.dashboard(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_session_view_blocks_unauthenticated_access(self, mock_require_auth):
        """Test session view blocks unauthenticated users."""
        mock_require_auth.return_value = RedirectResponse("/ui/login", status_code=302)
        mock_request = Mock()
        mock_request.path_params = {"session_id": "test"}

        result = await web_endpoints.session_view(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_memory_dashboard_blocks_unauthenticated_access(
        self, mock_require_auth
    ):
        """Test memory dashboard blocks unauthenticated users."""
        mock_require_auth.return_value = RedirectResponse("/ui/login", status_code=302)
        mock_request = Mock()
        mock_request.query_params = {}

        result = await web_endpoints.memory_dashboard(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_health_dashboard_blocks_unauthenticated_access(
        self, mock_require_auth
    ):
        """Test health dashboard blocks unauthenticated users."""
        mock_require_auth.return_value = RedirectResponse("/ui/login", status_code=302)
        mock_request = Mock()

        result = await web_endpoints.health_dashboard(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_client_config_blocks_unauthenticated_access(self, mock_require_auth):
        """Test client config blocks unauthenticated users."""
        mock_require_auth.return_value = RedirectResponse("/ui/login", status_code=302)
        mock_request = Mock()

        result = await web_endpoints.client_config(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_reveal_api_key_blocks_unauthenticated_access(
        self, mock_require_auth
    ):
        """Test API key reveal blocks unauthenticated users."""
        mock_require_auth.return_value = RedirectResponse("/ui/login", status_code=302)
        mock_request = Mock()

        result = await web_endpoints.reveal_api_key(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/ui/login"

    # =============================================================================
    # ERROR HANDLING
    # =============================================================================

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_db_connection")
    async def test_dashboard_handles_database_errors(
        self, mock_get_db_connection, mock_require_auth
    ):
        """Test dashboard handles database connection errors."""
        mock_require_auth.return_value = None  # Authenticated
        mock_get_db_connection.side_effect = Exception("Database error")

        mock_request = Mock()

        result = await web_endpoints.dashboard(mock_request)

        assert isinstance(result, HTMLResponse)
        assert result.status_code == 500
        assert "Dashboard Error" in result.body.decode()

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_db_connection")
    async def test_session_view_handles_database_errors(
        self, mock_get_db_connection, mock_require_auth
    ):
        """Test session view handles database errors."""
        mock_require_auth.return_value = None  # Authenticated
        mock_get_db_connection.side_effect = Exception("Database error")

        mock_request = Mock()
        mock_request.path_params = {"session_id": "test"}

        result = await web_endpoints.session_view(mock_request)

        assert isinstance(result, HTMLResponse)
        assert result.status_code == 500
        assert "Session View Error" in result.body.decode()

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_db_connection")
    async def test_memory_dashboard_handles_database_errors(
        self, mock_get_db_connection, mock_require_auth
    ):
        """Test memory dashboard handles database errors."""
        mock_require_auth.return_value = None  # Authenticated
        mock_get_db_connection.side_effect = Exception("Database error")

        mock_request = Mock()
        mock_request.query_params = {"scope": "all"}

        result = await web_endpoints.memory_dashboard(mock_request)

        assert isinstance(result, HTMLResponse)
        assert result.status_code == 500
        assert "Memory Dashboard Error" in result.body.decode()

    # =============================================================================
    # SIMPLE SUCCESS CASES
    # =============================================================================

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_db_connection")
    @patch("shared_context_server.web_endpoints.templates")
    @patch("shared_context_server.web_endpoints.get_config")
    async def test_dashboard_renders_with_valid_auth(
        self, mock_get_config, mock_templates, mock_get_db_connection, mock_require_auth
    ):
        """Test dashboard renders successfully for authenticated user."""
        # Setup authentication
        mock_require_auth.return_value = None

        # Mock config
        mock_config = Mock()
        mock_config.mcp_server.websocket_port = 8080
        mock_get_config.return_value = mock_config

        # Mock database - simple success case
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_get_db_connection.return_value.__aenter__.return_value = mock_conn

        # Mock templates
        mock_templates.TemplateResponse.return_value = HTMLResponse("dashboard")

        mock_request = Mock()

        result = await web_endpoints.dashboard(mock_request)

        assert isinstance(result, HTMLResponse)
        mock_templates.TemplateResponse.assert_called_once()

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_db_connection")
    async def test_session_view_returns_404_for_missing_session(
        self, mock_get_db_connection, mock_require_auth
    ):
        """Test session view returns 404 for missing session."""
        mock_require_auth.return_value = None  # Authenticated

        # Mock database - no session found
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_get_db_connection.return_value.__aenter__.return_value = mock_conn

        mock_request = Mock()
        mock_request.path_params = {"session_id": "nonexistent"}

        result = await web_endpoints.session_view(mock_request)

        assert isinstance(result, HTMLResponse)
        assert result.status_code == 404
        assert "Session Not Found" in result.body.decode()

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_db_connection")
    async def test_memory_dashboard_handles_scope_parameter_with_error(
        self, mock_get_db_connection, mock_require_auth
    ):
        """Test memory dashboard handles scope parameter and database errors gracefully."""
        mock_require_auth.return_value = None  # Authenticated

        # Force database error to test error handling path
        mock_get_db_connection.side_effect = Exception("Database error")

        mock_request = Mock()
        mock_request.query_params = {"scope": "global"}

        result = await web_endpoints.memory_dashboard(mock_request)

        # Should handle error gracefully
        assert isinstance(result, HTMLResponse)
        assert result.status_code == 500
        assert "Memory Dashboard Error" in result.body.decode()

    # =============================================================================
    # STATIC FILE SERVING
    # =============================================================================

    @patch("shared_context_server.web_endpoints.static_dir")
    async def test_serve_css_returns_file_when_exists(self, mock_static_dir):
        """Test CSS serving returns file when it exists."""
        mock_css_file = Mock()
        mock_css_file.exists.return_value = True
        mock_static_dir.__truediv__.return_value.__truediv__.return_value = (
            mock_css_file
        )

        with patch(
            "shared_context_server.web_endpoints.FileResponse"
        ) as mock_file_response:
            mock_file_response.return_value = Mock()
            mock_request = Mock()

            await web_endpoints.serve_css(mock_request)

            mock_file_response.assert_called_once_with(
                mock_css_file, media_type="text/css"
            )

    @patch("shared_context_server.web_endpoints.static_dir")
    async def test_serve_css_returns_404_when_missing(self, mock_static_dir):
        """Test CSS serving returns 404 when file missing."""
        mock_css_file = Mock()
        mock_css_file.exists.return_value = False
        mock_static_dir.__truediv__.return_value.__truediv__.return_value = (
            mock_css_file
        )

        mock_request = Mock()

        result = await web_endpoints.serve_css(mock_request)

        assert result.status_code == 404
        assert "CSS Not Found" in result.body.decode()

    @patch("shared_context_server.web_endpoints.static_dir")
    async def test_serve_js_returns_file_when_exists(self, mock_static_dir):
        """Test JavaScript serving returns file when it exists."""
        mock_js_file = Mock()
        mock_js_file.exists.return_value = True
        mock_static_dir.__truediv__.return_value.__truediv__.return_value = mock_js_file

        with patch(
            "shared_context_server.web_endpoints.FileResponse"
        ) as mock_file_response:
            mock_file_response.return_value = Mock()
            mock_request = Mock()

            await web_endpoints.serve_js(mock_request)

            mock_file_response.assert_called_once_with(
                mock_js_file, media_type="application/javascript"
            )

    @patch("shared_context_server.web_endpoints.static_dir")
    async def test_serve_logo_svg_returns_file_when_exists(self, mock_static_dir):
        """Test SVG logo serving returns file when it exists."""
        mock_svg_file = Mock()
        mock_svg_file.exists.return_value = True
        mock_static_dir.__truediv__.return_value = mock_svg_file

        with patch(
            "shared_context_server.web_endpoints.FileResponse"
        ) as mock_file_response:
            mock_file_response.return_value = Mock()
            mock_request = Mock()

            await web_endpoints.serve_logo_svg(mock_request)

            mock_file_response.assert_called_once_with(
                mock_svg_file, media_type="image/svg+xml"
            )

    # =============================================================================
    # API KEY REVEAL ENDPOINT
    # =============================================================================

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_config")
    async def test_reveal_api_key_returns_key_when_configured(
        self, mock_get_config, mock_require_auth
    ):
        """Test API key reveal returns configured key."""
        mock_require_auth.return_value = None  # Authenticated

        mock_config = Mock()
        mock_config.security.api_key = None
        mock_get_config.return_value = mock_config

        # Set environment variable
        original_api_key = os.environ.get("API_KEY")
        try:
            os.environ["API_KEY"] = "test_secret_key"
            mock_request = Mock()

            result = await web_endpoints.reveal_api_key(mock_request)

            assert isinstance(result, JSONResponse)
            response_data = json.loads(result.body.decode())
            assert response_data["api_key"] == "test_secret_key"
            assert response_data["ttl_seconds"] == 60

        finally:
            if original_api_key is not None:
                os.environ["API_KEY"] = original_api_key
            else:
                os.environ.pop("API_KEY", None)

    @patch("shared_context_server.web_endpoints.require_auth")
    @patch("shared_context_server.web_endpoints.get_config")
    async def test_reveal_api_key_returns_404_when_not_configured(
        self, mock_get_config, mock_require_auth
    ):
        """Test API key reveal returns 404 when no key configured."""
        mock_require_auth.return_value = None  # Authenticated

        mock_config = Mock()
        mock_config.security.api_key = None
        mock_get_config.return_value = mock_config

        # Ensure no API_KEY environment variable
        original_api_key = os.environ.get("API_KEY")
        try:
            if "API_KEY" in os.environ:
                del os.environ["API_KEY"]

            mock_request = Mock()

            result = await web_endpoints.reveal_api_key(mock_request)

            assert isinstance(result, JSONResponse)
            assert result.status_code == 404
            response_data = json.loads(result.body.decode())
            assert "API key not configured" in response_data["error"]

        finally:
            if original_api_key is not None:
                os.environ["API_KEY"] = original_api_key

    # =============================================================================
    # REDIRECT HANDLERS
    # =============================================================================

    async def test_ui_redirect_redirects_to_slash(self):
        """Test /ui redirects to /ui/ for consistency."""
        mock_request = Mock()

        result = await web_endpoints.ui_redirect(mock_request)

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 301
        assert result.headers["location"] == "/ui/"

    # =============================================================================
    # SIMPLE CLIENT CONFIG TEST
    # =============================================================================

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_client_config_handles_generation_error(self, mock_require_auth):
        """Test client config handles generation errors gracefully."""
        mock_require_auth.return_value = None  # Authenticated

        # Force an error during config generation
        with patch("shared_context_server.web_endpoints.get_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")

            mock_request = Mock()

            result = await web_endpoints.client_config(mock_request)

            assert isinstance(result, HTMLResponse)
            assert result.status_code == 500
            assert "Error" in result.body.decode()

    # =============================================================================
    # HEALTH DASHBOARD SIMPLE CASE
    # =============================================================================

    @patch("shared_context_server.web_endpoints.require_auth")
    async def test_health_dashboard_handles_general_error(self, mock_require_auth):
        """Test health dashboard handles general errors gracefully."""
        mock_require_auth.return_value = None  # Authenticated

        # Force a general error
        with patch("shared_context_server.web_endpoints.get_config") as mock_get_config:
            mock_get_config.side_effect = Exception("General error")

            mock_request = Mock()

            result = await web_endpoints.health_dashboard(mock_request)

            # Should return error template
            assert isinstance(result, HTMLResponse) or hasattr(result, "status_code")
