"""
Tests for datetime conversion functions in database.py module.

These tests target the uncovered datetime handling functions to improve coverage.
"""

import sqlite3
from datetime import datetime, timezone

import pytest

from src.shared_context_server.database import adapt_datetime_iso, convert_datetime


class TestDatetimeConversion:
    """Test datetime conversion and adaptation functions."""

    def test_adapt_datetime_iso(self):
        """Test datetime adaptation to ISO format."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = adapt_datetime_iso(dt)
        assert result == "2025-01-15T10:30:00+00:00"

    def test_adapt_datetime_iso_naive(self):
        """Test datetime adaptation for naive datetime."""
        dt = datetime(2025, 1, 15, 10, 30, 0)
        result = adapt_datetime_iso(dt)
        assert result == "2025-01-15T10:30:00"

    def test_convert_datetime_unix_timestamp(self):
        """Test conversion from Unix timestamp bytes."""
        timestamp_bytes = b"1642234200.123"
        result = convert_datetime(timestamp_bytes)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_convert_datetime_iso_format(self):
        """Test conversion from ISO format bytes."""
        iso_bytes = b"2025-01-15T10:30:00+00:00"
        result = convert_datetime(iso_bytes)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    def test_convert_datetime_z_suffix(self):
        """Test conversion from ISO format with Z suffix."""
        iso_bytes = b"2025-01-15T10:30:00Z"
        result = convert_datetime(iso_bytes)
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_convert_datetime_invalid_format(self):
        """Test conversion with invalid format raises ValueError."""
        invalid_bytes = b"invalid-datetime-format"
        with pytest.raises(ValueError):
            convert_datetime(invalid_bytes)

    def test_convert_datetime_invalid_unix_timestamp(self):
        """Test conversion with invalid Unix timestamp falls back to ISO."""
        # This will fail float conversion but succeed ISO conversion
        iso_bytes = b"2025-01-15T10:30:00"
        result = convert_datetime(iso_bytes)
        assert isinstance(result, datetime)

    def test_sqlite_adapter_registration(self):
        """Test that adapters are properly registered with sqlite3."""
        # Test that our adapters are registered
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        # Create in-memory database to test adapter
        conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()

        # Create test table
        cursor.execute("CREATE TABLE test (dt DATETIME)")

        # Insert datetime - this will use our adapter
        cursor.execute("INSERT INTO test (dt) VALUES (?)", (dt,))

        # Retrieve datetime - this will use our converter
        cursor.execute("SELECT dt FROM test")
        result = cursor.fetchone()[0]

        assert isinstance(result, datetime)
        conn.close()
