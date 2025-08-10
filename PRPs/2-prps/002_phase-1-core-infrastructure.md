# PRP-002: Phase 1 - Core Infrastructure

**Document Type**: Product Requirement Prompt  
**Created**: 2025-08-10  
**Phase**: 1 (Core Infrastructure)  
**Timeline**: 6 hours  
**Priority**: Critical Core  
**Status**: Ready for Execution  
**Prerequisites**: Phase 0 - Project Foundation completed

---

## Research Context & Architectural Analysis

### Planning Integration
**Source**: Final Decomposed Implementation Plan, Framework Integration Guide, Core Architecture Guide  
**Research Foundation**: FastMCP server implementation patterns, MCP protocol expertise, multi-agent session management architecture  
**Strategic Context**: Building the core MCP server infrastructure that enables session-based multi-agent collaboration, establishing the foundation for all subsequent features

### Architectural Scope
**MCP Server Core**: FastMCP server with stdio transport, async lifecycle management, structured error handling  
**Session Management**: UUID-based session creation, isolation boundaries, lifecycle management (create/retrieve/cleanup)  
**Message Storage**: Async SQLite operations with visibility controls (public/private/agent_only), agent-specific filtering, proper indexing  
**Agent Identity**: MCP context extraction, basic authentication middleware, audit logging foundation, security validation

### Existing Patterns to Leverage
**Framework Integration Guide**: Complete FastMCP server setup, session management tools, message visibility patterns  
**Core Architecture Guide**: Database schema implementation, MCP resource models, audit logging patterns  
**Phase 0 Foundation**: SQLite database with WAL mode, aiosqlite async operations, environment configuration, development tooling

---

## Implementation Specification

### Core Requirements

#### 1. FastMCP Server Foundation
**Server Initialization**:
```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import aiosqlite

# Initialize FastMCP server
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "shared-context-server"),
    version=os.getenv("MCP_SERVER_VERSION", "1.0.0"),
    description="Centralized memory store for multi-agent collaboration"
)
```

**Server Lifecycle Management**:
```python
from contextlib import asynccontextmanager
import aiosqlite
from .database import get_db_connection  # Phase 0 unified connection management

@asynccontextmanager
async def lifespan(app):
    """FastMCP server lifespan management."""
    
    # Startup
    print("Initializing Shared Context MCP Server...")
    
    # Use single shared connection with WAL mode (from Phase 0 fixes)
    # Connection pooling to be evaluated when P95 write latency > 50ms or concurrent writers > 10
    # Alternative: Migrate to Postgres when scaling requirements are met
    
    # Initialize database schema from Phase 0 (using unified connection management)
    async with get_db_connection() as conn:
        await initialize_schema(conn)
        # PRAGMA settings already configured in database.py
    
    print("Server ready!")
    
    yield
    
    # Shutdown
    print("Shutting down...")
    # Connection cleanup handled by get_db_connection context manager
    print("Shutdown complete")
```

**Transport Configuration**:
- **stdio transport** for MCP client communication
- **Async request/response handling** with proper error boundaries
- **Structured error responses** with error codes and helpful messages
- **Context extraction** for agent identity and authentication

#### 2. Session Management System
**Create Session Tool**:
```python
from uuid import uuid4

@mcp.tool()
async def create_session(
    purpose: str = Field(description="Purpose or description of the session"),
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the session"
    )
) -> Dict[str, Any]:
    """
    Create a new shared context session.
    
    Returns session_id for future operations.
    """
    
    # Generate unique session ID
    session_id = f"session_{uuid4().hex[:16]}"
    
    # Get agent identity from context
    agent_id = mcp.context.get("agent_id", "unknown")
    
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO sessions (id, purpose, created_by, metadata)
            VALUES (?, ?, ?, ?)
        """, (
            session_id,
            purpose,
            agent_id,
            json.dumps(metadata or {})
        ))
        await conn.commit()
        
        # Audit log
        await audit_log(conn, "session_created", agent_id, session_id)
    
    return {
        "success": True,
        "session_id": session_id,
        "created_by": agent_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
```

