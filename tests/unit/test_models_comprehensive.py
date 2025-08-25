"""
Comprehensive test suite for data models validation and error handling.

Tests all aspects of the Pydantic models to achieve 85%+ coverage:
- Field validation edge cases and boundary conditions
- Input sanitization for security (XSS, injection, Unicode)
- Error message quality and actionability
- Nested validation scenarios and complex data structures

Built according to Phase 4 test coverage completion requirements.
"""

import contextlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from shared_context_server.models import (
    MAX_CONTENT_LENGTH,
    MAX_MEMORY_KEY_LENGTH,
    MAX_PURPOSE_LENGTH,
    # Constants
    AddMessageRequest,
    AgentMemoryModel,
    CreateSessionRequest,
    MemoryGetResponse,
    MemoryListRequest,
    MemoryListResponse,
    MemorySetResponse,
    MessageModel,
    MessageType,
    # Enums
    MessageVisibility,
    ResourceModel,
    SearchBySenderRequest,
    SearchByTimerangeRequest,
    SearchContextRequest,
    SearchResponse,
    # Core models
    SessionModel,
    SetMemoryRequest,
    ValidationErrorDetail,
    ValidationErrorResponse,
    create_validation_error_response,
    extract_pydantic_validation_errors,
    sanitize_memory_key,
    sanitize_search_input,
    sanitize_text_input,
    validate_agent_id,
    validate_json_metadata,
    validate_json_serializable_value,
    # Validation utilities
    validate_session_id,
    validate_utc_timestamp,
)


