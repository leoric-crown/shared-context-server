# Framework Integration Guide

## Overview

This guide provides practical FastMCP server implementation patterns for the Shared Context MCP Server. For foundational architecture, database design, and MCP resource models, see the [Core Architecture Guide](core-architecture.md).

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
    description="Centralized memory store for multi-agent collaboration"
)
```

## Core MCP Tool Implementations

### Session Management Tools

```python
from uuid import uuid4
import aiosqlite
from aiosqlitepool import create_pool

# Global database pool
db_pool = None

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

    async with db_pool.acquire() as conn:
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

    async with db_pool.acquire() as conn:
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
    async with db_pool.acquire() as conn:
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

    async with db_pool.acquire() as conn:
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

    async with db_pool.acquire() as conn:
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

    async with db_pool.acquire() as conn:
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

    async with db_pool.acquire() as conn:
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
from contextlib import asynccontextmanager
import aiosqlitepool

@asynccontextmanager
async def lifespan(app):
    """FastMCP server lifespan management."""

    global db_pool

    # Startup
    print("Initializing Shared Context MCP Server...")

    # Initialize database pool
    db_pool = await aiosqlitepool.create_pool(
        "sqlite:///./chat_history.db",
        min_size=2,
        max_size=20,
        check_same_thread=False
    )

    # Initialize database schema
    async with db_pool.acquire() as conn:
        await initialize_schema(conn)
        await configure_sqlite_performance(conn)
        await create_indexes(conn)

    # Initialize caches
    global cache
    cache = LayeredCache()

    # Start background tasks
    asyncio.create_task(cleanup_expired_memory())
    asyncio.create_task(monitor_performance())

    print("Server ready!")

    yield

    # Shutdown
    print("Shutting down...")
    await db_pool.close()
    print("Shutdown complete")

async def initialize_schema(conn):
    """Create database schema if not exists."""
    # Import schema from core architecture module
    from shared_context_server.schema import get_database_schema

    schema_sql = get_database_schema()
    await conn.executescript(schema_sql)

    # Note: Complete schema definition available in Core Architecture Guide

async def configure_sqlite_performance(conn):
    """Configure SQLite for optimal performance."""

    await conn.execute("PRAGMA journal_mode = WAL")
    await conn.execute("PRAGMA synchronous = NORMAL")
    await conn.execute("PRAGMA cache_size = -8000")
    await conn.execute("PRAGMA temp_store = MEMORY")
    await conn.execute("PRAGMA mmap_size = 30000000000")
    await conn.execute("PRAGMA busy_timeout = 5000")
    await conn.execute("PRAGMA optimize")

async def create_indexes(conn):
    """Create performance indexes."""
    # Import indexes from core architecture module
    from shared_context_server.schema import get_performance_indexes

    indexes = get_performance_indexes()
    for index in indexes:
        await conn.execute(index)

    # Note: Complete index definitions available in Core Architecture Guide

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

### 1. Use Context for Agent Identity
```python
# Always get agent ID from context
agent_id = mcp.context.get("agent_id", "unknown")
```

### 2. Validate with Pydantic Fields
```python
# Use Field for validation
session_id: str = Field(
    description="Session ID",
    regex="^[a-zA-Z0-9-_]{8,64}$"
)
```

### 3. Handle Errors Gracefully
```python
# Return structured errors
return {
    "success": False,
    "error": "Session not found",
    "code": "SESSION_NOT_FOUND"
}
```

### 4. Cache Strategically
```python
# Cache read operations
if cached := await cache.get(key):
    return cached
result = await expensive_operation()
await cache.set(key, result, ttl=30)
```

## Common Pitfalls

### 1. ❌ Not Using Connection Pooling
```python
# BAD - Creates new connection
conn = await aiosqlite.connect("db.db")

# GOOD - Uses pool
async with db_pool.acquire() as conn:
    # Use connection
```

### 2. ❌ Forgetting to Invalidate Cache
```python
# BAD - Stale cache
await db.insert_message(...)

# GOOD - Invalidate after write
await db.insert_message(...)
await cache.invalidate(session_id)
```

### 3. ❌ Missing Context Validation
```python
# BAD - No agent identity
await db.add_message(session_id, content)

# GOOD - Include agent identity
agent_id = mcp.context.get("agent_id")
await db.add_message(session_id, content, agent_id)
```

## Performance Optimizations

- **Connection pooling**: 5-10x improvement for concurrent access
- **RapidFuzz search**: 5-10x faster than difflib
- **Caching**: 10-100x faster for hot data
- **WAL mode**: Enables concurrent reads/writes
- **In-memory testing**: 100x faster than subprocess

## References

- FastMCP Documentation: https://github.com/fastmcp/fastmcp
- RapidFuzz: https://github.com/maxbachmann/RapidFuzz
- Research findings: `/RESEARCH_FINDINGS_DEVELOPER.md`
- MCP Specification: https://modelcontextprotocol.io

## Related Guides

- MCP Integration Guide - MCP-specific patterns
- Pydantic Models Guide - Data validation
- Performance Optimization Guide - Speed improvements
- Testing Patterns Guide - Testing strategies
