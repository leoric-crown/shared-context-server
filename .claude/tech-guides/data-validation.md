# Data Validation Guide

## Overview

This guide defines all Pydantic v2 models for the Shared Context MCP Server, providing comprehensive data validation, serialization, and type safety for all API interactions and database operations.

## Core Concepts

### Why Pydantic for MCP Server?

1. **Automatic Validation**: Type hints become runtime validation
2. **FastAPI Integration**: Seamless request/response validation
3. **MCP Compatibility**: Clean JSON serialization for MCP protocol
4. **Security**: Input sanitization and validation at the boundary
5. **Documentation**: Models serve as living API documentation

### Pydantic v2 Key Features

- **Performance**: 5-50x faster than v1
- **Better Errors**: Detailed validation error messages
- **Strict Mode**: Optional strict type checking
- **Custom Validators**: Field and model-level validation
- **JSON Schema**: Automatic OpenAPI schema generation

## Implementation Patterns

### Pattern 1: Core Session Model

```python
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

class SessionModel(BaseModel):
    """Session model representing a shared context workspace."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique session identifier",
        pattern=r'^[a-zA-Z0-9-_]{8,64}$'
    )
    purpose: Optional[str] = Field(
        None,
        max_length=500,
        description="Purpose or description of the session"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation timestamp (UTC)"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp (UTC)"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the session is currently active"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional session metadata"
    )
    
    @field_validator('purpose')
    @classmethod
    def sanitize_purpose(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize purpose field to prevent injection."""
        if v is None:
            return v
        # Remove potential script tags and dangerous characters
        import re
        clean = re.sub(r'<[^>]*>', '', v)  # Remove HTML tags
        clean = re.sub(r'[^\w\s\-.,!?]', '', clean)  # Keep only safe chars
        return clean.strip() if clean else None
```

### Pattern 2: Message Model with Visibility

```python
from enum import Enum

class MessageVisibility(str, Enum):
    """Message visibility levels for tiered memory architecture."""
    PUBLIC = "public"      # Visible to all agents (blackboard)
    PRIVATE = "private"    # Visible only to creating agent
    AGENT_ONLY = "agent_only"  # Visible to specific agent group

class MessageType(str, Enum):
    """Types of messages in the system."""
    HUMAN_INPUT = "human_input"
    AGENT_RESPONSE = "agent_response"
    SYSTEM_STATUS = "system_status"
    TOOL_OUTPUT = "tool_output"
    PRIVATE_NOTE = "private_note"

class MessageModel(BaseModel):
    """Message model for agent communications."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=True
    )
    
    id: Optional[int] = Field(
        None,
        description="Auto-generated message ID"
    )
    session_id: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9-_]{8,64}$',
        description="Parent session ID"
    )
    sender: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-zA-Z0-9-_.]+$',
        description="Agent or user identifier"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Message content"
    )
    visibility: MessageVisibility = Field(
        default=MessageVisibility.PUBLIC,
        description="Message visibility level"
    )
    message_type: MessageType = Field(
        default=MessageType.AGENT_RESPONSE,
        description="Type of message"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Message metadata (files modified, test results, etc.)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Message timestamp (UTC)"
    )
    parent_message_id: Optional[int] = Field(
        None,
        description="Parent message for threading"
    )
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Sanitize content to prevent injection attacks."""
        import re
        # Remove script tags
        clean = re.sub(
            r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
            '',
            v,
            flags=re.IGNORECASE
        )
        # Remove other potentially dangerous HTML
        clean = re.sub(r'<iframe.*?</iframe>', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'javascript:', '', clean, flags=re.IGNORECASE)
        return clean.strip()
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure metadata doesn't contain sensitive information."""
        sensitive_keys = {'password', 'secret', 'token', 'api_key'}
        for key in list(v.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                v[key] = "[REDACTED]"
        return v
```

### Pattern 3: Agent Memory Model