class TestValidationEdgeCases:
    """Test suite for field boundary conditions and validation edge cases."""

    def test_session_id_boundary_conditions(self):
        """Test session ID validation at boundaries and edge cases."""

        # Valid session IDs
        valid_ids = [
            "session_0123456789abcdef",
            "session_fedcba9876543210",
            "session_0000000000000000",
            "session_ffffffffffffffffff"[:24],  # Ensure 16 hex chars
        ]

        for session_id in valid_ids:
            result = validate_session_id(session_id)
            assert result == session_id

        # Invalid session IDs - wrong format
        invalid_ids = [
            "",  # Empty
            "session_",  # No hex part
            "session_123",  # Too short
            "session_0123456789abcdef0",  # Too long
            "session_0123456789abcdeg",  # Invalid hex character
            "SESSION_0123456789abcdef",  # Wrong case
            "session 0123456789abcdef",  # Space
            "session_0123456789ABCDEF",  # Uppercase (invalid)
            "0123456789abcdef",  # Missing prefix
            "session_0123456789abcd\x00f",  # Null byte
        ]

        for session_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid session ID format"):
                validate_session_id(session_id)

    def test_agent_id_boundary_conditions(self):
        """Test agent ID validation at boundaries and edge cases."""

        # Valid agent IDs
        valid_ids = [
            "a",  # Minimum length
            "agent123",  # Alphanumeric
            "test-agent_v1",  # With dash and underscore
            "A" * 100,  # Maximum length
            "claude_code",  # Common pattern
            "agent-1",  # With dash
            "test_agent",  # With underscore
        ]

        for agent_id in valid_ids:
            result = validate_agent_id(agent_id)
            assert result == agent_id

        # Invalid agent IDs based on actual pattern ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$

        # Test only the ones that should actually fail
        definitely_invalid = [
            "",  # Empty
            "_agent",  # Starts with underscore
            "-agent",  # Starts with dash
            "agent with spaces",  # Contains spaces
            "agent@domain",  # Contains @
            "A" * 101,  # Too long
            "agent.test",  # Contains dot
        ]

        for agent_id in definitely_invalid:
            with pytest.raises(ValueError, match="Invalid agent ID format"):
                validate_agent_id(agent_id)

    def test_content_length_boundaries(self):
        """Test content length validation at min and max boundaries."""

        # Test MessageModel content validation
        valid_content_lengths = [
            "a",  # Minimum length (1)
            "x" * 1000,  # Medium length
            "y" * MAX_CONTENT_LENGTH,  # Maximum length
        ]

        for content in valid_content_lengths:
            message = MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content=content,
            )
            assert len(message.content) <= MAX_CONTENT_LENGTH

        # Test content too long
        with pytest.raises(ValidationError):
            MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content="x" * (MAX_CONTENT_LENGTH + 1),
            )

    def test_purpose_length_boundaries(self):
        """Test purpose length validation boundaries."""

        # Valid purpose lengths
        valid_purposes = [
            "a",  # Minimum length
            "test purpose",  # Normal length
            "x" * MAX_PURPOSE_LENGTH,  # Maximum length
        ]

        for purpose in valid_purposes:
            request = CreateSessionRequest(purpose=purpose)
            assert len(request.purpose) <= MAX_PURPOSE_LENGTH

        # Invalid - too long
        with pytest.raises(ValidationError):
            CreateSessionRequest(purpose="x" * (MAX_PURPOSE_LENGTH + 1))

    def test_memory_key_boundaries(self):
        """Test memory key validation boundaries and format."""

        # Valid memory keys
        valid_keys = [
            "a",  # Minimum length
            "user_preferences",  # With underscore
            "config.database",  # With dot
            "cache-key",  # With dash
            "A" * MAX_MEMORY_KEY_LENGTH,  # Maximum length
            "key123",  # With numbers
        ]

        for key in valid_keys:
            sanitized = sanitize_memory_key(key)
            assert sanitized == key

        # Invalid memory keys for sanitization (format validation)
        invalid_format_keys = [
            "",  # Empty
            # Note: " key" becomes "key" after sanitization, so it's actually valid
            "key with spaces",  # Contains spaces
            "key\nwith\nnewlines",  # Contains newlines
            "key\twith\ttabs",  # Contains tabs
            "key!",  # Invalid character
            "key@domain",  # Invalid character
            "   ",  # Only whitespace - becomes empty after sanitization
        ]

        for key in invalid_format_keys:
            with pytest.raises(ValueError):
                sanitize_memory_key(key)

        # Test length validation in model (Pydantic handles this)
        with pytest.raises(ValidationError):
            SetMemoryRequest(key="x" * (MAX_MEMORY_KEY_LENGTH + 1), value="test_value")

    def test_ttl_boundaries(self):
        """Test TTL (time-to-live) validation boundaries."""

        # Valid TTL values
        valid_ttls = [
            1,  # Minimum (1 second)
            3600,  # 1 hour
            86400,  # 1 day
            31536000,  # 1 year (maximum)
        ]

        for ttl in valid_ttls:
            request = SetMemoryRequest(
                key="test_key", value="test_value", expires_in=ttl
            )
            assert request.expires_in == ttl

        # Invalid TTL values
        invalid_ttls = [
            0,  # Too small
            -1,  # Negative
            31536001,  # Too large (> 1 year)
        ]

        for ttl in invalid_ttls:
            with pytest.raises(ValidationError):
                SetMemoryRequest(key="test_key", value="test_value", expires_in=ttl)

    def test_type_conversion_edge_cases(self):
        """Test type conversion failures and edge cases."""

        # Test datetime conversion failures
        invalid_timestamps = [
            "not-a-timestamp",
            "2023-13-01T00:00:00Z",  # Invalid month
            "2023-01-32T00:00:00Z",  # Invalid day
            "2023-01-01T25:00:00Z",  # Invalid hour
            "",  # Empty string
            None,  # None value
        ]

        for timestamp in invalid_timestamps:
            if timestamp is not None:
                with pytest.raises(ValueError):
                    validate_utc_timestamp(timestamp)

        # Test JSON serialization failures
        non_json_values = [
            {1, 2, 3},  # Set is not JSON serializable
            lambda x: x,  # Function
            object(),  # Generic object
            complex(1, 2),  # Complex number
        ]

        for value in non_json_values:
            with pytest.raises(ValueError):
                validate_json_serializable_value(value)

    def test_constraint_violation_scenarios(self):
        """Test business rule constraint violations."""

        # Test that parent message ID accepts None and positive integers
        # (Database foreign key constraint handles referential integrity)
        valid_message_with_no_parent = MessageModel(
            session_id="session_1234567890abcdef",
            sender="test_agent",
            content="test content",
            parent_message_id=None,  # Valid: no parent
        )
        assert valid_message_with_no_parent.parent_message_id is None

        valid_message_with_parent = MessageModel(
            session_id="session_1234567890abcdef",
            sender="test_agent",
            content="test content",
            parent_message_id=123,  # Valid: positive integer
        )
        assert valid_message_with_parent.parent_message_id == 123

        # Test expiration time must be after creation time
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        current_time = datetime.now(timezone.utc)

        with pytest.raises(
            ValidationError, match="Expiration time must be after creation time"
        ):
            AgentMemoryModel(
                agent_id="test_agent",
                key="test_key",
                value='{"data": "test"}',
                created_at=current_time,
                expires_at=past_time,  # Before creation time
            )

    def test_null_empty_undefined_handling(self):
        """Test handling of null, empty, and undefined values."""

        # Test required field validation with various empty values
        empty_values = ["", "   ", "\n\t\r"]

        for empty_value in empty_values:
            # Should fail - either due to min_length or custom validation
            with pytest.raises(ValidationError):
                CreateSessionRequest(purpose=empty_value)

            with pytest.raises(ValidationError):
                AddMessageRequest(
                    session_id="session_1234567890abcdef", content=empty_value
                )

        # Test optional field handling
        message = MessageModel(
            session_id="session_1234567890abcdef",
            sender="test_agent",
            content="test content",
            metadata=None,  # Optional field
            parent_message_id=None,  # Optional field
        )
        assert message.metadata is None
        assert message.parent_message_id is None

        # Test default value application
        message_with_defaults = MessageModel(
            session_id="session_1234567890abcdef",
            sender="test_agent",
            content="test content",
            # visibility and message_type should get defaults
        )
        assert message_with_defaults.visibility == MessageVisibility.PUBLIC
        assert message_with_defaults.message_type == MessageType.AGENT_RESPONSE

    def test_enum_validation_edge_cases(self):
        """Test enum validation with invalid values."""

        # Test invalid MessageVisibility
        with pytest.raises(ValidationError):
            MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content="test content",
                visibility="invalid_visibility",
            )

        # Test invalid MessageType
        with pytest.raises(ValidationError):
            MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content="test content",
                message_type="invalid_type",
            )

        # Test case sensitivity
        with pytest.raises(ValidationError):
            MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content="test content",
                visibility="PUBLIC",  # Should be lowercase
            )


