# Framework Integration Guide

## Overview

This guide provides practical FastMCP server implementation patterns for the Shared Context MCP Server - a collaborative agent workspace. For foundational architecture and session-based collaboration patterns, see the [Core Architecture Guide](core-architecture.md).

⚠️ **Framework Integration Status**: This guide provides production-ready MCP implementation patterns with comprehensive security, error handling, and database management. All examples follow established security and architectural standards.

## Core Framework: FastMCP

### Why FastMCP?

**Research Finding**: FastMCP provides the most Pythonic and performant MCP implementation with:
- Native async/await support
- Built-in validation with Pydantic
- In-memory testing capabilities (100x faster than subprocess)
- Minimal boilerplate code
- Production-ready features

> **Architecture Reference**: See [Core Architecture Guide](core-architecture.md) for complete system design, database schema, and MCP resource models.

### Installation and Setup

```python
# Installation
pip install fastmcp aiosqlite rapidfuzz pydantic httpx

# Basic server setup
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json

# Initialize FastMCP server
mcp = FastMCP(
    name="shared-context-server",
    version="1.0.0",
    description="Collaborative agent workspace for seamless handoffs and shared context"
)
```

## Core MCP Tool Implementations

### Session Management Tools

```python
from uuid import uuid4
import aiosqlite
from shared_context_server.database import get_db_connection, utc_now, utc_timestamp

# Database connection pattern using actual implementation

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

### Message Management with Visibility Control

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
    - public: Visible to all agents
    - private: Visible only to sender
    - agent_only: Visible only to agents of same type
    """

    agent_id = mcp.context.get("agent_id", "unknown")

    # Sanitize inputs
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

        # Invalidate cache
        await cache.invalidate(session_id)

        # Trigger resource update notification
        await mcp.notify_resource_updated(f"session://{session_id}")

    return {
        "success": True,
        "message_id": message_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

### Fuzzy Search with RapidFuzz (5-10x Performance)

```python
from rapidfuzz import fuzz, process

@mcp.tool()
async def search_context(
    session_id: str = Field(description="Session ID to search within"),
    query: str = Field(description="Search query"),
    fuzzy_threshold: float = Field(
        default=60.0,
        description="Minimum similarity score (0-100)",
        ge=0,
        le=100
    ),
    limit: int = Field(
        default=10,
        description="Maximum results to return",
        ge=1,
        le=100
    ),
    search_metadata: bool = Field(
        default=True,
        description="Include metadata in search"
    )
) -> Dict[str, Any]:
    """
    Fuzzy search messages using RapidFuzz for 5-10x performance.

    Searches content, sender, and optionally metadata fields.
    """

    agent_id = mcp.context.get("agent_id", "unknown")

    # Get all accessible messages
    async with get_db_connection() as conn:
        cursor = await conn.execute("""
            SELECT * FROM messages
            WHERE session_id = ?
            AND (visibility = 'public' OR
                 (visibility = 'private' AND sender = ?))
            ORDER BY timestamp DESC
        """, (session_id, agent_id))

        rows = await cursor.fetchall()

        if not rows:
            return {
                "success": True,
                "results": [],
                "query": query
            }

        # Prepare searchable text
        searchable_items = []
        for row in rows:
            msg = dict(row)

            # Build searchable text
            text_parts = [
                msg.get('sender', ''),
                msg.get('content', '')
            ]

            if search_metadata and msg.get('metadata'):
                try:
                    metadata = json.loads(msg['metadata'])
                    if isinstance(metadata, dict):
                        text_parts.extend([
                            str(v) for v in metadata.values()
                            if v and isinstance(v, (str, int, float))
                        ])
                except json.JSONDecodeError:
                    pass

            searchable_text = ' '.join(text_parts).lower()
            searchable_items.append((searchable_text, msg))

        # Use RapidFuzz for matching
        choices = [(item[0], idx) for idx, item in enumerate(searchable_items)]
        matches = process.extract(
            query.lower(),
            choices,
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=fuzzy_threshold,
            processor=lambda x: x[0]
        )

        # Build results
        results = []
        for match in matches:
            _, score, idx = match
            message = searchable_items[idx][1]

            if message.get('metadata'):
                message['metadata'] = json.loads(message['metadata'])

            results.append({
                "message": message,
                "score": score,
                "match_preview": message['content'][:100]
            })

    return {
        "success": True,
        "results": results,
        "query": query,
        "threshold": fuzzy_threshold,
        "count": len(results)
    }
