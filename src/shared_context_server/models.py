"""
Pydantic models with enhanced validation for Shared Context MCP Server.

This module addresses critical validation issues identified in consultant review:
- Moves REGEXP validation from SQL CHECK constraints to Pydantic models
- Adds comprehensive JSON validation for metadata fields
- Implements proper input sanitization and type checking
- Provides UTC timestamp handling and validation
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

# Session ID pattern (moved from SQL REGEXP constraint)
SESSION_ID_PATTERN = r"^session_[a-f0-9]{16}$"

# Agent ID pattern for validation
AGENT_ID_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$"

# Maximum lengths for text fields
MAX_PURPOSE_LENGTH = 1000
MAX_CONTENT_LENGTH = 100000
MAX_AGENT_ID_LENGTH = 100
MAX_MEMORY_KEY_LENGTH = 255
MAX_EVENT_TYPE_LENGTH = 100


class MessageVisibility(str, Enum):
    """Message visibility levels with clear definitions."""

    PUBLIC = "public"  # Visible to all agents in session
    PRIVATE = "private"  # Visible only to sender
    AGENT_ONLY = "agent_only"  # Visible to agents of same type
    ADMIN_ONLY = "admin_only"  # Visible only to agents with admin permission


class MessageType(str, Enum):
    """Message type categories."""

    AGENT_RESPONSE = "agent_response"
    HUMAN_INPUT = "human_input"
    SYSTEM_STATUS = "system_status"
    TOOL_OUTPUT = "tool_output"
    COORDINATION = "coordination"


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================


def validate_session_id(session_id: str) -> str:
    """Validate session ID format (replaces SQL REGEXP constraint)."""
    if not re.match(SESSION_ID_PATTERN, session_id):
        raise ValueError(f"Invalid session ID format: {session_id}")
    return session_id


def validate_agent_id(agent_id: str) -> str:
    """Validate agent ID format."""
    if not re.match(AGENT_ID_PATTERN, agent_id):
        raise ValueError(f"Invalid agent ID format: {agent_id}")
    return agent_id


def validate_json_metadata(metadata: dict[str, Any] | None) -> str | None:
    """
    Validate and serialize metadata as JSON string.

    Returns None for empty metadata, JSON string otherwise.
    Replaces SQL json_valid() constraint with proper validation.
    """
    if metadata is None:
        return None

    if not isinstance(metadata, dict):
        raise TypeError("Metadata must be a dictionary")

    # Validate metadata structure
    if len(metadata) > 50:  # Reasonable limit
        raise ValueError("Metadata cannot have more than 50 keys")

    for key, value in metadata.items():
        if not isinstance(key, str):
            raise TypeError("Metadata keys must be strings")

        if len(key) > 100:
            raise ValueError("Metadata keys cannot exceed 100 characters")

        # Validate value types (JSON serializable)
        if not _is_json_serializable(value):
            raise ValueError(f"Metadata value for key '{key}' is not JSON serializable")

    try:
        json_str = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))

        # Reasonable size limit for metadata
        if len(json_str) > 10000:  # 10KB limit
            _raise_metadata_too_large_error()

    except (TypeError, ValueError) as e:
        raise ValueError(f"Metadata serialization failed: {e}") from e
    else:
        return json_str


def _raise_metadata_too_large_error() -> None:
    """Raise a metadata too large error."""
    raise ValueError("Metadata JSON too large (max 10KB)")


def _is_json_serializable(value: Any) -> bool:
    """Check if value is JSON serializable."""
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    else:
        return True


def sanitize_text_input(text: str) -> str:
    """Sanitize text input for security and consistency."""
    # Input is guaranteed to be str by type annotation

    # Strip whitespace
    text = text.strip()

    # Basic security: remove null bytes and control characters (except newlines/tabs)
    return "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")


def validate_utc_timestamp(timestamp_str: str) -> datetime:
    """
    Validate and parse UTC timestamp string.

    Args:
        timestamp_str: ISO timestamp string

    Returns:
        UTC datetime object

    Raises:
        ValueError: If timestamp format is invalid
    """
    try:
        # Handle various timestamp formats
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        elif "+" not in timestamp_str and "T" in timestamp_str:
            timestamp_str += "+00:00"

        dt = datetime.fromisoformat(timestamp_str)

        # Ensure UTC timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

    except ValueError as e:
        raise ValueError(
            f"Invalid timestamp format: {timestamp_str}, error: {e}"
        ) from e
    else:
        return dt


# ============================================================================
# CORE DATA MODELS
# ============================================================================


class SessionModel(BaseModel):
    """
    Session model with enhanced validation.

    Replaces SQL REGEXP constraints with Pydantic validation.
    """

    id: str = Field(..., description="Unique session identifier")
    purpose: str = Field(
        ..., min_length=1, max_length=MAX_PURPOSE_LENGTH, description="Session purpose"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True, description="Whether session is active")
    created_by: str = Field(
        ...,
        min_length=1,
        max_length=MAX_AGENT_ID_LENGTH,
        description="Agent who created session",
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Session metadata"
    )

    @field_validator("id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        return validate_session_id(v)

    @field_validator("created_by")
    @classmethod
    def validate_created_by_format(cls, v: str) -> str:
        return validate_agent_id(v)

    @field_validator("purpose")
    @classmethod
    def sanitize_purpose(cls, v: str) -> str:
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Purpose cannot be empty after sanitization")
        return v

    @field_validator("created_at", "updated_at")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    model_config = ConfigDict()

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class MessageModel(BaseModel):
    """
    Message model with enhanced validation and security.
    """

    id: int | None = Field(None, description="Auto-generated message ID")
    session_id: str = Field(..., description="Session ID")
    sender: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH, description="Message sender"
    )
    content: str = Field(
        ..., min_length=1, max_length=MAX_CONTENT_LENGTH, description="Message content"
    )
    visibility: MessageVisibility = Field(
        default=MessageVisibility.PUBLIC, description="Message visibility"
    )
    message_type: MessageType = Field(
        default=MessageType.AGENT_RESPONSE, description="Message type"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Message metadata"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_message_id: int | None = Field(
        None, description="Parent message ID for threading"
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        return validate_session_id(v)

    @field_validator("sender")
    @classmethod
    def validate_sender_format(cls, v: str) -> str:
        return validate_agent_id(v)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Content cannot be empty after sanitization")
        return v

    @field_validator("timestamp")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("parent_message_id")
    @classmethod
    def validate_parent_message_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Parent message ID must be positive")
        return v

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("timestamp", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class AgentMemoryModel(BaseModel):
    """
    Agent memory model with TTL and scope validation.
    """

    id: int | None = Field(None, description="Auto-generated memory ID")
    agent_id: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH, description="Agent ID"
    )
    session_id: str | None = Field(
        None, description="Session ID for scoped memory (null for global)"
    )
    key: str = Field(
        ..., min_length=1, max_length=MAX_MEMORY_KEY_LENGTH, description="Memory key"
    )
    value: str = Field(..., min_length=1, description="Memory value (JSON string)")
    metadata: dict[str, Any] | None = Field(default=None, description="Memory metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = Field(None, description="Expiration timestamp")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id_format(cls, v: str) -> str:
        return validate_agent_id(v)

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_session_id(v)
        return v

    @field_validator("key")
    @classmethod
    def validate_memory_key(cls, v: str) -> str:
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Memory key cannot be empty after sanitization")

        # Validate key format (no special characters that could cause issues)
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError("Memory key contains invalid characters")

        return v

    @field_validator("value")
    @classmethod
    def validate_json_value(cls, v: str) -> str:
        """Validate that value is valid JSON string."""
        try:
            json.loads(v)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError("Memory value must be valid JSON string") from e
        else:
            return v

    @field_validator("created_at", "updated_at")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("expires_at")
    @classmethod
    def validate_expiration_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)
        return v

    @model_validator(mode="after")
    def validate_expiration_time(self) -> AgentMemoryModel:
        if (
            self.expires_at is not None
            and self.created_at is not None
            and self.expires_at <= self.created_at
        ):
            raise ValueError("Expiration time must be after creation time")
        return self

    model_config = ConfigDict()

    @field_serializer("created_at", "updated_at", "expires_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class AuditLogModel(BaseModel):
    """
    Audit log model for security and debugging.
    """

    id: int | None = Field(None, description="Auto-generated log ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = Field(
        ..., min_length=1, max_length=MAX_EVENT_TYPE_LENGTH, description="Event type"
    )
    agent_id: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH, description="Agent ID"
    )
    session_id: str | None = Field(None, description="Session ID if applicable")
    resource: str | None = Field(None, max_length=500, description="Resource involved")
    action: str | None = Field(None, max_length=200, description="Action performed")
    result: str | None = Field(None, max_length=100, description="Action result")
    metadata: dict[str, Any] | None = Field(default=None, description="Event metadata")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id_format(cls, v: str) -> str:
        return validate_agent_id(v)

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_session_id(v)
        return v

    @field_validator("event_type", "action", "result")
    @classmethod
    def sanitize_text_fields(cls, v: str | None) -> str | None:
        if v is not None:
            v = sanitize_text_input(v)
            if not v:
                raise ValueError("Field cannot be empty after sanitization")
        return v

    @field_validator("timestamp")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    model_config = ConfigDict()

    @field_serializer("timestamp", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    purpose: str = Field(..., min_length=1, max_length=MAX_PURPOSE_LENGTH)
    metadata: dict[str, Any] | None = None

    @field_validator("purpose")
    @classmethod
    def sanitize_purpose(cls, v: str) -> str:
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Purpose cannot be empty")
        return v


class CreateSessionResponse(BaseModel):
    """Response model for session creation."""

    success: bool
    session_id: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    error: str | None = None
    code: str | None = None

    model_config = ConfigDict()

    @field_serializer("created_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class AddMessageRequest(BaseModel):
    """Request model for adding a message."""

    session_id: str
    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    visibility: MessageVisibility = MessageVisibility.PUBLIC
    metadata: dict[str, Any] | None = None
    parent_message_id: int | None = None

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        return validate_session_id(v)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Content cannot be empty")
        return v

    model_config = ConfigDict(use_enum_values=True)


class AddMessageResponse(BaseModel):
    """Response model for message addition."""

    success: bool
    message_id: int | None = None
    timestamp: datetime | None = None
    error: str | None = None
    code: str | None = None

    model_config = ConfigDict()

    @field_serializer("timestamp", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class SetMemoryRequest(BaseModel):
    """Request model for setting agent memory."""

    key: str = Field(..., min_length=1, max_length=MAX_MEMORY_KEY_LENGTH)
    value: Any = Field(..., description="JSON serializable value")
    session_id: str | None = None
    expires_in: int | None = Field(
        None, ge=1, le=31536000, description="TTL in seconds (max 1 year)"
    )
    metadata: dict[str, Any] | None = None
    overwrite: bool = True

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_session_id(v)
        return v

    @field_validator("key")
    @classmethod
    def validate_memory_key(cls, v: str) -> str:
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Memory key cannot be empty")

        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError("Memory key contains invalid characters")

        return v

    @field_validator("value")
    @classmethod
    def validate_json_serializable(cls, v: Any) -> Any:
        """Ensure value is JSON serializable."""
        try:
            json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError("Value must be JSON serializable") from e
        else:
            return v


class GetMemoryRequest(BaseModel):
    """Request model for getting agent memory."""

    key: str = Field(..., min_length=1, max_length=MAX_MEMORY_KEY_LENGTH)
    session_id: str | None = None

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_session_id(v)
        return v


class SearchContextRequest(BaseModel):
    """Request model for context search."""

    session_id: str
    query: str = Field(..., min_length=1, max_length=500)
    fuzzy_threshold: float = Field(default=60.0, ge=0, le=100)
    limit: int = Field(default=10, ge=1, le=100)
    search_metadata: bool = True
    search_scope: Literal["all", "public", "private"] = "all"

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        return validate_session_id(v)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Search query cannot be empty")
        return v


class SearchResponse(BaseModel):
    """Response model for search operations."""

    success: bool = True
    results: list[dict[str, Any]] = Field(default_factory=list)
    query: str
    threshold: float
    search_scope: str
    message_count: int
    search_time_ms: float
    performance_note: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("timestamp", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class SearchBySenderRequest(BaseModel):
    """Request model for search by sender."""

    session_id: str
    sender: str = Field(..., min_length=1, max_length=MAX_AGENT_ID_LENGTH)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        return validate_session_id(v)

    @field_validator("sender")
    @classmethod
    def validate_sender_format(cls, v: str) -> str:
        return validate_agent_id(v)


class SearchByTimerangeRequest(BaseModel):
    """Request model for search by time range."""

    session_id: str
    start_time: str = Field(..., description="Start time (ISO format)")
    end_time: str = Field(..., description="End time (ISO format)")
    limit: int = Field(default=50, ge=1, le=200)

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        return validate_session_id(v)

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timestamp_format(cls, v: str) -> str:
        # Validate ISO timestamp format
        try:
            validate_utc_timestamp(v)
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {e}") from e
        else:
            return v


class MemorySetResponse(BaseModel):
    """Response model for memory set operation."""

    success: bool = True
    key: str
    session_scoped: bool
    expires_at: float | None = None
    scope: Literal["session", "global"]
    stored_at: str
    error: str | None = None
    code: str | None = None


class MemoryGetResponse(BaseModel):
    """Response model for memory get operation."""

    success: bool = True
    key: str
    value: Any
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    expires_at: float | None = None
    scope: Literal["session", "global"]
    error: str | None = None
    code: str | None = None


class MemoryListRequest(BaseModel):
    """Request model for listing memory entries."""

    session_id: str | None = Field(
        default=None, description="Session scope (null for global, 'all' for both)"
    )
    prefix: str | None = Field(
        default=None, max_length=100, description="Key prefix filter"
    )
    limit: int = Field(default=50, ge=1, le=200)

    @field_validator("session_id")
    @classmethod
    def validate_session_id_format(cls, v: str | None) -> str | None:
        if v is not None and v != "all":
            return validate_session_id(v)
        return v

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str | None) -> str | None:
        if v is not None:
            v = sanitize_text_input(v)
            if not v:
                raise ValueError("Prefix cannot be empty after sanitization")
        return v


class MemoryListResponse(BaseModel):
    """Response model for memory list operation."""

    success: bool = True
    entries: list[dict[str, Any]] = Field(default_factory=list)
    count: int
    scope_filter: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("timestamp", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ResourceModel(BaseModel):
    """Model for MCP resource data."""

    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Resource description")
    mime_type: str = Field(default="application/json", description="MIME type")
    content: dict[str, Any] = Field(..., description="Resource content")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    supports_subscriptions: bool = Field(default=True)

    @field_validator("uri")
    @classmethod
    def validate_uri_format(cls, v: str) -> str:
        """Validate resource URI format."""
        if not v.startswith(("session://", "agent://")):
            raise ValueError("URI must start with session:// or agent://")
        return v

    @field_serializer("last_updated", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information."""

    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    invalid_value: str | None = Field(
        None, description="The invalid value (if safe to expose)"
    )
    expected_type: str | None = Field(None, description="Expected type or format")


