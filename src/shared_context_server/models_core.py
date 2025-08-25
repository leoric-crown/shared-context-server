"""
Core Pydantic models for Shared Context MCP Server.

This module contains the primary data models that represent the core entities
in the system: sessions, messages, agent memory, and audit logs.

Extracted from models.py for better maintainability while preserving
all existing functionality and public interfaces.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, cast

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
    AGENT_ONLY = "agent_only"  # Visible only to agents of same type
    ADMIN_ONLY = "admin_only"  # Visible only to admins


class MessageType(str, Enum):
    """Message type enumeration with clear categories."""

    USER_MESSAGE = "user_message"
    SYSTEM_MESSAGE = "system_message"
    AGENT_RESPONSE = "agent_response"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================


def validate_session_id(session_id: str) -> str:
    """Validate session ID format (moved from SQL constraint)."""
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
    Validate and serialize metadata to JSON string.

    This replaces SQL CHECK constraints with proper Pydantic validation.
    Ensures metadata is valid JSON and within size limits.
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

    # Check for recursive structures or deeply nested objects
    try:
        # First validate it's JSON serializable
        json_str = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as e:
        raise ValueError(f"Metadata is not JSON serializable: {e}") from e

    # Check size limit (10KB JSON string limit)
    if len(json_str) > 10000:
        _raise_metadata_too_large_error()

    return json_str


def _raise_metadata_too_large_error() -> None:
    """Raise metadata size error."""
    raise ValueError("Metadata JSON too large")


def _raise_invalid_json_type_error() -> None:
    """Raise error for JSON that doesn't deserialize to a dictionary."""
    raise TypeError("JSON string must deserialize to a dictionary")


def _is_json_serializable(value: Any) -> bool:
    """Check if a value is JSON serializable."""
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


def sanitize_text_input(text: str) -> str:
    """
    Sanitize text input by removing or escaping dangerous characters.

    This provides additional protection beyond database parameterization.
    """
    # Remove null bytes and other control characters except newlines/tabs
    sanitized = "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")
    return sanitized.strip()


def validate_utc_timestamp(timestamp_str: str) -> datetime:
    """
    Validate and parse UTC timestamp string.

    Ensures all timestamps are properly formatted and in UTC timezone.
    """
    try:
        # Handle both with and without timezone info
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        elif "+" not in timestamp_str and "T" in timestamp_str:
            # Add UTC timezone if missing
            timestamp_str += "+00:00"

        dt = datetime.fromisoformat(timestamp_str)

        # Convert to UTC if not already
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        return dt
    except ValueError as e:
        raise ValueError(
            f"Invalid timestamp format: {timestamp_str}, error: {e}"
        ) from e


# ============================================================================
# CORE DATA MODELS
# ============================================================================


class SessionModel(BaseModel):
    """
    Session model with enhanced validation.

    Represents a collaboration session where multiple agents can participate.
    Includes proper validation for session IDs and metadata.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    id: str = Field(..., description="Unique session identifier")

    purpose: str = Field(
        ...,
        description="Purpose or description of the session",
        min_length=1,
        max_length=MAX_PURPOSE_LENGTH,
    )

    created_by: str = Field(
        ...,
        description="Agent ID that created the session",
        min_length=1,
        max_length=MAX_AGENT_ID_LENGTH,
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when session was created",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when session was last updated",
    )

    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata as JSON object"
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
    def validate_purpose_content(cls, v: str) -> str:
        return sanitize_text_input(v)

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_datetime_timezone(cls, v: datetime) -> datetime:
        """Ensure datetime fields have timezone info."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_json(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            # This will raise if invalid
            validate_json_metadata(v)
        return v

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime) -> str:
        return value.isoformat()