```

## Agent Memory Management

### Private Key-Value Store

```python
@mcp.tool()
async def set_memory(
    key: str = Field(description="Memory key"),
    value: Any = Field(description="Value to store"),
    session_id: Optional[str] = Field(
        default=None,
        description="Session scope (null for global)"
    ),
    expires_in: Optional[int] = Field(
        default=None,
        description="TTL in seconds",
        ge=0
    ),
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata"
    )
) -> Dict[str, Any]:
    """
    Store value in agent's private memory.

    Can be session-scoped or global to the agent.
    """

    agent_id = mcp.context.get("agent_id", "unknown")

    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in

    # Serialize value
    if not isinstance(value, str):
        value = json.dumps(value)

    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO agent_memory
            (agent_id, session_id, key, value, metadata, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, session_id, key)
            DO UPDATE SET
                value = excluded.value,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP,
                expires_at = excluded.expires_at
        """, (
            agent_id,
            session_id,
            key,
            value,
            json.dumps(metadata or {}),
            expires_at
        ))
        await conn.commit()

    return {
        "success": True,
        "key": key,
        "session_scoped": session_id is not None,
        "expires_at": expires_at
    }

@mcp.tool()
async def get_memory(
    key: str = Field(description="Memory key to retrieve"),
    session_id: Optional[str] = Field(
        default=None,
        description="Session scope (null for global)"
    )
) -> Dict[str, Any]:
    """
    Retrieve value from agent's private memory.
    """

    agent_id = mcp.context.get("agent_id", "unknown")

    async with get_db_connection() as conn:
        # Clean expired entries
        await conn.execute("""
            DELETE FROM agent_memory
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (datetime.now(timezone.utc).timestamp(),))

        # Retrieve value
        cursor = await conn.execute("""
            SELECT value, metadata FROM agent_memory
            WHERE agent_id = ? AND key = ?
            AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
            AND (expires_at IS NULL OR expires_at > ?)
        """, (
            agent_id,
            key,
            session_id,
            session_id,
            datetime.now(timezone.utc).timestamp()
        ))

        row = await cursor.fetchone()

        if not row:
            return {
                "success": False,
                "error": "Memory key not found",
                "code": "MEMORY_NOT_FOUND"
            }

        value = row['value']
        # Try to deserialize JSON
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass

        metadata = {}
        if row['metadata']:
            metadata = json.loads(row['metadata'])

        return {
            "success": True,
            "key": key,
            "value": value,
            "metadata": metadata
        }
