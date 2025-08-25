"""
LLM-Optimized Error Framework for Shared Context MCP Server.

This module provides enhanced error messaging specifically optimized for AI agent
decision-making and recovery. All error messages include:
- Clear, actionable descriptions
- Semantic error codes for categorization
- Specific recovery suggestions for LLMs
- Context information to guide decision-making
- Severity levels for appropriate response prioritization
- Recovery guidance with retry information

Built according to PRP-005: Phase 4 - Production Ready specification.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

# ============================================================================
# ERROR SEVERITY AND CORE CLASSES
# ============================================================================


class ErrorSeverity(str, Enum):
    """Error severity levels for LLM decision-making."""

    WARNING = "warning"  # Non-critical, operation may continue
    ERROR = "error"  # Operation failed, retry possible
    CRITICAL = "critical"  # System issue, immediate attention required


class LLMOptimizedErrorResponse:
    """Enhanced error response optimized for LLM understanding and recovery."""

    def __init__(
        self,
        error: str,  # Clear, actionable description
        code: str,  # Semantic error code
        suggestions: list[str] | None = None,  # Specific next actions for LLMs
        context: dict[str, Any] | None = None,  # Relevant context for decision-making
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recoverable: bool = True,  # Whether operation can be retried
        retry_after: int | None = None,  # Seconds to wait before retry
        related_resources: list[str] | None = None,  # Related MCP resources/tools
        **kwargs: Any,
    ):
        self.error = error
        self.code = code
        self.suggestions = suggestions or []
        self.context = context or {}
        self.severity = severity
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.related_resources = related_resources or []
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.additional_data = kwargs

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MCP response."""
        response = {
            "success": False,
            "error": self.error,
            "code": self.code,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp,
        }

        if self.suggestions:
            response["suggestions"] = self.suggestions

        if self.context:
            response["context"] = self.context

        if self.retry_after is not None:
            response["retry_after"] = self.retry_after

        if self.related_resources:
            response["related_resources"] = self.related_resources

        response.update(self.additional_data)
        return response


# ============================================================================
# ERROR CREATION FUNCTIONS
# ============================================================================


