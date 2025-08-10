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
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, validator

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


def validate_json_metadata(metadata: Optional[dict[str, Any]]) -> Optional[str]:
    """
    Validate and serialize metadata as JSON string.

    Returns None for empty metadata, JSON string otherwise.
    Replaces SQL json_valid() constraint with proper validation.
    """
    if metadata is None:
        return None

    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary")

    # Validate metadata structure
    if len(metadata) > 50:  # Reasonable limit
        raise ValueError("Metadata cannot have more than 50 keys")

    for key, value in metadata.items():
        if not isinstance(key, str):
            raise ValueError("Metadata keys must be strings")

        if len(key) > 100:
            raise ValueError("Metadata keys cannot exceed 100 characters")

        # Validate value types (JSON serializable)
        if not _is_json_serializable(value):
            raise ValueError(f"Metadata value for key '{key}' is not JSON serializable")

    try:
        json_str = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))

        # Reasonable size limit for metadata
        if len(json_str) > 10000:  # 10KB limit
            raise ValueError("Metadata JSON too large (max 10KB)")

        return json_str

    except (TypeError, ValueError) as e:
        raise ValueError(f"Metadata serialization failed: {e}")


def _is_json_serializable(value: Any) -> bool:
    """Check if value is JSON serializable."""
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