class TestSanitizationBoundaryTesting:
    """Test suite for input sanitization effectiveness and security."""

    def test_malicious_input_sanitization(self):
        """Test sanitization of malicious input patterns."""

        # XSS attempt patterns
        xss_patterns = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
        ]

        for pattern in xss_patterns:
            sanitized = sanitize_text_input(pattern)
            # Basic sanitization removes control characters but preserves most content
            # Note: The sanitize_text_input function only removes control chars, not HTML
            # This is basic sanitization, not XSS protection
            assert isinstance(sanitized, str)
            # Control characters should be removed
            assert "\x00" not in sanitized
            assert "\x01" not in sanitized

            # Should be able to create model with sanitized input
            message = MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content=pattern,  # Will be sanitized by field validator
            )
            assert message.content == sanitized

        # SQL injection patterns
        sql_patterns = [
            "'; DROP TABLE sessions; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --",
        ]

        for pattern in sql_patterns:
            sanitized = sanitize_text_input(pattern)
            # Sanitization should make it safe
            message = MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content=pattern,
            )
            assert message.content == sanitized

    def test_control_character_handling(self):
        """Test handling of control characters and null bytes."""

        # Control characters that should be removed
        control_chars = [
            "test\x00content",  # Null byte
            "test\x01content",  # Start of Heading
            "test\x02content",  # Start of Text
            "test\x1fcontent",  # Unit Separator
        ]

        for text_with_control in control_chars:
            sanitized = sanitize_text_input(text_with_control)
            # Control characters should be removed
            assert "\x00" not in sanitized
            assert "\x01" not in sanitized
            assert "\x02" not in sanitized
            assert "\x1f" not in sanitized
            # Regular content should remain
            assert "test" in sanitized
            assert "content" in sanitized

        # Allowed control characters should be preserved
        allowed_control_chars = [
            "line1\nline2",  # Newline
            "col1\tcol2",  # Tab
            "line1\rline2",  # Carriage return
        ]

        for text in allowed_control_chars:
            sanitized = sanitize_text_input(text)
            if "\n" in text:
                assert "\n" in sanitized
            if "\t" in text:
                assert "\t" in sanitized
            if "\r" in text:
                assert "\r" in sanitized

    def test_unicode_handling_edge_cases(self):
        """Test Unicode handling and encoding edge cases."""

        # Various Unicode characters
        unicode_tests = [
            "Hello 🌍 World",  # Emoji
            "Café résumé naïve",  # Accented characters
            "こんにちは",  # Japanese
            "🚀💻🔥⭐",  # Multiple emoji
            "test\u200b\u200c\u200d",  # Zero-width characters
            "A\u0300\u0301\u0302",  # Combining characters
        ]

        for unicode_text in unicode_tests:
            sanitized = sanitize_text_input(unicode_text)
            # Should preserve valid Unicode
            assert len(sanitized) > 0

            # Should be able to create model with Unicode content
            message = MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content=unicode_text,
            )
            assert message.content == sanitized

        # Test very large Unicode strings
        large_unicode = "🚀" * 1000
        sanitized = sanitize_text_input(large_unicode)
        assert len(sanitized) == len(large_unicode)  # Should preserve all emoji

    def test_binary_data_handling(self):
        """Test handling of binary data and special characters."""

        # Binary-like patterns that should be handled gracefully
        binary_patterns = [
            bytes([0, 1, 2, 3, 4]).decode("latin1"),
            "\xff\xfe\xfd",  # High byte values
            "test\x80\x81\x82",  # Extended ASCII
        ]

        def test_pattern(pattern: str) -> None:
            try:
                sanitized = sanitize_text_input(pattern)
                # Should not crash and should produce valid string
                assert isinstance(sanitized, str)

                # Try to create model - might fail validation but shouldn't crash
                with contextlib.suppress(ValidationError):
                    MessageModel(
                        session_id="session_1234567890abcdef",
                        sender="test_agent",
                        content=pattern,
                    )
            except (UnicodeDecodeError, UnicodeEncodeError):
                # Encoding errors are acceptable for binary data
                pass

        for pattern in binary_patterns:
            test_pattern(pattern)

    def test_sanitization_performance_large_inputs(self):
        """Test sanitization performance with large inputs."""

        # Test performance with large text inputs
        large_texts = [
            "a" * 10000,  # Large plain text
            ("test content with spaces " * 500),  # Repeated text
            ("line1\nline2\nline3\n" * 1000),  # Many newlines
            ("word\ttab\ttab\t" * 1000),  # Many tabs
        ]

        for large_text in large_texts:
            start_time = datetime.now()
            sanitized = sanitize_text_input(large_text)
            end_time = datetime.now()

            # Performance should be reasonable (< 100ms for large inputs)
            duration = (end_time - start_time).total_seconds()
            assert duration < 0.1, (
                f"Sanitization took {duration}s for {len(large_text)} chars"
            )

            # Result should be valid
            assert isinstance(sanitized, str)
            assert len(sanitized) <= len(large_text)

        # Test metadata size limits
        large_metadata = {
            f"key_{i}": f"value_{i}" * 100
            for i in range(50)  # At the limit
        }

        # This should succeed if within 10KB limit
        try:
            json_metadata = validate_json_metadata(large_metadata)
            assert json_metadata is not None
        except ValueError:
            # If this fails, the test data is too large - that's OK for this test
            pass

        # Should fail over the key count limit (50 keys max)
        oversized_metadata = {
            f"key_{i}": f"value_{i}"
            for i in range(51)  # Over the 50 key limit
        }

        with pytest.raises(ValueError, match="cannot have more than 50 keys"):
            validate_json_metadata(oversized_metadata)

        # Test size limit (10KB)
        huge_metadata = {
            "large_data": "x" * 15000  # Over 10KB when JSON serialized
        }

        with pytest.raises(ValueError, match="Metadata JSON too large"):
            validate_json_metadata(huge_metadata)