**Session Retrieval & Management**:
```python
@mcp.tool()
async def get_session(
    session_id: str = Field(description="Session ID to retrieve")
) -> Dict[str, Any]:
    """
    Retrieve session information and recent messages.
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    async with get_db_connection() as conn:
        # Get session info
        cursor = await conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        session = await cursor.fetchone()
        
        if not session:
            return {
                "success": False,
                "error": "Session not found",
                "code": "SESSION_NOT_FOUND"
            }
        
        # Get accessible messages
        cursor = await conn.execute("""
            SELECT * FROM messages 
            WHERE session_id = ? 
            AND (visibility = 'public' OR 
                 (visibility = 'private' AND sender = ?))
            ORDER BY timestamp DESC
            LIMIT 50
        """, (session_id, agent_id))
        
        messages = await cursor.fetchall()
        
        return {
            "success": True,
            "session": dict(session),
            "messages": [dict(msg) for msg in messages],
            "message_count": len(messages)
        }
```

#### 3. Message Storage with Visibility Controls
**Add Message Tool**:
```python
@mcp.tool()
async def add_message(
    session_id: str = Field(description="Session ID to add message to"),
    content: str = Field(description="Message content"),
    visibility: str = Field(
        default="public",
        description="Message visibility: public, private, or agent_only",
        regex="^(public|private|agent_only)$"
    ),
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional message metadata"
    ),
    parent_message_id: Optional[int] = Field(
        default=None,
        description="ID of parent message for threading"
    )
) -> Dict[str, Any]:
    """
    Add a message to the shared context session.
    
    Visibility controls:
    - public: Visible to all agents in session
    - private: Visible only to sender
    - agent_only: Visible only to agents of same type
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    # Input sanitization
    content = sanitize_text(content)
    if metadata:
        metadata = sanitize_json(metadata)
    
    async with get_db_connection() as conn:
        # Verify session exists
        cursor = await conn.execute(
            "SELECT id FROM sessions WHERE id = ?",
            (session_id,)
        )
        if not await cursor.fetchone():
            return {
                "success": False,
                "error": "Session not found",
                "code": "SESSION_NOT_FOUND"
            }
        
        # Insert message
        cursor = await conn.execute("""
            INSERT INTO messages 
            (session_id, sender, content, visibility, metadata, parent_message_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            agent_id,
            content,
            visibility,
            json.dumps(metadata or {}),
            parent_message_id
        ))
        
        message_id = cursor.lastrowid
        await conn.commit()
        
        # Audit log
        await audit_log(conn, "message_added", agent_id, session_id, {
            "message_id": message_id,
            "visibility": visibility
        })
    
    return {
        "success": True,
        "message_id": message_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

**Message Retrieval with Filtering**:
```python
@mcp.tool()
async def get_messages(
    session_id: str = Field(description="Session ID to retrieve messages from"),
    limit: int = Field(default=50, description="Maximum messages to return", ge=1, le=1000),
    offset: int = Field(default=0, description="Offset for pagination", ge=0),
    visibility_filter: Optional[str] = Field(
        default=None,
        description="Filter by visibility: public, private, agent_only"
    )
) -> Dict[str, Any]:
    """
    Retrieve messages from session with agent-specific filtering.
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    async with get_db_connection() as conn:
        # Build query with visibility controls
        where_conditions = ["session_id = ?"]
        params = [session_id]
        
        # Agent-specific visibility filtering
        visibility_conditions = [
            "visibility = 'public'",
            "(visibility = 'private' AND sender = ?)"
        ]
        params.append(agent_id)
        
        if visibility_filter:
            visibility_conditions.append("visibility = ?")
            params.append(visibility_filter)
        
        where_conditions.append(f"({' OR '.join(visibility_conditions)})")
        
        query = f"""
            SELECT * FROM messages 
            WHERE {' AND '.join(where_conditions)}
            ORDER BY timestamp ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        cursor = await conn.execute(query, params)
        messages = await cursor.fetchall()
        
        return {
            "success": True,
            "messages": [dict(msg) for msg in messages],
            "count": len(messages),
            "has_more": len(messages) == limit
        }
