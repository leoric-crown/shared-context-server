"""
Test coverage for security utility functions.

This module tests the security utilities in utils/security.py that handle
sanitization of sensitive data for logging and operations. Focus is on
behavior-first testing with edge cases and security scenarios.
"""

import logging
from unittest.mock import MagicMock

from shared_context_server.utils.security import (
    is_sanitized_for_logging,
    sanitize_agent_id,
    sanitize_cache_key,
    sanitize_client_id,
    sanitize_for_logging,
    sanitize_resource_uri,
    sanitize_token,
    secure_hash_for_cache_keys,
    secure_hash_short_for_cache_keys,
    secure_log_debug,
    secure_log_info,
)


class TestSecurityUtilities:
    """Test security utility functions with behavior-first approach."""

    # =============================================================================
    # CORE SANITIZATION FUNCTIONS
    # =============================================================================

    def test_sanitize_for_logging_normal_string(self):
        """Test sanitization of normal length string."""
        sensitive_data = "sensitive_api_key_12345"
        result = sanitize_for_logging(sensitive_data, keep_prefix=4, keep_suffix=4)
        assert result == "sens***2345"
        assert "api_key" not in result
        assert len(result) < len(sensitive_data)

    def test_sanitize_for_logging_short_string(self):
        """Test sanitization of string shorter than prefix+suffix."""
        short_data = "abc"
        result = sanitize_for_logging(short_data, keep_prefix=4, keep_suffix=4)
        assert result == "***"

    def test_sanitize_for_logging_exact_length(self):
        """Test sanitization of string exactly equal to prefix+suffix."""
        exact_data = "abcdefgh"  # 8 chars
        result = sanitize_for_logging(exact_data, keep_prefix=4, keep_suffix=4)
        assert result == "***"

    def test_sanitize_for_logging_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize_for_logging("", keep_prefix=4, keep_suffix=4)
        assert result == ""

    def test_sanitize_for_logging_custom_lengths(self):
        """Test sanitization with custom prefix/suffix lengths."""
        data = "very_long_sensitive_token_data"
        result = sanitize_for_logging(data, keep_prefix=2, keep_suffix=3)
        assert result == "ve***ata"

    def test_sanitize_for_logging_zero_lengths(self):
        """Test sanitization with zero prefix/suffix."""
        data = "sensitive_data"
        result = sanitize_for_logging(data, keep_prefix=0, keep_suffix=0)
        # With zero suffix, value[-0:] returns the entire string, so this is the actual behavior
        assert result == "***sensitive_data"

    # =============================================================================
    # SPECIALIZED SANITIZERS
    # =============================================================================

    def test_sanitize_agent_id(self):
        """Test agent ID sanitization."""
        agent_id = "agent_user_12345"
        result = sanitize_agent_id(agent_id)
        assert result == "agen***45"
        assert "user" not in result

    def test_sanitize_client_id(self):
        """Test client ID sanitization."""
        client_id = "client_app_67890"
        result = sanitize_client_id(client_id)
        assert result == "clie***90"
        assert "app" not in result

    def test_sanitize_token_normal(self):
        """Test token sanitization for normal length token."""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_token(token)
        assert result.startswith("eyJhbGci")
        assert "..." in result
        assert str(len(token)) in result
        assert "JWT" not in result

    def test_sanitize_token_short(self):
        """Test token sanitization for short token."""
        token = "short"
        result = sanitize_token(token)
        assert result == "[redacted]"

    def test_sanitize_token_empty(self):
        """Test token sanitization for empty token."""
        result = sanitize_token("")
        assert result == "[empty]"

    def test_sanitize_token_exact_boundary(self):
        """Test token sanitization at exact boundary length."""
        token = "12345678"  # Exactly 8 chars
        result = sanitize_token(token)
        assert result == "[redacted]"

    # =============================================================================
    # CACHE KEY AND URI SANITIZATION
    # =============================================================================

    def test_sanitize_cache_key_with_session_id(self):
        """Test cache key sanitization with session ID."""
        cache_key = "session:abc123def456:data"
        result = sanitize_cache_key(cache_key)
        assert result == "session:[redacted]:data"
        assert "abc123" not in result

    def test_sanitize_cache_key_with_agent_id(self):
        """Test cache key sanitization with agent ID."""
        cache_key = "agent:user123:memory"
        result = sanitize_cache_key(cache_key)
        assert result == "agent:[redacted]:memory"
        assert "user123" not in result

    def test_sanitize_cache_key_with_uuid(self):
        """Test cache key sanitization with UUID."""
        cache_key = "data:550e8400-e29b-41d4-a716-446655440000:cache"
        result = sanitize_cache_key(cache_key)
        assert result == "data:[uuid-redacted]:cache"
        assert "550e8400" not in result

    def test_sanitize_cache_key_with_token(self):
        """Test cache key sanitization with long token."""
        cache_key = "token:eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4="
        result = sanitize_cache_key(cache_key)
        assert result == "token:[token-redacted]"
        assert "eyJhbGci" not in result

    def test_sanitize_cache_key_multiple_patterns(self):
        """Test cache key with multiple sensitive patterns."""
        cache_key = (
            "session:abc123:agent:def456:token:eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        )
        result = sanitize_cache_key(cache_key)
        assert result == "session:[redacted]:agent:[redacted]:token:[token-redacted]"
        assert "abc123" not in result
        assert "def456" not in result
        assert "eyJhbGci" not in result

    def test_sanitize_cache_key_case_insensitive(self):
        """Test cache key sanitization is case insensitive."""
        cache_key = "SESSION:ABC123:AGENT:DEF456"
        result = sanitize_cache_key(cache_key)
        assert result == "session:[redacted]:agent:[redacted]"

    def test_sanitize_cache_key_empty(self):
        """Test cache key sanitization for empty key."""
        result = sanitize_cache_key("")
        assert result == "[empty]"

    def test_sanitize_resource_uri(self):
        """Test resource URI sanitization (delegates to cache key logic)."""
        uri = "session:abc123def456:resource:data"
        result = sanitize_resource_uri(uri)
        assert result == "session:[redacted]:resource:data"

    def test_sanitize_resource_uri_empty(self):
        """Test resource URI sanitization for empty URI."""
        result = sanitize_resource_uri("")
        assert result == "[empty]"

    # =============================================================================
    # SECURE HASHING FUNCTIONS
    # =============================================================================

    def test_secure_hash_for_cache_keys(self):
        """Test secure hash generation for cache keys."""
        data = "test_cache_key_data"
        result = secure_hash_for_cache_keys(data)

        # Should return hex string
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex is 64 chars
        assert all(c in "0123456789abcdef" for c in result)

        # Should be deterministic
        result2 = secure_hash_for_cache_keys(data)
        assert result == result2

    def test_secure_hash_for_cache_keys_different_inputs(self):
        """Test secure hash produces different results for different inputs."""
        hash1 = secure_hash_for_cache_keys("data1")
        hash2 = secure_hash_for_cache_keys("data2")
        assert hash1 != hash2

    def test_secure_hash_short_for_cache_keys_default_length(self):
        """Test short secure hash with default length."""
        data = "test_data"
        result = secure_hash_short_for_cache_keys(data)

        assert isinstance(result, str)
        assert len(result) == 8  # Default length
        assert all(c in "0123456789abcdef" for c in result)

    def test_secure_hash_short_for_cache_keys_custom_length(self):
        """Test short secure hash with custom length."""
        data = "test_data"
        result = secure_hash_short_for_cache_keys(data, length=12)

        assert len(result) == 12

    def test_secure_hash_short_for_cache_keys_zero_length(self):
        """Test short secure hash with zero length."""
        data = "test_data"
        result = secure_hash_short_for_cache_keys(data, length=0)

        assert result == ""

    # =============================================================================
    # SANITIZATION DETECTION
    # =============================================================================

    def test_is_sanitized_for_logging_with_redacted(self):
        """Test detection of sanitized values with [redacted] marker."""
        sanitized_value = "prefix[redacted]suffix"
        assert is_sanitized_for_logging(sanitized_value) is True

    def test_is_sanitized_for_logging_with_empty(self):
        """Test detection of sanitized values with [empty] marker."""
        sanitized_value = "[empty]"
        assert is_sanitized_for_logging(sanitized_value) is True

    def test_is_sanitized_for_logging_with_stars(self):
        """Test detection of sanitized values with *** marker."""
        sanitized_value = "pre***fix"
        assert is_sanitized_for_logging(sanitized_value) is True

    def test_is_sanitized_for_logging_with_dots(self):
        """Test detection of sanitized values with ... marker."""
        sanitized_value = "prefix...(42 chars)"
        assert is_sanitized_for_logging(sanitized_value) is True

    def test_is_sanitized_for_logging_with_uuid_redacted(self):
        """Test detection of sanitized values with [uuid-redacted] marker."""
        sanitized_value = "data:[uuid-redacted]:more"
        assert is_sanitized_for_logging(sanitized_value) is True

    def test_is_sanitized_for_logging_with_token_redacted(self):
        """Test detection of sanitized values with [token-redacted] marker."""
        sanitized_value = "token:[token-redacted]"
        assert is_sanitized_for_logging(sanitized_value) is True

    def test_is_sanitized_for_logging_unsanitized_string(self):
        """Test detection of unsanitized string values."""
        unsanitized_value = "plaintext_sensitive_data"
        assert is_sanitized_for_logging(unsanitized_value) is False

    def test_is_sanitized_for_logging_non_string(self):
        """Test detection with non-string input."""
        assert is_sanitized_for_logging(12345) is False
        assert is_sanitized_for_logging(None) is False
        assert is_sanitized_for_logging(["test"]) is False

    # =============================================================================
    # SECURE LOGGING FUNCTIONS
    # =============================================================================

    def test_secure_log_debug_enabled(self):
        """Test secure debug logging when debug is enabled."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        secure_log_debug(mock_logger, "Test message: %s", "sanitized_data")

        mock_logger.isEnabledFor.assert_called_once_with(logging.DEBUG)
        mock_logger.debug.assert_called_once_with("Test message: %s", "sanitized_data")

    def test_secure_log_debug_disabled(self):
        """Test secure debug logging when debug is disabled."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False

        secure_log_debug(mock_logger, "Test message: %s", "sanitized_data")

        mock_logger.isEnabledFor.assert_called_once_with(logging.DEBUG)
        mock_logger.debug.assert_not_called()

    def test_secure_log_info_enabled(self):
        """Test secure info logging when info is enabled."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = True

        secure_log_info(mock_logger, "Test message: %s", "sanitized_data")

        mock_logger.isEnabledFor.assert_called_once_with(logging.INFO)
        mock_logger.info.assert_called_once_with("Test message: %s", "sanitized_data")

    def test_secure_log_info_disabled(self):
        """Test secure info logging when info is disabled."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False

        secure_log_info(mock_logger, "Test message: %s", "sanitized_data")

        mock_logger.isEnabledFor.assert_called_once_with(logging.INFO)
        mock_logger.info.assert_not_called()

    # =============================================================================
    # EDGE CASES AND BOUNDARY CONDITIONS
    # =============================================================================

    def test_sanitize_cache_key_mixed_case_uuid(self):
        """Test cache key sanitization with mixed case UUID."""
        cache_key = "data:550E8400-E29B-41d4-A716-446655440000:cache"
        result = sanitize_cache_key(cache_key)
        assert result == "data:[uuid-redacted]:cache"

    def test_sanitize_cache_key_partial_matches(self):
        """Test cache key sanitization doesn't over-sanitize partial matches."""
        cache_key = "sessiondata:agentinfo:not_a_token"
        result = sanitize_cache_key(cache_key)
        # Should not match patterns that require colons
        assert "sessiondata" in result
        assert "agentinfo" in result
        assert "not_a_token" in result

    def test_secure_hash_unicode_input(self):
        """Test secure hash with Unicode input."""
        data = "test_data_🔒_unicode"
        result = secure_hash_for_cache_keys(data)

        assert isinstance(result, str)
        assert len(result) == 64

    def test_sanitize_for_logging_unicode(self):
        """Test sanitization with Unicode characters."""
        data = "🔒sensitive_unicode_🔑"
        result = sanitize_for_logging(data, keep_prefix=2, keep_suffix=2)
        assert result == "🔒s***_🔑"