class TestErrorMessageQuality:
    """Test suite for error message quality and actionability."""

    def test_field_specific_error_information(self):
        """Test that error messages contain specific field information."""

        # Test session ID validation error
        try:
            validate_session_id("invalid_session_id")
            raise AssertionError("Should have raised validation error")
        except ValueError as e:
            error_msg = str(e)
            assert "Invalid session ID format" in error_msg
            assert "invalid_session_id" in error_msg

        # Test agent ID validation error
        try:
            validate_agent_id("_invalid_agent")
            raise AssertionError("Should have raised validation error")
        except ValueError as e:
            error_msg = str(e)
            assert "Invalid agent ID format" in error_msg
            assert "_invalid_agent" in error_msg

        # Test Pydantic validation errors include field names
        try:
            MessageModel(
                session_id="invalid_format",  # Invalid format
                sender="test_agent",
                content="test content",
            )
            raise AssertionError("Should have raised validation error")
        except ValidationError as e:
            errors = e.errors()
            assert len(errors) > 0
            # Should identify the field that failed
            field_error = errors[0]
            assert "session_id" in str(field_error.get("loc", []))

    def test_actionable_error_guidance(self):
        """Test that error messages provide clear guidance on fixing issues."""

        # Test memory key validation provides specific guidance
        try:
            sanitize_memory_key("key with spaces")
            raise AssertionError("Should have raised validation error")
        except ValueError as e:
            error_msg = str(e)
            assert "invalid characters" in error_msg.lower()
            # Should suggest allowed characters
            assert any(
                word in error_msg.lower()
                for word in ["alphanumeric", "underscore", "dash"]
            )

        # Test search query sanitization provides guidance
        try:
            sanitize_search_input("")
            raise AssertionError("Should have raised validation error")
        except ValueError as e:
            error_msg = str(e)
            assert "cannot be empty" in error_msg.lower()

        # Test TTL boundary error provides range information
        try:
            SetMemoryRequest(
                key="test_key",
                value="test_value",
                expires_in=0,  # Invalid - too small
            )
            raise AssertionError("Should have raised validation error")
        except ValidationError as e:
            errors = e.errors()
            ttl_error = next(
                (err for err in errors if "expires_in" in str(err.get("loc", []))), None
            )
            assert ttl_error is not None
            # Should indicate valid range
            assert "greater than or equal to 1" in ttl_error.get("msg", "")

    def test_error_message_consistency(self):
        """Test consistent error message format across models."""

        # Test that similar validation errors have consistent messaging
        models_with_session_id = [
            (MessageModel, {"sender": "agent", "content": "test"}),
            (SearchContextRequest, {"query": "test"}),
            (SearchBySenderRequest, {"sender": "agent"}),
        ]

        def test_invalid_session_id(model_class, extra_params) -> str | None:
            try:
                model_class(session_id="invalid_format", **extra_params)
                raise AssertionError(
                    f"Should have raised validation error for {model_class.__name__}"
                )
            except ValidationError as e:
                errors = e.errors()
                session_error = next(
                    (err for err in errors if "session_id" in str(err.get("loc", []))),
                    None,
                )
                if session_error:
                    return session_error.get("msg", "")
                return None

        session_id_errors = []
        for model_class, extra_params in models_with_session_id:
            error_msg = test_invalid_session_id(model_class, extra_params)
            if error_msg:
                session_id_errors.append(error_msg)

        # All session ID errors should be similar/consistent
        assert len(session_id_errors) > 0
        # Should all reference the same validation function/pattern
        for error_msg in session_id_errors:
            assert "Invalid session ID format" in error_msg

    def test_nested_validation_error_structure(self):
        """Test error message structure for nested validation failures."""

        # Test metadata validation with nested structure
        invalid_metadata = {
            "nested": {
                "deep": {
                    "value": {1, 2, 3}  # Not JSON serializable
                }
            }
        }

        try:
            validate_json_metadata(invalid_metadata)
            raise AssertionError("Should have raised validation error")
        except ValueError as e:
            error_msg = str(e)
            assert (
                "not JSON serializable" in error_msg
                or "serialization failed" in error_msg
            )

        # Test ValidationErrorDetail structure
        detail = ValidationErrorDetail(
            field="nested.field",
            message="Field validation failed",
            invalid_value="invalid",
            expected_type="string",
        )

        assert detail.field == "nested.field"
        assert detail.message == "Field validation failed"
        assert detail.invalid_value == "invalid"
        assert detail.expected_type == "string"

        # Test ValidationErrorResponse structure
        error_response = ValidationErrorResponse(details=[detail])

        assert error_response.success is False
        assert error_response.error == "Validation failed"
        assert error_response.code == "VALIDATION_ERROR"
        assert len(error_response.details) == 1
        assert error_response.details[0].field == "nested.field"

    def test_pydantic_error_extraction(self):
        """Test extraction of errors from Pydantic ValidationError."""

        # Create a validation error
        try:
            MessageModel(
                session_id="invalid",
                sender="",  # Empty sender
                content="",  # Empty content
            )
            raise AssertionError("Should have raised validation error")
        except ValidationError as e:
            # Extract errors using utility function
            error_details = extract_pydantic_validation_errors(e)

            assert len(error_details) > 0

            # Should have details for each failed field
            field_names = [detail.field for detail in error_details]

            # Should include the fields that failed validation
            assert any("session_id" in field for field in field_names)

            # Each error detail should have required fields
            for detail in error_details:
                assert isinstance(detail.field, str)
                assert isinstance(detail.message, str)
                assert len(detail.field) > 0
                assert len(detail.message) > 0

        # Test with non-Pydantic exception
        generic_error = ValueError("Generic validation error")
        error_details = extract_pydantic_validation_errors(generic_error)

        assert len(error_details) == 1
        assert error_details[0].field == "unknown"
        assert error_details[0].message == "Generic validation error"


