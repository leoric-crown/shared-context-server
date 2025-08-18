"""
Utility functions for Shared Context MCP Server models.

This module contains utility functions for model validation, serialization,
error handling, and response creation.

Extracted from models.py for better maintainability while preserving
all existing functionality and public interfaces.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pydantic import BaseModel

# Import core validation functions
from .models_core import (
    sanitize_text_input,
    validate_json_metadata,
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def create_standard_response(success: bool, **kwargs: Any) -> dict[str, Any]:
    """Create standard API response format."""
    response = {"success": success, "timestamp": datetime.now(timezone.utc).isoformat()}
    response.update(kwargs)
    return response


def create_error_response(error: str, code: str, **kwargs: Any) -> dict[str, Any]:
    """Create standard error response format."""
    return create_standard_response(success=False, error=error, code=code, **kwargs)


def serialize_metadata(metadata: dict[str, Any] | None) -> str | None:
    """
    Serialize metadata for database storage.

    Args:
        metadata: Metadata dictionary

    Returns:
        JSON string or None

    Raises:
        ValueError: If metadata is invalid
    """
    return validate_json_metadata(metadata)


def deserialize_metadata(metadata_str: str | None) -> dict[str, Any] | None:
    """
    Deserialize metadata from database storage.

    Args:
        metadata_str: JSON string from database

    Returns:
        Metadata dictionary or None
    """
    if not metadata_str:
        return None

    try:
        return cast("dict[str, Any]", json.loads(metadata_str))
    except (json.JSONDecodeError, TypeError):
        return None  # Return None for invalid JSON rather than raising


def validate_model_dict(
    model_class: type[BaseModel],
    data: dict[str, Any],
) -> BaseModel:
    """
    Validate dictionary data against Pydantic model.

    Args:
        model_class: Pydantic model class
        data: Dictionary data to validate

    Returns:
        Validated model instance

    Raises:
        ValueError: If validation fails
    """
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"Validation failed for {model_class.__name__}: {e}") from e


def sanitize_search_input(query: str, max_length: int = 500) -> str:
    """
    Sanitize search query input for security and performance.

    Args:
        query: Search query string
        max_length: Maximum allowed length

    Returns:
        Sanitized query string

    Raises:
        ValueError: If query is invalid after sanitization
    """
    # Basic sanitization
    query = sanitize_text_input(query)

    # Remove potentially problematic patterns for fuzzy search
    # Remove excessive whitespace
    query = re.sub(r"\s+", " ", query)

    # Limit length for performance
    if len(query) > max_length:
        query = query[:max_length]

    if not query:
        raise ValueError("Search query cannot be empty after sanitization")

    return query


def sanitize_memory_key(key: str) -> str:
    """
    Sanitize memory key for storage and security.

    Args:
        key: Memory key string

    Returns:
        Sanitized key string

    Raises:
        ValueError: If key is invalid after sanitization
    """
    key = sanitize_text_input(key)

    if not key:
        raise ValueError("Memory key cannot be empty after sanitization")

    # Validate key format (alphanumeric with limited special chars)
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", key):
        raise ValueError(
            "Memory key contains invalid characters. Use alphanumeric, underscore, dot, or hyphen."
        )

    return key


def _raise_metadata_type_error(parsed_type: str) -> None:
    """Helper function to raise metadata type error."""
    raise TypeError(
        f"Metadata string must parse to a dictionary object, got {parsed_type}"
    )


def parse_mcp_metadata(metadata: Any) -> dict[str, Any] | None:
    """
    Parse metadata parameter from MCP client requests.

    MCP clients may send metadata as JSON strings when using Any type annotations,
    while direct API calls send dict objects. This function handles both cases.

    Args:
        metadata: Metadata from MCP request (str, dict, or None)

    Returns:
        Parsed metadata dictionary or None

    Raises:
        ValueError: If metadata is not a valid dictionary or None
    """
    if metadata is None:
        return None

    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
            if not isinstance(parsed, dict):
                _raise_metadata_type_error(type(parsed).__name__)
            return cast("dict[str, Any]", parsed)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid JSON in metadata parameter: {e}") from e

    # Validate that non-string metadata is actually a dict
    if not isinstance(metadata, dict):
        raise TypeError(
            f"Metadata must be a dictionary object or null, got {type(metadata).__name__}"
        )

    return cast("dict[str, Any]", metadata)


def validate_json_serializable_value(value: Any) -> Any:
    """
    Validate that a value is JSON serializable.

    Args:
        value: Value to validate

    Returns:
        The value if valid

    Raises:
        ValueError: If value is not JSON serializable
    """
    try:
        json.dumps(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Value is not JSON serializable: {e}") from e
    else:
        return value


# ============================================================================
# VALIDATION ERROR HANDLING
# ============================================================================


def create_validation_error_response(
    errors: list[Any], message: str = "Validation failed"
) -> Any:
    """
    Create a comprehensive validation error response.

    Args:
        errors: List of validation error details
        message: General error message

    Returns:
        ValidationErrorResponse with detailed error information
    """
    from .models_requests import ValidationErrorResponse

    return ValidationErrorResponse(error=message, details=errors)


def extract_pydantic_validation_errors(exc: Exception) -> list[Any]:
    """
    Extract validation errors from Pydantic ValidationError.

    Args:
        exc: Pydantic ValidationError exception

    Returns:
        List of ValidationErrorDetail objects
    """
    from .models_requests import ValidationErrorDetail

    details = []

    # Handle Pydantic ValidationError
    if hasattr(exc, "errors"):
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error.get("loc", []))
            details.append(
                ValidationErrorDetail(
                    field=field_path or "unknown",
                    message=error.get("msg", "Validation failed"),
                    invalid_value=None,
                    expected_type=error.get("type", None),
                )
            )
    else:
        # Generic validation error
        details.append(
            ValidationErrorDetail(
                field="unknown",
                message=str(exc),
                invalid_value=None,
                expected_type=None,
            )
        )

    return details
