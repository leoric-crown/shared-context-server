"""
Pydantic models with enhanced validation for Shared Context MCP Server.

This module serves as a facade for the refactored models, preserving all
existing functionality and public interfaces while organizing code into
specialized modules for better maintainability.

All models, validation functions, and utilities are re-exported from:
- models_core: Core data models and validation functions
- models_requests: Request/response models for API operations
- models_utilities: Utility functions and error handling
"""

from __future__ import annotations

# Re-export all constants, enums, and validation functions
# Re-export all core data models
from .models_core import (
    AGENT_ID_PATTERN,
    MAX_AGENT_ID_LENGTH,
    MAX_CONTENT_LENGTH,
    MAX_EVENT_TYPE_LENGTH,
    MAX_MEMORY_KEY_LENGTH,
    MAX_PURPOSE_LENGTH,
    SESSION_ID_PATTERN,
    AgentMemoryModel,
    AuditLogModel,
    MessageModel,
    MessageType,
    MessageVisibility,
    SessionModel,
    _is_json_serializable,
    _raise_metadata_too_large_error,
    sanitize_text_input,
    validate_agent_id,
    validate_json_metadata,
    validate_session_id,
    validate_utc_timestamp,
)

# Re-export all request/response models
from .models_requests import (
    AddMessageRequest,
    AddMessageResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    GetMemoryRequest,
    MemoryGetResponse,
    MemoryListRequest,
    MemoryListResponse,
    MemorySetResponse,
    ResourceModel,
    SearchBySenderRequest,
    SearchByTimerangeRequest,
    SearchContextRequest,
    SearchResponse,
    SetMemoryRequest,
    ValidationErrorDetail,
    ValidationErrorResponse,
)

# Re-export all utility functions
from .models_utilities import (
    create_error_response,
    create_standard_response,
    create_validation_error_response,
    deserialize_metadata,
    extract_pydantic_validation_errors,
    parse_mcp_metadata,
    sanitize_memory_key,
    sanitize_search_input,
    serialize_metadata,
    validate_json_serializable_value,
    validate_model_dict,
)

# Ensure all public interfaces remain available
__all__ = [
    # Constants and patterns
    "AGENT_ID_PATTERN",
    "MAX_AGENT_ID_LENGTH",
    "MAX_CONTENT_LENGTH",
    "MAX_EVENT_TYPE_LENGTH",
    "MAX_MEMORY_KEY_LENGTH",
    "MAX_PURPOSE_LENGTH",
    "SESSION_ID_PATTERN",
    # Enums
    "MessageType",
    "MessageVisibility",
    # Core data models
    "AgentMemoryModel",
    "AuditLogModel",
    "MessageModel",
    "SessionModel",
    # Request/response models
    "AddMessageRequest",
    "AddMessageResponse",
    "CreateSessionRequest",
    "CreateSessionResponse",
    "GetMemoryRequest",
    "MemoryGetResponse",
    "MemoryListRequest",
    "MemoryListResponse",
    "MemorySetResponse",
    "ResourceModel",
    "SearchBySenderRequest",
    "SearchByTimerangeRequest",
    "SearchContextRequest",
    "SearchResponse",
    "SetMemoryRequest",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    # Validation functions
    "sanitize_text_input",
    "validate_agent_id",
    "validate_json_metadata",
    "validate_session_id",
    "validate_utc_timestamp",
    # Utility functions
    "create_error_response",
    "create_standard_response",
    "create_validation_error_response",
    "deserialize_metadata",
    "extract_pydantic_validation_errors",
    "parse_mcp_metadata",
    "sanitize_memory_key",
    "sanitize_search_input",
    "serialize_metadata",
    "validate_json_serializable_value",
    "validate_model_dict",
    # Internal functions (for backward compatibility)
    "_is_json_serializable",
    "_raise_metadata_too_large_error",
]