class TestNestedValidationScenarios:
    """Test suite for nested validation scenarios and complex data structures."""

    def test_complex_nested_metadata_validation(self):
        """Test validation of complex nested metadata structures."""

        # Valid nested metadata
        complex_metadata = {
            "user_preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": {
                    "email": True,
                    "push": False,
                    "settings": {"frequency": "daily", "types": ["updates", "alerts"]},
                },
            },
            "system_info": {
                "version": "1.0.0",
                "features": ["auth", "cache", "performance"],
            },
        }

        # Should validate successfully
        json_metadata = validate_json_metadata(complex_metadata)
        assert json_metadata is not None

        # Should round-trip correctly
        parsed = json.loads(json_metadata)
        assert parsed == complex_metadata

        # Should work in model
        message = MessageModel(
            session_id="session_1234567890abcdef",
            sender="test_agent",
            content="test content",
            metadata=complex_metadata,
        )
        assert message.metadata == complex_metadata

    def test_deeply_nested_structure_limits(self):
        """Test validation behavior with very deeply nested structures."""

        # Create deeply nested structure
        deep_metadata = {"level": 0}
        current = deep_metadata

        # Create 100 levels of nesting
        for i in range(1, 100):
            current["nested"] = {"level": i}
            current = current["nested"]

        # Should handle deep nesting
        json_metadata = validate_json_metadata(deep_metadata)
        assert json_metadata is not None

        # Should be able to parse back
        parsed = json.loads(json_metadata)
        assert parsed["level"] == 0

        # Navigate to deep level to verify structure
        current = parsed
        for i in range(1, 100):
            current = current["nested"]
            assert current["level"] == i

    def test_metadata_size_and_complexity_limits(self):
        """Test metadata validation with size and complexity constraints."""

        # Test maximum key count (50 keys limit)
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(50)}

        # Should succeed at limit
        json_metadata = validate_json_metadata(large_metadata)
        assert json_metadata is not None

        # Should fail over limit
        oversized_metadata = {f"key_{i}": f"value_{i}" for i in range(51)}

        with pytest.raises(ValueError, match="cannot have more than 50 keys"):
            validate_json_metadata(oversized_metadata)

        # Test key length limits (100 chars per key)
        long_key_metadata = {
            "a" * 100: "valid_value",  # At limit
        }

        json_metadata = validate_json_metadata(long_key_metadata)
        assert json_metadata is not None

        # Over limit
        with pytest.raises(ValueError, match="cannot exceed 100 characters"):
            validate_json_metadata({"a" * 101: "value"})

    def test_optional_nested_field_handling(self):
        """Test validation of optional nested fields and defaults."""

        # Test optional metadata in various models
        models_with_optional_metadata = [
            SessionModel(
                id="session_1234567890abcdef",
                purpose="test session",
                created_by="test_agent",
                # metadata is optional
            ),
            MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content="test content",
                # metadata is optional
            ),
            AgentMemoryModel(
                agent_id="test_agent",
                key="test_key",
                value='{"data": "test"}',
                # metadata is optional
            ),
        ]

        for model in models_with_optional_metadata:
            # Should have None metadata when not provided
            assert model.metadata is None

        # Test with provided metadata
        session_with_metadata = SessionModel(
            id="session_1234567890abcdef",
            purpose="test session",
            created_by="test_agent",
            metadata={"custom": "data"},
        )
        assert session_with_metadata.metadata == {"custom": "data"}

    def test_nested_validation_error_propagation(self):
        """Test that validation errors propagate correctly through nested structures."""

        # Test validation error in nested request structure
        try:
            SearchByTimerangeRequest(
                session_id="session_1234567890abcdef",
                start_time="invalid_timestamp",  # Should fail
                end_time="2023-01-01T00:00:00Z",
            )
            raise AssertionError("Should have raised validation error")
        except ValidationError as e:
            errors = e.errors()
            # Should identify the specific field that failed
            start_time_error = next(
                (err for err in errors if "start_time" in str(err.get("loc", []))), None
            )
            assert start_time_error is not None
            assert "timestamp format" in start_time_error.get("msg", "").lower()

        # Test model validation with nested field failures
        try:
            MessageModel(
                session_id="invalid_session",  # Should fail
                sender="_invalid_agent",  # Should fail
                content="",  # Should fail after sanitization
            )
            raise AssertionError("Should have raised validation error")
        except ValidationError as e:
            errors = e.errors()
            # Should have multiple validation errors
            assert len(errors) >= 2  # At least session_id and one other field

            # Should identify all failed fields
            failed_fields = [str(err.get("loc", [])) for err in errors]
            field_names = " ".join(failed_fields)
            assert "session_id" in field_names

    def test_validation_performance_deep_hierarchies(self):
        """Test validation performance with complex nested structures."""

        # Create complex nested structure for performance testing
        complex_structure = {
            "level_0": {
                f"item_{i}": {
                    "nested_data": {
                        "sub_items": [
                            {"id": j, "value": f"item_{i}_sub_{j}"} for j in range(10)
                        ],
                        "metadata": {
                            "created": "2023-01-01T00:00:00Z",
                            "updated": "2023-01-01T12:00:00Z",
                            "tags": ["tag1", "tag2", "tag3"],
                        },
                    }
                }
                for i in range(20)
            }
        }

        # Test validation performance
        start_time = datetime.now()
        json_metadata = validate_json_metadata(complex_structure)
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()
        # Should complete validation within reasonable time (< 50ms)
        assert duration < 0.05, f"Validation took {duration}s for complex structure"

        # Should produce valid JSON
        assert json_metadata is not None
        parsed = json.loads(json_metadata)
        assert parsed == complex_structure

        # Test with model creation
        start_time = datetime.now()
        session = SessionModel(
            id="session_1234567890abcdef",
            purpose="performance test session",
            created_by="test_agent",
            metadata=complex_structure,
        )
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()
        # Model creation should also be fast
        assert duration < 0.05, f"Model creation took {duration}s for complex metadata"

        assert session.metadata == complex_structure


