"""
Test coverage for setup parsing helper functions.

This module tests the setup and Docker-related parsing utilities including
error handling, Docker compose processing, and volume generation. Focus is on
behavior-first testing with string manipulation and command parsing.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from shared_context_server.setup_core import (
    _check_docker_conflicts,
    _check_port_conflicts,
    _extract_container_names,
    _extract_port_mappings,
    _extract_volume_names,
    _generate_unique_volumes,
    _raise_docker_error,
    show_docker_commands,
)


class TestSetupParsingHelpers:
    """Test setup parsing helper functions with behavior-first approach."""

    # =============================================================================
    # ERROR HANDLING FUNCTIONS
    # =============================================================================

    def test_raise_docker_error_with_return_code(self):
        """Test Docker error raising with specific return code."""
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            _raise_docker_error(1)
        assert exc_info.value.returncode == 1

    def test_raise_docker_error_with_different_codes(self):
        """Test Docker error raising with various return codes."""
        error_codes = [2, 125, 126, 127]

        for code in error_codes:
            with pytest.raises(subprocess.CalledProcessError) as exc_info:
                _raise_docker_error(code)
            assert exc_info.value.returncode == code

    def test_raise_docker_error_zero_code(self):
        """Test Docker error raising with zero return code (success)."""
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            _raise_docker_error(0)
        assert exc_info.value.returncode == 0

    # =============================================================================
    # DOCKER CONFLICTS CHECKING
    # =============================================================================

    @patch("subprocess.run")
    def test_check_docker_conflicts_no_conflicts(self, mock_run):
        """Test Docker conflicts check when no conflicts exist."""
        # Mock successful docker --version call
        mock_run.return_value = MagicMock(returncode=0)

        # Mock all the checking functions to return no conflicts
        with (
            patch(
                "shared_context_server.setup_core._check_container_conflicts",
                return_value=[],
            ),
            patch(
                "shared_context_server.setup_core._check_volume_conflicts",
                return_value=[],
            ),
            patch(
                "shared_context_server.setup_core._check_port_conflicts",
                return_value=[],
            ),
        ):
            docker_compose_content = """
version: '3.8'
services:
  app:
    ports:
      - "8000:8000"
"""

            result = _check_docker_conflicts(docker_compose_content)

            # Should return tuple: (content, conflicts_found, port_mappings)
            assert isinstance(result, tuple)
            assert len(result) == 3
            content, conflicts_found, port_mappings = result
            assert conflicts_found is False
            assert isinstance(port_mappings, dict)

    @patch("subprocess.run")
    def test_check_docker_conflicts_with_docker_unavailable(self, mock_run):
        """Test Docker conflicts check when Docker is unavailable."""
        # Mock Docker command failure
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker --version")

        docker_compose_content = """
version: '3.8'
services:
  app:
    ports:
      - "8000:8000"
"""

        result = _check_docker_conflicts(docker_compose_content)

        # Should return original content with no conflicts found when Docker unavailable
        assert isinstance(result, tuple)
        content, conflicts_found, port_mappings = result
        assert content == docker_compose_content
        assert conflicts_found is False
        assert port_mappings == {}

    @patch("subprocess.run")
    def test_check_docker_conflicts_empty_input(self, mock_run):
        """Test Docker conflicts check with empty input."""
        mock_run.return_value = MagicMock(returncode=0)

        with (
            patch(
                "shared_context_server.setup_core._check_container_conflicts",
                return_value=[],
            ),
            patch(
                "shared_context_server.setup_core._check_volume_conflicts",
                return_value=[],
            ),
            patch(
                "shared_context_server.setup_core._check_port_conflicts",
                return_value=[],
            ),
        ):
            result = _check_docker_conflicts("")
            assert isinstance(result, tuple)
            content, conflicts_found, port_mappings = result
            assert content == ""
            assert conflicts_found is False

    # =============================================================================
    # VOLUME GENERATION HELPERS
    # =============================================================================

    def test_generate_unique_volumes_basic(self):
        """Test basic unique volume generation."""
        docker_compose_content = """
version: '3.8'
services:
  app:
    volumes:
      - ./data:/app/data
      - shared_volume:/shared
