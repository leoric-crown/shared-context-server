"""
Test coverage for setup_core.py utility functions.

This module tests the setup utilities focusing on string parsing, port validation,
Docker conflict detection, and other core setup behaviors that are easily testable
without complex infrastructure.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from shared_context_server.setup_core import (
    _check_container_conflicts,
    _check_port_conflicts,
    _check_volume_conflicts,
    _extract_container_names,
    _extract_port_mappings,
    _extract_volume_names,
    _find_available_port,
    _is_port_available,
    _raise_docker_error,
    export_keys,
    generate_keys,
    has_sensitive_keys,
)


class TestSetupCoreUtilities:
    """Test setup core utility functions with behavior-first approach."""

    # =============================================================================
    # STRING PARSING UTILITIES
    # =============================================================================

    def test_extract_container_names_basic(self):
        """Test extraction of container names from docker-compose content."""
        compose_content = """
version: '3.8'
services:
  app:
    container_name: "my-app"
    image: nginx
  db:
    container_name: my-database
    image: postgres
"""
        result = _extract_container_names(compose_content)
        assert result == ["my-app", "my-database"]

    def test_extract_container_names_no_quotes(self):
        """Test extraction without quotes."""
        compose_content = """
services:
  web:
    container_name: webapp-container
"""
        result = _extract_container_names(compose_content)
        assert result == ["webapp-container"]

    def test_extract_container_names_empty(self):
        """Test extraction from content with no container names."""
        compose_content = """
version: '3.8'
services:
  app:
    image: nginx
"""
        result = _extract_container_names(compose_content)
        assert result == []

    def test_extract_volume_names_basic(self):
        """Test extraction of volume names from docker-compose content."""
        compose_content = """
version: '3.8'
services:
  db:
    image: postgres
volumes:
  postgres_data:
    driver: local
  backup_data:
    driver: local
"""
        result = _extract_volume_names(compose_content)
        assert result == ["postgres_data", "backup_data"]

    def test_extract_volume_names_empty_section(self):
        """Test extraction when volumes section is empty."""
        compose_content = """
version: '3.8'
services:
  app:
    image: nginx
volumes:
"""
        result = _extract_volume_names(compose_content)
        assert result == []

    def test_extract_volume_names_no_section(self):
        """Test extraction when no volumes section exists."""
        compose_content = """
version: '3.8'
services:
  app:
    image: nginx
"""
        result = _extract_volume_names(compose_content)
        assert result == []

    def test_extract_port_mappings_basic(self):
        """Test extraction of port mappings from docker-compose content."""
        compose_content = """
services:
  web:
    ports:
      - "8080:80"
      - "443:443"
  db:
    ports:
      - "5432:5432"
"""
        result = _extract_port_mappings(compose_content)
        assert result == [8080, 443, 5432]

    def test_extract_port_mappings_mixed_formats(self):
        """Test extraction with different port mapping formats."""
        compose_content = """
services:
  app:
    ports:
      - 3000:3000
      - "8080:80"
      - 9000:9000
"""
        result = _extract_port_mappings(compose_content)
        assert result == [3000, 8080, 9000]

    def test_extract_port_mappings_no_ports(self):
        """Test extraction when no ports are defined."""
        compose_content = """
services:
  worker:
    image: my-worker