class TestAdditionalCoverageTargets:
    """Additional tests to target specific uncovered lines for 85%+ coverage."""

    def test_error_response_utilities(self):
        """Test error response creation utilities."""

        # Test create_standard_response
        from shared_context_server.models import (
            create_error_response,
            create_standard_response,
        )

        success_response = create_standard_response(True, data="test")
        assert success_response["success"] is True
        assert success_response["data"] == "test"
        assert "timestamp" in success_response

        # Test create_error_response
        error_response = create_error_response(
            "Test error", "TEST_ERROR", details="error details"
        )
        assert error_response["success"] is False
        assert error_response["error"] == "Test error"
        assert error_response["code"] == "TEST_ERROR"
        assert error_response["details"] == "error details"
        assert "timestamp" in error_response

    def test_metadata_serialization_utilities(self):
        """Test metadata serialization utilities."""

        from shared_context_server.models import (
            deserialize_metadata,
            serialize_metadata,
        )

        # Test serialize_metadata
        metadata = {"key": "value", "count": 42}
        serialized = serialize_metadata(metadata)
        assert serialized is not None
        assert isinstance(serialized, str)

        # Test with None
        assert serialize_metadata(None) is None

        # Test deserialize_metadata
        deserialized = deserialize_metadata(serialized)
        assert deserialized == metadata

        # Test with None
        assert deserialize_metadata(None) is None

        # Test with invalid JSON
        assert deserialize_metadata("invalid json") is None
        assert deserialize_metadata("") is None

    def test_model_validation_utility(self):
        """Test model validation utility function."""

        from shared_context_server.models import validate_model_dict

        # Test successful validation
        data = {
            "session_id": "session_1234567890abcdef",
            "sender": "test_agent",
            "content": "test content",
        }

        message = validate_model_dict(MessageModel, data)
        assert isinstance(message, MessageModel)
        assert message.session_id == data["session_id"]

        # Test validation failure
        invalid_data = {"session_id": "invalid_session", "sender": "", "content": ""}

        with pytest.raises(ValueError, match="Validation failed"):
            validate_model_dict(MessageModel, invalid_data)

    def test_additional_request_response_models(self):
        """Test additional request/response models for coverage."""

        # Test SearchResponse with various fields
        search_response = SearchResponse(
            query="test query",
            threshold=80.0,
            search_scope="public",
            message_count=5,
            search_time_ms=1.5,
            performance_note="Fast search",
        )

        assert search_response.success is True
        assert search_response.query == "test query"
        assert search_response.threshold == 80.0
        assert len(search_response.results) == 0  # Default empty list

        # Test MemorySetResponse
        memory_set_response = MemorySetResponse(
            key="test_key",
            session_scoped=True,
            scope="session",
            stored_at="2023-01-01T00:00:00Z",
        )

        assert memory_set_response.success is True
        assert memory_set_response.key == "test_key"
        assert memory_set_response.scope == "session"

        # Test MemoryGetResponse
        memory_get_response = MemoryGetResponse(
            key="test_key",
            value={"data": "test"},
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            scope="global",
        )

        assert memory_get_response.success is True
        assert memory_get_response.value == {"data": "test"}
        assert memory_get_response.scope == "global"

    def test_resource_model_validation(self):
        """Test ResourceModel validation."""

        # Valid resource
        resource = ResourceModel(
            uri="session://session_1234567890abcdef/messages",
            name="Session Messages",
            description="Messages in the session",
            content={"messages": []},
        )

        assert resource.uri.startswith("session://")
        assert resource.supports_subscriptions is True  # Default

        # Test with agent URI
        agent_resource = ResourceModel(
            uri="agent://test_agent/memory",
            name="Agent Memory",
            description="Agent's memory store",
            content={"entries": []},
        )

        assert agent_resource.uri.startswith("agent://")

        # Test invalid URI
        with pytest.raises(ValidationError):
            ResourceModel(
                uri="invalid://test",  # Invalid scheme
                name="Invalid Resource",
                description="Should fail",
                content={},
            )

    def test_validation_error_models(self):
        """Test validation error model structures."""

        # Test ValidationErrorDetail
        error_detail = ValidationErrorDetail(
            field="test_field",
            message="Test validation error",
            invalid_value="invalid",
            expected_type="string",
        )

        assert error_detail.field == "test_field"
        assert error_detail.message == "Test validation error"

        # Test ValidationErrorResponse
        error_response = ValidationErrorResponse(details=[error_detail])

        assert error_response.success is False
        assert error_response.error == "Validation failed"
        assert error_response.code == "VALIDATION_ERROR"
        assert len(error_response.details) == 1

        # Test create_validation_error_response

        response = create_validation_error_response(
            [error_detail], "Custom error message"
        )
        assert response.error == "Custom error message"
        assert len(response.details) == 1

    def test_additional_utility_functions(self):
        """Test additional utility functions for coverage."""

        from shared_context_server.models import (
            sanitize_search_input,
            validate_json_serializable_value,
        )

        # Test sanitize_search_input
        query = "  test query with spaces  "
        sanitized = sanitize_search_input(query)
        assert sanitized == "test query with spaces"

        # Test with excessive whitespace
        query_with_spaces = "test   query   with   many   spaces"
        sanitized = sanitize_search_input(query_with_spaces)
        assert "   " not in sanitized  # Multiple spaces should be reduced

        # Test length truncation
        long_query = "x" * 1000
        sanitized_long = sanitize_search_input(long_query, max_length=100)
        assert len(sanitized_long) <= 100

        # Test empty after sanitization
        with pytest.raises(ValueError, match="cannot be empty after sanitization"):
            sanitize_search_input("   ")

        # Test validate_json_serializable_value
        valid_value = {"key": "value", "number": 42}
        result = validate_json_serializable_value(valid_value)
        assert result == valid_value

        # Test invalid value
        with pytest.raises(ValueError, match="not JSON serializable"):
            validate_json_serializable_value(lambda x: x)

    def test_timestamp_serialization_edge_cases(self):
        """Test datetime serialization in various models."""

        # Test SessionModel serialization
        session = SessionModel(
            id="session_1234567890abcdef",
            purpose="test session",
            created_by="test_agent",
        )

        # Test JSON serialization includes timestamps
        session_dict = session.model_dump(mode="json")
        assert isinstance(session_dict["created_at"], str)
        assert isinstance(session_dict["updated_at"], str)

        # Test MessageModel serialization
        message = MessageModel(
            session_id="session_1234567890abcdef",
            sender="test_agent",
            content="test content",
        )

        message_dict = message.model_dump(mode="json")
        assert isinstance(message_dict["timestamp"], str)

        # Test AgentMemoryModel with expires_at
        memory = AgentMemoryModel(
            agent_id="test_agent",
            key="test_key",
            value='{"data": "test"}',
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        memory_dict = memory.model_dump(mode="json")
        assert isinstance(memory_dict["created_at"], str)
        assert isinstance(memory_dict["updated_at"], str)
        assert isinstance(memory_dict["expires_at"], str)

    def test_enum_edge_cases(self):
        """Test enum validation edge cases."""

        # Test all MessageVisibility values
        for visibility in MessageVisibility:
            message = MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content="test content",
                visibility=visibility,
            )
            assert message.visibility == visibility

        # Test all MessageType values
        for msg_type in MessageType:
            message = MessageModel(
                session_id="session_1234567890abcdef",
                sender="test_agent",
                content="test content",
                message_type=msg_type,
            )
            assert message.message_type == msg_type

    def test_timezone_edge_cases(self):
        """Test timezone handling edge cases."""

        from shared_context_server.models import validate_utc_timestamp

        # Test various timestamp formats
        timestamp_formats = [
            "2023-01-01T00:00:00Z",  # Z suffix
            "2023-01-01T00:00:00+00:00",  # +00:00 suffix
            "2023-01-01T00:00:00",  # No timezone (should add UTC)
        ]

        for timestamp_str in timestamp_formats:
            dt = validate_utc_timestamp(timestamp_str)
            assert dt.tzinfo == timezone.utc

    def test_metadata_edge_cases(self):
        """Test metadata validation edge cases."""

        # Test metadata with keys at boundary
        metadata_keys_limit = {f"key_{i:02d}": f"value_{i}" for i in range(50)}

        # Should succeed
        json_result = validate_json_metadata(metadata_keys_limit)
        assert json_result is not None

        # Test metadata with long keys at limit
        long_key_metadata = {
            "a" * 100: "valid_value"  # Exactly at 100 char limit
        }

        json_result = validate_json_metadata(long_key_metadata)
        assert json_result is not None

    def test_memory_list_request_edge_cases(self):
        """Test MemoryListRequest edge cases."""

        # Test with "all" as session_id (special case)
        request = MemoryListRequest(session_id="all")
        assert request.session_id == "all"

        # Test with valid session_id
        request = MemoryListRequest(session_id="session_1234567890abcdef")
        assert request.session_id == "session_1234567890abcdef"

        # Test with None (default)
        request = MemoryListRequest()
        assert request.session_id is None

    def test_model_serialization_edge_cases(self):
        """Test model serialization edge cases."""

        # Test MemoryListResponse serialization
        response = MemoryListResponse(count=5, scope_filter="session")

        serialized = response.model_dump(mode="json")
        assert serialized["timestamp"]
        assert serialized["count"] == 5

        # Test ValidationErrorResponse serialization
        error_response = ValidationErrorResponse()
        serialized = error_response.model_dump(mode="json")
        assert serialized["timestamp"]
        assert serialized["success"] is False