class ValidationErrorResponse(BaseModel):
    """Comprehensive validation error response."""

    success: bool = False
    error: str = "Validation failed"
    code: str = "VALIDATION_ERROR"
    details: list[ValidationErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("timestamp", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


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
    model_class: type[BaseModel], data: dict[str, Any]
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
    # Input is guaranteed to be str by type annotation

    # Basic sanitization
    query = sanitize_text_input(query)

    # Remove potentially problematic patterns for fuzzy search
    import re

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
    # Input is guaranteed to be str by type annotation

    key = sanitize_text_input(key)

    if not key:
        raise ValueError("Memory key cannot be empty after sanitization")

    # Validate key format (alphanumeric with limited special chars)
    import re

    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", key):
        raise ValueError(
            "Memory key contains invalid characters. Use alphanumeric, underscore, dot, or hyphen."
        )

    return key


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


def create_validation_error_response(
    errors: list[ValidationErrorDetail], message: str = "Validation failed"
) -> ValidationErrorResponse:
    """
    Create a comprehensive validation error response.

    Args:
        errors: List of validation error details
        message: General error message

    Returns:
        ValidationErrorResponse with detailed error information
    """
    return ValidationErrorResponse(error=message, details=errors)


def extract_pydantic_validation_errors(exc: Exception) -> list[ValidationErrorDetail]:
    """
    Extract validation errors from Pydantic ValidationError.

    Args:
        exc: Pydantic ValidationError exception

    Returns:
        List of ValidationErrorDetail objects
    """
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