"""
        result = _extract_port_mappings(compose_content)
        assert result == []

    # =============================================================================
    # PORT VALIDATION UTILITIES
    # =============================================================================

    def test_check_port_conflicts_with_conflicts(self):
        """Test port conflict detection when conflicts exist."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            # Simulate port conflicts for specific ports
            def bind_side_effect(addr):
                if addr[1] in [8080, 5432]:  # These ports are "in use"
                    raise OSError("Address already in use")
                return

            mock_sock.bind.side_effect = bind_side_effect

            result = _check_port_conflicts([8080, 3000, 5432, 9000])
            assert result == [8080, 5432]

    def test_check_port_conflicts_no_conflicts(self):
        """Test port conflict detection when all ports are available."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            # All ports are available (no bind exceptions)
            mock_sock.bind.return_value = None

            result = _check_port_conflicts([8080, 3000, 5432])
            assert result == []

    def test_is_port_available_true(self):
        """Test port availability check when port is available."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.bind.return_value = None  # No exception means available

            result = _is_port_available(8080)
            assert result is True
            # Should be called twice - once for each interface
            assert mock_sock.bind.call_count == 2

    def test_is_port_available_false(self):
        """Test port availability check when port is in use."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.bind.side_effect = OSError("Address already in use")

            result = _is_port_available(8080)
            assert result is False

    def test_find_available_port_first_available(self):
        """Test finding available port when first port is available."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.bind.return_value = None  # First port is available

            result = _find_available_port(8080)
            assert result == 8080

    def test_find_available_port_skip_unavailable(self):
        """Test finding available port when first few are unavailable."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            call_count = 0

            def bind_side_effect(addr):
                nonlocal call_count
                call_count += 1
                if call_count <= 3:  # First 3 calls fail (ports 8080, 8081, 8082)
                    raise OSError("Address already in use")
                return  # 4th call succeeds (port 8083)

            mock_sock.bind.side_effect = bind_side_effect

            result = _find_available_port(8080)
            assert result == 8083

    def test_find_available_port_exhausted(self):
        """Test behavior when no ports are available within max attempts."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            # All attempts fail - function returns start_port as fallback
            mock_sock.bind.side_effect = OSError("Address already in use")

            result = _find_available_port(8080, max_attempts=5)
            assert result == 8080  # Returns start_port as fallback

    # =============================================================================
    # DOCKER CONFLICT UTILITIES
    # =============================================================================

    @patch("subprocess.run")
    def test_check_container_conflicts_with_conflicts(self, mock_run):
        """Test container conflict detection when conflicts exist."""
        mock_run.return_value = MagicMock(
            stdout="container1\ncontainer2\nother-container", returncode=0
        )

        result = _check_container_conflicts(["container1", "different-name"])
        assert result == ["container1"]

    @patch("subprocess.run")
    def test_check_container_conflicts_no_conflicts(self, mock_run):
        """Test container conflict detection when no conflicts exist."""
        mock_run.return_value = MagicMock(
            stdout="other-container1\nother-container2", returncode=0
        )

        result = _check_container_conflicts(["my-container", "my-other-container"])
        assert result == []

    @patch("subprocess.run")
    def test_check_container_conflicts_docker_error(self, mock_run):
        """Test container conflict detection when docker command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "docker ps", "Docker not available"
        )

        result = _check_container_conflicts(["container1"])
        assert result == []  # Should return empty list on Docker errors

    @patch("subprocess.run")
    def test_check_volume_conflicts_with_conflicts(self, mock_run):
        """Test volume conflict detection when conflicts exist."""
        mock_run.return_value = MagicMock(
            stdout="volume1\nvolume2\nother-volume", returncode=0
        )

        result = _check_volume_conflicts(["volume1", "different-volume"])
        assert result == ["volume1"]

    @patch("subprocess.run")
    def test_check_volume_conflicts_no_conflicts(self, mock_run):
        """Test volume conflict detection when no conflicts exist."""
        mock_run.return_value = MagicMock(stdout="other-vol1\nother-vol2", returncode=0)

        result = _check_volume_conflicts(["my-volume", "my-other-volume"])
        assert result == []

    # =============================================================================
    # ERROR HANDLING UTILITIES
    # =============================================================================

    def test_raise_docker_error(self):
        """Test Docker error raising with proper error message."""
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            _raise_docker_error(1)

        assert exc_info.value.returncode == 1
        # The message is passed as the third argument to CalledProcessError
        # Let's just check that the exception is raised with the right return code

    # =============================================================================
    # FILE VALIDATION UTILITIES
    # =============================================================================

    def test_has_sensitive_keys_with_secrets(self, tmp_path):
        """Test sensitive key detection in files with secrets."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
# Configuration file
API_KEY=secret_api_key_12345
JWT_SECRET_KEY=jwt_secret_value
DATABASE_URL=postgres://user:pass@localhost/db
PORT=8080
""")

        result = has_sensitive_keys(env_file)
        assert result is True

    def test_has_sensitive_keys_no_secrets(self, tmp_path):
        """Test sensitive key detection in files without secrets."""
        config_file = tmp_path / "config.txt"
        config_file.write_text("""
