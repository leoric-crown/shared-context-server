# Shared Context MCP Server - API Reference

Complete API reference for the production-ready Shared Context MCP Server with 12+ MCP tools for multi-agent collaboration.

## Table of Contents

- [Authentication & Authorization](#authentication--authorization)
- [Session Management](#session-management)
- [Message System](#message-system)
- [Context Search & Discovery](#context-search--discovery)
- [Agent Memory System](#agent-memory-system)
- [Performance & Monitoring](#performance--monitoring)
- [MCP Resources](#mcp-resources)
- [Error Handling](#error-handling)
- [Rate Limits & Performance](#rate-limits--performance)

## Authentication & Authorization

### JWT Token Authentication

The server uses JWT tokens for secure agent authentication with role-based permissions.

#### `authenticate_agent`

Generate JWT token with role-based permissions for agent authentication.

**Parameters:**
- `agent_id` (string, required): Unique agent identifier (1-100 chars)
- `agent_type` (string, required): Agent type (claude, gemini, custom) (max 50 chars)
- `api_key` (string, required): Agent API key for initial authentication
- `requested_permissions` (array, optional): Requested permissions (default: ["read", "write"])

**Available Permissions:**
- `read`: View public messages and session info
- `write`: Create sessions and add messages
- `admin`: Access admin_only messages, view audit logs, modify visibility

**Request Example:**
```json
{
  "tool": "authenticate_agent",
  "parameters": {
    "agent_id": "claude-main",
    "agent_type": "claude",
    "api_key": "your-secure-api-key",
    "requested_permissions": ["read", "write", "admin"]
  }
}
```

**Response Example:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "agent_id": "claude-main",
  "agent_type": "claude",
  "permissions": ["read", "write", "admin"],
  "expires_at": "2025-01-15T11:30:00Z",
  "token_type": "Bearer",
  "issued_at": "2025-01-15T10:30:00Z"
}
```

**Error Responses:**
- `INVALID_API_KEY`: Invalid or missing API key
- `AUTHENTICATION_ERROR`: System authentication error

---

## Session Management

### `create_session`

Create a new isolated collaboration session for multi-agent work.

**Permissions Required:** `write`

**Parameters:**
- `purpose` (string, required): Purpose or description of the session
- `metadata` (object, optional): Optional metadata for the session

**Request Example:**
```json
{
  "tool": "create_session",
  "parameters": {
    "purpose": "Planning new MCP integration feature",
    "metadata": {
      "priority": "high",
      "estimated_duration": "2h",
      "team": "backend"
    }
  }
}
```

**Response Example:**
```json
{
  "success": true,
  "session_id": "session_a1b2c3d4e5f6g7h8",
  "created_by": "claude-main",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Performance:** < 10ms typical response time

### `get_session`

Retrieve session information and recent message history.

**Permissions Required:** `read`

**Parameters:**
- `session_id` (string, required): Session ID to retrieve

**Response Example:**
```json
{
  "success": true,
  "session": {
    "id": "session_a1b2c3d4e5f6g7h8",
    "purpose": "Planning new MCP integration feature",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:35:00Z",
    "created_by": "claude-main",
    "is_active": true,
    "metadata": {
      "priority": "high",
      "team": "backend"
    }
  },
  "messages": [...],
  "message_count": 15
}
```

---

## Message System

### `add_message`

Add a message to a shared context session with visibility controls.

**Permissions Required:** `write` (basic), `admin` (for admin_only visibility)

**Parameters:**
- `session_id` (string, required): Session ID (format: `session_[16-hex-chars]`)
- `content` (string, required): Message content (1-10,000 chars)
- `visibility` (string, optional): Message visibility level (default: "public")
  - `public`: Visible to all agents in session
  - `private`: Visible only to sender
  - `agent_only`: Visible only to agents of same type
  - `admin_only`: Visible only to agents with admin permission
- `metadata` (object, optional): Optional message metadata
- `parent_message_id` (integer, optional): ID of parent message for threading

**Request Example:**
```json
{
  "tool": "add_message",
  "parameters": {
    "session_id": "session_a1b2c3d4e5f6g7h8",
    "content": "I've completed the database schema design. Ready for review.",
    "visibility": "public",
    "metadata": {
      "type": "status_update",
      "component": "database",
      "confidence": 0.95
    }
  }
}
```

**Response Example:**
```json
{
  "success": true,
  "message_id": 42,
  "timestamp": "2025-01-15T10:35:00Z"
}
```

**Performance:** < 20ms typical response time

### `get_messages`

Retrieve messages from session with agent-specific filtering and pagination.

**Permissions Required:** `read`

**Parameters:**
- `session_id` (string, required): Session ID to retrieve messages from
- `limit` (integer, optional): Maximum messages to return (1-1000, default: 50)
- `offset` (integer, optional): Offset for pagination (default: 0)
- `visibility_filter` (string, optional): Filter by visibility: public, private, agent_only, admin_only

**Response Example:**
```json
{
  "success": true,
  "messages": [
    {
      "id": 42,
      "sender": "claude-main",
      "sender_type": "claude",
      "content": "I've completed the database schema design.",
      "timestamp": "2025-01-15T10:35:00Z",
      "visibility": "public",
      "metadata": {
        "type": "status_update",
        "component": "database"
      },
      "parent_message_id": null
    }
  ],
  "count": 1,
  "total_count": 15,
  "has_more": true
}
```

**Performance:** < 30ms for 50 messages

---

## Context Search & Discovery

### `search_context`

Fuzzy search messages using RapidFuzz for 5-10x performance improvement.

**Permissions Required:** `read`

**Parameters:**
- `session_id` (string, required): Session ID to search within
- `query` (string, required): Search query (max 500 chars)
- `fuzzy_threshold` (number, optional): Minimum similarity score 0-100 (default: 60.0)
- `limit` (integer, optional): Maximum results to return (1-100, default: 10)
- `search_metadata` (boolean, optional): Include metadata in search (default: true)
- `search_scope` (enum, optional): Search scope - "all", "public", "private" (default: "all")

**Request Example:**
```json
{
  "tool": "search_context",
  "parameters": {
    "session_id": "session_a1b2c3d4e5f6g7h8",
    "query": "database schema design",
    "fuzzy_threshold": 70.0,
    "limit": 5,
    "search_scope": "all"
  }
}
```

**Response Example:**
```json
{
  "success": true,
  "results": [
    {
      "message": {
        "id": 42,
        "sender": "claude-main",
        "content": "I've completed the database schema design. Ready for review.",
        "timestamp": "2025-01-15T10:35:00Z",
        "visibility": "public",
        "metadata": {
          "type": "status_update",
          "component": "database"
        }
      },
      "score": 95.8,
      "match_preview": "I've completed the database schema design. Ready for review.",
      "relevance": "high"
    }
  ],
  "query": "database schema design",
  "threshold": 70.0,
  "search_scope": "all",
  "message_count": 1,
  "search_time_ms": 12.5,
  "performance_note": "RapidFuzz enabled (5-10x faster than standard fuzzy search)",
  "cache_hit": false
}
```

**Performance:** < 100ms for 1000 messages with RapidFuzz optimization

### `search_by_sender`

Search messages by specific sender with agent visibility controls.

**Permissions Required:** `read`

**Parameters:**
- `session_id` (string, required): Session ID to search within
- `sender` (string, required): Sender to search for
- `limit` (integer, optional): Maximum results (1-100, default: 20)

**Response Example:**
```json
{
  "success": true,
  "messages": [...],
  "sender": "claude-main",
  "count": 8
}
```

### `search_by_timerange`

Search messages within a specific time range.

**Permissions Required:** `read`

**Parameters:**
- `session_id` (string, required): Session ID to search within
- `start_time` (string, required): Start time (ISO format)
- `end_time` (string, required): End time (ISO format)
- `limit` (integer, optional): Maximum results (1-200, default: 50)

**Response Example:**
```json
{
  "success": true,
  "messages": [...],
  "timerange": {
    "start": "2025-01-15T10:00:00Z",
    "end": "2025-01-15T11:00:00Z"
  },
  "count": 12
}
```

---

## Agent Memory System

### `set_memory`

Store value in agent's private memory with TTL and scope management.

**Permissions Required:** `write`

**Parameters:**
- `key` (string, required): Memory key (1-255 chars, alphanumeric + underscore/dash)
- `value` (any, required): JSON serializable value to store
- `session_id` (string, optional): Session scope (null for global memory)
- `expires_in` (integer, optional): TTL in seconds (1 to 31,536,000 = 1 year)
- `metadata` (object, optional): Optional metadata for the memory entry
- `overwrite` (boolean, optional): Whether to overwrite existing key (default: true)

**Request Example:**
```json
{
  "tool": "set_memory",
  "parameters": {
    "key": "current_task_state",
    "value": {
      "phase": "implementation",
      "progress": 0.6,
      "blockers": ["waiting for API review"],
      "priority": "high"
    },
    "session_id": "session_a1b2c3d4e5f6g7h8",
    "expires_in": 3600,
    "metadata": {
      "type": "task_tracking",
      "updated_by": "claude-main"
    }
  }
}
```

**Response Example:**
```json
{
  "success": true,
  "key": "current_task_state",
  "session_scoped": true,
  "expires_at": 1705317000.0,
  "scope": "session",
  "stored_at": "2025-01-15T10:35:00Z"
}
```

**Performance:** < 10ms typical response time

### `get_memory`

Retrieve value from agent's private memory with automatic cleanup.

**Permissions Required:** `read`

**Parameters:**
- `key` (string, required): Memory key to retrieve
- `session_id` (string, optional): Session scope (null for global memory)

**Response Example:**
```json
{
  "success": true,
  "key": "current_task_state",
  "value": {
    "phase": "implementation",
    "progress": 0.6,
    "blockers": ["waiting for API review"]
  },
  "metadata": {
    "type": "task_tracking",
    "updated_by": "claude-main"
  },
  "created_at": 1705316000.0,
  "updated_at": "2025-01-15T10:35:00Z",
  "expires_at": 1705317000.0,
  "scope": "session"
}
```

### `list_memory`

List agent's memory entries with filtering options.

**Permissions Required:** `read`

**Parameters:**
- `session_id` (string, optional): Session scope ("all" for both global and session)
- `prefix` (string, optional): Key prefix filter
- `limit` (integer, optional): Maximum entries (1-200, default: 50)

**Response Example:**
```json
{
  "success": true,
  "entries": [
    {
      "key": "current_task_state",
      "scope": "session",
      "session_id": "session_a1b2c3d4e5f6g7h8",
      "created_at": 1705316000.0,
      "updated_at": "2025-01-15T10:35:00Z",
      "expires_at": 1705317000.0,
      "value_size": 245
    }
  ],
  "count": 1,
  "scope_filter": "session"
}
```

---

## Performance & Monitoring

### `get_performance_metrics`

Get comprehensive performance metrics for monitoring and optimization.

**Permissions Required:** `admin`

**Response Example:**
```json
{
  "success": true,
  "timestamp": "2025-01-15T10:35:00Z",
  "database_performance": {
    "connection_stats": {
      "total_connections": 127,
      "active_connections": 3,
      "peak_connections": 12,
      "total_queries": 1547,
      "avg_query_time": 15.7,
      "slow_queries": 2
    },
    "pool_stats": {
      "pool_size": 10,
      "available_connections": 7,
      "checked_out_connections": 3,
      "pool_utilization": 0.3
    },
    "cache_stats": {
      "cached_queries": 45,
      "cache_hit_ratio": 0.73
    }
  },
  "system_info": {
    "pool_initialized": true,
    "database_url": "chat_history.db",
    "min_pool_size": 5,
    "max_pool_size": 50,
    "connection_timeout": 30.0
  },
  "performance_targets": {
    "session_creation": "< 10ms",
    "message_insertion": "< 20ms",
    "message_retrieval_50": "< 30ms",
    "fuzzy_search_1000": "< 100ms",
    "concurrent_agents": "20+",
    "cache_hit_ratio": "> 70%"
  },
  "requesting_agent": "admin-agent"
}
```

**Performance Monitoring Features:**
- **Connection Pooling**: aiosqlitepool with 5-50 connections
- **Multi-Level Caching**: L1/L2 cache system with >70% hit ratio
- **Query Optimization**: <50ms average query time
- **Performance Targets**: All endpoints meet <100ms response targets

---

## MCP Resources

The server provides MCP resources for real-time updates and subscriptions.

### Session Resource: `session://{session_id}`

Real-time session data with message history and statistics.

**Access Control**: Read permission required, respects message visibility
**Update Frequency**: Real-time updates on session changes
**Subscription Support**: Full MCP subscription support

**Resource Content:**
```json
{
  "session": {
    "id": "session_a1b2c3d4e5f6g7h8",
    "purpose": "Planning new MCP integration",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:35:00Z",
    "created_by": "claude-main",
    "is_active": true,
    "metadata": {
      "priority": "high",
      "estimated_duration": "2h",
      "team": "backend"
    }
  },
  "messages": [
    {
      "id": 42,
      "sender": "claude-main",
      "sender_type": "claude",
      "content": "I've completed the database schema design.",
      "timestamp": "2025-01-15T10:35:00Z",
      "visibility": "public",
      "metadata": {
        "type": "status_update",
        "component": "database"
      }
    }
  ],
  "statistics": {
    "message_count": 15,
    "visible_message_count": 12,
    "unique_agents": 3,
    "last_activity": "2025-01-15T10:35:00Z",
    "session_duration_minutes": 120,
    "coordination_locks": 0
  },
  "resource_info": {
    "last_updated": "2025-01-15T10:35:15Z",
    "requesting_agent": "claude-main",
    "supports_subscriptions": true,
    "cache_ttl": 300
  }
}
```

**Resource Subscription Example:**
```python
import httpx

# Subscribe to session updates
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:23456/mcp/resource/subscribe",
        headers={"Authorization": f"Bearer {token}"},
        json={"uri": "session://session_a1b2c3d4e5f6g7h8"}
    )
```

### Agent Memory Resource: `agent://{agent_id}/memory`

Agent's private memory store organized by scope.

**Security**: Only accessible by the agent itself
**Scoping**: Global and session-scoped memory separation
**TTL Support**: Automatic cleanup of expired entries

**Resource Content:**
```json
{
  "agent_id": "claude-main",
  "memory": {
    "global": {
      "user_preferences": {
        "value": {"theme": "dark", "notifications": true, "language": "en"},
        "metadata": {"source": "user_config", "last_sync": "2025-01-15T10:00:00Z"},
        "created_at": 1705316000.0,
        "updated_at": "2025-01-15T10:30:00Z",
        "expires_at": null,
        "scope": "global"
      },
      "agent_capabilities": {
        "value": {
          "languages": ["python", "javascript", "sql"],
          "frameworks": ["fastapi", "react", "postgresql"],
          "specialties": ["backend", "databases", "apis"]
        },
        "metadata": {"type": "capabilities", "version": "1.2"},
        "created_at": 1705315000.0,
        "updated_at": "2025-01-15T10:15:00Z",
        "expires_at": null,
        "scope": "global"
      }
    },
    "sessions": {
      "session_a1b2c3d4e5f6g7h8": {
        "current_task": {
          "value": {
            "task": "API documentation",
            "status": "in_progress",
            "progress": 0.75,
            "estimated_completion": "2025-01-15T11:00:00Z"
          },
          "metadata": {"priority": "high", "assigned_by": "user"},
          "created_at": 1705316300.0,
          "updated_at": "2025-01-15T10:35:00Z",
          "expires_at": 1705319900.0,
          "scope": "session"
        },
        "collaboration_context": {
          "value": {
            "team_members": ["claude-main", "developer-agent", "tester-agent"],
            "current_phase": "implementation",
            "coordination_mode": "sequential"
          },
          "metadata": {"type": "coordination", "lock_holder": null},
          "created_at": 1705316400.0,
          "updated_at": "2025-01-15T10:34:00Z",
          "expires_at": 1705320000.0,
          "scope": "session"
        }
      }
    }
  },
  "statistics": {
    "global_keys": 2,
    "session_scopes": 1,
    "total_entries": 4,
    "memory_usage_kb": 12.5,
    "expired_entries_cleaned": 0
  },
  "resource_info": {
    "last_updated": "2025-01-15T10:35:15Z",
    "supports_subscriptions": true,
    "cleanup_interval": 300,
    "max_memory_mb": 100
  }
}
```

**Memory Resource Usage Example:**
```python
# Access agent memory resource
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:23456/mcp/resource/agent://claude-main/memory",
        headers={"Authorization": f"Bearer {token}"}
    )

    memory_data = response.json()
    global_prefs = memory_data["memory"]["global"]["user_preferences"]["value"]
    session_task = memory_data["memory"]["sessions"]["session_abc123"]["current_task"]["value"]
```

### Performance Metrics Resource: `performance://metrics` (Admin Only)

Real-time performance metrics for monitoring and optimization.

**Access Control**: Admin permission required
**Update Frequency**: Updated every 30 seconds
**Historical Data**: Last 24 hours of metrics

**Resource Content:**
```json
{
  "timestamp": "2025-01-15T10:35:00Z",
  "database_performance": {
    "connection_stats": {
      "total_connections": 127,
      "active_connections": 3,
      "peak_connections": 12,
      "total_queries": 1547,
      "avg_query_time": 15.7,
      "slow_queries": 2,
      "connection_errors": 0
    },
    "pool_stats": {
      "pool_size": 20,
      "available_connections": 17,
      "checked_out_connections": 3,
      "pool_utilization": 0.15,
      "wait_time_avg": 2.3
    },
    "cache_stats": {
      "l1_cache_size": 1247,
      "l2_cache_size": 4521,
      "cache_hit_ratio": 0.73,
      "cache_misses": 342,
      "evictions": 15
    }
  },
  "system_performance": {
    "memory_usage_mb": 245.7,
    "cpu_usage_percent": 12.4,
    "active_sessions": 8,
    "active_agents": 12,
    "messages_per_second": 3.2,
    "search_operations_per_minute": 45
  },
  "performance_trends": {
    "response_time_trend": "stable",
    "throughput_trend": "increasing",
    "error_rate_trend": "decreasing",
    "cache_efficiency_trend": "stable"
  },
  "resource_info": {
    "collection_interval": 30,
    "retention_hours": 24,
    "supports_subscriptions": true,
    "admin_only": true
  }
}
```

---

## Error Handling

The server uses LLM-optimized error responses for better AI agent decision-making.

### Error Response Format

All errors include actionable guidance and recovery suggestions:

```json
{
  "success": false,
  "error": "Session 'session_invalid123' not found",
  "code": "SESSION_NOT_FOUND",
  "severity": "error",
  "recoverable": true,
  "suggestions": [
    "Verify the session_id parameter is correct",
    "Use create_session to create a new session",
    "Check available sessions with list_sessions"
  ],
  "context": {
    "resource_type": "session",
    "resource_id": "session_invalid123",
    "available_alternatives": ["session_a1b2c3d4e5f6g7h8"]
  },
  "related_resources": ["create_session", "list_sessions"],
  "timestamp": "2025-01-15T10:35:00Z"
}
```

### Common Error Codes

- `INVALID_INPUT_FORMAT`: Parameter format validation failed
- `SESSION_NOT_FOUND`: Requested session does not exist
- `PERMISSION_DENIED`: Insufficient permissions for operation
- `INVALID_API_KEY`: Authentication failed
- `CONTENT_TOO_LARGE`: Message content exceeds size limits
- `MEMORY_LIMIT_EXCEEDED`: Agent memory storage limit reached
- `POOL_NOT_INITIALIZED`: Database connection pool not ready
- `SYSTEM_UNAVAILABLE`: Temporary system issue

### Error Severity Levels

- `warning`: Non-critical, operation may continue
- `error`: Operation failed, retry possible
- `critical`: System issue, immediate attention required

---

## Rate Limits & Performance

### Performance Targets (All Met in Production)

- **Session Creation**: < 10ms
- **Message Addition**: < 20ms
- **Message Retrieval (50 messages)**: < 30ms
- **Fuzzy Search (1000 messages)**: < 100ms
- **Memory Operations**: < 10ms
- **JWT Token Validation**: < 5ms

### Concurrency & Scale

- **Concurrent Agents**: 20+ simultaneous connections supported
- **Database Connections**: Connection pooling with 5-50 connections
- **Cache Performance**: >70% hit ratio with multi-level caching
- **Database Performance**: <50ms average query time

### Rate Limits

- **Authentication**: 60 requests/minute, 1000 requests/hour
- **Message Operations**: 1000 requests/minute per agent
- **Search Operations**: 100 requests/minute per agent
- **Memory Operations**: 500 requests/minute per agent

### Caching Strategy

- **Session Data**: 5-minute TTL for message lists
- **Search Results**: 10-minute TTL due to computational cost
- **Performance Metrics**: 1-minute TTL for admin monitoring
- **Agent Memory**: 15-minute TTL for frequently accessed data

---

## Integration Examples

### Basic Agent Integration

```python
import httpx
import json

# Authenticate and get token
auth_response = httpx.post("http://localhost:23456/mcp/tool/authenticate_agent", json={
    "agent_id": "my-agent",
    "agent_type": "claude",
    "api_key": "your-api-key"
})
token = auth_response.json()["token"]

# Create session
session_response = httpx.post("http://localhost:23456/mcp/tool/create_session",
    headers={"Authorization": f"Bearer {token}"},
    json={"purpose": "Multi-agent collaboration"}
)
session_id = session_response.json()["session_id"]

# Add message
message_response = httpx.post("http://localhost:23456/mcp/tool/add_message",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "session_id": session_id,
        "content": "Hello from my agent!",
        "visibility": "public"
    }
)
```

### Search and Memory Usage

```python
# Search context
search_response = httpx.post("http://localhost:23456/mcp/tool/search_context",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "session_id": session_id,
        "query": "collaboration",
        "fuzzy_threshold": 70.0
    }
)

# Store in memory
memory_response = httpx.post("http://localhost:23456/mcp/tool/set_memory",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "key": "agent_state",
        "value": {"status": "active", "session": session_id},
        "expires_in": 3600
    }
)
```

---

## Security Considerations

- **JWT Authentication**: All operations require valid JWT tokens
- **Role-Based Access**: Granular permissions (read, write, admin)
- **Input Validation**: Comprehensive input sanitization and validation
- **Audit Logging**: Complete audit trail for security events
- **Agent Isolation**: Private memory and session-based isolation
- **Rate Limiting**: Protection against abuse and DoS attacks

---

For more detailed integration guides and troubleshooting, see:
- [Integration Guide](./integration-guide.md)
- [Troubleshooting Guide](./troubleshooting.md)
- [Performance Optimization](./performance-guide.md)
