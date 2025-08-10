# PRP-003: Phase 2 - Essential Features

**Document Type**: Product Requirement Prompt  
**Created**: 2025-08-10  
**Phase**: 2 (Essential Features)  
**Timeline**: 8 hours  
**Priority**: High Features  
**Status**: Ready for Execution  
**Prerequisites**: Phase 1 - Core Infrastructure completed

---

## Research Context & Architectural Analysis

### Planning Integration
**Source**: Final Decomposed Implementation Plan, Framework Integration Guide, Performance Optimization Research  
**Research Foundation**: RapidFuzz fuzzy search (5-10x performance improvement), MCP resource subscriptions, agent memory scoping patterns  
**Strategic Context**: Building essential collaboration features that differentiate from mem0's retrieval-based approach with real-time search, persistent agent memory, and MCP-native resource subscriptions

### Architectural Scope
**Search Performance**: RapidFuzz implementation for fuzzy search with configurable thresholds, 5-10x faster than difflib  
**Agent Memory System**: Private key-value store with agent scoping, TTL expiration, session vs global scope management  
**MCP Resources**: Session resources with `session://{id}` URI scheme, agent memory resources with security, real-time subscriptions  
**Data Validation**: Comprehensive Pydantic models, input validation, type-safe request/response handling

### Existing Patterns to Leverage
**Framework Integration Guide**: Complete RapidFuzz search implementation, agent memory management, MCP resource providers  
**Core Architecture Guide**: MCP resource models, agent memory table schema, performance optimization strategies  
**Phase 1 Foundation**: FastMCP server operational, session management, message storage with visibility, agent identity system

---

## Implementation Specification

### Core Requirements

#### 1. RapidFuzz Search Implementation (5-10x Performance)
**Search Context Tool**:
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
    ),
    search_scope: str = Field(
        default="all",
        description="Search scope: all, public, private",
        regex="^(all|public|private)$"
    )
) -> Dict[str, Any]:
    """
    Fuzzy search messages using RapidFuzz for 5-10x performance improvement.
    
    Searches content, sender, and optionally metadata fields with agent-specific
    visibility controls.
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    async with get_db_connection() as conn:
        # Pre-filter optimization: Apply time window and row limits first
        max_rows_scanned = Field(default=1000, description="Maximum rows to scan for large datasets")
        recent_hours = Field(default=24, description="Default time window for recent content")
        
        # Build query with visibility, scope, and pre-filtering
        where_conditions = ["session_id = ?"]
        params = [session_id]
        
        # Add recency filter to reduce scan scope
        where_conditions.append("timestamp >= datetime('now', '-{} hours')".format(recent_hours))
        
        # Apply visibility controls
        if search_scope == "public":
            where_conditions.append("visibility = 'public'")
        elif search_scope == "private":
            where_conditions.append("visibility = 'private' AND sender = ?")
            params.append(agent_id)
        else:  # all accessible messages
            where_conditions.append("""
                (visibility = 'public' OR 
                 (visibility = 'private' AND sender = ?))
            """)
            params.append(agent_id)
        
        cursor = await conn.execute(f"""
            SELECT * FROM messages 
            WHERE {' AND '.join(where_conditions)}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params + [max_rows_scanned])
        
        rows = await cursor.fetchall()
        
        if not rows:
            return {
                "success": True,
                "results": [],
                "query": query,
                "message_count": 0
            }
        
        # Prepare searchable text with optimized processing
        searchable_items = []
        for row in rows:
            msg = dict(row)
            
            # Build searchable text efficiently
            text_parts = [
                msg.get('sender', ''),
                msg.get('content', '')
            ]
            
            if search_metadata and msg.get('metadata'):
                try:
                    metadata = json.loads(msg['metadata'])
                    if isinstance(metadata, dict):
                        # Extract searchable metadata values
                        searchable_values = [
                            str(v) for v in metadata.values()
                            if v and isinstance(v, (str, int, float, bool))
                        ]
                        text_parts.extend(searchable_values)
                except json.JSONDecodeError:
                    pass
            
            searchable_text = ' '.join(text_parts).lower()
            searchable_items.append((searchable_text, msg))
        
        # Use RapidFuzz for high-performance matching
        choices = [(item[0], idx) for idx, item in enumerate(searchable_items)]
        
        # RapidFuzz process.extract for optimal performance
        matches = process.extract(
            query.lower(),
            choices,
            scorer=fuzz.WRatio,  # Best balance of speed and accuracy
            limit=limit,
            score_cutoff=fuzzy_threshold,
            processor=lambda x: x[0]
        )
        
        # Build optimized results
        results = []
        for match in matches:
            _, score, choice_idx = match
            message = searchable_items[choice_idx][1]
            
            # Parse metadata for result
            metadata = {}
            if message.get('metadata'):
                try:
                    metadata = json.loads(message['metadata'])
                except json.JSONDecodeError:
                    metadata = {}
            
            # Create match preview with highlighting context
            content = message['content']
            preview_length = 150
            if len(content) > preview_length:
                content = content[:preview_length] + "..."
            
            results.append({
                "message": {
                    "id": message['id'],
                    "sender": message['sender'],
                    "content": message['content'],
                    "timestamp": message['timestamp'],
                    "visibility": message['visibility'],
                    "metadata": metadata
                },
                "score": round(score, 2),
                "match_preview": content,
                "relevance": "high" if score >= 80 else "medium" if score >= 60 else "low"
            })
        
        # Audit search operation
        await audit_log(conn, "context_searched", agent_id, session_id, {
            "query": query,
            "results_count": len(results),
            "threshold": fuzzy_threshold,
            "search_scope": search_scope
        })
    
    return {
        "success": True,
        "results": results,
        "query": query,
        "threshold": fuzzy_threshold,
        "search_scope": search_scope,
        "message_count": len(results),
        "performance_note": "RapidFuzz enabled (5-10x faster than standard fuzzy search)"
    }
