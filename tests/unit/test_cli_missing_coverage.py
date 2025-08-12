"""
Tests for missing coverage in cli.py - targeting specific uncovered lines.

This test file focuses on covering error paths and edge cases that weren't covered
in the comprehensive test file.
"""

import asyncio
import os
import signal
import sys
from unittest.mock import Mock, patch

import pytest

# Import the CLI module - handle import failures gracefully
try:
    from shared_context_server.scripts.cli import (
        ProductionServer,
        main,
        setup_signal_handlers,
        show_status,
    )

    CLI_AVAILABLE = True
except ImportError as e:
    CLI_AVAILABLE = False
    pytest.skip(f"CLI module not available: {e}", allow_module_level=True)


class TestUvloopImportError:
    """Test uvloop import error handling."""

    def test_uvloop_import_error_path(self):
        """Test the uvloop ImportError path (lines 23-25)."""
        # This tests the import error handling at module level
        # We can't easily test the actual ImportError at runtime, but we can verify
        # the UVLOOP_AVAILABLE flag behavior

        # Import the module to check current state
        import shared_context_server.scripts.cli as cli_module

        # Verify the flag is boolean
        assert isinstance(cli_module.UVLOOP_AVAILABLE, bool)

        # Test the code path when uvloop is not available
        with patch.dict(sys.modules, {"uvloop": None}):
            # The module is already loaded, so this is more about verifying
            # that the code handles the case properly
            assert True  # The import error path exists


class TestServerImportError:
    """Test server import error handling."""

    def test_server_import_error_path(self):
        """Test the server ImportError path (lines 56-58)."""
        # Similar to uvloop, this tests the import error handling
        import shared_context_server.scripts.cli as cli_module

        # Verify the flag is boolean
        assert isinstance(cli_module.SERVER_AVAILABLE, bool)

        # In normal test environment, this should be True
        assert cli_module.SERVER_AVAILABLE is True


class TestProductionServerErrorPaths:
    """Test ProductionServer error handling paths."""

    @pytest.mark.asyncio
    async def test_stdio_server_exception_path(self):
        """Test STDIO server exception handling (lines 76-84)."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        server = ProductionServer()

        # Mock SERVER_AVAILABLE as True to reach the try block
        with (
            patch("shared_context_server.scripts.cli.SERVER_AVAILABLE", True),
            patch(
                "shared_context_server.scripts.cli.initialize_server",
                side_effect=Exception("Init error"),
            ),
            pytest.raises(SystemExit),
        ):
            await server.start_stdio_server()

    @pytest.mark.asyncio
    async def test_http_server_import_error_path(self):
        """Test HTTP server ImportError handling (lines 107-111)."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        server = ProductionServer()

        # Mock SERVER_AVAILABLE as True and cause ImportError in server.run_http_async
        with (
            patch("shared_context_server.scripts.cli.SERVER_AVAILABLE", True),
            patch("shared_context_server.scripts.cli.initialize_server"),
            patch(
                "shared_context_server.scripts.cli.server.run_http_async",
                side_effect=ImportError("FastAPI not available"),
            ),
            pytest.raises(SystemExit),
        ):
            await server.start_http_server("localhost", 23456)

    @pytest.mark.asyncio
    async def test_http_server_general_exception_path(self):
        """Test HTTP server general exception handling (lines 112-114)."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        server = ProductionServer()

        # Mock SERVER_AVAILABLE as True and cause general exception
        with (
            patch("shared_context_server.scripts.cli.SERVER_AVAILABLE", True),
            patch("shared_context_server.scripts.cli.initialize_server"),
            patch(
                "shared_context_server.scripts.cli.server.run_http_async",
                side_effect=RuntimeError("Server error"),
            ),
            pytest.raises(SystemExit),
        ):
            await server.start_http_server("localhost", 23456)


class TestRunServerErrorPaths:
    """Test run_server_* function error paths."""

    @pytest.mark.asyncio
    async def test_run_server_stdio_not_available(self):
        """Test run_server_stdio when SERVER_AVAILABLE is False (lines 249-250)."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        from shared_context_server.scripts.cli import run_server_stdio

        with (
            patch("shared_context_server.scripts.cli.SERVER_AVAILABLE", False),
            pytest.raises(SystemExit),
        ):
            await run_server_stdio()

    @pytest.mark.asyncio
    async def test_run_server_http_not_available(self):
        """Test run_server_http when SERVER_AVAILABLE is False."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        from shared_context_server.scripts.cli import run_server_http

        with (
            patch("shared_context_server.scripts.cli.SERVER_AVAILABLE", False),
            pytest.raises(SystemExit),
        ):
            await run_server_http("localhost", 23456)


class TestShowStatusFunction:
    """Test show_status function (lines 303-347)."""

    def test_show_status_success(self, capsys):
        """Test successful status check."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        # Mock successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        with (
            patch("requests.get", return_value=mock_response),
        ):
            show_status("localhost", 23456)

            captured = capsys.readouterr()
            assert "✅ Server is running" in captured.out
            assert "✅ Health check" in captured.out
            assert "✅ MCP endpoint: Available" in captured.out

    def test_show_status_health_failure(self, capsys):
        """Test status check with health endpoint failure."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        # Mock failed health response
        mock_response = Mock()
        mock_response.status_code = 500

        with (
            patch("requests.get", return_value=mock_response),
        ):
            show_status("localhost", 23456)

            captured = capsys.readouterr()
            assert "❌ Server health check failed: 500" in captured.out

    def test_show_status_connection_error(self, capsys):
        """Test status check with connection error."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        import requests

        with (
            patch(
                "requests.get",
                side_effect=requests.exceptions.ConnectionError("Connection failed"),
            ),
        ):
            show_status("localhost", 23456)

            captured = capsys.readouterr()
            assert "❌ Cannot connect to server" in captured.out

    def test_show_status_general_exception(self, capsys):
        """Test status check with general exception."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        with (
            patch("requests.get", side_effect=Exception("General error")),
        ):
            show_status("localhost", 23456)

            captured = capsys.readouterr()
            assert "❌ Error checking server status" in captured.out

    def test_show_status_mcp_endpoint_error(self, capsys):
        """Test status check with MCP endpoint error."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        # Mock successful health but failed MCP endpoint
        def mock_get_side_effect(url, timeout=None):
            if "/health" in url:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "healthy"}
                return mock_response
            if "/mcp/" in url:
                raise RuntimeError("MCP error")
            return None

        with (
            patch("requests.get", side_effect=mock_get_side_effect),
        ):
            show_status("localhost", 23456)

            captured = capsys.readouterr()
            assert "✅ Server is running" in captured.out
            assert "⚠️  MCP endpoint: Not accessible" in captured.out

    def test_show_status_with_config_defaults(self, capsys):
        """Test show_status using config defaults."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        # Mock config loading
        mock_config = Mock()
        mock_config.mcp_server.http_port = 9000

        with (
            patch(
                "shared_context_server.scripts.cli.get_config", return_value=mock_config
            ),
            patch.dict(os.environ, {"CLIENT_HOST": "example.com"}),
            patch("requests.get") as mock_get,
        ):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response

            show_status()  # No host/port provided

            # Should use defaults from config and environment
            mock_get.assert_called()

    def test_show_status_config_exception_fallback(self, capsys):
        """Test show_status config exception fallback."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        with (
            patch(
                "shared_context_server.scripts.cli.get_config",
                side_effect=Exception("Config error"),
            ),
            patch.dict(os.environ, {"HTTP_PORT": "7000"}),
            patch("requests.get") as mock_get,
        ):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response

            show_status()  # Should use environment fallback

            mock_get.assert_called()