```python
class AgentMemoryModel(BaseModel):
    """Private memory storage for individual agents."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: Optional[int] = Field(None)
    agent_id: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9-_.]+$',
        description="Agent identifier"
    )
    session_id: Optional[str] = Field(
        None,
        pattern=r'^[a-zA-Z0-9-_]{8,64}$',
        description="Optional session scope"
    )
    key: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r'^[a-zA-Z0-9-_.]+$',
        description="Memory key"
    )
    value: str = Field(
        ...,
        max_length=100000,
        description="Memory value (JSON-serializable)"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration timestamp"
    )
    
    @field_validator('value')
    @classmethod
    def validate_json_serializable(cls, v: str) -> str:
        """Ensure value is JSON-serializable."""
        try:
            import json
            json.loads(v)  # Validate it's valid JSON
            return v
        except json.JSONDecodeError:
            # If not JSON, wrap as string
            return json.dumps(v)
    
    @property
    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
```

### Pattern 4: MCP Tool Request/Response Models

```python
class MCPToolRequest(BaseModel):
    """Request model for MCP tool invocations."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra='forbid'  # Reject unknown fields
    )
    
    name: str = Field(
        ...,
        pattern=r'^[a-zA-Z][a-zA-Z0-9_-]*$',
        description="Tool name"
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments"
    )
    session_id: Optional[str] = Field(
        None,
        pattern=r'^[a-zA-Z0-9-_]{8,64}$',
        description="Session context"
    )
    
    @field_validator('name')
    @classmethod
    def validate_tool_exists(cls, v: str) -> str:
        """Validate tool name exists."""
        valid_tools = {
            'create_session', 'add_message', 'get_message',
            'get_context', 'search_context', 'list_sessions',
            'set_memory', 'get_memory', 'list_memory',
            'delete_memory', 'add_private_note'
        }
        if v not in valid_tools:
            raise ValueError(f"Unknown tool: {v}")
        return v

class MCPToolResponse(BaseModel):
    """Response model for MCP tool invocations."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    success: bool = Field(..., description="Whether tool execution succeeded")
    result: Optional[Any] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[float] = Field(
        None,
        description="Execution time in milliseconds"
    )
    
    @model_validator(mode='after')
    def validate_response(self):
        """Ensure either result or error is present."""
        if not self.success and not self.error:
            raise ValueError("Failed response must include error message")
        if self.success and self.error:
            raise ValueError("Successful response should not include error")
        return self
```

### Pattern 5: Authentication Models

```python
from typing import Set

class AgentIdentity(BaseModel):
    """Agent identity extracted from JWT token."""
    
    model_config = ConfigDict(frozen=True)  # Immutable
    
    id: str = Field(..., pattern=r'^[a-zA-Z0-9-_.]+$')
    type: str = Field(default="unknown")
    permissions: Set[str] = Field(default_factory=set)
    session_scope: Optional[str] = Field(None)
    
    def has_permission(self, permission: str) -> bool:
        """Check if agent has specific permission."""
        return permission in self.permissions

class JWTPayload(BaseModel):
    """JWT token payload for authentication."""
    
    agent_id: str = Field(..., description="Agent identifier")
    agent_type: Optional[str] = Field(None, description="Agent type")
    permissions: list[str] = Field(
        default_factory=list,
        description="Agent permissions"
    )
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    aud: str = Field(..., description="Audience (must be 'mcp-shared-context-server')")
    iss: str = Field(..., description="Issuer")
    
    @field_validator('aud')
    @classmethod
    def validate_audience(cls, v: str) -> str:
        """Validate audience claim for MCP server."""
        if v != 'mcp-shared-context-server':
            raise ValueError(f"Invalid audience: {v}")
        return v
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc).timestamp() > self.exp
```

### Pattern 6: Search and Query Models

```python
class SearchRequest(BaseModel):
    """Request model for fuzzy search operations."""
    
    model_config = ConfigDict(str_min_length=1)
    
    session_id: str = Field(..., pattern=r'^[a-zA-Z0-9-_]{8,64}$')
    query: str = Field(..., min_length=1, max_length=500)
    fuzzy_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0.0-1.0)"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return"
    )
    include_private: bool = Field(
        default=False,
        description="Include private messages in search"
    )

class SearchResult(BaseModel):
    """Search result with similarity scoring."""
    
    message: MessageModel
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_locations: list[str] = Field(
        default_factory=list,
        description="Where matches were found (content, sender, metadata)"
    )
```

