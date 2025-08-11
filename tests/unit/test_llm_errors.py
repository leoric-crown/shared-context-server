"""
Unit tests for LLM-Optimized Error Framework.

Tests the comprehensive error messaging system designed for AI agent
decision-making and recovery guidance.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from shared_context_server.utils.llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    ErrorSeverity,
    LLMOptimizedErrorResponse,
    create_enhanced_error_response,
    create_input_validation_error,
    create_llm_error_response,
    create_llm_friendly_validation_error,
    create_permission_denied_error,
    create_resource_not_found_error,
    create_system_error,
    enhance_legacy_error_response,
    get_error_recovery_suggestions,
    validate_error_response,
)


class TestLLMOptimizedErrorResponse:
    """Test the core LLMOptimizedErrorResponse class."""

    def test_basic_error_creation(self):
        """Test basic error response creation."""
        error = LLMOptimizedErrorResponse(
            error="Test error message",
            code="TEST_ERROR",
            suggestions=["Try again", "Check input"],
            context={"field": "test_field"},
        )

        assert error.error == "Test error message"
        assert error.code == "TEST_ERROR"
        assert error.suggestions == ["Try again", "Check input"]
        assert error.context == {"field": "test_field"}
        assert error.severity == ErrorSeverity.ERROR
        assert error.recoverable is True

    def test_error_to_dict(self):
        """Test conversion to dictionary format."""
        error = LLMOptimizedErrorResponse(
            error="Test error",
            code="TEST_ERROR",
            suggestions=["Fix it"],
            context={"test": "value"},
            severity=ErrorSeverity.WARNING,
        )

        result = error.to_dict()

        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["code"] == "TEST_ERROR"
        assert result["severity"] == "warning"
        assert result["recoverable"] is True
        assert "timestamp" in result
        assert result["suggestions"] == ["Fix it"]
        assert result["context"] == {"test": "value"}

    def test_error_with_retry_after(self):
        """Test error with retry_after setting."""
        error = LLMOptimizedErrorResponse(
            error="System busy",
            code="SYSTEM_BUSY",
            retry_after=30,
            related_resources=["health_check"],
        )

        result = error.to_dict()

        assert result["retry_after"] == 30
        assert result["related_resources"] == ["health_check"]


class TestErrorCreationFunctions:
    """Test individual error creation functions."""

    def test_create_llm_error_response(self):
        """Test basic LLM error response creation."""
        response = create_llm_error_response(
            error="Test error",
            code="TEST_CODE",
            suggestions=["Do something"],
            severity=ErrorSeverity.CRITICAL,
        )

        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["code"] == "TEST_CODE"
        assert response["severity"] == "critical"
        assert response["suggestions"] == ["Do something"]

    def test_create_input_validation_error(self):
        """Test input validation error creation."""
        response = create_input_validation_error(
            field="session_id",
            value="invalid_value",
            expected="session_[16-hex]",
        )

        assert response["code"] == "INVALID_INPUT_FORMAT"
        assert response["severity"] == "warning"
        assert "session_id" in response["error"]
        assert len(response["suggestions"]) >= 2
        assert response["context"]["invalid_field"] == "session_id"
        assert response["context"]["expected_format"] == "session_[16-hex]"

    def test_create_resource_not_found_error(self):
        """Test resource not found error creation."""
        response = create_resource_not_found_error(
            resource_type="session",
            resource_id="missing_session_123",
            available_alternatives=["session_abc", "session_def"],
        )

        assert response["code"] == "SESSION_NOT_FOUND"
        assert "missing_session_123" in response["error"]
        assert "session_abc" in response["suggestions"][2]  # Available alternatives
        assert response["context"]["resource_type"] == "session"
        assert "create_session" in response["related_resources"]

    def test_create_permission_denied_error(self):
        """Test permission denied error creation."""
        response = create_permission_denied_error(
            required_permission="admin",
            current_permissions=["read", "write"],
        )

        assert response["code"] == "PERMISSION_DENIED"
        assert response["severity"] == "error"
        assert response["recoverable"] is False
        assert "admin" in response["error"].lower()
        assert "read, write" in response["suggestions"][1]  # Current permissions
        assert "authenticate_agent" in response["related_resources"]

    def test_create_system_error_temporary(self):
        """Test temporary system error creation."""
        response = create_system_error(
            operation="create_session",
            system_component="database",
            temporary=True,
        )

        assert response["code"] == "DATABASE_UNAVAILABLE"
        assert response["severity"] == "error"
        assert response["retry_after"] == 5
        assert response["context"]["temporary_issue"] is True
        assert "Retry the operation" in response["suggestions"][0]

    def test_create_system_error_permanent(self):
        """Test permanent system error creation."""
        response = create_system_error(
            operation="backup_data",
            system_component="storage",
            temporary=False,
        )

        assert response["code"] == "STORAGE_UNAVAILABLE"
        assert response["severity"] == "critical"
        assert "retry_after" not in response  # Should not be included when None
        assert response["context"]["temporary_issue"] is False
        assert "Contact system administrator" in response["suggestions"][0]


class TestErrorMessagePatterns:
    """Test the ERROR_MESSAGE_PATTERNS dictionary."""

    def test_session_not_found_pattern(self):
        """Test session not found pattern."""
        response = ERROR_MESSAGE_PATTERNS["session_not_found"]("test_session_123")

        assert response["code"] == "SESSION_NOT_FOUND"
        assert "test_session_123" in response["error"]
        assert "create_session" in response["related_resources"]

    def test_purpose_empty_pattern(self):
        """Test purpose empty pattern."""
        response = ERROR_MESSAGE_PATTERNS["purpose_empty"]()

        assert response["code"] == "INVALID_INPUT"
        assert response["severity"] == "warning"
        assert "purpose cannot be empty" in response["error"].lower()
        assert len(response["suggestions"]) >= 2

    def test_content_empty_pattern(self):
        """Test content empty pattern."""
        response = ERROR_MESSAGE_PATTERNS["content_empty"]()

        assert response["code"] == "INVALID_INPUT"
        assert "content cannot be empty" in response["error"].lower()
        assert "meaningful message content" in response["suggestions"][0]

    def test_memory_key_invalid_pattern(self):
        """Test memory key invalid pattern."""
        response = ERROR_MESSAGE_PATTERNS["memory_key_invalid"]("invalid key")

        assert response["code"] == "INVALID_KEY"
        assert "spaces" in response["error"]
        assert "underscore or dash" in response["suggestions"][0]
        assert response["context"]["invalid_key"] == "invalid key"

    def test_admin_required_pattern(self):
        """Test admin required pattern."""
        response = ERROR_MESSAGE_PATTERNS["admin_required"]()

        assert response["code"] == "PERMISSION_DENIED"
        assert response["recoverable"] is False
        assert "admin" in response["error"].lower()

    def test_invalid_api_key_pattern(self):
        """Test invalid API key pattern."""
        response = ERROR_MESSAGE_PATTERNS["invalid_api_key"]("test_agent")

        assert response["code"] == "AUTH_FAILED"
        assert response["context"]["agent_id"] == "test_agent"
        assert "Verify the API key" in response["suggestions"][0]

    def test_memory_key_exists_pattern(self):
        """Test memory key exists pattern."""
        response = ERROR_MESSAGE_PATTERNS["memory_key_exists"]("existing_key")

        assert response["code"] == "KEY_EXISTS"
        assert "existing_key" in response["error"]
        assert "overwrite=True" in response["suggestions"][0]
        assert response["context"]["overwrite_option"] is True

    def test_memory_not_found_pattern(self):
        """Test memory not found pattern."""
        response = ERROR_MESSAGE_PATTERNS["memory_not_found"]("missing_key")

        assert response["code"] == "MEMORY_NOT_FOUND"
        assert "missing_key" in response["error"]
        assert "list_memory" in response["suggestions"][1]


class TestUtilityFunctions:
    """Test utility functions."""

    def test_validate_error_response_valid(self):
        """Test validation of valid error response."""
        valid_response = {
            "success": False,
            "error": "Test error",
            "code": "TEST_ERROR",
            "severity": "error",
            "recoverable": True,
            "timestamp": "2023-01-01T00:00:00Z",
            "suggestions": ["Try again"],
        }

        assert validate_error_response(valid_response) is True

    def test_validate_error_response_invalid(self):
        """Test validation of invalid error response."""
        invalid_responses = [
            # Missing required fields
            {"success": False, "error": "Test"},
            # Success should be False
            {
                "success": True,
                "error": "Test",
                "code": "TEST",
                "severity": "error",
                "recoverable": True,
                "timestamp": "2023-01-01T00:00:00Z",
                "suggestions": ["Try"],
            },
            # No suggestions
            {
                "success": False,
                "error": "Test",
                "code": "TEST",
                "severity": "error",
                "recoverable": True,
                "timestamp": "2023-01-01T00:00:00Z",
            },
            # Invalid severity
            {
                "success": False,
                "error": "Test",
                "code": "TEST",
                "severity": "invalid",
                "recoverable": True,
                "timestamp": "2023-01-01T00:00:00Z",
                "suggestions": ["Try"],
            },
        ]

        for invalid_response in invalid_responses:
            assert validate_error_response(invalid_response) is False

    def test_enhance_legacy_error_response(self):
        """Test enhancement of legacy error response."""
        legacy = {"success": False, "error": "Old error", "code": "OLD_ERROR"}

        enhanced = enhance_legacy_error_response(
            legacy,
            suggestions=["New suggestion"],
            context={"enhanced": True},
            severity=ErrorSeverity.WARNING,
        )

        assert enhanced["error"] == "Old error"
        assert enhanced["code"] == "OLD_ERROR"
        assert enhanced["suggestions"] == ["New suggestion"]
        assert enhanced["context"] == {"enhanced": True}
        assert enhanced["severity"] == "warning"
        assert enhanced["recoverable"] is True
        assert "timestamp" in enhanced

    def test_create_llm_friendly_validation_error(self):
        """Test creation of LLM-friendly validation error."""
        field_errors = [
            {"field": "session_id", "message": "Invalid format", "value": "bad_id"},
            {"field": "content", "message": "Too long", "value": "x" * 1000},
        ]

        response = create_llm_friendly_validation_error(field_errors)

        assert response["code"] == "VALIDATION_ERROR"
        assert response["severity"] == "warning"
        assert "2 field(s)" in response["error"]
        assert len(response["suggestions"]) >= 4  # 2 field-specific + 3 general
        assert len(response["context"]["invalid_fields"]) == 2

    def test_get_error_recovery_suggestions(self):
        """Test error recovery suggestions."""
        # Test known error code
        suggestions = get_error_recovery_suggestions("SESSION_NOT_FOUND")
        assert "create_session" in suggestions[0]
        assert len(suggestions) >= 3

        # Test unknown error code
        suggestions = get_error_recovery_suggestions("UNKNOWN_ERROR")
        assert "Review the error message" in suggestions[0]
        assert len(suggestions) >= 3

    def test_create_enhanced_error_response_known_pattern(self):
        """Test enhanced error response with known pattern."""
        response = create_enhanced_error_response("session_not_found", "test_session")

        assert response["code"] == "SESSION_NOT_FOUND"
        assert "test_session" in response["error"]

    def test_create_enhanced_error_response_unknown_pattern(self):
        """Test enhanced error response with unknown pattern."""
        response = create_enhanced_error_response("unknown_error", "error message")

        assert response["code"] == "UNKNOWN_ERROR"
        assert response["error"] == "error message"


class TestIntegrationScenarios:
    """Test integration scenarios with realistic use cases."""

    def test_authentication_flow_errors(self):
        """Test authentication flow error scenarios."""
        # Invalid API key
        auth_error = ERROR_MESSAGE_PATTERNS["invalid_api_key"]("agent_123")
        assert auth_error["severity"] == "error"
        assert auth_error["recoverable"] is True
        assert "authenticate_agent" in auth_error["related_resources"]

        # Token expired
        token_error = ERROR_MESSAGE_PATTERNS["token_expired"]()
        assert token_error["code"] == "TOKEN_EXPIRED"
        assert token_error["retry_after"] == 0  # Can retry immediately

    def test_session_management_errors(self):
        """Test session management error scenarios."""
        # Session not found
        session_error = ERROR_MESSAGE_PATTERNS["session_not_found"]("session_abc123")
        assert "session_abc123" in session_error["error"]
        assert "create_session" in session_error["related_resources"]

        # Empty purpose
        purpose_error = ERROR_MESSAGE_PATTERNS["purpose_empty"]()
        assert purpose_error["severity"] == "warning"
        assert "descriptive purpose" in purpose_error["suggestions"][0]

    def test_memory_management_errors(self):
        """Test memory management error scenarios."""
        # Invalid key
        key_error = ERROR_MESSAGE_PATTERNS["memory_key_invalid"]("bad key")
        assert "spaces" in key_error["error"]
        assert "underscore" in key_error["suggestions"][0]

        # Key exists
        exists_error = ERROR_MESSAGE_PATTERNS["memory_key_exists"]("duplicate")
        assert "overwrite=True" in exists_error["suggestions"][0]
        assert "list_memory" in exists_error["related_resources"]

        # Not found
        not_found_error = ERROR_MESSAGE_PATTERNS["memory_not_found"]("missing")
        assert "missing" in not_found_error["error"]
        assert "expired" in not_found_error["suggestions"][2]

    @patch("shared_context_server.utils.llm_errors.datetime")
    def test_timestamp_consistency(self, mock_datetime):
        """Test that timestamps are consistent and UTC."""
        mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        response = create_llm_error_response("Test error", "TEST_ERROR")
        assert response["timestamp"] == "2023-01-01T12:00:00+00:00"

    def test_error_context_information(self):
        """Test that errors provide sufficient context for LLM decision-making."""
        # Test input validation error context
        validation_error = create_input_validation_error(
            "session_id", "invalid_value", "session_[hex]"
        )

        context = validation_error["context"]
        assert "invalid_field" in context
        assert "provided_value" in context
        assert "expected_format" in context

        # Test resource not found error context
        not_found_error = create_resource_not_found_error(
            "session", "missing", ["alt1", "alt2", "alt3", "alt4", "alt5", "alt6"]
        )

        context = not_found_error["context"]
        assert "resource_type" in context
        assert "resource_id" in context
        assert "available_alternatives" in context
        assert len(context["available_alternatives"]) == 5  # Limited to 5

    def test_error_severity_appropriateness(self):
        """Test that error severities are appropriate for different scenarios."""
        # Warning level errors (user can fix)
        purpose_error = ERROR_MESSAGE_PATTERNS["purpose_empty"]()
        assert purpose_error["severity"] == "warning"

        # Error level (operation failed, retry possible)
        auth_error = ERROR_MESSAGE_PATTERNS["invalid_api_key"]("agent")
        assert auth_error["severity"] == "error"

        # Critical level (system issue)
        system_error = create_system_error("operation", "system", temporary=False)
        assert system_error["severity"] == "critical"
