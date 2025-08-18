"""
Request and Response models for Shared Context MCP Server API.

This module contains all the Pydantic models used for API requests and responses,
including validation, search operations, and memory management.

Extracted from models.py for better maintainability while preserving
all existing functionality and public interfaces.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

# Import core models and validation functions
from .models_core import (
    MAX_AGENT_ID_LENGTH,
    MAX_CONTENT_LENGTH,
    MAX_MEMORY_KEY_LENGTH,
    MAX_PURPOSE_LENGTH,
    MessageVisibility,
    sanitize_text_input,
    validate_agent_id,
    validate_session_id,
    validate_utc_timestamp,
)

# ============================================================================
# SESSION MANAGEMENT REQUESTS/RESPONSES
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


# ============================================================================
# MESSAGE MANAGEMENT REQUESTS/RESPONSES
# ============================================================================


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


# ============================================================================
# MEMORY MANAGEMENT REQUESTS/RESPONSES
# ============================================================================


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
        import re

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


# ============================================================================
# SEARCH REQUESTS/RESPONSES
# ============================================================================


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


# ============================================================================
# RESOURCE AND VALIDATION MODELS
# ============================================================================


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