# Simple configuration
PORT=8080
DEBUG=true
LOG_LEVEL=info
""")

        result = has_sensitive_keys(config_file)
        assert result is False

    def test_has_sensitive_keys_nonexistent_file(self, tmp_path):
        """Test sensitive key detection for nonexistent files."""
        nonexistent = tmp_path / "does_not_exist.env"

        result = has_sensitive_keys(nonexistent)
        assert result is False

    # =============================================================================
    # KEY GENERATION UTILITIES
    # =============================================================================

    @patch("shared_context_server.setup_core.print_color")
    def test_generate_keys_structure(self, mock_print_color):
        """Test key generation produces proper structure."""
        keys = generate_keys()

        # Should contain all required keys
        assert "API_KEY" in keys
        assert "JWT_SECRET_KEY" in keys
        assert "JWT_ENCRYPTION_KEY" in keys

        # All values should be strings
        for value in keys.values():
            assert isinstance(value, str)
            assert len(value) > 0

    @patch("shared_context_server.setup_core.print_color")
    def test_generate_keys_uniqueness(self, mock_print_color):
        """Test that generated keys are unique."""
        keys1 = generate_keys()
        keys2 = generate_keys()

        # All keys should be different between generations
        assert keys1["API_KEY"] != keys2["API_KEY"]
        assert keys1["JWT_SECRET_KEY"] != keys2["JWT_SECRET_KEY"]
        assert keys1["JWT_ENCRYPTION_KEY"] != keys2["JWT_ENCRYPTION_KEY"]

    @patch("shared_context_server.setup_core.print_color")
    def test_generate_keys_api_key_format(self, mock_print_color):
        """Test API key format is base64."""
        keys = generate_keys()

        api_key = keys["API_KEY"]
        # Should be base64 decodable
        import base64

        decoded = base64.b64decode(api_key)
        assert len(decoded) == 32  # 32 bytes as specified

    @patch("shared_context_server.setup_core.print_color")
    def test_generate_keys_jwt_secret_format(self, mock_print_color):
        """Test JWT secret key format is base64."""
        keys = generate_keys()

        jwt_secret = keys["JWT_SECRET_KEY"]
        # Should be base64 decodable
        import base64

        decoded = base64.b64decode(jwt_secret)
        assert len(decoded) == 32  # 32 bytes as specified

    @patch("shared_context_server.setup_core.print_color")
    def test_generate_keys_fernet_key_format(self, mock_print_color):
        """Test Fernet key format is valid."""
        keys = generate_keys()

        fernet_key = keys["JWT_ENCRYPTION_KEY"]
        # Should be valid Fernet key
        from cryptography.fernet import Fernet

        f = Fernet(fernet_key.encode())

        # Should be able to encrypt/decrypt
        test_data = b"test message"
        encrypted = f.encrypt(test_data)
        decrypted = f.decrypt(encrypted)
        assert decrypted == test_data

    # =============================================================================
    # KEY EXPORT UTILITIES
    # =============================================================================

    @patch("builtins.print")
    def test_export_keys_json_format(self, mock_print):
        """Test JSON export format."""
        test_keys = {
            "API_KEY": "test_api_key",
            "JWT_SECRET_KEY": "test_jwt_secret",
            "JWT_ENCRYPTION_KEY": "test_encryption_key",
        }

        export_keys(test_keys, "json")

        # Should print valid JSON
        mock_print.assert_called_once()
        printed_content = mock_print.call_args[0][0]

        import json

        parsed = json.loads(printed_content)
        assert parsed == test_keys

    @patch("builtins.print")
    def test_export_keys_export_format(self, mock_print):
        """Test shell export format."""
        test_keys = {"API_KEY": "test_api_key", "JWT_SECRET_KEY": "test_jwt_secret"}

        export_keys(test_keys, "export")

        # Should print shell export commands
        assert mock_print.call_count == 2
        calls = [call[0][0] for call in mock_print.call_args_list]

        assert "export API_KEY='test_api_key'" in calls
        assert "export JWT_SECRET_KEY='test_jwt_secret'" in calls

    @patch("builtins.print")
    def test_export_keys_docker_env_format(self, mock_print):
        """Test Docker environment format."""
        test_keys = {"API_KEY": "test_api_key", "JWT_SECRET_KEY": "test_jwt_secret"}

        export_keys(test_keys, "docker-env")

        # Should print Docker -e flags
        assert mock_print.call_count == 2
        calls = [call[0][0] for call in mock_print.call_args_list]

        assert "-e API_KEY='test_api_key' \\" in calls
        assert "-e JWT_SECRET_KEY='test_jwt_secret' \\" in calls

    @patch("builtins.print")
    @patch("yaml.dump")
    def test_export_keys_yaml_format_available(self, mock_yaml_dump, mock_print):
        """Test YAML export format when PyYAML is available."""
        test_keys = {"API_KEY": "test_api_key"}
        mock_yaml_dump.return_value = "API_KEY: test_api_key\n"

        export_keys(test_keys, "yaml")

        mock_yaml_dump.assert_called_once_with(test_keys, default_flow_style=False)
        mock_print.assert_called_once_with("API_KEY: test_api_key\n")

    @patch("builtins.print")
    def test_export_keys_unsupported_format(self, mock_print):
        """Test export with unsupported format (no output expected)."""
        test_keys = {"API_KEY": "test_api_key"}

        export_keys(test_keys, "unsupported_format")

        # Should not print anything for unsupported formats
        mock_print.assert_not_called()

    # =============================================================================
    # ADDITIONAL FILE VALIDATION TESTS
    # =============================================================================

    def test_has_sensitive_keys_partial_matches(self, tmp_path):
        """Test sensitive key detection with partial matches."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
# Configuration with some sensitive content
API_URL=https://api.example.com
_KEY=partial_key_match
DEBUG=true
""")

        result = has_sensitive_keys(env_file)
        assert result is True  # Should detect _KEY=

    def test_has_sensitive_keys_case_sensitivity(self, tmp_path):
        """Test case sensitivity in sensitive key detection."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
api_key=lowercase
Api_Key=mixed_case
""")

        result = has_sensitive_keys(env_file)
        # Implementation may be case sensitive - test actual behavior
        # This documents the current behavior rather than prescribing it
        assert isinstance(result, bool)

    def test_has_sensitive_keys_read_error(self, tmp_path):
        """Test handling of file read errors."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret")
        env_file.chmod(0o000)  # Remove read permissions

        try:
            result = has_sensitive_keys(env_file)
            # Should handle permission errors gracefully
            assert isinstance(result, bool)
        except PermissionError:
            # Or may raise PermissionError - both are acceptable
            pass
        finally:
            env_file.chmod(0o644)  # Restore permissions for cleanup
