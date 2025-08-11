"""
Utilities package for Shared Context Server.

Contains utility modules including error handling, caching, and other helper functions.
"""

from .llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    ErrorSeverity,
    LLMOptimizedErrorResponse,
    create_enhanced_error_response,
    create_input_validation_error,
    create_llm_error_response,
    create_permission_denied_error,
    create_resource_not_found_error,
    create_system_error,
)

__all__ = [
    "ErrorSeverity",
    "LLMOptimizedErrorResponse",
    "create_llm_error_response",
    "create_input_validation_error",
    "create_resource_not_found_error",
    "create_permission_denied_error",
    "create_system_error",
    "ERROR_MESSAGE_PATTERNS",
    "create_enhanced_error_response",
]