class MessageModel(BaseModel):
    """
    Message model with comprehensive validation.

    Represents messages exchanged between agents in a session.
    Includes content validation, visibility controls, and proper typing.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="ignore"
    )

    id: int | None = Field(default=None, description="Auto-generated message ID")

    session_id: str = Field(..., description="Session this message belongs to")

    sender: str = Field(
        ...,
        description="Agent ID that sent the message",
        min_length=1,
        max_length=MAX_AGENT_ID_LENGTH,
    )

    content: str = Field(
        ..., description="Message content", min_length=1, max_length=MAX_CONTENT_LENGTH
    )

    message_type: MessageType = Field(
        default=MessageType.AGENT_RESPONSE, description="Type of message"
    )

    visibility: MessageVisibility = Field(
        default=MessageVisibility.PUBLIC, description="Who can see this message"
    )

    parent_message_id: int | None = Field(
        default=None, description="ID of parent message for threading"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when message was created",
    )

    @property
    def timestamp(self) -> datetime:
        """Alias for created_at for backwards compatibility."""
        return self.created_at

    @model_validator(mode="before")
    @classmethod
    def handle_timestamp_alias(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Handle timestamp field as alias for created_at."""
        if isinstance(values, dict) and "timestamp" in values:
            if "created_at" not in values:
                values["created_at"] = values["timestamp"]
            del values["timestamp"]
        return values

    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata as JSON object"
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
    def validate_content_safety(cls, v: str) -> str:
        return sanitize_text_input(v)

    @field_validator("created_at")
    @classmethod
    def validate_created_at_timezone(cls, v: datetime) -> datetime:
        """Ensure created_at has timezone info."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        else:
            v = v.astimezone(timezone.utc)
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_json(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            validate_json_metadata(v)
        return v

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override model_dump to include timestamp alias."""
        data = super().model_dump(**kwargs)
        # Add timestamp as alias for created_at for backwards compatibility
        if "created_at" in data:
            data["timestamp"] = data["created_at"]
        return data


class AgentMemoryModel(BaseModel):
    """
    Agent memory model with TTL and security validation.

    Represents key-value storage for agents with optional TTL expiration
    and session scoping. Includes validation for memory keys and values.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    id: int | None = Field(default=None, description="Auto-generated memory entry ID")

    agent_id: str = Field(
        ...,
        description="Agent that owns this memory",
        min_length=1,
        max_length=MAX_AGENT_ID_LENGTH,
    )

    session_id: str | None = Field(
        default=None,
        description="Optional session scope for memory",
    )

    key: str = Field(
        ...,
        description="Memory key identifier",
        min_length=1,
        max_length=MAX_MEMORY_KEY_LENGTH,
    )

    value: dict[str, Any] | str = Field(
        ..., description="Memory value as JSON object or JSON string"
    )

    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional metadata as JSON object"
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when memory was created",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when memory was last updated",
    )

    expires_at: datetime | None = Field(
        default=None, description="Optional UTC timestamp when memory expires"
    )

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
    def validate_key_format(cls, v: str) -> str:
        # Memory keys should be simple identifiers
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError("Memory key contains invalid characters")
        return sanitize_text_input(v)

    @field_validator("value")
    @classmethod
    def validate_value_json(cls, v: dict[str, Any] | str) -> dict[str, Any]:
        # Handle both dict and JSON string inputs
        if isinstance(v, str):
            try:
                import json

                parsed_v = json.loads(v)
                if not isinstance(parsed_v, dict):
                    _raise_invalid_json_type_error()
                v = cast("dict[str, Any]", parsed_v)
            except (json.JSONDecodeError, TypeError) as e:
                raise ValueError(f"Invalid JSON string: {e}") from e

        # At this point, v is guaranteed to be dict[str, Any]
        validate_json_metadata(v)
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_json(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            validate_json_metadata(v)
        return v

    @model_validator(mode="after")
    def validate_expiration_time(self) -> AgentMemoryModel:
        """Validate that expiration time is in the future if set."""
        if self.expires_at is not None and self.expires_at <= self.created_at:
            raise ValueError("Expiration time must be after creation time")
        return self

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("expires_at")
    def serialize_expires_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class AuditLogModel(BaseModel):
    """
    Audit log model for security and compliance tracking.

    Tracks all significant actions in the system for security auditing
    and compliance purposes. Includes validation for event data.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    id: int | None = Field(
        default=None, description="Auto-generated audit log entry ID"
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when event occurred",
    )

    agent_id: str = Field(
        ...,
        description="Agent that performed the action",
        min_length=1,
        max_length=MAX_AGENT_ID_LENGTH,
    )

    session_id: str | None = Field(
        default=None,
        description="Optional session context",
    )

    event_type: str = Field(
        ...,
        description="Type of event being logged",
        min_length=1,
        max_length=MAX_EVENT_TYPE_LENGTH,
    )

    event_data: dict[str, Any] = Field(..., description="Event data as JSON object")

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

    @field_validator("event_type")
    @classmethod
    def validate_event_type_format(cls, v: str) -> str:
        # Event types should be simple identifiers
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError(f"Invalid event type format: {v}")
        return sanitize_text_input(v)

    @field_validator("event_data")
    @classmethod
    def validate_event_data_json(cls, v: dict[str, Any]) -> dict[str, Any]:
        # Validate the event data is JSON serializable
        validate_json_metadata(v)
        return v

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()