def sanitize_text_input(text: str) -> str:
    """Sanitize text input for security and consistency."""
    if not isinstance(text, str):
        text = str(text)

    # Strip whitespace
    text = text.strip()

    # Basic security: remove null bytes and control characters (except newlines/tabs)
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")

    return text


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

        return dt

    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}, error: {e}")


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
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Session metadata"
    )

    @validator("id")
    def validate_session_id_format(cls, v):
        return validate_session_id(v)

    @validator("created_by")
    def validate_created_by_format(cls, v):
        return validate_agent_id(v)

    @validator("purpose")
    def sanitize_purpose(cls, v):
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Purpose cannot be empty after sanitization")
        return v

    @validator("created_at", "updated_at")
    def ensure_utc_timezone(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MessageModel(BaseModel):
    """
    Message model with enhanced validation and security.
    """

    id: Optional[int] = Field(None, description="Auto-generated message ID")
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
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Message metadata"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_message_id: Optional[int] = Field(
        None, description="Parent message ID for threading"
    )

    @validator("session_id")
    def validate_session_id_format(cls, v):
        return validate_session_id(v)

    @validator("sender")
    def validate_sender_format(cls, v):
        return validate_agent_id(v)

    @validator("content")
    def sanitize_content(cls, v):
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Content cannot be empty after sanitization")
        return v

    @validator("timestamp")
    def ensure_utc_timezone(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @validator("parent_message_id")
    def validate_parent_message_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Parent message ID must be positive")
        return v

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentMemoryModel(BaseModel):
    """
    Agent memory model with TTL and scope validation.
    """

    id: Optional[int] = Field(None, description="Auto-generated memory ID")
    agent_id: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH, description="Agent ID"
    )
    session_id: Optional[str] = Field(
        None, description="Session ID for scoped memory (null for global)"
    )
    key: str = Field(
        ..., min_length=1, max_length=MAX_MEMORY_KEY_LENGTH, description="Memory key"
    )
    value: str = Field(..., min_length=1, description="Memory value (JSON string)")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Memory metadata"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    @validator("agent_id")
    def validate_agent_id_format(cls, v):
        return validate_agent_id(v)

    @validator("session_id")
    def validate_session_id_format(cls, v):
        if v is not None:
            return validate_session_id(v)
        return v

    @validator("key")
    def validate_memory_key(cls, v):
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Memory key cannot be empty after sanitization")

        # Validate key format (no special characters that could cause issues)
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError("Memory key contains invalid characters")

        return v

    @validator("value")
    def validate_json_value(cls, v):
        """Validate that value is valid JSON string."""
        try:
            json.loads(v)
            return v
        except (json.JSONDecodeError, TypeError):
            raise ValueError("Memory value must be valid JSON string")

    @validator("created_at", "updated_at")
    def ensure_utc_timezone(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @validator("expires_at")
    def validate_expiration(cls, v, values):
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)

            # Validate expiration is in the future
            created_at = values.get("created_at")
            if created_at and v <= created_at:
                raise ValueError("Expiration time must be after creation time")

        return v

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AuditLogModel(BaseModel):
    """
    Audit log model for security and debugging.
    """

    id: Optional[int] = Field(None, description="Auto-generated log ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = Field(
        ..., min_length=1, max_length=MAX_EVENT_TYPE_LENGTH, description="Event type"
    )
    agent_id: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH, description="Agent ID"
    )
    session_id: Optional[str] = Field(None, description="Session ID if applicable")
    resource: Optional[str] = Field(
        None, max_length=500, description="Resource involved"
    )
    action: Optional[str] = Field(None, max_length=200, description="Action performed")
    result: Optional[str] = Field(None, max_length=100, description="Action result")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Event metadata"
    )

    @validator("agent_id")
    def validate_agent_id_format(cls, v):
        return validate_agent_id(v)

    @validator("session_id")
    def validate_session_id_format(cls, v):
        if v is not None:
            return validate_session_id(v)
        return v

    @validator("event_type", "action", "result")
    def sanitize_text_fields(cls, v):
        if v is not None:
            v = sanitize_text_input(v)
            if not v:
                raise ValueError("Field cannot be empty after sanitization")
        return v

    @validator("timestamp")
    def ensure_utc_timezone(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    purpose: str = Field(..., min_length=1, max_length=MAX_PURPOSE_LENGTH)
    metadata: Optional[dict[str, Any]] = None

    @validator("purpose")
    def sanitize_purpose(cls, v):
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Purpose cannot be empty")
        return v


class CreateSessionResponse(BaseModel):
    """Response model for session creation."""

    success: bool
    session_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    error: Optional[str] = None
    code: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AddMessageRequest(BaseModel):
    """Request model for adding a message."""

    session_id: str
    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    visibility: MessageVisibility = MessageVisibility.PUBLIC
    metadata: Optional[dict[str, Any]] = None
    parent_message_id: Optional[int] = None

    @validator("session_id")
    def validate_session_id_format(cls, v):
        return validate_session_id(v)

    @validator("content")
    def sanitize_content(cls, v):
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Content cannot be empty")
        return v

    class Config:
        use_enum_values = True


class AddMessageResponse(BaseModel):
    """Response model for message addition."""

    success: bool
    message_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    error: Optional[str] = None
    code: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SetMemoryRequest(BaseModel):
    """Request model for setting agent memory."""

    key: str = Field(..., min_length=1, max_length=MAX_MEMORY_KEY_LENGTH)
    value: Any = Field(..., description="JSON serializable value")
    session_id: Optional[str] = None
    expires_in: Optional[int] = Field(
        None, ge=1, le=31536000, description="TTL in seconds (max 1 year)"
    )
    metadata: Optional[dict[str, Any]] = None
    overwrite: bool = True

    @validator("session_id")
    def validate_session_id_format(cls, v):
        if v is not None:
            return validate_session_id(v)
        return v

    @validator("key")
    def validate_memory_key(cls, v):
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Memory key cannot be empty")

        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError("Memory key contains invalid characters")

        return v

    @validator("value")
    def validate_json_serializable(cls, v):
        """Ensure value is JSON serializable."""
        try:
            json.dumps(v)
            return v
        except (TypeError, ValueError):
            raise ValueError("Value must be JSON serializable")


class GetMemoryRequest(BaseModel):
    """Request model for getting agent memory."""

    key: str = Field(..., min_length=1, max_length=MAX_MEMORY_KEY_LENGTH)
    session_id: Optional[str] = None

    @validator("session_id")
    def validate_session_id_format(cls, v):
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

    @validator("session_id")
    def validate_session_id_format(cls, v):
        return validate_session_id(v)

    @validator("query")
    def sanitize_query(cls, v):
        v = sanitize_text_input(v)
        if not v:
            raise ValueError("Search query cannot be empty")
        return v


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def create_standard_response(success: bool, **kwargs) -> dict[str, Any]:
    """Create standard API response format."""
    response = {"success": success, "timestamp": datetime.now(timezone.utc).isoformat()}
    response.update(kwargs)
    return response


def create_error_response(error: str, code: str, **kwargs) -> dict[str, Any]:
    """Create standard error response format."""
    return create_standard_response(success=False, error=error, code=code, **kwargs)


def serialize_metadata(metadata: Optional[dict[str, Any]]) -> Optional[str]:
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


def deserialize_metadata(metadata_str: Optional[str]) -> Optional[dict[str, Any]]:
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
        return json.loads(metadata_str)
    except (json.JSONDecodeError, TypeError):
        return None  # Return None for invalid JSON rather than raising


def validate_model_dict(model_class: BaseModel, data: dict[str, Any]) -> BaseModel:
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
        raise ValueError(f"Validation failed for {model_class.__name__}: {e}")
