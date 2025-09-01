"""
Test setup core utility functions for 70% coverage breakthrough.

Targets key utility functions in setup_core.py to achieve the final 0.65 percentage points
needed to reach 70% total coverage through strategic utility function testing.
"""

import base64
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.shared_context_server.setup_core import (
    _extract_container_names,
    _extract_volume_names,
    _raise_docker_error,
    export_keys,
    generate_keys,
    has_sensitive_keys,
    is_shared_context_repo,
)


class TestSetupCoreUtilities:
    """Test setup core utility functions for coverage breakthrough."""

    def test_raise_docker_error_with_different_codes(self):
        """Test _raise_docker_error raises correct exception with return code."""
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            _raise_docker_error(1)

        assert exc_info.value.returncode == 1
        # The exact message format may vary, but it should be a CalledProcessError

        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            _raise_docker_error(127)

        assert exc_info.value.returncode == 127
        # Focus on the behavior (correct exception type and return code) not exact message

    def test_extract_container_names_basic(self):
        """Test extracting container names from docker-compose content."""
        compose_content = """
version: '3.8'
services:
  web:
    image: nginx
    container_name: my-web-server
  db:
    image: postgres
    container_name: "my-database"
  cache:
    image: redis
    container_name: 'my-cache'
"""

        names = _extract_container_names(compose_content)

        assert len(names) == 3
        assert "my-web-server" in names
        assert "my-database" in names
        assert "my-cache" in names

    def test_extract_container_names_empty_content(self):
        """Test extracting container names from empty content."""
        names = _extract_container_names("")
        assert names == []

        names = _extract_container_names(
            "version: '3.8'\nservices:\n  web:\n    image: nginx"
        )
        assert names == []

    def test_extract_container_names_mixed_formats(self):
        """Test extracting container names with various formatting."""
        compose_content = """
services:
  app:
    container_name: simple-name
  api:
    container_name:  "spaced-name"
  worker:
    container_name:    'quoted-name'
  monitor:
    container_name: hyphen-and_underscore
"""

        names = _extract_container_names(compose_content)

        assert len(names) == 4
        assert "simple-name" in names
        assert "spaced-name" in names
        assert "quoted-name" in names
        assert "hyphen-and_underscore" in names

    def test_extract_volume_names_simple_section(self):
        """Test extracting volume names from docker-compose volumes section."""
        compose_content = """
version: '3.8'
services:
  app:
    image: nginx
volumes:
  postgres_data:
  redis_cache:
  app_logs:
"""

        names = _extract_volume_names(compose_content)

        assert len(names) == 3
        assert "postgres_data" in names
        assert "redis_cache" in names
        assert "app_logs" in names

    def test_extract_volume_names_no_volumes_section(self):
        """Test extracting volume names when no volumes section exists."""
        compose_content = """
version: '3.8'
services:
  app:
    image: nginx
"""

        names = _extract_volume_names(compose_content)
        assert names == []

    def test_extract_volume_names_empty_volumes_section(self):
        """Test extracting volume names from empty volumes section."""
        compose_content = """
version: '3.8'
services:
  app:
    image: nginx
volumes:
"""

        names = _extract_volume_names(compose_content)
        assert names == []

    def test_extract_volume_names_with_configurations(self):
        """Test extracting volume names with volume configurations."""
        compose_content = """
volumes:
  postgres_data:
    driver: local
  redis_cache:
    external: true
  app_logs:
    driver_opts:
      type: none
networks:
  default:
    name: mynet
"""

        names = _extract_volume_names(compose_content)

        assert len(names) == 3
        assert "postgres_data" in names
        assert "redis_cache" in names
        assert "app_logs" in names