```

#### 4. Agent Identity & Authentication
**Agent Context Extraction**:
```python
def extract_agent_context(request_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract agent identity and authentication from MCP context.
    
    Returns agent_id, permissions, and authentication status.
    """
    
    # Extract from MCP context (implementation depends on MCP client)
    agent_id = request_context.get("agent_id", "unknown")
    agent_type = request_context.get("agent_type", "generic")
    
    # Basic authentication (enhanced in Phase 3)
    api_key = request_context.get("authorization", "").replace("Bearer ", "")
    authenticated = api_key == os.getenv("API_KEY", "")
    
    return {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "authenticated": authenticated,
        "permissions": ["read", "write"] if authenticated else ["read"]
    }

@mcp.middleware
async def authentication_middleware(request, call_next):
    """
    Basic authentication middleware for agent requests.
    """
    
    # Extract and validate agent context
    context = extract_agent_context(request.context)
    
    # Set context for tools to access
    mcp.context["agent_id"] = context["agent_id"]
    mcp.context["agent_type"] = context["agent_type"]
    mcp.context["authenticated"] = context["authenticated"]
    
    response = await call_next(request)
    return response
```

**Audit Logging System**:
```python
async def audit_log(
    conn: aiosqlite.Connection,
    event_type: str,
    agent_id: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log security and operational events for debugging and monitoring.
    """
    
    await conn.execute("""
        INSERT INTO audit_log 
        (event_type, agent_id, session_id, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event_type,
        agent_id,
        session_id,
        json.dumps(metadata or {}),
        datetime.now(timezone.utc).isoformat()
    ))
```

### Integration Points

#### 1. Database Layer Integration
- **Connection Strategy**: Single shared connection with WAL mode (Phase 0 unified management)
- **Pooling Decision**: Evaluate aiosqlitepool when P95 write latency > 50ms or concurrent writers > 10
- **Schema Validation**: Verify Phase 0 database schema is properly initialized  
- **Performance Configuration**: Leverage optimized PRAGMA settings from database.py
- **Index Creation**: Add `idx_messages_session_time` and `idx_audit_log_time` for Phase 3 protection
- **Error Handling**: Proper SQLite error handling with unified error envelope

#### 2. MCP Protocol Integration
- **Tool Registration**: All tools properly registered with FastMCP framework
- **Context Handling**: Agent identity extraction from MCP request context
- **Response Formatting**: Consistent JSON response structure with success/error patterns
- **Error Boundaries**: Proper exception handling with structured error responses

#### 3. Security Integration
- **Input Sanitization**: Prevent SQL injection and XSS attacks
- **Agent Authentication**: Basic API key authentication (enhanced in Phase 3)
- **Audit Trail**: Comprehensive logging of all agent operations
- **Session Isolation**: Ensure proper session boundaries and access controls

### API Requirements

**Core MCP Tools**:
1. **`create_session`** - Session creation with purpose and metadata
2. **`get_session`** - Session retrieval with message history
3. **`add_message`** - Message creation with visibility controls
4. **`get_messages`** - Message retrieval with filtering and pagination

**Response Format Standards** (Unified Error Envelope):
```json
{
  "success": true,
  "data": { ... },
  "code": "SUCCESS",
  "timestamp": "2025-01-15T10:30:00Z"
}

// Error responses
{
  "success": false,
  "error": "Human-readable error message", 
  "code": "ERROR_CODE",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Critical Implementation Notes**:
- **Connection Strategy**: Use aiosqlite single shared connection with WAL mode initially
- **Performance Threshold**: Evaluate aiosqlitepool or Postgres migration when P95 write latency > 50ms or concurrent writers > 10
- **Index Requirements**: Create `idx_messages_session_time` and `idx_audit_log_time` indexes now for Phase 3 query protection
- **Error Consistency**: All tools must emit unified error envelope format including edge cases

---

## Quality Requirements

### Testing Strategy
**Framework**: FastMCP TestClient for in-memory testing  
**Test Categories**:
- **Unit Tests**: Individual tool functionality, database operations, context extraction
- **Integration Tests**: Multi-tool workflows, session lifecycle, message visibility
- **Behavioral Tests**: Multi-agent collaboration scenarios, session isolation

**Key Test Scenarios**:
```python
@pytest.mark.asyncio
async def test_session_workflow(client):
    """Test complete session workflow."""
    
    client.set_context({"agent_id": "test_agent"})
    
    # Create session
    result = await client.call_tool(
        "create_session",
        {"purpose": "test session"}
    )
    assert result["success"] is True
    session_id = result["session_id"]
    
    # Add message
    result = await client.call_tool(
        "add_message",
        {
            "session_id": session_id,
            "content": "Test message",
            "visibility": "public"
        }
    )
    assert result["success"] is True
    
    # Retrieve session
    result = await client.call_tool("get_session", {"session_id": session_id})
    assert result["success"] is True
    assert len(result["messages"]) == 1

@pytest.mark.asyncio
async def test_visibility_controls(client):
    """Test message visibility controls."""
    
    # Test with different agents
    agent1_context = {"agent_id": "agent1"}
    agent2_context = {"agent_id": "agent2"}
    
    client.set_context(agent1_context)
    
    # Create session and add private message
    session_result = await client.call_tool(
        "create_session", 
        {"purpose": "visibility test"}
    )
    session_id = session_result["session_id"]
    
    await client.call_tool("add_message", {
        "session_id": session_id,
        "content": "Private message",
        "visibility": "private"
    })
    
    # Switch to agent2, should not see private message
    client.set_context(agent2_context)
    result = await client.call_tool("get_messages", {"session_id": session_id})
    
    assert result["success"] is True
    assert len(result["messages"]) == 0  # Should not see agent1's private message
```

### Documentation Needs
**Core Infrastructure Documentation**:
- **MCP Tools API**: Complete documentation of all tools with examples
- **Session Management**: Session lifecycle, isolation, and best practices
- **Message System**: Visibility controls, threading, metadata usage
- **Agent Integration**: Context extraction, authentication, audit logging

### Performance Considerations
**Core Infrastructure Performance Requirements**:
- Session creation: < 10ms
- Message insertion: < 20ms
- Message retrieval (50 messages): < 30ms
- Session retrieval: < 25ms
- Agent context extraction: < 5ms

**Database Optimization**:
- Proper indexes for session_id, sender, timestamp queries
- Connection pooling for concurrent agent access
- Prepared statements for frequently used queries

---

## Coordination Strategy

### Recommended Approach: Direct Agent Assignment
**Complexity Assessment**: Core infrastructure with moderate complexity  
**File Count**: 6-8 files (server.py, database.py, tools.py, models.py, middleware.py, tests/)  
**Integration Risk**: Medium (building on Phase 0 foundation, establishing core patterns)  
**Time Estimation**: 6 hours with incremental validation

**Agent Assignment**: **Developer Agent** for complete Phase 1 execution  
**Rationale**: Core infrastructure requires deep FastMCP expertise, database architecture, and MCP protocol implementation - all developer agent specialties

### Implementation Phases

#### Phase 1.1: FastMCP Server Foundation (1.5 hours)
**Implementation Steps**:
1. **Server Initialization** (30 minutes): FastMCP server setup, configuration
2. **Lifecycle Management** (30 minutes): Startup/shutdown, database connection
3. **Transport & Error Handling** (30 minutes): stdio transport, structured errors

**Validation Checkpoints**:
```python
# Server startup validation
async with TestClient(mcp_server) as client:
    assert client.server_name == "shared-context-server"
    
# Error handling validation
result = await client.call_tool("nonexistent_tool", {})
assert result["success"] is False
assert "code" in result
```

#### Phase 1.2: Session Management (2 hours)
**Implementation Steps**:
1. **Create Session Tool** (45 minutes): UUID generation, database storage, audit logging
2. **Session Retrieval** (45 minutes): Session info, message filtering, pagination
3. **Session Lifecycle** (30 minutes): Cleanup, validation, error handling

**Validation Checkpoints**:
```python
# Session creation validation
session = await client.call_tool("create_session", {"purpose": "test"})
assert session["success"] is True
assert session["session_id"].startswith("session_")

# Session isolation validation  
# (Test that different sessions are properly isolated)
```

#### Phase 1.3: Message Storage & Visibility (1.5 hours)  
**Implementation Steps**:
1. **Add Message Tool** (45 minutes): Content storage, visibility controls, metadata
2. **Message Retrieval** (45 minutes): Filtering, pagination, agent-specific access
3. **Visibility Logic** (30 minutes): Public/private/agent_only filtering

**Validation Checkpoints**:
```python
# Message visibility validation
await client.call_tool("add_message", {
    "session_id": session_id,
    "content": "Public message",
    "visibility": "public"
})

# Verify visibility enforcement works correctly
messages = await client.call_tool("get_messages", {"session_id": session_id})
assert len(messages["messages"]) == 1
```

#### Phase 1.4: Agent Identity & Authentication (1 hour)
**Implementation Steps**:
1. **Context Extraction** (30 minutes): Agent ID, type, authentication from MCP context
2. **Authentication Middleware** (30 minutes): Basic API key validation, context setting
3. **Audit Logging** (30 minutes): Operation tracking, security logging

**Validation Checkpoints**:
```python
# Agent identity validation
client.set_context({"agent_id": "test_agent", "api_key": "valid_key"})
result = await client.call_tool("create_session", {"purpose": "auth test"})
assert result["created_by"] == "test_agent"

# Authentication validation
client.set_context({"agent_id": "test_agent", "api_key": "invalid_key"})
result = await client.call_tool("create_session", {"purpose": "auth test"})
# Should handle authentication appropriately
```

### Risk Mitigation

#### Technical Risks
**MCP Protocol Complexity**: Use FastMCP TestClient for validation, incremental testing  
**Database Concurrency**: Leverage Phase 0 WAL mode configuration, connection pooling  
**Context Extraction Issues**: Careful MCP context handling, fallback values  
**Performance Bottlenecks**: Monitor database query performance, optimize indexes

#### Integration Risks
**Phase 0 Dependency Issues**: Verify database schema and tooling before starting  
**Agent Context Problems**: Test context extraction thoroughly with different scenarios  
**Visibility Logic Bugs**: Comprehensive testing of all visibility combinations  
**Audit Logging Gaps**: Ensure all operations are properly logged

### Dependencies & Prerequisites
**Phase 0 Completion**: Modern tooling, database schema, development environment  
**Database Readiness**: SQLite with WAL mode, schema initialization, connection pooling  
**FastMCP Knowledge**: Server setup, tool registration, context handling patterns  
**Async/Await Patterns**: aiosqlite operations, connection management, error handling

---

## Success Criteria

### Functional Success
**FastMCP Server**:
- ✅ Server initialization and configuration working
- ✅ stdio transport for MCP client communication functional  
- ✅ Proper lifecycle management (startup/shutdown) with database connections
- ✅ Structured error handling with helpful error messages

**Session Management**:
- ✅ Session creation with UUID generation and database persistence
- ✅ Session retrieval with message filtering and pagination
- ✅ Session isolation boundaries properly enforced
- ✅ Session lifecycle management (create/retrieve/cleanup) operational

**Message Storage**:
- ✅ Message creation with visibility controls (public/private/agent_only)
- ✅ Message retrieval with agent-specific filtering
- ✅ Proper indexing and performance optimization
- ✅ Threading support with parent_message_id relationships

**Agent Identity & Authentication**:
- ✅ Agent identity extraction from MCP context
- ✅ Basic authentication middleware operational  
- ✅ Audit logging for all operations
- ✅ Security validation and input sanitization

### Integration Success
**MCP Protocol Integration**: All tools properly registered and responding to MCP clients  
**Database Integration**: Efficient async operations with proper error handling  
**Security Integration**: Agent authentication and audit logging working  
**Performance Integration**: Connection pooling and query optimization operational

### Quality Gates
**Core Infrastructure Testing**:
```bash
uv run test tests/unit/test_session_management.py    # Session tool tests pass
uv run test tests/unit/test_message_storage.py       # Message tool tests pass  
uv run test tests/integration/test_agent_workflow.py # Multi-tool workflows pass
uv run test tests/behavioral/test_visibility.py     # Visibility controls pass
```

**Performance Benchmarks**:
- Session creation: < 10ms
- Message insertion: < 20ms  
- Message retrieval: < 30ms for 50 messages
- Agent context extraction: < 5ms

**Code Quality**:
```bash
uv run ruff check .     # No linting errors
uv run mypy .           # No type checking errors
coverage report         # >80% test coverage for core infrastructure
```

### Validation Checklist

#### ✅ FastMCP Server Foundation
- [ ] Server initialization with proper configuration
- [ ] stdio transport working with MCP clients
- [ ] Lifecycle management (startup/shutdown) functional
- [ ] Structured error handling with error codes

#### ✅ Session Management System
- [ ] create_session tool working with UUID generation
- [ ] get_session tool with message filtering
- [ ] Session isolation boundaries properly enforced
- [ ] Session validation and error handling

#### ✅ Message Storage with Visibility  
- [ ] add_message tool with visibility controls
- [ ] get_messages tool with agent-specific filtering
- [ ] Visibility logic (public/private/agent_only) working
- [ ] Message threading and metadata support

#### ✅ Agent Identity & Authentication
- [ ] Agent context extraction from MCP requests
- [ ] Basic authentication middleware operational
- [ ] Audit logging for all operations
- [ ] Input sanitization and security validation

---

## Implementation Notes

### Critical Success Factors
1. **MCP Protocol Compliance**: Proper tool registration and response formatting
2. **Database Performance**: Efficient async operations with connection pooling  
3. **Security Foundation**: Agent identity and authentication working correctly
4. **Testing Rigor**: Comprehensive validation of all tools and workflows
5. **Error Handling**: Structured error responses with helpful diagnostic information

### Common Pitfalls to Avoid
1. **❌ MCP Context Issues**: Careful handling of agent identity extraction and fallbacks
2. **❌ Database Concurrency Problems**: Proper use of connection pooling and WAL mode
3. **❌ Visibility Logic Bugs**: Thorough testing of all visibility control combinations  
4. **❌ Performance Bottlenecks**: Monitor and optimize database queries and indexes
5. **❌ Authentication Gaps**: Ensure all tools properly validate agent identity

### Post-Phase Integration
**Preparation for Phase 2**:
- Session and message management provides foundation for search features
- Agent identity system ready for memory scoping
- MCP resource patterns established for subscriptions
- Database performance optimized for advanced features

---

## References

### Planning Documents
- [Final Decomposed Implementation Plan](../1-planning/shared-context-mcp-server/FINAL_DECOMPOSED_IMPLEMENTATION_PLAN.md)
- [Framework Integration Guide](../../.claude/tech-guides/framework-integration.md) - FastMCP Implementation Patterns
- [Core Architecture Guide](../../.claude/tech-guides/core-architecture.md) - Database Schema, MCP Resource Models

### Implementation Patterns
- **Session Management Tools**: Framework Integration Guide lines 44-94
- **Message Management with Visibility**: Framework Integration Guide lines 96-174
- **Agent Identity & Authentication**: Framework Integration Guide lines 276-292

### External References
- [FastMCP Documentation](https://github.com/jlowin/fastmcp) - Server setup, tool registration
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification) - Protocol details
- [aiosqlite Documentation](https://aiosqlite.omnilib.dev/) - Async SQLite operations

---

**Ready for Execution**: Phase 1 core infrastructure implementation  
**Next Phase**: Phase 2 - Essential Features (search, agent memory, MCP resources)  
**Coordination**: Direct developer agent assignment for complete Phase 1 execution