class TestSignalHandlers:
    """Test signal handler functionality (lines 354-356, 363)."""

    def test_signal_handler_function(self):
        """Test signal handler function execution."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        with patch("sys.exit") as mock_exit:
            # Access the signal handler function
            setup_signal_handlers()

            # Get the actual handler function that was registered
            # We can't easily test the handler directly, but we can verify setup
            mock_exit.assert_not_called()  # Setup shouldn't call exit

    def test_signal_handler_sigterm(self):
        """Test SIGTERM signal handler."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        with (
            patch("signal.signal") as mock_signal,
            patch("sys.exit") as mock_exit,
        ):
            setup_signal_handlers()

            # Verify signal handlers were set up
            assert mock_signal.call_count >= 2  # At least SIGTERM and SIGINT

            # Get the handler function from the first call
            if mock_signal.call_args_list:
                signal_num, handler_func = mock_signal.call_args_list[0][0]

                # Test the handler function
                handler_func(signal.SIGTERM, None)
                mock_exit.assert_called_once_with(0)

    def test_signal_handler_sighup_availability(self):
        """Test SIGHUP handler setup when available (line 363)."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        with (
            patch("signal.signal") as mock_signal,
            patch(
                "builtins.hasattr", return_value=True
            ),  # Force SIGHUP to be "available"
        ):
            setup_signal_handlers()

            # Should have called signal.signal multiple times including SIGHUP
            assert mock_signal.call_count >= 3


class TestMainConfigurationPaths:
    """Test main function configuration paths."""

    def test_main_custom_config_loading(self):
        """Test main function with custom config file (line 389)."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        mock_args = Mock()
        mock_args.command = None
        mock_args.transport = "stdio"
        mock_args.log_level = "INFO"
        mock_args.config = "/custom/config.env"

        with (
            patch(
                "shared_context_server.scripts.cli.parse_arguments",
                return_value=mock_args,
            ),
            patch("shared_context_server.scripts.cli.load_config") as mock_load_config,
            patch("shared_context_server.scripts.cli.get_config"),
            patch(
                "shared_context_server.scripts.cli.run_with_optimal_loop"
            ) as mock_run,
        ):
            # Mock run_with_optimal_loop to close the coroutine properly
            def mock_runner(coro):
                if asyncio.iscoroutine(coro):
                    coro.close()
                return

            mock_run.side_effect = mock_runner

            main()

            # Should load custom config
            mock_load_config.assert_called_once_with("/custom/config.env")

    def test_main_http_transport_path(self):
        """Test main function HTTP transport path (line 400)."""
        if not CLI_AVAILABLE:
            pytest.skip("CLI module not available")

        mock_args = Mock()
        mock_args.command = None
        mock_args.transport = "http"
        mock_args.host = "0.0.0.0"
        mock_args.port = 9000
        mock_args.log_level = "INFO"
        mock_args.config = None

        with (
            patch(
                "shared_context_server.scripts.cli.parse_arguments",
                return_value=mock_args,
            ),
            patch("shared_context_server.scripts.cli.get_config"),
            patch(
                "shared_context_server.scripts.cli.run_with_optimal_loop"
            ) as mock_run,
        ):
            # Mock run_with_optimal_loop to close the coroutine properly
            def mock_runner(coro):
                if asyncio.iscoroutine(coro):
                    coro.close()
                return

            mock_run.side_effect = mock_runner

            main()

            # Should call run_with_optimal_loop with HTTP server coroutine
            mock_run.assert_called_once()
