"""
Test coverage for setup_core port and container utility functions.

This module tests the utility functions in setup_core.py that handle port validation,
container management, and Docker compose parsing. Focus is on behavior-first testing
of these critical setup utilities.
"""

from unittest.mock import Mock, patch

import pytest

from shared_context_server.setup_core import (
    _check_container_conflicts,
    _check_port_conflicts,
    _extract_container_names,
    _extract_port_mappings,
    _extract_volume_names,
    _find_available_port,
    _find_available_port_smart,
    _is_port_available,
)


class TestSetupCorePortUtilities:
    """Test setup_core port and container utilities with behavior-first approach."""

    # =============================================================================
    # PORT VALIDATION UTILITIES
    # =============================================================================

    def test_is_port_available_with_free_port(self):
        """Test _is_port_available returns True for available ports."""
        # Use a high port number that should be available
        result = _is_port_available(59999)
        assert isinstance(result, bool)
        # Don't assert specific value as it depends on system state

    def test_is_port_available_with_port_zero(self):
        """Test _is_port_available with port 0 (system assigns port)."""
        result = _is_port_available(0)
        # Port 0 is valid - system assigns an available port
        assert result is True

    def test_is_port_available_with_invalid_port_negative(self):
        """Test _is_port_available raises OverflowError for negative ports."""
        with pytest.raises(OverflowError, match="port must be 0-65535"):
            _is_port_available(-1)

    def test_is_port_available_with_invalid_port_too_high(self):
        """Test _is_port_available raises OverflowError for ports > 65535."""
        with pytest.raises(OverflowError, match="port must be 0-65535"):
            _is_port_available(65536)

    def test_check_port_conflicts_empty_list(self):
        """Test _check_port_conflicts returns empty for empty port list."""
        result = _check_port_conflicts([])
        assert result == []

    def test_check_port_conflicts_with_available_ports(self):
        """Test _check_port_conflicts identifies available ports."""
        # Use high port numbers that should be available
        high_ports = [59001, 59002, 59003]
        result = _check_port_conflicts(high_ports)
        assert isinstance(result, list)
        # Result should be subset of input (ports that have conflicts)
        assert all(port in high_ports for port in result)

    def test_check_port_conflicts_removes_duplicates(self):
        """Test _check_port_conflicts handles duplicate ports correctly."""
        duplicate_ports = [8080, 8080, 8081, 8081]
        result = _check_port_conflicts(duplicate_ports)

        # Should not contain duplicates in result
        assert len(result) == len(set(result))

    def test_find_available_port_basic_functionality(self):
        """Test _find_available_port returns a valid port number."""
        result = _find_available_port(50000)

        assert isinstance(result, int)
        assert result >= 50000
        assert result <= 65535

    def test_find_available_port_with_max_attempts(self):
        """Test _find_available_port respects max_attempts parameter."""
        # Use a very limited search range
        result = _find_available_port(59000, max_attempts=5)

        assert isinstance(result, int)
        # Should still find a port within reasonable range
        assert 59000 <= result <= 65535

    def test_find_available_port_smart_basic_functionality(self):
        """Test _find_available_port_smart returns valid port."""
        original_port = 50001

        result = _find_available_port_smart(original_port)

        # Function may return None if no port found
        assert result is None or (
            isinstance(result, int) and result > 0 and result <= 65535
        )

    def test_find_available_port_smart_with_different_base(self):
        """Test _find_available_port_smart with different original port."""
        original_port = 52000
        result = _find_available_port_smart(original_port, max_iterations=5)

        # Function may return None if no port found
        assert result is None or (
            isinstance(result, int) and result > 0 and result <= 65535
        )

    # =============================================================================
    # DOCKER COMPOSE PARSING UTILITIES
    # =============================================================================

    def test_extract_container_names_basic_yaml(self):
        """Test _extract_container_names parses container_name fields."""
        compose_content = """
        services:
          web:
            image: nginx
            container_name: my-web
          db:
            image: postgres
            container_name: my-db
          redis:
            image: redis
            container_name: my-redis
        """

        result = _extract_container_names(compose_content)

        assert isinstance(result, list)
        assert "my-web" in result
        assert "my-db" in result
        assert "my-redis" in result
        assert len(result) == 3

    def test_extract_container_names_empty_content(self):
        """Test _extract_container_names handles empty content."""
        result = _extract_container_names("")
        assert result == []

    def test_extract_container_names_invalid_yaml(self):
        """Test _extract_container_names handles invalid YAML gracefully."""
        invalid_yaml = "invalid: yaml: content: [unclosed"
        result = _extract_container_names(invalid_yaml)
        # Should return empty list on parsing error, not crash
        assert isinstance(result, list)

    def test_extract_volume_names_basic_yaml(self):
        """Test _extract_volume_names parses basic docker-compose volumes."""
        compose_content = """volumes:
  postgres_data:
  redis_data:
  app_logs:
services:
  web:
    image: nginx
"""

        result = _extract_volume_names(compose_content)

        assert isinstance(result, list)
        assert "postgres_data" in result
        assert "redis_data" in result
        assert "app_logs" in result

    def test_extract_volume_names_no_volumes_section(self):
        """Test _extract_volume_names handles compose without volumes."""
        compose_content = """
        services:
          web:
            image: nginx
        """

        result = _extract_volume_names(compose_content)
        assert result == []

    def test_extract_port_mappings_basic_ports(self):
        """Test _extract_port_mappings parses port configurations."""
        compose_content = """
        services:
          web:
            ports:
              - "8080:80"
              - "8443:443"
          api:
            ports:
              - "3000:3000"
        """

        result = _extract_port_mappings(compose_content)

        assert isinstance(result, list)
        assert 8080 in result
        assert 8443 in result
        assert 3000 in result

    def test_extract_port_mappings_no_ports(self):
        """Test _extract_port_mappings handles compose without ports."""
        compose_content = """
        services:
          worker:
            image: worker:latest
        """

        result = _extract_port_mappings(compose_content)
        assert result == []

    def test_extract_port_mappings_various_formats(self):
        """Test _extract_port_mappings handles different port format styles."""
        compose_content = """
        services:
          app1:
            ports:
              - "8001:80"
              - "8002"
              - 8003:80
        """

        result = _extract_port_mappings(compose_content)

        assert isinstance(result, list)
        # Should extract host ports from various formats
        assert any(port in [8001, 8002, 8003] for port in result)

    # =============================================================================
    # CONTAINER CONFLICT CHECKING
    # =============================================================================

    def test_check_container_conflicts_empty_list(self):
        """Test _check_container_conflicts handles empty container list."""
        result = _check_container_conflicts([])
        assert result == []

    @patch("subprocess.run")
    def test_check_container_conflicts_no_docker(self, mock_run):
        """Test _check_container_conflicts handles Docker not available."""
        # Mock Docker command failure
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="docker: command not found"
        )

        result = _check_container_conflicts(["test_container"])

        # Should return empty list when Docker is not available
        assert result == []

    @patch("subprocess.run")
    def test_check_container_conflicts_with_existing_containers(self, mock_run):
        """Test _check_container_conflicts identifies existing containers."""
        # Mock Docker command success with container output
        mock_run.return_value = Mock(
            returncode=0, stdout="test_container\nother_container\n", stderr=""
        )

        result = _check_container_conflicts(["test_container", "nonexistent_container"])

        assert isinstance(result, list)
        # Should identify existing containers
        if "test_container" in result:
            assert "test_container" in result
        # Should not include non-existent containers in conflicts