class TestKeyGenerationUtilities:
    """Test key generation and validation utilities."""

    def test_generate_keys_returns_all_required_keys(self):
        """Test that generate_keys returns all required keys."""
        with patch("src.shared_context_server.setup_core.print_color"):
            keys = generate_keys()

            assert "API_KEY" in keys
            assert "JWT_SECRET_KEY" in keys
            assert "JWT_ENCRYPTION_KEY" in keys

            # Verify all keys are non-empty strings
            for key_value in keys.values():
                assert isinstance(key_value, str)
                assert len(key_value) > 0

    def test_generate_keys_creates_secure_keys(self):
        """Test that generated keys meet security requirements."""
        with patch("src.shared_context_server.setup_core.print_color"):
            keys = generate_keys()

            # API_KEY and JWT_SECRET_KEY should be base64 encoded (32 bytes = 44 chars base64)
            api_key = keys["API_KEY"]
            jwt_secret = keys["JWT_SECRET_KEY"]

            # Test they're valid base64
            assert len(base64.b64decode(api_key)) == 32
            assert len(base64.b64decode(jwt_secret)) == 32

            # JWT_ENCRYPTION_KEY should be a Fernet key (44 chars base64)
            jwt_encryption = keys["JWT_ENCRYPTION_KEY"]
            assert len(jwt_encryption) >= 40  # Fernet keys are 44 chars

    def test_generate_keys_produces_unique_values(self):
        """Test that generate_keys produces unique values across calls."""
        with patch("src.shared_context_server.setup_core.print_color"):
            keys1 = generate_keys()
            keys2 = generate_keys()

            # All keys should be different between calls
            assert keys1["API_KEY"] != keys2["API_KEY"]
            assert keys1["JWT_SECRET_KEY"] != keys2["JWT_SECRET_KEY"]
            assert keys1["JWT_ENCRYPTION_KEY"] != keys2["JWT_ENCRYPTION_KEY"]

    def test_export_keys_json_format(self):
        """Test exporting keys in JSON format."""
        test_keys = {
            "API_KEY": "test-api-key",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "JWT_ENCRYPTION_KEY": "test-jwt-encryption",
        }

        with patch("builtins.print") as mock_print:
            export_keys(test_keys, "json")

            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]

            # Should be valid JSON containing our keys
            import json

            parsed = json.loads(call_args)
            assert parsed["API_KEY"] == "test-api-key"
            assert parsed["JWT_SECRET_KEY"] == "test-jwt-secret"
            assert parsed["JWT_ENCRYPTION_KEY"] == "test-jwt-encryption"

    def test_export_keys_export_format(self):
        """Test exporting keys in shell export format."""
        test_keys = {"API_KEY": "test-api-key", "JWT_SECRET_KEY": "test-jwt-secret"}

        with patch("builtins.print") as mock_print:
            export_keys(test_keys, "export")

            # Should call print twice (once per key)
            assert mock_print.call_count == 2

            # Check the format of the calls
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert "export API_KEY='test-api-key'" in calls
            assert "export JWT_SECRET_KEY='test-jwt-secret'" in calls

    def test_export_keys_docker_env_format(self):
        """Test exporting keys in Docker environment format."""
        test_keys = {"API_KEY": "test-api-key", "JWT_SECRET_KEY": "test-jwt-secret"}

        with patch("builtins.print") as mock_print:
            export_keys(test_keys, "docker-env")

            # Should call print twice (once per key)
            assert mock_print.call_count == 2

            # Check the format of the calls
            calls = [call[0][0] for call in mock_print.call_args_list]
            assert "-e API_KEY='test-api-key' \\" in calls
            assert "-e JWT_SECRET_KEY='test-jwt-secret' \\" in calls

    def test_export_keys_yaml_format_with_pyyaml(self):
        """Test exporting keys in YAML format when PyYAML is available."""
        test_keys = {"API_KEY": "test-key"}

        # Mock successful yaml import and dump
        mock_yaml = Mock()
        mock_yaml.dump.return_value = "API_KEY: test-key\n"

        with (
            patch.dict("sys.modules", {"yaml": mock_yaml}),
            patch("builtins.print") as mock_print,
        ):
            export_keys(test_keys, "yaml")

            mock_yaml.dump.assert_called_once_with(test_keys, default_flow_style=False)
            mock_print.assert_called_once_with("API_KEY: test-key\n")

    def test_export_keys_yaml_format_without_pyyaml(self):
        """Test exporting keys in YAML format when PyYAML is not available."""
        test_keys = {"API_KEY": "test-key"}

        # Simulate ImportError when importing yaml
        # Important: Patch print before patching __import__ to avoid
        # Python 3.10 resolving 'builtins' via the patched importer.
        with (
            patch("builtins.print") as mock_print,
            patch(
                "builtins.__import__", side_effect=ImportError("No module named 'yaml'")
            ),
        ):
            export_keys(test_keys, "yaml")

            mock_print.assert_called_once_with(
                "❌ PyYAML not installed. Install with: pip install pyyaml"
            )