def create_llm_error_response(
    error: str, code: str, suggestions: list[str] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Create LLM-optimized error response."""

    enhanced_error = LLMOptimizedErrorResponse(
        error=error, code=code, suggestions=suggestions or [], **kwargs
    )
    return enhanced_error.to_dict()


def create_input_validation_error(
    field: str, value: Any, expected: str, **kwargs: Any
) -> dict[str, Any]:
    """Create input validation error with recovery guidance."""

    suggestions = [
        f"Check the {field} parameter format",
        f"Expected format: {expected}",
        "Review the API documentation for parameter requirements",
    ]

    context = {
        "invalid_field": field,
        "provided_value": str(value)[:100]
        if value is not None
        else None,  # Truncate long values
        "expected_format": expected,
    }

    return create_llm_error_response(
        error=f"Invalid {field} format. Expected {expected}",
        code="INVALID_INPUT_FORMAT",
        suggestions=suggestions,
        context=context,
        severity=ErrorSeverity.WARNING,
        **kwargs,
    )


def create_resource_not_found_error(
    resource_type: str,
    resource_id: str,
    available_alternatives: list[str] | None = None,
    suggestions: list[str] | None = None,  # Allow custom suggestions
    **kwargs: Any,
) -> dict[str, Any]:
    """Create resource not found error with alternatives."""

    # Use custom suggestions if provided, otherwise use defaults
    if suggestions is None:
        suggestions = [
            f"Verify the {resource_type} ID is correct",
            f"Use create_{resource_type} to create a new {resource_type}",
        ]

        if available_alternatives:
            suggestions.append(
                f"Available {resource_type}s: {', '.join(available_alternatives[:3])}"
            )

    context: dict[str, Any] = {
        "resource_type": resource_type,
        "resource_id": resource_id,
    }

    if available_alternatives:
        context["available_alternatives"] = available_alternatives[
            :5
        ]  # Limit context size

    return create_llm_error_response(
        error=f"{resource_type.title()} '{resource_id}' not found",
        code=f"{resource_type.upper()}_NOT_FOUND",
        suggestions=suggestions,
        context=context,
        related_resources=[f"create_{resource_type}", f"list_{resource_type}s"],
        **kwargs,
    )


def create_permission_denied_error(
    required_permission: str,
    current_permissions: list[str] | None = None,
    suggestions: list[str] | None = None,  # Allow custom suggestions
    **kwargs: Any,
) -> dict[str, Any]:
    """Create permission denied error with guidance."""

    # Use custom suggestions if provided, otherwise use defaults
    if suggestions is None:
        suggestions = [
            "Check your agent authentication and permissions",
            f"Request {required_permission} permission from the user",
            "Use operations that require lower permissions",
        ]

        if current_permissions:
            suggestions.insert(
                1, f"Current permissions: {', '.join(current_permissions)}"
            )

    context = {
        "required_permission": required_permission,
        "current_permissions": current_permissions or [],
    }

    return create_llm_error_response(
        error=f"{required_permission.title()} permission required for this operation",
        code="PERMISSION_DENIED",
        suggestions=suggestions,
        context=context,
        severity=ErrorSeverity.ERROR,
        recoverable=False,  # Requires user intervention
        related_resources=["authenticate_agent"],
        **kwargs,
    )


def create_system_error(
    operation: str, system_component: str, temporary: bool = True, **kwargs: Any
) -> dict[str, Any]:
    """Create system error with recovery guidance."""

    if temporary:
        suggestions = [
            "Retry the operation in a few seconds",
            "Check system health with the health endpoint",
            "Contact support if the issue persists",
        ]
        severity = ErrorSeverity.ERROR
        retry_after = 5
    else:
        suggestions = [
            "Contact system administrator",
            "Check system logs for detailed error information",
            "Use alternative operations if available",
        ]
        severity = ErrorSeverity.CRITICAL
        retry_after = None

    context = {
        "failed_operation": operation,
        "system_component": system_component,
        "temporary_issue": temporary,
    }

    return create_llm_error_response(
        error=f"{system_component} temporarily unavailable during {operation}. {'This is likely temporary.' if temporary else 'This requires system maintenance.'}",
        code=f"{system_component.upper()}_UNAVAILABLE",
        suggestions=suggestions,
        context=context,
        severity=severity,
        retry_after=retry_after,
        related_resources=["get_performance_metrics"] if temporary else [],
        **kwargs,
    )


# ============================================================================
# ERROR MESSAGE PATTERNS
# ============================================================================


# Enhanced error patterns for existing tools
ERROR_MESSAGE_PATTERNS = {
    # Session management errors
    "session_not_found": lambda session_id,
    available_sessions=[]: create_resource_not_found_error(
        "session", session_id, available_alternatives=available_sessions
    ),
    # Input validation errors
    "invalid_session_id": lambda session_id: create_input_validation_error(
        "session_id",
        session_id,
        "session_[16-character-hex]",
        suggestions=[
            "Check the session_id parameter format",
            "Use create_session to generate a valid session ID",
            "Session IDs must start with 'session_' followed by 16 hex characters",
        ],
    ),
    "content_too_large": lambda content_size,
    max_size=100000: create_llm_error_response(
        error=f"Message content too large ({content_size} characters). Maximum allowed: {max_size}",
        code="CONTENT_TOO_LARGE",
        suggestions=[
            "Reduce message content length",
            "Split large content into multiple messages",
            f"Maximum content size is {max_size} characters",
        ],
        context={
            "content_size": content_size,
            "max_allowed": max_size,
            "excess_characters": content_size - max_size,
        },
        severity=ErrorSeverity.WARNING,
    ),
    "purpose_empty": lambda: create_llm_error_response(
        error="Session purpose cannot be empty after sanitization",
        code="INVALID_INPUT",
        suggestions=[
            "Provide a descriptive purpose for the session",
            "Purpose should describe the collaboration goal",
            "Example: 'Feature planning for user authentication'",
        ],
        context={"field": "purpose", "requirement": "non_empty_string"},
        severity=ErrorSeverity.WARNING,
    ),
    "content_empty": lambda: create_llm_error_response(
        error="Message content cannot be empty after sanitization",
        code="INVALID_INPUT",
        suggestions=[
            "Provide meaningful message content",
            "Content should contain relevant information for other agents",
            "Empty or whitespace-only content is not allowed",
        ],
        context={"field": "content", "requirement": "non_empty_string"},
        severity=ErrorSeverity.WARNING,
    ),
    "memory_key_invalid": lambda key: create_llm_error_response(
        error="Memory key contains invalid characters. Keys cannot contain spaces, newlines, or tabs",
        code="INVALID_KEY",
        suggestions=[
            "Use underscore or dash separators instead of spaces",
            "Example: 'user_preferences' instead of 'user preferences'",
            "Keys should contain only alphanumeric characters, underscores, and dashes",
        ],
        context={
            "invalid_key": key,
            "allowed_characters": "alphanumeric, underscore, dash",
        },
        severity=ErrorSeverity.WARNING,
    ),
    # Permission errors
    "admin_required": lambda: create_permission_denied_error(
        "admin",
        current_permissions=[],
        suggestions=[
            "Use 'public' or 'private' visibility instead",
            "Request admin privileges from user",
            "Check agent authentication and role assignment",
        ],
    ),
    "write_required": lambda current_permissions=None: create_permission_denied_error(
        "write",
        current_permissions=current_permissions or [],
        suggestions=[
            "Use read-only operations like get_session or get_messages",
            "Request write permission from user",
            "Check agent authentication and role assignment",
        ],
    ),
    # System errors
    "database_error": lambda operation: create_system_error(
        operation, "database", temporary=True
    ),
    "memory_limit_exceeded": lambda: create_llm_error_response(
        error="Agent memory storage limit exceeded. Clean up unused memory entries.",
        code="MEMORY_LIMIT_EXCEEDED",
        suggestions=[
            "Remove unused memory entries with delete operations",
            "Set shorter TTL values for temporary data",
            "Use session-scoped memory instead of global memory",
            "Contact administrator if limit needs to be increased",
        ],
        context={"recommended_action": "cleanup_old_entries"},
        related_resources=["list_memory", "delete_memory"],
        severity=ErrorSeverity.WARNING,
    ),
    # Authentication errors
    "invalid_api_key": lambda agent_id: create_llm_error_response(
        error="Invalid API key provided for authentication",
        code="AUTH_FAILED",
        suggestions=[
            "Verify the API key is correct",
            "Check if the API key has expired",
            "Regenerate API key if necessary",
            "Ensure API key matches the environment configuration",
        ],
        context={"agent_id": agent_id, "auth_method": "api_key"},
        related_resources=["authenticate_agent"],
        severity=ErrorSeverity.ERROR,
        recoverable=True,
    ),
    "token_expired": lambda: create_llm_error_response(
        error="Authentication token has expired. Please re-authenticate.",
        code="TOKEN_EXPIRED",
        suggestions=[
            "Use authenticate_agent to get a new token",
            "Store the new token for subsequent requests",
            "Check token expiration time in authentication response",
        ],
        context={"auth_method": "jwt", "action_required": "re_authenticate"},
        related_resources=["authenticate_agent"],
        severity=ErrorSeverity.ERROR,
        recoverable=True,
        retry_after=0,  # Can retry immediately
    ),
    # Search errors
    "search_query_too_short": lambda query: create_llm_error_response(
        error=f"Search query too short: '{query}'. Minimum length is 1 character after sanitization.",
        code="INVALID_SEARCH_QUERY",
        suggestions=[
            "Provide a more specific search term",
            "Use meaningful keywords for better results",
            "Avoid queries with only whitespace or special characters",
        ],
        context={"provided_query": query, "min_length": 1},
        severity=ErrorSeverity.WARNING,
    ),
    # Agent memory errors
    "memory_key_exists": lambda key: create_llm_error_response(
        error=f"Memory key '{key}' already exists. Use overwrite=True to replace.",
        code="KEY_EXISTS",
        suggestions=[
            "Set overwrite=True parameter to replace existing value",
            "Use a different key name to avoid conflicts",
            "Check existing memory with list_memory first",
        ],
        context={"existing_key": key, "overwrite_option": True},
        related_resources=["list_memory"],
        severity=ErrorSeverity.WARNING,
    ),
    "memory_not_found": lambda key: create_resource_not_found_error(
        "memory",
        key,
        available_alternatives=[],
        suggestions=[
            "Check the memory key spelling and format",
            "Use list_memory to see available keys",
            "The memory entry may have expired (check TTL)",
        ],
    ),
}


# ============================================================================
# INTEGRATION FUNCTIONS
# ============================================================================


def create_enhanced_error_response(
    error_key: str, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    """Create enhanced error response using patterns."""
    if error_key in ERROR_MESSAGE_PATTERNS:
        pattern_func = ERROR_MESSAGE_PATTERNS[error_key]
        return pattern_func(*args, **kwargs)  # type: ignore[no-any-return,operator]
    # Fallback to basic error response
    from ..models import create_error_response

    return create_error_response(
        str(args[0]) if args else "Unknown error", error_key.upper()
    )


# ============================================================================
# VALIDATION AND UTILITIES
# ============================================================================


def validate_error_response(response: dict[str, Any]) -> bool:
    """
    Validate that an error response contains required LLM guidance fields.

    Args:
        response: Error response dictionary

    Returns:
        True if response contains proper LLM guidance, False otherwise
    """
    required_fields = [
        "success",
        "error",
        "code",
        "severity",
        "recoverable",
        "timestamp",
    ]

    # Check required fields
    for field in required_fields:
        if field not in response:
            return False

    # Validate that success is False for error responses
    if response.get("success") is not False:
        return False

    # Check that suggestions are provided for better LLM guidance
    if not response.get("suggestions"):
        return False

    # Validate severity is valid enum value
    return response.get("severity") in [s.value for s in ErrorSeverity]


def enhance_legacy_error_response(
    legacy_response: dict[str, Any],
    suggestions: list[str] | None = None,
    context: dict[str, Any] | None = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
) -> dict[str, Any]:
    """
    Enhance a legacy error response with LLM-optimized fields.

    Args:
        legacy_response: Existing error response
        suggestions: Additional suggestions for LLMs
        context: Additional context information
        severity: Error severity level

    Returns:
        Enhanced error response with LLM optimization
    """
    enhanced = legacy_response.copy()

    # Add LLM-optimized fields
    if suggestions:
        enhanced["suggestions"] = suggestions

    if context:
        enhanced["context"] = context

    enhanced["severity"] = severity.value
    enhanced["recoverable"] = True  # Default assumption
    enhanced["timestamp"] = datetime.now(timezone.utc).isoformat()

    return enhanced


def create_llm_friendly_validation_error(
    field_errors: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Create LLM-friendly validation error from field validation errors.

    Args:
        field_errors: List of field validation error dictionaries

    Returns:
        LLM-optimized validation error response
    """
    # Create comprehensive suggestions based on field errors
    suggestions: list[str] = []
    context: dict[str, Any] = {"invalid_fields": []}

    for field_error in field_errors:
        field_name = field_error.get("field", "unknown")
        error_message = field_error.get("message", "Invalid value")

        suggestions.append(f"Fix {field_name}: {error_message}")
        context["invalid_fields"].append(
            {
                "field": field_name,
                "error": error_message,
                "provided_value": field_error.get("value", None),
            }
        )

    # Add general guidance
    suggestions.extend(
        [
            "Check the API documentation for correct parameter formats",
            "Validate input data before making requests",
            "Use proper data types for each field",
        ]
    )

    return create_llm_error_response(
        error=f"Validation failed for {len(field_errors)} field(s)",
        code="VALIDATION_ERROR",
        suggestions=suggestions,
        context=context,
        severity=ErrorSeverity.WARNING,
        related_resources=["api_documentation"],
    )


def get_error_recovery_suggestions(error_code: str) -> list[str]:
    """
    Get recovery suggestions for a specific error code.

    Args:
        error_code: Error code to get suggestions for

    Returns:
        List of recovery suggestions for LLMs
    """
    recovery_map = {
        "SESSION_NOT_FOUND": [
            "Create a new session with create_session",
            "Verify the session ID format is correct",
            "Check if the session was recently created",
        ],
        "PERMISSION_DENIED": [
            "Re-authenticate with authenticate_agent",
            "Request higher permissions from user",
            "Use operations that require lower permissions",
        ],
        "INVALID_INPUT_FORMAT": [
            "Check the parameter format requirements",
            "Validate input data before sending",
            "Review the API documentation",
        ],
        "CONTENT_TOO_LARGE": [
            "Split content into smaller chunks",
            "Reduce content length",
            "Use file attachments for large data",
        ],
        "DATABASE_UNAVAILABLE": [
            "Retry the operation after a short delay",
            "Check system status",
            "Contact system administrator",
        ],
    }

    return recovery_map.get(
        error_code,
        [
            "Review the error message for specific guidance",
            "Check the API documentation",
            "Contact support if the issue persists",
        ],
    )