```

## MCP Resources and Subscriptions

### Session Resource Provider

```python
@mcp.resource("session://{session_id}")
async def get_session_resource(session_id: str) -> Resource:
    """
    Provide session as an MCP resource with real-time updates.

    Clients can subscribe to changes.
    """

    agent_id = mcp.context.get("agent_id", "unknown")

    async with get_db_connection() as conn:
        # Get session info
        cursor = await conn.execute("""
            SELECT * FROM sessions WHERE id = ?
        """, (session_id,))

        session = await cursor.fetchone()
        if not session:
            raise ResourceNotFound(f"Session {session_id} not found")

        # Get visible messages
        cursor = await conn.execute("""
            SELECT * FROM messages
            WHERE session_id = ?
            AND (visibility = 'public' OR
                 (visibility = 'private' AND sender = ?))
            ORDER BY timestamp ASC
        """, (session_id, agent_id))

        messages = await cursor.fetchall()

        # Format as resource
        content = {
            "session": dict(session),
            "messages": [dict(msg) for msg in messages],
            "message_count": len(messages),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        return Resource(
            uri=f"session://{session_id}",
            name=f"Session: {session['purpose']}",
            mimeType="application/json",
            text=json.dumps(content, indent=2)
        )

@mcp.resource("agent://{agent_id}/memory")
async def get_agent_memory_resource(agent_id: str) -> Resource:
    """
    Provide agent memory as a resource.

    Only accessible by the agent itself.
    """

    requesting_agent = mcp.context.get("agent_id", "unknown")

    # Security check
    if requesting_agent != agent_id:
        raise ResourceNotFound("Unauthorized access to agent memory")

    async with get_db_connection() as conn:
        cursor = await conn.execute("""
            SELECT key, value, session_id, expires_at
            FROM agent_memory
            WHERE agent_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
        """, (agent_id, datetime.now(timezone.utc).timestamp()))

        memories = await cursor.fetchall()

        memory_dict = {}
        for row in memories:
            scope = "global" if row['session_id'] is None else row['session_id']
            if scope not in memory_dict:
                memory_dict[scope] = {}

            value = row['value']
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass

            memory_dict[scope][row['key']] = {
                "value": value,
                "expires_at": row['expires_at']
            }

        return Resource(
            uri=f"agent://{agent_id}/memory",
            name=f"Agent Memory: {agent_id}",
            mimeType="application/json",
            text=json.dumps(memory_dict, indent=2)
        )
```

## Testing with FastMCP TestClient

### In-Memory Testing (100x Faster)

```python
import pytest
from fastmcp.testing import TestClient

@pytest.fixture
async def client():
    """Create test client with in-memory binding."""
    async with TestClient(mcp) as client:
        # Initialize database for testing
        from shared_context_server.database import initialize_database
        await initialize_database()
        yield client

@pytest.mark.asyncio
async def test_session_workflow(client):
    """Test complete session workflow."""

    # Set agent context
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

    # Search context
    result = await client.call_tool(
        "search_context",
        {
            "session_id": session_id,
            "query": "test",
            "fuzzy_threshold": 60
        }
    )
    assert result["success"] is True
    assert len(result["results"]) > 0

@pytest.mark.asyncio
async def test_resource_subscription(client):
    """Test resource subscription updates."""

    client.set_context({"agent_id": "test_agent"})

    # Create session
    result = await client.call_tool(
        "create_session",
        {"purpose": "subscription test"}
    )
    session_id = result["session_id"]

    # Subscribe to resource
    subscription = await client.subscribe_to_resource(
        f"session://{session_id}"
    )

    # Add message (should trigger update)
    await client.call_tool(
        "add_message",
        {
            "session_id": session_id,
            "content": "New message"
        }
    )

    # Check for notification
    notification = await client.wait_for_notification(timeout=5)
    assert notification is not None
    assert notification["uri"] == f"session://{session_id}"
```

## Server Initialization and Configuration

```python
import asyncio
import logging
from contextlib import asynccontextmanager
from shared_context_server.database import initialize_database

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    """FastMCP server lifespan management."""

    # Startup
    logger.info("Initializing Shared Context MCP Server...")

    # Initialize database with DatabaseManager
    await initialize_database()

    # Start background tasks
    asyncio.create_task(cleanup_expired_data())
    asyncio.create_task(monitor_performance())

    logger.info("Server ready!")

    yield

    # Shutdown
    logger.info("Shutting down...")
    # DatabaseManager handles cleanup automatically
    logger.info("Shutdown complete")

async def cleanup_expired_data():
    """Background task to clean up expired data."""
    from shared_context_server.database import cleanup_expired_data

    while True:
        try:
            await asyncio.sleep(3600)  # Run hourly
            stats = await cleanup_expired_data()
            logger.info(f"Cleanup completed: {stats}")
        except Exception as e:
            logger.exception(f"Cleanup failed: {e}")

async def monitor_performance():
    """Background task to monitor performance."""
    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            # Add performance monitoring logic here
            logger.debug("Performance monitoring check completed")
        except Exception as e:
            logger.exception(f"Performance monitoring failed: {e}")

async def initialize_schema(conn):
    """Create database schema if not exists."""
    # DatabaseManager handles schema initialization automatically
    # Schema is loaded from database.sql file in project structure
    logger.info("Database schema initialization handled by DatabaseManager")

async def configure_sqlite_performance(conn):
    """Configure SQLite for optimal performance."""
    # DatabaseManager applies all PRAGMA settings automatically
    # See database.py _SQLITE_PRAGMAS for complete configuration
    logger.info("SQLite performance configuration handled by DatabaseManager")

async def create_indexes(conn):
    """Create performance indexes."""
    # Performance indexes are created as part of database.sql schema
    # DatabaseManager ensures all indexes are applied during initialization
    logger.info("Performance indexes handled by database schema initialization")

# Run the server
if __name__ == "__main__":
    import uvicorn

    # Create FastMCP app with lifespan
    app = mcp.create_app(lifespan=lifespan)

    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
```

## Best Practices

### 1. Use DatabaseManager for All Database Operations
```python
# Always use the centralized database manager
from shared_context_server.database import get_db_connection, utc_timestamp

async with get_db_connection() as conn:
    # Connection has all optimized settings applied
    cursor = await conn.execute(query, params)
    await conn.commit()
```

### 2. Sanitize and Validate All Inputs
```python
# Always sanitize user inputs
from shared_context_server.models import sanitize_text_input
from shared_context_server.utils.llm_errors import create_input_validation_error

# Validate and sanitize content using actual patterns
content = sanitize_text_input(content)
if not content.strip():
    return create_input_validation_error(
        "content", "", "non-empty text content"
    )
```

### 3. Use Consistent Error Handling
```python
# Always use LLMOptimizedErrorResponse hierarchy for errors
from shared_context_server.utils.llm_errors import create_system_error

try:
    # Operation logic
    pass
except Exception as e:
    logger.exception(f"Operation failed: {e}")
    return create_system_error("operation_name", "database")
```

### 4. Verify Permissions Before Operations
```python
# Always check permissions before proceeding
from shared_context_server.auth import validate_agent_context_or_error
from shared_context_server.utils.llm_errors import create_permission_denied_error

# Validate agent permissions using actual auth patterns
auth_result = await validate_agent_context_or_error(mcp.context)
if "error" in auth_result:
    return create_permission_denied_error(
        "write_session", "insufficient permissions"
    )
```

## Common Pitfalls

### 1. ❌ Not Using DatabaseManager
```python
# BAD - Direct aiosqlite connection
conn = await aiosqlite.connect("db.db")

# GOOD - Use DatabaseManager singleton
from shared_context_server.database import get_db_connection
async with get_db_connection() as conn:
    # Connection with optimized settings applied
```

### 2. ❌ Not Using Consistent Error Responses
```python
# BAD - Generic error response
return {"success": False, "error": "Not found"}

# GOOD - Use LLMOptimizedErrorResponse hierarchy
from shared_context_server.utils.llm_errors import create_resource_not_found_error
return create_resource_not_found_error("session", session_id)
```

### 3. ❌ Missing Input Sanitization
```python
# BAD - No input validation or sanitization
content = request_data["content"]

# GOOD - Validate and sanitize inputs
from shared_context_server.models import sanitize_text_input
content = sanitize_text_input(request_data["content"])
if not content.strip():
    return create_input_validation_error("content", "", "non-empty text")
```

## Performance Optimizations

- **DatabaseManager**: Consistent connection handling with optimized settings
- **RapidFuzz search**: 5-10x faster than difflib
- **Input sanitization**: Prevents XSS and injection attacks
- **LLMOptimizedErrorResponse hierarchy**: Structured error handling optimized for AI agents
- **In-memory testing**: 100x faster than subprocess with proper database setup

## References

- FastMCP Documentation: https://github.com/fastmcp/fastmcp
- RapidFuzz: https://github.com/maxbachmann/RapidFuzz
- Research findings: `/RESEARCH_FINDINGS_DEVELOPER.md`
- MCP Specification: https://modelcontextprotocol.io

## Related Guides

- Core Architecture Guide - MCP resource models and system design
- Data Validation Guide - Pydantic models and validation patterns
- Performance Optimization Guide - Speed improvements and monitoring
- Testing Guide - FastMCP testing strategies