## Best Practices

### 1. Always Use UTC Timestamps

```python
from datetime import datetime, timezone

# Correct
timestamp = datetime.now(timezone.utc)

# Incorrect - uses local timezone
timestamp = datetime.now()
```

### 2. Validate at the Boundary

```python
@app.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    message: MessageModel,  # Pydantic validates automatically
    current_agent: AgentIdentity = Depends(get_current_agent)
):
    # Message is already validated by Pydantic
    # No need for manual validation here
    return await db.add_message(message)
```

### 3. Use Enums for Fixed Values

```python
# Good - Type-safe and self-documenting
visibility: MessageVisibility = MessageVisibility.PUBLIC

# Bad - Magic strings
visibility: str = "public"
```

### 4. Custom Validators for Business Logic

```python
@field_validator('session_id')
@classmethod
def validate_session_exists(cls, v: str) -> str:
    """Ensure session exists in database."""
    if not session_exists(v):  # Custom check
        raise ValueError(f"Session {v} not found")
    return v
```

## Common Pitfalls

### 1. ❌ Not Sanitizing User Input

```python
# BAD - No sanitization
content: str = Field(...)

# GOOD - Sanitize in validator
@field_validator('content')
@classmethod
def sanitize_content(cls, v: str) -> str:
    # Remove dangerous content
    return sanitize_html(v)
```

### 2. ❌ Using Mutable Defaults

```python
# BAD - Shared mutable default
metadata: Dict = {}

# GOOD - Factory function
metadata: Dict = Field(default_factory=dict)
```

### 3. ❌ Ignoring Timezone

```python
# BAD - Timezone-naive
timestamp: datetime = datetime.now()

# GOOD - UTC timezone-aware
timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
)
```

### 4. ❌ Loose Pattern Matching

```python
# BAD - Too permissive
session_id: str = Field(...)

# GOOD - Strict pattern
session_id: str = Field(
    ...,
    pattern=r'^[a-zA-Z0-9-_]{8,64}$'
)
```

## Performance Considerations

### 1. Validation Performance

- Pydantic v2 is 5-50x faster than v1
- Use `model_validate()` for existing dicts
- Avoid repeated validation in loops

### 2. Serialization Optimization

```python
# Fast JSON serialization
model.model_dump_json()  # Optimized C implementation

# Slower
import json
json.dumps(model.model_dump())
```

### 3. Schema Caching

```python
# Cache schema generation
schema_cache = {}

def get_model_schema(model_class):
    if model_class not in schema_cache:
        schema_cache[model_class] = model_class.model_json_schema()
    return schema_cache[model_class]
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

def test_message_model_validation():
    # Valid message
    msg = MessageModel(
        session_id="test-session-123",
        sender="agent-1",
        content="Test message"
    )
    assert msg.visibility == MessageVisibility.PUBLIC
    
    # Invalid session_id pattern
    with pytest.raises(ValidationError) as exc:
        MessageModel(
            session_id="invalid!@#",
            sender="agent-1",
            content="Test"
        )
    assert "session_id" in str(exc.value)
```

### 2. Sanitization Testing

```python
def test_content_sanitization():
    msg = MessageModel(
        session_id="test-123",
        sender="agent",
        content="<script>alert('xss')</script>Normal text"
    )
    assert "<script>" not in msg.content
    assert "Normal text" in msg.content
```

### 3. Custom Validator Testing

```python
def test_metadata_redaction():
    msg = MessageModel(
        session_id="test-123",
        sender="agent",
        content="Test",
        metadata={
            "api_key": "secret123",
            "normal_field": "value"
        }
    )
    assert msg.metadata["api_key"] == "[REDACTED]"
    assert msg.metadata["normal_field"] == "value"
```

## References

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Integration](https://fastapi.tiangolo.com/tutorial/body/)
- Research findings: `/RESEARCH_FINDINGS_DEVELOPER.md`
- MCP Integration: `/.claude/tech-guides/mcp-integration.md`
- Security patterns: `/.claude/tech-guides/security-authentication.md`

## Related Guides

- Security & Authentication Guide - JWT and permission models
- Data Architecture Guide - Database schema alignment
- Testing Patterns Guide - Model validation testing