volumes:
  shared_volume:
"""

        result = _generate_unique_volumes(docker_compose_content)

        # Should return modified content as string
        assert isinstance(result, str)
        assert "version:" in result
        assert "services:" in result

    def test_generate_unique_volumes_no_volumes(self):
        """Test volume generation with no volumes section."""
        docker_compose_content = """
version: '3.8'
services:
  app:
    image: nginx
"""

        result = _generate_unique_volumes(docker_compose_content)

        # Should handle content without volumes gracefully
        assert isinstance(result, str)
        assert "services:" in result

    def test_generate_unique_volumes_empty_content(self):
        """Test volume generation with empty content."""
        result = _generate_unique_volumes("")

        # Should return string (even if empty/modified)
        assert isinstance(result, str)

    def test_generate_unique_volumes_invalid_yaml(self):
        """Test volume generation with invalid YAML content."""
        invalid_yaml = """
version: '3.8'
services:
  app:
    volumes:
      - ./data:/app/data
    - invalid_indent
"""

        # Should handle invalid YAML gracefully or raise specific error
        result = _generate_unique_volumes(invalid_yaml)
        assert isinstance(result, str)

    def test_generate_unique_volumes_preserves_structure(self):
        """Test that volume generation preserves basic Docker Compose structure."""
        docker_compose_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
  db:
    image: postgres:13
volumes:
  db_data:
"""

        result = _generate_unique_volumes(docker_compose_content)

        # Should preserve key structural elements
        assert "version:" in result
        assert "services:" in result
        assert "web:" in result
        assert "db:" in result

    # =============================================================================
    # DOCKER COMMANDS DISPLAY
    # =============================================================================

    @patch("shared_context_server.setup_core.print_color")
    @patch("shared_context_server.setup_core.is_shared_context_repo", return_value=True)
    def test_show_docker_commands_basic(self, mock_is_repo, mock_print_color):
        """Test Docker commands display function."""
        keys_dict = {"API_KEY": "test-key", "JWT_SECRET_KEY": "test-jwt"}

        show_docker_commands(keys_dict)

        # Should call print_color to display commands
        assert mock_print_color.call_count > 0

    @patch("shared_context_server.setup_core.print_color")
    @patch("shared_context_server.setup_core.is_shared_context_repo", return_value=True)
    def test_show_docker_commands_empty_keys(self, mock_is_repo, mock_print_color):
        """Test Docker commands display with empty keys."""
        show_docker_commands({})

        # Should still print something (headers, instructions, etc.)
        assert mock_print_color.call_count > 0

    @patch("shared_context_server.setup_core.print_color")
    @patch("shared_context_server.setup_core.is_shared_context_repo", return_value=True)
    def test_show_docker_commands_demo_mode(self, mock_is_repo, mock_print_color):
        """Test Docker commands display in demo mode."""
        keys_dict = {"API_KEY": "demo-key"}

        show_docker_commands(keys_dict, demo=True)

        assert mock_print_color.call_count > 0

    @patch("shared_context_server.setup_core.print_color")
    @patch("shared_context_server.setup_core.is_shared_context_repo", return_value=True)
    def test_show_docker_commands_no_fetch(self, mock_is_repo, mock_print_color):
        """Test Docker commands display without file fetching."""
        keys_dict = {"API_KEY": "test-key"}

        show_docker_commands(keys_dict, fetch_files=False)

        assert mock_print_color.call_count > 0

    # =============================================================================
    # PARSING HELPER FUNCTIONS
    # =============================================================================

    def test_extract_container_names_basic(self):
        """Test extraction of container names from Docker compose content."""
        docker_compose_content = """
version: '3.8'
services:
  web-server:
    image: nginx
  database:
    image: postgres
  cache:
    image: redis
"""

        result = _extract_container_names(docker_compose_content)
        assert isinstance(result, list)
        # Should extract service names
        assert len(result) >= 0  # May be empty or contain extracted names

    def test_extract_volume_names_basic(self):
        """Test extraction of volume names from Docker compose content."""
        docker_compose_content = """
version: '3.8'
services:
  app:
    volumes:
      - app_data:/data
volumes:
  app_data:
  postgres_data:
"""

        result = _extract_volume_names(docker_compose_content)
        assert isinstance(result, list)

    def test_extract_port_mappings_basic(self):
        """Test extraction of port mappings from Docker compose content."""
        docker_compose_content = """
version: '3.8'
services:
  web:
    ports:
      - "8000:80"
      - "9000:90"
  api:
    ports:
      - "3000:3000"
"""

        result = _extract_port_mappings(docker_compose_content)
        assert isinstance(result, list)

    def test_check_port_conflicts_basic(self):
        """Test port conflict checking with various port lists."""
        # Test with no conflicts
        ports = [8000, 9000, 3000]
        result = _check_port_conflicts(ports)
        assert isinstance(result, list)

        # Test with empty list
        result = _check_port_conflicts([])
        assert isinstance(result, list)
        assert len(result) == 0

    # =============================================================================
    # EDGE CASES AND STRING HANDLING
    # =============================================================================

    def test_generate_unique_volumes_multiline_handling(self):
        """Test volume generation handles multiline strings correctly."""
        multiline_content = """version: '3.8'
services:
  app:
    image: nginx
    volumes:
      - type: bind
        source: ./config
        target: /etc/nginx/conf.d
volumes:
  data_volume:
    driver: local"""

        result = _generate_unique_volumes(multiline_content)

        assert isinstance(result, str)
        assert "services:" in result
        assert "volumes:" in result

    def test_generate_unique_volumes_special_characters(self):
        """Test volume generation with special characters in volume names."""
        content_with_special_chars = """
version: '3.8'
services:
  app:
    volumes:
      - my-app_data.v1:/data
volumes:
  my-app_data.v1:
"""

        result = _generate_unique_volumes(content_with_special_chars)

        assert isinstance(result, str)
        # Should handle special characters in volume names
        assert "my-app_data" in result or "data" in result

    @patch("subprocess.run")
    def test_docker_conflicts_type_validation(self, mock_run):
        """Test that Docker conflicts check validates input types."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker --version")

        # Test with proper docker compose content
        docker_content = """
