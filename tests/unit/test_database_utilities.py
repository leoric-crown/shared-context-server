"""
Test coverage for database.py utility functions.

This module tests the database utility functions focusing on validation logic,
timestamp handling, error raising, and other core database behaviors that are
easily testable without complex database infrastructure.
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from shared_context_server.database import (
    _is_testing_environment,
    _raise_basic_query_error,
    _raise_journal_mode_check_error,
    _raise_no_schema_version_error,
    _raise_table_not_found_error,
    _raise_wal_mode_error,
    parse_utc_timestamp,
    utc_now,
    utc_timestamp,
    validate_json_string,
    validate_session_id,
)
from shared_context_server.database_manager import DatabaseError, DatabaseSchemaError


class TestDatabaseUtilities:
    """Test database utility functions with behavior-first approach."""

    # =============================================================================
    # TIMESTAMP UTILITIES
    # =============================================================================

    def test_utc_now(self):
        """Test UTC datetime generation."""
        result = utc_now()

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        # Should be close to current time (within a few seconds)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 5

    def test_utc_timestamp(self):
        """Test UTC timestamp string generation."""
        result = utc_timestamp()

        assert isinstance(result, str)
        # Should be in ISO format with timezone
        assert "T" in result
        assert result.endswith("+00:00") or result.endswith("Z")

        # Should be parseable back to datetime
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert parsed.tzinfo == timezone.utc

    def test_parse_utc_timestamp_string(self):
        """Test parsing UTC timestamp from ISO string."""
        test_timestamp = "2023-12-25T10:30:45+00:00"

        result = parse_utc_timestamp(test_timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45

    def test_parse_utc_timestamp_z_format(self):
        """Test parsing UTC timestamp with Z suffix."""
        test_timestamp = "2023-12-25T10:30:45Z"

        result = parse_utc_timestamp(test_timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2023

    def test_parse_utc_timestamp_datetime_object(self):
        """Test parsing UTC timestamp from datetime object."""
        test_datetime = datetime(2023, 12, 25, 10, 30, 45, tzinfo=timezone.utc)

        result = parse_utc_timestamp(test_datetime)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result == test_datetime

    def test_parse_utc_timestamp_naive_datetime(self):
        """Test parsing naive datetime (assumes UTC)."""
        test_datetime = datetime(2023, 12, 25, 10, 30, 45)  # No timezone

        result = parse_utc_timestamp(test_datetime)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 12

    def test_parse_utc_timestamp_invalid_string(self):
        """Test parsing invalid timestamp string raises ValueError."""
        with pytest.raises(ValueError):
            parse_utc_timestamp("invalid-timestamp")

    def test_parse_utc_timestamp_empty_string(self):
        """Test parsing empty timestamp string raises ValueError."""
        with pytest.raises(ValueError):
            parse_utc_timestamp("")

    # =============================================================================
    # VALIDATION UTILITIES
    # =============================================================================

    def test_validate_session_id_valid(self):
        """Test session ID validation with valid IDs."""
        valid_ids = [
            "session_1234567890abcdef",  # 16 hex chars
            "session_0123456789abcdef",  # 16 hex chars
            "session_fedcba0987654321",  # 16 hex chars
        ]

        for session_id in valid_ids:
            result = validate_session_id(session_id)
            assert result is True, f"Failed for valid ID: {session_id}"

    def test_validate_session_id_invalid(self):
        """Test session ID validation with invalid IDs."""
        invalid_ids = [
            "",  # Empty
            "session_123",  # Too short (not 16 hex chars)
            "session_1234567890abcdefg",  # Too long (17 chars)
            "session_1234567890abcde",  # Too short (15 chars)
            "session_1234567890ABCDEF",  # Uppercase hex
            "session_123456789gabcdef",  # Non-hex character 'g'
            "session_123456789-abcdef",  # Contains dash
            "other_prefix_123456789abc",  # Wrong prefix
            "session_",  # Missing hex part
            "1234567890abcdef",  # Missing session_ prefix
        ]

        for session_id in invalid_ids:
            result = validate_session_id(session_id)
            assert result is False, f"Should be invalid but passed: {session_id}"

    def test_validate_json_string_valid(self):
        """Test JSON string validation with valid JSON."""
        valid_json = [
            '{"key": "value"}',
            "[]",
            "{}",
            "[1, 2, 3]",
            '{"nested": {"key": "value"}, "array": [1, 2]}',
            '"simple string"',
            "null",
            "true",
            "false",
            "123",
        ]

        for json_str in valid_json:
            result = validate_json_string(json_str)
            assert result is True, f"Failed for valid JSON: {json_str}"

    def test_validate_json_string_invalid(self):
        """Test JSON string validation with invalid JSON."""
        invalid_json = [
            "{invalid json}",  # Missing quotes
            '{"key": value}',  # Unquoted value
            "{'key': 'value'}",  # Single quotes
            '{"key": "value",}',  # Trailing comma
            "[1, 2, 3,]",  # Trailing comma in array
            '{"unclosed": "object"',  # Unclosed brace
            "undefined",  # Undefined keyword
            '{key: "value"}',  # Unquoted key
        ]

        for json_str in invalid_json:
            result = validate_json_string(json_str)
            assert result is False, f"Should be invalid but passed: {json_str}"

    def test_validate_json_string_empty_allowed(self):
        """Test that empty string is valid per implementation."""
        result = validate_json_string("")
        assert result is True  # Empty is valid per implementation

    def test_validate_json_string_none_input(self):
        """Test JSON validation with None input."""
        result = validate_json_string(None)
        assert result is True  # None/empty is valid per implementation

    # =============================================================================
    # ENVIRONMENT DETECTION
    # =============================================================================

    @patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"})
    def test_is_testing_environment_pytest(self):
        """Test testing environment detection with pytest."""
        result = _is_testing_environment()
        assert result is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.modules")
    def test_is_testing_environment_pytest_in_modules(self, mock_modules):
        """Test testing environment detection when pytest is in sys.modules."""
        mock_modules.__contains__.return_value = True  # pytest in modules

        result = _is_testing_environment()
        assert result is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("sys.modules")
    def test_is_testing_environment_false(self, mock_modules):
        """Test testing environment detection when not testing."""
        mock_modules.__contains__.return_value = False  # pytest not in modules

        result = _is_testing_environment()
        assert result is False

    # =============================================================================
    # ERROR RAISING UTILITIES
    # =============================================================================

    def test_raise_basic_query_error(self):
        """Test basic query error raising."""
        with pytest.raises(DatabaseError, match="Basic query failed"):
            _raise_basic_query_error()

    def test_raise_wal_mode_error(self):
        """Test WAL mode error raising."""
        with pytest.raises(DatabaseSchemaError) as exc_info:
            _raise_wal_mode_error("TRUNCATE")

        assert "Expected WAL mode, got TRUNCATE" in str(exc_info.value)

    def test_raise_journal_mode_check_error(self):
        """Test journal mode check error raising."""
        with pytest.raises(DatabaseSchemaError) as exc_info:
            _raise_journal_mode_check_error("DELETE")

        assert "Journal mode check failed: DELETE" in str(exc_info.value)

    def test_raise_table_not_found_error(self):
        """Test table not found error raising."""
        with pytest.raises(DatabaseSchemaError) as exc_info:
            _raise_table_not_found_error("users")

        assert "Required table 'users' not found" in str(exc_info.value)

    def test_raise_no_schema_version_error(self):
        """Test no schema version error raising."""
        with pytest.raises(DatabaseSchemaError, match="No schema version found"):
            _raise_no_schema_version_error()

    # =============================================================================
    # EDGE CASES AND ROBUSTNESS
    # =============================================================================

    def test_timestamp_consistency(self):
        """Test that repeated timestamp calls are consistent."""
        timestamp1 = utc_timestamp()
        timestamp2 = utc_timestamp()

        # Parse both to compare
        dt1 = parse_utc_timestamp(timestamp1)
        dt2 = parse_utc_timestamp(timestamp2)

        # Should be within a few milliseconds
        time_diff = abs((dt2 - dt1).total_seconds())
        assert time_diff < 1  # Less than 1 second apart

    def test_validate_json_complex_structure(self):
        """Test JSON validation with complex nested structures."""
        complex_json = {
            "users": [
                {"id": 1, "name": "John", "active": True},
                {"id": 2, "name": "Jane", "active": False},
            ],
            "metadata": {
                "version": "1.0",
                "timestamp": "2023-12-25T10:30:45Z",
                "config": {"debug": True, "features": ["auth", "logging", "metrics"]},
            },
        }

        json_str = json.dumps(complex_json)
        result = validate_json_string(json_str)
        assert result is True

    def test_session_id_boundary_conditions(self):
        """Test session ID validation at boundary conditions."""
        # Exactly 16 hex chars (valid)
        assert validate_session_id("session_1234567890abcdef") is True

        # 15 hex chars (too short)
        assert validate_session_id("session_1234567890abcde") is False

        # 17 hex chars (too long)
        assert validate_session_id("session_1234567890abcdef0") is False

        # Mixed case (invalid)
        assert validate_session_id("session_1234567890ABCDEF") is False