class TestFileValidationUtilities:
    """Test file validation utility functions."""

    def test_has_sensitive_keys_file_not_exists(self):
        """Test has_sensitive_keys returns False for non-existent files."""
        non_existent_path = Path("/tmp/does-not-exist-test-file")

        result = has_sensitive_keys(non_existent_path)
        assert result is False

    def test_has_sensitive_keys_with_sensitive_content(self):
        """Test has_sensitive_keys detects sensitive keys in file content."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".env"
        ) as tmp_file:
            tmp_file.write("API_KEY=actual-secret-key\nJWT_SECRET_KEY=another-secret\n")
            tmp_file.flush()

            temp_path = Path(tmp_file.name)

            try:
                result = has_sensitive_keys(temp_path)
                assert result is True
            finally:
                temp_path.unlink()

    def test_has_sensitive_keys_with_placeholder_content(self):
        """Test has_sensitive_keys ignores placeholder values."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".env"
        ) as tmp_file:
            tmp_file.write(
                "API_KEY=your-api-key-here\nJWT_SECRET_KEY=replace-with-secret\n"
            )
            tmp_file.flush()

            temp_path = Path(tmp_file.name)

            try:
                result = has_sensitive_keys(temp_path)
                assert result is False
            finally:
                temp_path.unlink()

    def test_has_sensitive_keys_with_no_sensitive_content(self):
        """Test has_sensitive_keys returns False for files without sensitive content."""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as tmp_file:
            tmp_file.write("SOME_CONFIG=value\nDEBUG=true\nHOST=localhost\n")
            tmp_file.flush()

            temp_path = Path(tmp_file.name)

            try:
                result = has_sensitive_keys(temp_path)
                assert result is False
            finally:
                temp_path.unlink()

    def test_has_sensitive_keys_handles_read_errors(self):
        """Test has_sensitive_keys handles file read errors gracefully."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)

        # File exists but simulate read error by mocking read_text
        with patch.object(
            Path, "read_text", side_effect=PermissionError("Access denied")
        ):
            result = has_sensitive_keys(temp_path)
            assert result is False

        # Clean up
        temp_path.unlink()


class TestRepositoryDetectionUtilities:
    """Test repository detection utility functions."""

    def test_is_shared_context_repo_with_correct_pyproject(self):
        """Test is_shared_context_repo detects correct repository via pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pyproject_file = temp_dir / "pyproject.toml"

            pyproject_content = """[build-system]
requires = ["hatchling"]

[project]
name = "shared-context-server"
version = "1.0.0"
"""
            pyproject_file.write_text(pyproject_content)

            # Change to temp directory for test
            import os

            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                result = is_shared_context_repo()
                assert result is True
            finally:
                os.chdir(original_cwd)

    def test_is_shared_context_repo_with_wrong_pyproject(self):
        """Test is_shared_context_repo returns False for different project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pyproject_file = temp_dir / "pyproject.toml"

            pyproject_content = """[project]
name = "some-other-project"
version = "1.0.0"
"""
            pyproject_file.write_text(pyproject_content)

            # Change to temp directory for test
            import os

            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                result = is_shared_context_repo()
                assert result is False
            finally:
                os.chdir(original_cwd)

    def test_is_shared_context_repo_no_pyproject(self):
        """Test is_shared_context_repo fallback behavior without pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory with no pyproject.toml
            import os

            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                result = is_shared_context_repo()
                assert result is False
            finally:
                os.chdir(original_cwd)