```

**Advanced Search Features**:
```python
@mcp.tool()
async def search_by_sender(
    session_id: str = Field(description="Session ID to search within"),
    sender: str = Field(description="Sender to search for"),
    limit: int = Field(default=20, ge=1, le=100)
) -> Dict[str, Any]:
    """Search messages by specific sender with agent visibility controls."""
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    async with get_db_connection() as conn:
        cursor = await conn.execute("""
            SELECT * FROM messages 
            WHERE session_id = ? AND sender = ?
            AND (visibility = 'public' OR 
                 (visibility = 'private' AND sender = ?))
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, sender, agent_id, limit))
        
        messages = await cursor.fetchall()
        
        return {
            "success": True,
            "messages": [dict(msg) for msg in messages],
            "sender": sender,
            "count": len(messages)
        }

@mcp.tool()
async def search_by_timerange(
    session_id: str = Field(description="Session ID to search within"),
    start_time: str = Field(description="Start time (ISO format)"),
    end_time: str = Field(description="End time (ISO format)"),
    limit: int = Field(default=50, ge=1, le=200)
) -> Dict[str, Any]:
    """Search messages within a specific time range."""
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    async with get_db_connection() as conn:
        cursor = await conn.execute("""
            SELECT * FROM messages 
            WHERE session_id = ? 
            AND timestamp >= ? AND timestamp <= ?
            AND (visibility = 'public' OR 
                 (visibility = 'private' AND sender = ?))
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, start_time, end_time, agent_id, limit))
        
        messages = await cursor.fetchall()
        
        return {
            "success": True,
            "messages": [dict(msg) for msg in messages],
            "timerange": {"start": start_time, "end": end_time},
            "count": len(messages)
        }
```

#### 2. Agent Memory System
**Set Memory Tool**:
```python
@mcp.tool()
async def set_memory(
    key: str = Field(description="Memory key", min_length=1, max_length=255),
    value: Any = Field(description="Value to store (JSON serializable)"),
    session_id: Optional[str] = Field(
        default=None,
        description="Session scope (null for global memory)"
    ),
    expires_in: Optional[int] = Field(
        default=None,
        description="TTL in seconds (null for permanent)",
        ge=1,
        le=86400 * 365  # Max 1 year
    ),
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata for the memory entry"
    ),
    overwrite: bool = Field(
        default=True,
        description="Whether to overwrite existing key"
    )
) -> Dict[str, Any]:
    """
    Store value in agent's private memory with TTL and scope management.
    
    Memory can be session-scoped (isolated to specific session) or global
    (available across all sessions for the agent).
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    # Calculate expiration timestamp
    expires_at = None
    if expires_in:
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in
    
    # Serialize value to JSON with error handling
    try:
        if not isinstance(value, str):
            serialized_value = json.dumps(value, ensure_ascii=False)
        else:
            serialized_value = value
    except (TypeError, ValueError) as e:
        return {
            "success": False,
            "error": f"Value is not JSON serializable: {str(e)}",
            "code": "SERIALIZATION_ERROR"
        }
    
    async with get_db_connection() as conn:
        # Check if session exists (if session-scoped)
        if session_id:
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
        
        # Check for existing key if overwrite is False
        if not overwrite:
            cursor = await conn.execute("""
                SELECT key FROM agent_memory
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
            
            if await cursor.fetchone():
                return {
                    "success": False,
                    "error": f"Memory key '{key}' already exists",
                    "code": "KEY_EXISTS"
                }
        
        # Insert or update memory entry
        await conn.execute("""
            INSERT INTO agent_memory 
            (agent_id, session_id, key, value, metadata, expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, session_id, key) 
            DO UPDATE SET 
                value = excluded.value,
                metadata = excluded.metadata,
                updated_at = excluded.updated_at,
                expires_at = excluded.expires_at
        """, (
            agent_id,
            session_id,
            key,
            serialized_value,
            json.dumps(metadata or {}),
            expires_at,
            datetime.now(timezone.utc).isoformat()
        ))
        await conn.commit()
        
        # Audit log
        await audit_log(conn, "memory_set", agent_id, session_id, {
            "key": key,
            "session_scoped": session_id is not None,
            "has_expiration": expires_at is not None,
            "value_size": len(serialized_value)
        })
    
    return {
        "success": True,
        "key": key,
        "session_scoped": session_id is not None,
        "expires_at": expires_at,
        "scope": "session" if session_id else "global",
        "stored_at": datetime.now(timezone.utc).isoformat()
    }

@mcp.tool()
async def get_memory(
    key: str = Field(description="Memory key to retrieve"),
    session_id: Optional[str] = Field(
        default=None,
        description="Session scope (null for global memory)"
    )
) -> Dict[str, Any]:
    """
    Retrieve value from agent's private memory with automatic cleanup.
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    current_timestamp = datetime.now(timezone.utc).timestamp()
    
    async with get_db_connection() as conn:
        # Clean expired entries first
        await conn.execute("""
            DELETE FROM agent_memory 
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (current_timestamp,))
        
        # Retrieve memory entry
        cursor = await conn.execute("""
            SELECT key, value, metadata, created_at, updated_at, expires_at
            FROM agent_memory
            WHERE agent_id = ? AND key = ? 
            AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
            AND (expires_at IS NULL OR expires_at > ?)
        """, (
            agent_id,
            key,
            session_id,
            session_id,
            current_timestamp
        ))
        
        row = await cursor.fetchone()
        
        if not row:
            return {
                "success": False,
                "error": f"Memory key '{key}' not found or expired",
                "code": "MEMORY_NOT_FOUND"
            }
        
        # Parse stored value
        stored_value = row['value']
        try:
            # Try to deserialize JSON
            parsed_value = json.loads(stored_value)
        except json.JSONDecodeError:
            # If not JSON, return as string
            parsed_value = stored_value
        
        # Parse metadata
        metadata = {}
        if row['metadata']:
            try:
                metadata = json.loads(row['metadata'])
            except json.JSONDecodeError:
                metadata = {}
        
        return {
            "success": True,
            "key": key,
            "value": parsed_value,
            "metadata": metadata,
            "created_at": row['created_at'],
            "updated_at": row['updated_at'],
            "expires_at": row['expires_at'],
            "scope": "session" if session_id else "global"
        }

