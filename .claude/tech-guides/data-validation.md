# Data Validation Guide

## Overview

This guide defines Pydantic v2 data validation patterns for the Shared Context MCP Server, providing comprehensive validation, serialization, and type safety that integrates with the established DatabaseManager and error handling architecture.

## Core Concepts

### Why Pydantic for MCP Server?

1. **Automatic Validation**: Type hints become runtime validation
2. **FastAPI Integration**: Seamless request/response validation
3. **MCP Compatibility**: Clean JSON serialization for MCP protocol
4. **Security**: Input sanitization and validation at the boundary
5. **Documentation**: Models serve as living API documentation

### Pydantic v2 Key Features

- **Performance**: Significantly faster validation and serialization
- **Better Errors**: Detailed validation error messages with field-level granularity
- **Strict Mode**: Optional strict type checking for enhanced validation
- **Custom Validators**: Field and model-level validation with business logic
- **JSON Schema**: Automatic schema generation for API documentation

## Implementation Patterns

### Pattern 1: Core Session Model

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from typing import Any
from datetime import datetime, timezone
from shared_context_server.models import (
    validate_session_id, validate_agent_id, sanitize_text_input,
    MAX_PURPOSE_LENGTH, MAX_AGENT_ID_LENGTH
)

class SessionModel(BaseModel):
    """Session model representing a shared context workspace."""

    model_config = ConfigDict()

    id: str = Field(..., description="Unique session identifier")
    purpose: str = Field(
        ..., min_length=1, max_length=MAX_PURPOSE_LENGTH,
        description="Session purpose"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True, description="Whether session is active")
    created_by: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH,
        description="Agent who created session"
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

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()
```

### Pattern 2: Message Model with Visibility

```python
from shared_context_server.models import (
    MessageVisibility, MessageType, MessageModel,
    validate_session_id, validate_agent_id, sanitize_text_input,
    MAX_CONTENT_LENGTH, MAX_AGENT_ID_LENGTH
)

# Use enum values from the actual codebase:
# MessageVisibility.PUBLIC, MessageVisibility.PRIVATE,
# MessageVisibility.AGENT_ONLY, MessageVisibility.ADMIN_ONLY

# MessageType.AGENT_RESPONSE, MessageType.HUMAN_INPUT,
# MessageType.SYSTEM_STATUS, MessageType.TOOL_OUTPUT, MessageType.COORDINATION