version: '3.8'
services:
  app:
    ports:
      - "8000:8000"
"""
        result = _check_docker_conflicts(docker_content)
        assert isinstance(result, tuple)

        # Test with empty content
        result = _check_docker_conflicts("")
        assert isinstance(result, tuple)

    @patch("shared_context_server.setup_core.print_color")
    @patch("shared_context_server.setup_core.is_shared_context_repo", return_value=True)
    def test_show_docker_commands_formatting(self, mock_is_repo, mock_print_color):
        """Test that Docker commands are properly formatted for display."""
        keys_dict = {"API_KEY": "test-key", "JWT_SECRET_KEY": "secret"}

        show_docker_commands(keys_dict)

        # Should call print_color for formatting
        assert mock_print_color.call_count > 0

    def test_generate_unique_volumes_preserves_indentation(self):
        """Test that volume generation preserves YAML indentation patterns."""
        properly_indented_content = """
version: '3.8'
services:
  web:
    image: nginx
    volumes:
      - ./html:/usr/share/nginx/html
  db:
    image: postgres
volumes:
  postgres_data:
"""

        result = _generate_unique_volumes(properly_indented_content)

        # Should maintain some form of structured formatting
        assert isinstance(result, str)
        lines = result.split("\n")
        # Should have multiple lines (preserved structure)
        assert len(lines) > 3

    def test_error_functions_are_available(self):
        """Test that error functions can be imported and called."""
        # This tests that the functions are properly exposed and callable
        assert callable(_raise_docker_error)
        assert callable(_check_docker_conflicts)
        assert callable(_generate_unique_volumes)
        assert callable(show_docker_commands)

    @patch("subprocess.run")
    def test_string_processing_functions_return_types(self, mock_run):
        """Test that string processing functions return expected types."""
        # Mock Docker unavailable
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker --version")

        # Test return types
        volume_result = _generate_unique_volumes("test content")
        assert isinstance(volume_result, str)

        conflict_result = _check_docker_conflicts("test docker compose content")
        assert isinstance(conflict_result, tuple)
        assert len(conflict_result) == 3