@mcp.tool()
async def list_memory(
    session_id: Optional[str] = Field(
        default=None,
        description="Session scope (null for global, 'all' for both)"
    ),
    prefix: Optional[str] = Field(
        default=None,
        description="Key prefix filter"
    ),
    limit: int = Field(default=50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    List agent's memory entries with filtering options.
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    current_timestamp = datetime.now(timezone.utc).timestamp()
    
    async with get_db_connection() as conn:
        # Clean expired entries
        await conn.execute("""
            DELETE FROM agent_memory 
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (current_timestamp,))
        
        # Build query based on scope
        where_conditions = ["agent_id = ?"]
        params = [agent_id]
        
        if session_id and session_id != "all":
            where_conditions.append("session_id = ?")
            params.append(session_id)
        
        if prefix:
            where_conditions.append("key LIKE ?")
            params.append(f"{prefix}%")
        
        where_conditions.append("(expires_at IS NULL OR expires_at > ?)")
        params.append(current_timestamp)
        
        params.append(limit)
        
        cursor = await conn.execute(f"""
            SELECT key, session_id, created_at, updated_at, expires_at, 
                   length(value) as value_size
            FROM agent_memory
            WHERE {' AND '.join(where_conditions)}
            ORDER BY updated_at DESC
            LIMIT ?
        """, params)
        
        entries = await cursor.fetchall()
        
        return {
            "success": True,
            "entries": [
                {
                    "key": entry['key'],
                    "scope": "session" if entry['session_id'] else "global",
                    "session_id": entry['session_id'],
                    "created_at": entry['created_at'],
                    "updated_at": entry['updated_at'],
                    "expires_at": entry['expires_at'],
                    "value_size": entry['value_size']
                }
                for entry in entries
            ],
            "count": len(entries),
            "scope_filter": session_id or "global"
        }
```

#### 3. MCP Resources & Subscriptions
**Session Resource Provider**:
```python
@mcp.resource("session://{session_id}")
async def get_session_resource(session_id: str) -> Resource:
    """
    Provide session as an MCP resource with real-time updates.
    
    Clients can subscribe to changes and receive notifications.
    """
    
    agent_id = mcp.context.get("agent_id", "unknown")
    
    async with get_db_connection() as conn:
        # Get session information
        cursor = await conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        session = await cursor.fetchone()
        
        if not session:
            raise ResourceNotFound(f"Session {session_id} not found")
        
        # Get visible messages for this agent
        cursor = await conn.execute("""
            SELECT * FROM messages 
            WHERE session_id = ? 
            AND (visibility = 'public' OR 
                 (visibility = 'private' AND sender = ?))
            ORDER BY timestamp ASC
        """, (session_id, agent_id))
        
        messages = await cursor.fetchall()
        
        # Get session statistics
        cursor = await conn.execute("""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(DISTINCT sender) as unique_agents,
                MAX(timestamp) as last_activity
            FROM messages 
            WHERE session_id = ?
        """, (session_id,))
        
        stats = await cursor.fetchone()
        
        # Format resource content
        content = {
            "session": {
                "id": session['id'],
                "purpose": session['purpose'],
                "created_at": session['created_at'],
                "updated_at": session['updated_at'],
                "created_by": session['created_by'],
                "is_active": bool(session['is_active']),
                "metadata": json.loads(session['metadata'] or '{}')
            },
            "messages": [
                {
                    "id": msg['id'],
                    "sender": msg['sender'],
                    "content": msg['content'],
                    "timestamp": msg['timestamp'],
                    "visibility": msg['visibility'],
                    "metadata": json.loads(msg['metadata'] or '{}'),
                    "parent_message_id": msg['parent_message_id']
                }
                for msg in messages
            ],
            "statistics": {
                "message_count": stats['total_messages'],
                "visible_message_count": len(messages),
                "unique_agents": stats['unique_agents'],
                "last_activity": stats['last_activity']
            },
            "resource_info": {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "requesting_agent": agent_id,
                "supports_subscriptions": True
            }
        }
        
        return Resource(
            uri=f"session://{session_id}",
            name=f"Session: {session['purpose']}",
            description=f"Shared context session with {len(messages)} visible messages",
            mimeType="application/json",
            text=json.dumps(content, indent=2, ensure_ascii=False)
        )

@mcp.resource("agent://{agent_id}/memory")
async def get_agent_memory_resource(requested_agent_id: str) -> Resource:
    """
    Provide agent memory as a resource with security controls.
    
    Only accessible by the agent itself for security.
    """
    
    requesting_agent = mcp.context.get("agent_id", "unknown")
    
    # Security check: only allow agents to access their own memory
    if requesting_agent != requested_agent_id:
        raise ResourceNotFound(f"Unauthorized access to agent memory for {requested_agent_id}")
    
    current_timestamp = datetime.now(timezone.utc).timestamp()
    
    async with get_db_connection() as conn:
        # Clean expired memory entries
        await conn.execute("""
            DELETE FROM agent_memory 
            WHERE agent_id = ? AND expires_at IS NOT NULL AND expires_at < ?
        """, (requested_agent_id, current_timestamp))
        
        # Get all memory entries for the agent
        cursor = await conn.execute("""
            SELECT key, value, session_id, metadata, created_at, updated_at, expires_at
            FROM agent_memory
            WHERE agent_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY updated_at DESC
        """, (requested_agent_id, current_timestamp))
        
        memories = await cursor.fetchall()
        
        # Organize memory by scope
        memory_by_scope = {
            "global": {},
            "sessions": {}
        }
        
        for row in memories:
            # Parse value
            try:
                value = json.loads(row['value'])
            except json.JSONDecodeError:
                value = row['value']
            
            # Parse metadata
            metadata = {}
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    pass
            
            memory_entry = {
                "value": value,
                "metadata": metadata,
                "created_at": row['created_at'],
                "updated_at": row['updated_at'],
                "expires_at": row['expires_at']
            }
            
            if row['session_id'] is None:
                # Global memory
                memory_by_scope["global"][row['key']] = memory_entry
            else:
                # Session-scoped memory
                session_id = row['session_id']
                if session_id not in memory_by_scope["sessions"]:
                    memory_by_scope["sessions"][session_id] = {}
                memory_by_scope["sessions"][session_id][row['key']] = memory_entry
        
        # Create resource content
        content = {
            "agent_id": requested_agent_id,
            "memory": memory_by_scope,
            "statistics": {
                "global_keys": len(memory_by_scope["global"]),
                "session_scopes": len(memory_by_scope["sessions"]),
                "total_entries": len(memories)
            },
            "resource_info": {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "supports_subscriptions": True
            }
        }
        
        return Resource(
            uri=f"agent://{requested_agent_id}/memory",
            name=f"Agent Memory: {requested_agent_id}",
            description=f"Private memory store with {len(memories)} entries",
            mimeType="application/json",
            text=json.dumps(content, indent=2, ensure_ascii=False)
        )
```

**Resource Subscription System with Lifecycle Management**:
```python
# Resource notification system for real-time updates with leak prevention
class ResourceNotificationManager:
    def __init__(self):
        self.subscribers = {}  # {resource_uri: set(client_ids)}
        self.client_last_seen = {}  # {client_id: timestamp}
        self.subscription_timeout = 300  # 5 minutes idle timeout
        
    async def subscribe(self, client_id: str, resource_uri: str):
        """Subscribe client to resource updates with timeout tracking."""
        if resource_uri not in self.subscribers:
            self.subscribers[resource_uri] = set()
        self.subscribers[resource_uri].add(client_id)
        self.client_last_seen[client_id] = time.time()
        
    async def unsubscribe(self, client_id: str, resource_uri: str = None):
        """Unsubscribe client from resource updates. If resource_uri is None, unsubscribe from all."""
        if resource_uri:
            if resource_uri in self.subscribers:
                self.subscribers[resource_uri].discard(client_id)
        else:
            # Unsubscribe from all resources
            for resource_subscribers in self.subscribers.values():
                resource_subscribers.discard(client_id)
        
        # Remove client tracking if no longer subscribed to anything
        if not any(client_id in subscribers for subscribers in self.subscribers.values()):
            self.client_last_seen.pop(client_id, None)
        
    async def cleanup_stale_subscriptions(self):
        """Remove subscriptions for clients that haven't been seen recently."""
        current_time = time.time()
        stale_clients = {
            client_id for client_id, last_seen in self.client_last_seen.items()
            if current_time - last_seen > self.subscription_timeout
        }
        
        for client_id in stale_clients:
            await self.unsubscribe(client_id)
            
    async def notify_resource_updated(self, resource_uri: str, debounce_ms: int = 100):
        """Notify all subscribers of resource changes with debouncing."""
        if resource_uri in self.subscribers:
            # Simple debounce: batch updates within debounce_ms window
            await asyncio.sleep(debounce_ms / 1000)
            
            for client_id in self.subscribers[resource_uri]:
                try:
                    await mcp.notify_resource_updated(resource_uri, client_id)
                    self.client_last_seen[client_id] = time.time()
                except Exception as e:
                    # Remove failed client subscription
                    await self.unsubscribe(client_id, resource_uri)

# Global notification manager
notification_manager = ResourceNotificationManager()

# Background task for periodic cleanup (lightweight scheduled sweeper)
@mcp.background_task(interval=60)  # Run every minute
async def cleanup_subscriptions():
    """Periodic cleanup of stale subscriptions."""
    await notification_manager.cleanup_stale_subscriptions()

@mcp.background_task(interval=300)  # Run every 5 minutes
async def cleanup_expired_memory():
    """Lightweight TTL sweeper for expired memory entries."""
    current_timestamp = datetime.now(timezone.utc).timestamp()
    
    async with get_db_connection() as conn:
        cursor = await conn.execute("""
            DELETE FROM agent_memory 
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (current_timestamp,))
        
        deleted_count = cursor.rowcount
        await conn.commit()
        
        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} expired memory entries")

# Integration with message and memory operations
async def trigger_resource_notifications(session_id: str, agent_id: str):
    """Trigger resource update notifications after changes."""
    
    # Notify session resource subscribers
    await notification_manager.notify_resource_updated(f"session://{session_id}")
    
    # Notify agent memory subscribers
    await notification_manager.notify_resource_updated(f"agent://{agent_id}/memory")
```

#### 4. Data Validation & Type Safety
**Comprehensive Pydantic Models**:
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone

class SessionModel(BaseModel):
    id: str = Field(..., regex=r'^session_[a-zA-Z0-9]{16}$')
    purpose: str = Field(..., min_length=1, max_length=500)
    created_by: str = Field(..., min_length=1, max_length=100)
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

class MessageModel(BaseModel):
    id: int
    session_id: str = Field(..., regex=r'^session_[a-zA-Z0-9]{16}$')
    sender: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=10000)
    visibility: Literal['public', 'private', 'agent_only']
    message_type: str = Field(default='agent_response', max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime
    parent_message_id: Optional[int] = None
    
    @validator('timestamp')
    def timestamp_must_be_utc(cls, v):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v

class AgentMemoryModel(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=100)
    session_id: Optional[str] = Field(None, regex=r'^session_[a-zA-Z0-9]{16}$')
    key: str = Field(..., min_length=1, max_length=255)
    value: str  # JSON serialized
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

class SearchRequest(BaseModel):
    session_id: str = Field(..., regex=r'^session_[a-zA-Z0-9]{16}$')
    query: str = Field(..., min_length=1, max_length=500)
    fuzzy_threshold: float = Field(default=60.0, ge=0, le=100)
    limit: int = Field(default=10, ge=1, le=100)
    search_metadata: bool = True
    search_scope: Literal['all', 'public', 'private'] = 'all'

class MemorySetRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: Any
    session_id: Optional[str] = Field(None, regex=r'^session_[a-zA-Z0-9]{16}$')
    expires_in: Optional[int] = Field(None, ge=1, le=86400 * 365)
    metadata: Optional[Dict[str, Any]] = None
    overwrite: bool = True
    
    @validator('key')
    def key_must_be_valid(cls, v):
        # Ensure key doesn't contain problematic characters
        if any(char in v for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
            raise ValueError('Key contains invalid characters')
        return v

class StandardResponse(BaseModel):
    success: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class ErrorResponse(StandardResponse):
    success: bool = False
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None

class SearchResponse(StandardResponse):
    success: bool = True
    results: List[Dict[str, Any]]
    query: str
    threshold: float
    search_scope: str
    message_count: int
    performance_note: str

class MemoryResponse(StandardResponse):
    success: bool = True
    key: str
    value: Any
    metadata: Dict[str, Any]
    scope: str
    created_at: str
    updated_at: str
```

**Input Validation & Sanitization**:
```python
import html
import re
from typing import Any, Dict

def sanitize_text(text: str) -> str:
    """Sanitize text input for security and consistency."""
    if not isinstance(text, str):
        text = str(text)
    
    # HTML escape
    text = html.escape(text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Limit length
    if len(text) > 10000:
        text = text[:10000] + "... [truncated]"
    
    return text

def sanitize_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize JSON metadata for security."""
    if not isinstance(data, dict):
        return {}
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(key, str) and len(key) <= 100:
            if isinstance(value, (str, int, float, bool)) or value is None:
                if isinstance(value, str):
                    value = sanitize_text(value)
                sanitized[key] = value
            elif isinstance(value, (list, dict)):
                # Simple nested structure support
                if isinstance(value, list) and len(value) <= 20:
                    sanitized[key] = [
                        sanitize_text(str(item)) if isinstance(item, str) else item
                        for item in value
                        if isinstance(item, (str, int, float, bool)) or item is None
                    ][:20]
                elif isinstance(value, dict) and len(value) <= 10:
                    sanitized[key] = {
                        k: sanitize_text(str(v)) if isinstance(v, str) else v
                        for k, v in value.items()
                        if isinstance(k, str) and len(k) <= 50
                        and isinstance(v, (str, int, float, bool)) or v is None
                    }
    
    return sanitized

def validate_session_id(session_id: str) -> bool:
    """Validate session ID format."""
    return bool(re.match(r'^session_[a-zA-Z0-9]{16}$', session_id))

def validate_agent_id(agent_id: str) -> bool:
    """Validate agent ID format."""
    return bool(re.match(r'^[a-zA-Z0-9_-]{1,100}$', agent_id))
```

### Integration Points

#### 1. Search Integration with Phase 1
- **Message Storage Integration**: Search leverages existing message visibility controls
- **Agent Context Integration**: Search respects agent identity and authentication
- **Session Isolation**: Search operates within session boundaries established in Phase 1
- **Performance Optimization**: RapidFuzz provides 5-10x improvement over standard search

#### 2. Memory System Integration
- **Agent Identity Integration**: Memory scoped to authenticated agents from Phase 1
- **Session Management Integration**: Memory can be session-scoped or global
- **Database Integration**: Leverages existing agent_memory table from Phase 0
- **TTL Integration**: Automatic cleanup of expired memory entries

#### 3. MCP Resource Integration
- **Session Resource Integration**: Resources expose session data with agent visibility controls
- **Real-time Integration**: Resource subscriptions enable live collaboration
- **Authentication Integration**: Resources respect agent identity and permissions
- **Notification Integration**: Resource updates trigger MCP notifications

### API Requirements

**Essential Feature Tools**:
1. **`search_context`** - RapidFuzz fuzzy search with agent visibility controls
2. **`search_by_sender`** - Sender-specific search with filtering
3. **`search_by_timerange`** - Time-based search for historical analysis
4. **`set_memory`** - Agent memory storage with TTL and scope management
5. **`get_memory`** - Memory retrieval with automatic cleanup
6. **`list_memory`** - Memory listing with filtering options

**MCP Resources**:
1. **`session://{session_id}`** - Live session data with subscription support
2. **`agent://{agent_id}/memory`** - Agent memory resource with security

---

## Quality Requirements

### Testing Strategy
**Framework**: FastMCP TestClient with behavioral testing focus  
**Test Categories**:
- **Unit Tests**: Individual feature functionality, RapidFuzz performance, memory operations
- **Integration Tests**: Search with visibility controls, memory with session scoping, resource subscriptions
- **Performance Tests**: Search speed benchmarks, memory TTL cleanup, resource update latency
- **Behavioral Tests**: Multi-agent search scenarios, memory isolation, real-time resource updates

**Key Test Scenarios**:
```python
@pytest.mark.asyncio
async def test_rapidfuzz_search_performance(client):
    """Test RapidFuzz search performance and accuracy."""
    
    client.set_context({"agent_id": "test_agent"})
    
    # Create session with test messages
    session_result = await client.call_tool(
        "create_session", 
        {"purpose": "search performance test"}
    )
    session_id = session_result["session_id"]
    
    # Add test messages for search
    test_messages = [
        "The quick brown fox jumps over the lazy dog",
        "Python programming with async await patterns",
        "FastMCP server implementation guide",
        "Agent memory system with TTL expiration",
        "RapidFuzz fuzzy search performance optimization"
    ]
    
    for content in test_messages:
        await client.call_tool("add_message", {
            "session_id": session_id,
            "content": content,
            "visibility": "public"
        })
    
    # Test search performance
    start_time = time.time()
    result = await client.call_tool("search_context", {
        "session_id": session_id,
        "query": "fuzzy search performance",
        "fuzzy_threshold": 60
    })
    search_time = (time.time() - start_time) * 1000  # ms
    
    assert result["success"] is True
    assert len(result["results"]) > 0
    assert search_time < 100  # <100ms for fuzzy search
    assert "RapidFuzz enabled" in result["performance_note"]

@pytest.mark.asyncio
async def test_agent_memory_ttl_system(client):
    """Test agent memory TTL and cleanup system."""
    
    client.set_context({"agent_id": "test_agent"})
    
    # Set memory with short TTL
    result = await client.call_tool("set_memory", {
        "key": "temp_key",
        "value": {"test": "data"},
        "expires_in": 1  # 1 second
    })
    assert result["success"] is True
    
    # Immediately retrieve - should work
    result = await client.call_tool("get_memory", {"key": "temp_key"})
    assert result["success"] is True
    assert result["value"]["test"] == "data"
    
    # Wait for expiration
    await asyncio.sleep(2)
    
    # Should be expired/cleaned up
    result = await client.call_tool("get_memory", {"key": "temp_key"})
    assert result["success"] is False
    assert result["code"] == "MEMORY_NOT_FOUND"

@pytest.mark.asyncio
async def test_mcp_resource_subscriptions(client):
    """Test MCP resource subscription and notification system."""
    
    client.set_context({"agent_id": "test_agent"})
    
    # Create session
    session_result = await client.call_tool(
        "create_session",
        {"purpose": "resource subscription test"}
    )
    session_id = session_result["session_id"]
    
    # Subscribe to session resource
    subscription = await client.subscribe_to_resource(f"session://{session_id}")
    assert subscription is not None
    
    # Add message (should trigger notification)
    await client.call_tool("add_message", {
        "session_id": session_id,
        "content": "Notification trigger message"
    })
    
    # Check for resource update notification
    notification = await client.wait_for_notification(timeout=5)
    assert notification is not None
    assert notification["uri"] == f"session://{session_id}"

@pytest.mark.asyncio
async def test_search_visibility_controls(client):
    """Test search respects message visibility controls."""
    
    agent1_context = {"agent_id": "agent1"}
    agent2_context = {"agent_id": "agent2"}
    
    client.set_context(agent1_context)
    
    # Create session and add messages with different visibility
    session_result = await client.call_tool(
        "create_session", 
        {"purpose": "visibility test"}
    )
    session_id = session_result["session_id"]
    
    # Add public message
    await client.call_tool("add_message", {
        "session_id": session_id,
        "content": "Public searchable content",
        "visibility": "public"
    })
    
    # Add private message
    await client.call_tool("add_message", {
        "session_id": session_id,
        "content": "Private searchable content",
        "visibility": "private"
    })
    
    # Search as agent1 (should see both)
    result = await client.call_tool("search_context", {
        "session_id": session_id,
        "query": "searchable content",
        "search_scope": "all"
    })
    assert len(result["results"]) == 2
    
    # Search as agent2 (should only see public)
    client.set_context(agent2_context)
    result = await client.call_tool("search_context", {
        "session_id": session_id,
        "query": "searchable content",
        "search_scope": "all"
    })
    assert len(result["results"]) == 1
    assert "Public" in result["results"][0]["message"]["content"]
```

### Documentation Needs
**Essential Features Documentation**:
- **Search System**: RapidFuzz search capabilities, visibility controls, performance characteristics
- **Memory System**: Agent memory scoping, TTL management, best practices for key design
- **MCP Resources**: Resource URI schemes, subscription patterns, real-time update handling
- **Data Validation**: Pydantic models, input sanitization, error handling patterns

### Performance Considerations
**Essential Features Performance Requirements**:
- Fuzzy search (1000 messages): < 100ms (5-10x faster than standard search)
- Memory set/get operations: < 10ms
- Resource subscription notification: < 50ms
- Memory TTL cleanup: < 20ms per cleanup cycle

**Optimization Strategies**:
- **RapidFuzz Implementation**: WRatio scorer for optimal speed/accuracy balance
- **Memory Indexing**: Efficient indexes on agent_id, session_id, key combinations
- **Resource Caching**: Cache frequently accessed resources for faster subscription updates
- **Batch Operations**: TTL cleanup and resource notifications optimized for batch processing

---

## Coordination Strategy

### Recommended Approach: Direct Agent Assignment
**Complexity Assessment**: Essential features with moderate-high complexity  
**File Count**: 8-12 files (search.py, memory.py, resources.py, models.py, validators.py, multiple test files)  
**Integration Risk**: Medium (integrating with Phase 1 infrastructure, new performance requirements)  
**Time Estimation**: 8 hours with comprehensive validation and performance testing

**Agent Assignment**: **Developer Agent** for complete Phase 2 execution  
**Rationale**: Essential features require deep FastMCP knowledge, RapidFuzz optimization, MCP resource implementation - all developer agent core competencies

### Implementation Phases

#### Phase 2.1: RapidFuzz Search Implementation (2 hours)
**Implementation Steps**:
1. **Core Search Tool** (60 minutes): RapidFuzz integration, fuzzy matching, result ranking
2. **Advanced Search Features** (30 minutes): Sender search, timerange search, metadata search
3. **Performance Optimization** (30 minutes): Query optimization, result caching, search scope filtering

**Validation Checkpoints**:
```python
# Performance validation
search_time = await measure_search_performance()
assert search_time < 100  # <100ms for 1000 messages

# Accuracy validation  
results = await client.call_tool("search_context", {
    "query": "test query",
    "fuzzy_threshold": 80
})
assert all(result["score"] >= 80 for result in results["results"])
```

#### Phase 2.2: Agent Memory System (2 hours)
**Implementation Steps**:
1. **Memory Storage** (45 minutes): set_memory tool with TTL, JSON serialization, scope management
2. **Memory Retrieval** (45 minutes): get_memory tool with cleanup, deserialization, error handling  
3. **Memory Management** (30 minutes): list_memory tool, batch cleanup, performance optimization

**Validation Checkpoints**:
```python
# TTL validation
await client.call_tool("set_memory", {"key": "test", "value": "data", "expires_in": 1})
await asyncio.sleep(2)
result = await client.call_tool("get_memory", {"key": "test"})
assert result["success"] is False  # Should be expired

# Scope validation
# (Test global vs session-scoped memory isolation)
```

#### Phase 2.3: MCP Resources & Subscriptions (2 hours)
**Implementation Steps**:
1. **Session Resources** (60 minutes): session:// URI scheme, agent visibility, statistics
2. **Agent Memory Resources** (30 minutes): agent:// URI scheme, security controls, memory organization
3. **Subscription System** (30 minutes): Resource notifications, real-time updates, client management

**Validation Checkpoints**:
```python
# Resource access validation
resource = await client.get_resource("session://session_123")
assert resource["session"]["id"] == "session_123"

# Subscription validation
subscription = await client.subscribe_to_resource("session://session_123")
# (Verify notifications are received on updates)
```

#### Phase 2.4: Data Validation & Type Safety (2 hours)
**Implementation Steps**:
1. **Pydantic Models** (60 minutes): Comprehensive models for all data structures, validation rules
2. **Input Sanitization** (30 minutes): Text sanitization, JSON validation, security controls
3. **Error Handling** (30 minutes): Structured error responses, validation error messages, user feedback

**Validation Checkpoints**:
```python
# Model validation
try:
    SearchRequest(session_id="invalid", query="test")
    assert False, "Should have raised validation error"
except ValueError as e:
    assert "session_id" in str(e)

# Sanitization validation
sanitized = sanitize_text("<script>alert('xss')</script>")
assert "<script>" not in sanitized
```

### Risk Mitigation

#### Technical Risks
**RapidFuzz Performance Issues**: Comprehensive benchmarking, scorer selection optimization, result caching  
**Memory System Complexity**: TTL management testing, scope isolation validation, cleanup automation  
**Resource Subscription Overhead**: Efficient notification system, subscription management, client cleanup  
**Data Validation Complexity**: Incremental model development, comprehensive test coverage, error handling

#### Integration Risks
**Phase 1 Integration Issues**: Thorough testing of search with message visibility, memory with agent identity  
**Database Performance Bottlenecks**: Memory query optimization, search result caching, index utilization  
**MCP Protocol Complexity**: Resource URI scheme validation, subscription notification testing  
**Security Validation Gaps**: Input sanitization testing, agent memory access controls, resource security

### Dependencies & Prerequisites
**Phase 1 Completion**: FastMCP server operational, session management, message storage, agent identity  
**Database Optimization**: Proper indexes for search and memory operations, connection pooling operational  
**RapidFuzz Integration**: Performance benchmarking environment, fuzzy search test data  
**MCP Resource Knowledge**: Resource provider patterns, subscription mechanisms, client notification handling

---

## Success Criteria

### Functional Success
**RapidFuzz Search System**:
- ✅ Fuzzy search with 5-10x performance improvement over standard search
- ✅ Configurable similarity thresholds and result limiting  
- ✅ Agent visibility controls properly integrated with search results
- ✅ Advanced search features (sender, timerange, metadata) operational
- ✅ Search result ranking and relevance scoring working correctly

**Agent Memory System**:
- ✅ Private key-value store with agent scoping and session isolation
- ✅ TTL expiration system with automatic cleanup functional
- ✅ Session-scoped vs global memory management working correctly
- ✅ JSON serialization/deserialization with error handling
- ✅ Memory listing and filtering operations optimal

**MCP Resources & Subscriptions**:
- ✅ Session resources with proper URI scheme and agent visibility controls
- ✅ Agent memory resources with security access controls  
- ✅ Real-time resource subscriptions and notification system functional
- ✅ Resource update triggers and client notification delivery working

**Data Validation & Type Safety**:
- ✅ Comprehensive Pydantic models with proper validation rules
- ✅ Input sanitization preventing XSS and injection attacks
- ✅ Type-safe request/response handling throughout
- ✅ Structured error responses with helpful validation messages

### Integration Success
**Search Integration**: Search system properly integrated with Phase 1 message storage and visibility controls  
**Memory Integration**: Agent memory system working with Phase 1 agent identity and authentication  
**Resource Integration**: MCP resources properly exposing session and memory data with real-time updates  
**Security Integration**: Data validation and sanitization preventing security vulnerabilities

### Quality Gates
**Essential Features Testing**:
```bash
uv run test tests/unit/test_search_performance.py        # RapidFuzz performance tests pass
uv run test tests/unit/test_memory_ttl.py               # Memory TTL system tests pass
uv run test tests/integration/test_mcp_resources.py     # Resource subscription tests pass
uv run test tests/behavioral/test_agent_collaboration.py # Multi-agent feature tests pass
```

**Performance Benchmarks**:
- Fuzzy search (1000 messages): < 100ms
- Memory operations: < 10ms
- Resource notifications: < 50ms
- TTL cleanup cycle: < 20ms

**Code Quality**:
```bash
uv run ruff check .     # No linting errors
uv run mypy .           # No type checking errors  
coverage report         # >85% test coverage for essential features
```

### Validation Checklist

#### ✅ RapidFuzz Search Implementation
- [ ] search_context tool with RapidFuzz integration working
- [ ] 5-10x performance improvement verified through benchmarks
- [ ] Agent visibility controls properly integrated with search
- [ ] Advanced search features (sender, timerange) operational
- [ ] Search result ranking and relevance scoring accurate

#### ✅ Agent Memory System
- [ ] set_memory tool with TTL and scope management working
- [ ] get_memory tool with automatic cleanup functional
- [ ] list_memory tool with filtering options operational  
- [ ] Session-scoped vs global memory isolation working
- [ ] JSON serialization/deserialization error handling robust

#### ✅ MCP Resources & Subscriptions
- [ ] Session resources with session:// URI scheme working
- [ ] Agent memory resources with agent:// URI scheme functional
- [ ] Resource subscription and notification system operational
- [ ] Real-time updates triggering proper notifications
- [ ] Security controls preventing unauthorized resource access

#### ✅ Data Validation & Type Safety  
- [ ] Comprehensive Pydantic models with validation rules
- [ ] Input sanitization preventing security vulnerabilities
- [ ] Type-safe request/response handling throughout
- [ ] Structured error responses with helpful messages
- [ ] Validation error handling providing clear user feedback

---

## Implementation Notes

### Critical Success Factors
1. **RapidFuzz Performance**: Proper scorer selection (WRatio) and optimization for 5-10x improvement
2. **Memory System Reliability**: TTL management, automatic cleanup, scope isolation working correctly
3. **Resource Subscription Efficiency**: Real-time notifications without performance overhead
4. **Data Validation Rigor**: Comprehensive input sanitization and type safety throughout
5. **Integration Quality**: Seamless integration with Phase 1 session and message systems

### Common Pitfalls to Avoid
1. **❌ Search Performance Bottlenecks**: Monitor RapidFuzz configuration, optimize for speed vs accuracy
2. **❌ Memory System Race Conditions**: Proper TTL cleanup, concurrent access handling  
3. **❌ Resource Subscription Leaks**: Client subscription management, cleanup on disconnect
4. **❌ Validation Bypass**: Ensure all inputs go through validation, no direct database access
5. **❌ Security Gaps**: Input sanitization, agent memory access controls, resource security

### Post-Phase Integration  
**Preparation for Phase 3**:
- Search system ready for advanced authentication integration
- Memory system prepared for enhanced permission models
- Resource subscription system ready for advanced visibility controls
- Data validation framework ready for production security features

---

## References

### Planning Documents
- [Final Decomposed Implementation Plan](../1-planning/shared-context-mcp-server/FINAL_DECOMPOSED_IMPLEMENTATION_PLAN.md)  
- [Framework Integration Guide](../../.claude/tech-guides/framework-integration.md) - RapidFuzz Search, Agent Memory Management
- [Core Architecture Guide](../../.claude/tech-guides/core-architecture.md) - MCP Resource Models, Performance Optimization

### Implementation Patterns
- **RapidFuzz Search Implementation**: Framework Integration Guide lines 176-287
- **Agent Memory Management**: Framework Integration Guide lines 289-417  
- **MCP Resources & Subscriptions**: Framework Integration Guide lines 419-517

### External References
- [RapidFuzz Documentation](https://github.com/maxbachmann/RapidFuzz) - Performance optimization, scorer selection
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation, model design patterns
- [MCP Resource Specification](https://modelcontextprotocol.io/specification/server/resources) - Resource patterns

---

## Documentation Updates

### README.md Updates Required
Upon completion of Phase 2, update README.md to reflect:

**Status Section**:
```markdown
## Status

🎯 **Phase 2 Complete**: Essential Features ready
- ✅ RapidFuzz search with 5-10x performance improvement
- ✅ Agent memory system with TTL and scope management
- ✅ MCP resources with session:// and agent:// URI schemes
- ✅ Real-time subscriptions and notifications
- ✅ Comprehensive data validation and type safety

🚀 **Next**: Phase 3 - Multi-Agent Features implementation

## API Tools

### Session Management
- `create_session` - Create isolated collaboration sessions
- `get_session` - Retrieve session info and message history

### Message System  
- `add_message` - Add messages with visibility controls
- `get_messages` - Retrieve messages with agent-specific filtering

### Search & Discovery
- `search_context` - RapidFuzz fuzzy search with ranking
- Advanced filters: sender, timerange, visibility scopes

### Agent Memory
- `set_memory` - Store values with TTL and scope management
- `get_memory` - Retrieve memory with automatic cleanup
- `list_memory` - Browse memory with filtering options

**Performance**: < 100ms search, < 10ms memory operations  
**Features**: MCP resources, real-time subscriptions, comprehensive validation
```

**Architecture Section Update**:
```markdown
## Architecture

### Essential Features (Phase 2)
- **RapidFuzz Search**: High-performance fuzzy matching with relevance scoring
- **Agent Memory System**: TTL-managed storage with session/global scoping
- **MCP Resources**: URI-based resources (session://, agent://) with subscriptions
- **Real-time Notifications**: Resource change events with filtered delivery
- **Data Validation**: Comprehensive Pydantic models with security sanitization
```

---

**Ready for Execution**: Phase 2 essential features implementation  
**Next Phase**: Phase 3 - Multi-Agent Features (authentication, visibility, real-time coordination)  
**Coordination**: Direct developer agent assignment for complete Phase 2 execution