class MessageModel(BaseModel):
    """Message model for agent communications."""

    model_config = ConfigDict(use_enum_values=True)

    id: int | None = Field(None, description="Auto-generated message ID")
    session_id: str = Field(..., description="Session ID")
    sender: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH,
        description="Message sender"
    )
    content: str = Field(
        ..., min_length=1, max_length=MAX_CONTENT_LENGTH,
        description="Message content"
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

    @field_serializer("timestamp", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()
```

### Pattern 3: Agent Memory Model

```python
from shared_context_server.models import (
    AgentMemoryModel, validate_agent_id, validate_session_id,
    sanitize_text_input, MAX_AGENT_ID_LENGTH, MAX_MEMORY_KEY_LENGTH
)

# Use the actual AgentMemoryModel from codebase:
class AgentMemoryModel(BaseModel):
    """Agent memory model with TTL and scope validation."""

    model_config = ConfigDict()

    id: int | None = Field(None, description="Auto-generated memory ID")
    agent_id: str = Field(
        ..., min_length=1, max_length=MAX_AGENT_ID_LENGTH,
        description="Agent ID"
    )
    session_id: str | None = Field(
        None, description="Session ID for scoped memory (null for global)"
    )
    key: str = Field(
        ..., min_length=1, max_length=MAX_MEMORY_KEY_LENGTH,
        description="Memory key"
    )
    value: str = Field(
        ..., min_length=1, description="Memory value (JSON string)"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Memory metadata"
    )
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

        # Use actual validation pattern from codebase
        import re
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$", v):
            raise ValueError("Memory key contains invalid characters")

        return v

    @field_serializer("created_at", "updated_at", "expires_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None
```

### Pattern 4: Request/Response Models with Database Operations

```python
from shared_context_server.models import (
    CreateSessionRequest, CreateSessionResponse, AddMessageRequest, AddMessageResponse,
    SetMemoryRequest, GetMemoryRequest, SearchContextRequest, SearchResponse
)
from shared_context_server.database import get_db_connection, execute_insert, execute_query

# Use actual request/response models from codebase:

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

# Standard response format using actual patterns
async def create_standard_response(success: bool, **kwargs: Any) -> dict[str, Any]:
    """Create standard API response format with UTC timestamps."""
    from shared_context_server.database import utc_timestamp
    response = {"success": success, "timestamp": utc_timestamp()}
    response.update(kwargs)
    return response
```

### Pattern 5: Search and Resource Models

```python
from shared_context_server.models import (
    SearchContextRequest, SearchResponse, ResourceModel,
    sanitize_search_input, validate_session_id
)

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
        return sanitize_search_input(v)

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
```

### Pattern 6: Validation Error Models

```python
from shared_context_server.models import (
    ValidationErrorDetail, ValidationErrorResponse,
    create_validation_error_response, extract_pydantic_validation_errors
)

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

# Utility function for handling validation errors
def handle_validation_error(exc: Exception) -> ValidationErrorResponse:
    """Create validation error response from exception."""
    error_details = extract_pydantic_validation_errors(exc)
    return create_validation_error_response(error_details)
```

## Best Practices

### 1. Always Use UTC Timestamps

```python
from shared_context_server.database import utc_now, utc_timestamp, parse_utc_timestamp
from datetime import datetime, timezone

# Correct - Use DatabaseManager UTC utilities
current_time = utc_now()  # Returns timezone-aware datetime
current_timestamp = utc_timestamp()  # Returns ISO string

# Correct - Manual UTC creation
timestamp = datetime.now(timezone.utc)

# Incorrect - uses local timezone (avoid)
timestamp = datetime.now()

# Correct - Parsing timestamps
parse_timestamp = parse_utc_timestamp("2025-01-15T10:30:00Z")
```

### 2. Validate at the Boundary

```python
from shared_context_server.database import get_db_connection, execute_insert
from shared_context_server.models import MessageModel, AddMessageRequest

# FastMCP tool validation (actual pattern used)
async def add_message_tool(
    request: AddMessageRequest,  # Pydantic validates automatically
    agent_id: str
) -> dict[str, Any]:
    """Add message with database operation using DatabaseManager pattern."""
    # Create message model from validated request
    message = MessageModel(
        session_id=request.session_id,
        sender=agent_id,
        content=request.content,
        visibility=request.visibility,
        metadata=request.metadata,
        parent_message_id=request.parent_message_id
    )

    # Use DatabaseManager pattern for persistence
    async with get_db_connection() as conn:
        message_id = await execute_insert(
            """INSERT INTO messages
               (session_id, sender, content, visibility, message_type, metadata, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message.session_id, message.sender, message.content,
             message.visibility.value, message.message_type.value,
             message.metadata, message.timestamp.isoformat())
        )

    return {"success": True, "message_id": message_id}
```

### 3. Use Enums for Fixed Values

```python
from shared_context_server.models import MessageVisibility, MessageType

# Good - Type-safe with actual enum values
visibility: MessageVisibility = MessageVisibility.PUBLIC
message_type: MessageType = MessageType.AGENT_RESPONSE

# Bad - Magic strings that can break
visibility: str = "public"
message_type: str = "agent_response"
```

### 4. Custom Validators for Business Logic

```python
@field_validator('session_id')
@classmethod
def validate_session_exists(cls, v: str) -> str:
    """Ensure session exists in database using DatabaseManager."""
    # Use actual database pattern from codebase
    from shared_context_server.database import execute_query

    async def check_session():
        results = await execute_query(
            "SELECT id FROM sessions WHERE id = ?", (v,)
        )
        return len(results) > 0

    # Note: In practice, this would need async validation
    # For demonstration of the pattern only
    if not v.startswith("session_"):
        raise ValueError(f"Session {v} has invalid format")
    return v
```

## Common Pitfalls

### 1. ❌ Not Using Established Validation Functions

```python
# BAD - Custom validation without established patterns
content: str = Field(...)

@field_validator('content')
@classmethod
def custom_sanitize(cls, v: str) -> str:
    return v.replace("<", "").replace(">", "")  # Incomplete

# GOOD - Use established sanitization from codebase
from shared_context_server.models import sanitize_text_input

@field_validator('content')
@classmethod
def sanitize_content(cls, v: str) -> str:
    v = sanitize_text_input(v)
    if not v:
        raise ValueError("Content cannot be empty after sanitization")
    return v
```

### 2. ❌ Incorrect Type Annotations

```python
# BAD - Old-style type annotations
from typing import Dict, Optional
metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

# GOOD - Modern Python 3.10+ annotations (as used in codebase)
metadata: dict[str, Any] | None = Field(default=None)
```

### 3. ❌ Inconsistent UTC Handling

```python
# BAD - Not using established UTC utilities
from datetime import datetime, timezone
timestamp = datetime.now()  # Local timezone
created_at = datetime.utcnow()  # Deprecated in Python 3.12+

# GOOD - Use DatabaseManager UTC utilities
from shared_context_server.database import utc_now, utc_timestamp
created_at = utc_now()  # Proper UTC with timezone info
timestamp_str = utc_timestamp()  # ISO string format

# GOOD - Field definition with UTC default
timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
)
```

### 4. ❌ Not Using Database Validation Functions

```python
# BAD - Inconsistent validation patterns
session_id: str = Field(..., pattern=r'^[a-zA-Z0-9-_]{8,64}$')

# GOOD - Use established validation functions
from shared_context_server.models import validate_session_id

@field_validator('session_id')
@classmethod
def validate_session_id_format(cls, v: str) -> str:
    return validate_session_id(v)  # Uses proper pattern: session_[16 hex chars]
```

## Database Integration Patterns

### 1. Using DatabaseManager Pattern

```python
from shared_context_server.database import get_db_connection, execute_query, execute_insert
from shared_context_server.models import SessionModel, validate_session_id

async def create_session(request: CreateSessionRequest, agent_id: str) -> dict[str, Any]:
    """Create session using established DatabaseManager pattern."""
    # Generate session ID with proper format
    import secrets
    session_id = f"session_{secrets.token_hex(8)}"

    # Create validated session model
    session = SessionModel(
        id=session_id,
        purpose=request.purpose,
        created_by=agent_id,
        metadata=request.metadata
    )

    # Use DatabaseManager connection pattern
    async with get_db_connection() as conn:
        await execute_insert(
            """INSERT INTO sessions
               (id, purpose, created_by, created_at, updated_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session.id, session.purpose, session.created_by,
             session.created_at.isoformat(), session.updated_at.isoformat(),
             serialize_metadata(session.metadata))
        )

    return {"success": True, "session_id": session.id}
```

### 2. UTC Timestamp Consistency

```python
from shared_context_server.database import utc_now, utc_timestamp, parse_utc_timestamp

# Always use DatabaseManager UTC utilities
created_at = utc_now()  # datetime object
created_at_str = utc_timestamp()  # ISO string

# Parse timestamp with proper UTC handling
timestamp = parse_utc_timestamp("2025-01-15T10:30:00Z")
```

## Security Implications

### 1. Input Validation

All user input MUST pass through Pydantic validation:
- Prevents SQL injection via pattern validation
- Blocks XSS via content sanitization
- Ensures type safety

### 2. Sensitive Data Handling

```python
class SecureModel(BaseModel):
    model_config = ConfigDict(
        # Hide sensitive fields in logs
        json_encoders={
            SecretStr: lambda v: "***"
        }
    )

    api_key: SecretStr  # Won't be logged
```

### 3. JWT Validation

Always validate JWT claims:
- Audience must match server
- Expiration must be checked
- Permissions must be validated

## Testing Strategies

### 1. Model Validation Testing

```python
import pytest
from pydantic import ValidationError
from shared_context_server.models import MessageModel, MessageVisibility

def test_message_model_validation():
    # Valid message with proper session_id format
    msg = MessageModel(
        session_id="session_1234567890abcdef",  # Proper format: session_[16 hex chars]
        sender="agent_1",
        content="Test message"
    )
    assert msg.visibility == MessageVisibility.PUBLIC

    # Invalid session_id pattern
    with pytest.raises(ValidationError) as exc:
        MessageModel(
            session_id="invalid_session_format",
            sender="agent_1",
            content="Test"
        )
    assert "session_id" in str(exc.value)

    # Test UTC timezone handling
    from datetime import datetime, timezone
    assert msg.timestamp.tzinfo == timezone.utc
```

### 2. Sanitization Testing

```python
def test_content_sanitization():
    """Test content sanitization with actual validation functions."""
    from shared_context_server.models import sanitize_text_input

    # Test sanitization directly
    dangerous_content = "<script>alert('xss')</script>Normal text\x00\x01"
    sanitized = sanitize_text_input(dangerous_content)

    # Verify null bytes and control characters are removed
    assert "\x00" not in sanitized
    assert "\x01" not in sanitized
    assert "Normal text" in sanitized

    # Test via model validation
    msg = MessageModel(
        session_id="session_1234567890abcdef",
        sender="agent_1",
        content=dangerous_content
    )
    assert "Normal text" in msg.content
```

### 3. Database Integration Testing

```python
import pytest
from shared_context_server.database import get_db_connection, execute_query
from shared_context_server.models import MessageModel, serialize_metadata

@pytest.mark.asyncio
async def test_message_database_integration():
    """Test message validation with database operations."""

    # Create valid message
    msg = MessageModel(
        session_id="session_1234567890abcdef",
        sender="test_agent",
        content="Test message",
        metadata={"test_key": "test_value"}
    )

    # Test database insertion with proper UTC timestamps
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """INSERT INTO messages
               (session_id, sender, content, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (msg.session_id, msg.sender, msg.content,
             msg.timestamp.isoformat(), serialize_metadata(msg.metadata))
        )
        message_id = cursor.lastrowid

    # Verify message was stored correctly
    results = await execute_query(
        "SELECT * FROM messages WHERE id = ?", (message_id,)
    )
    assert len(results) == 1
    assert results[0]["sender"] == "test_agent"
```

## Error Handling Integration

### Using Established Error Hierarchy

```python
from shared_context_server.database import DatabaseError, DatabaseConnectionError
from shared_context_server.models import ValidationErrorResponse, extract_pydantic_validation_errors

async def handle_validation_with_proper_errors(data: dict[str, Any]) -> dict[str, Any]:
    """Handle validation using established error patterns."""
    try:
        # Validate using actual model
        model = MessageModel(**data)
        return {"success": True, "data": model.model_dump()}

    except ValidationError as e:
        # Use established error extraction pattern
        error_details = extract_pydantic_validation_errors(e)
        error_response = ValidationErrorResponse(
            error="Message validation failed",
            details=error_details
        )
        return error_response.model_dump()

    except DatabaseError as e:
        # Handle database errors using established hierarchy
        return {
            "success": False,
            "error": "Database operation failed",
            "code": "DATABASE_ERROR",
            "details": str(e)
        }
```

## References

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [FastMCP Integration](https://github.com/jlowin/fastmcp) - MCP server framework
- Core Architecture: `/.claude/tech-guides/core-architecture.md` - Database patterns
- Framework Integration: `/.claude/tech-guides/framework-integration.md` - FastMCP patterns
- Error Handling: `/.claude/tech-guides/error-handling.md` - Error hierarchy
- CI Environment: `/.claude/tech-guides/ci.md` - Testing environment configurations

## Related Guides

- **Core Architecture Guide** - DatabaseManager patterns and schema design
- **Framework Integration Guide** - FastMCP server and tool validation patterns
- **Error Handling Guide** - Comprehensive error hierarchy and validation patterns
- **Security & Authentication Guide** - JWT validation and input sanitization
