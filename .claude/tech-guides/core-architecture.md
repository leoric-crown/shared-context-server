# Core Architecture Guide

## Overview

This guide defines the foundational architecture for the Shared Context MCP Server - a collaborative agent workspace enabling seamless agent handoffs and shared context through the Model Context Protocol. The system implements a session-based collaboration pattern with MCP-native integration for real-time agent coordination.

## Architecture Principles

### 1. Session-Based Collaboration System
Designed for agent handoffs and collaborative workflows:

- **Shared Sessions**: Isolated workspaces where agents build on each other's discoveries
- **Agent Handoffs**: Clean transitions with context preservation between specialized agents
- **Message Visibility**: Public/private/agent-only controls for granular information sharing

### 2. MCP-Native Design
- Sessions exposed as MCP resources with URI scheme `session://{id}`
- Context management through MCP tools
- Real-time updates via resource subscriptions
- Standard MCP authentication and security

### 3. Collaborative Agent Workflows
- **Real-time coordination**: <30ms message operations for smooth agent handoffs
- **Session isolation**: Clean boundaries between different collaborative tasks
- **Context search**: Sub-3ms fuzzy search for relevant prior discoveries
- **Agent coordination**: Identity management and handoff tracking

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client Layer                         │
├─────────────────────────────────────────────────────────────┤
│  Claude Main  │ Developer │ Tester │  Docs  │ Custom Agent │
├─────────────────────────────────────────────────────────────┤
│                    FastMCP Server                           │
├─────────────────────────────────────────────────────────────┤
│  Tools Layer        │        Resources Layer               │
│  - create_session   │        - session://{id}              │
│  - add_message      │        - agent://{id}/memory         │
│  - search_context   │        - Subscriptions               │
│  - set_memory       │                                      │
├─────────────────────────────────────────────────────────────┤
│                   Business Logic Layer                     │
├─────────────────────────────────────────────────────────────┤
│                   Data Persistence Layer                   │
│  SQLite Database with WAL Mode + Connection Pooling        │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### Core Tables

```sql
-- Sessions table: Manages shared context workspaces
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    purpose TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'utc')),
    updated_at TIMESTAMP DEFAULT (datetime('now', 'utc')),
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT NOT NULL,  -- Agent who created the session
    metadata JSON,
    CONSTRAINT valid_session_id CHECK (
        id REGEXP '^[a-zA-Z0-9-_]{8,64}$'
    )
);

-- Messages table: Stores all agent communications
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    visibility TEXT DEFAULT 'public' CHECK (visibility IN ('public', 'private', 'agent_only')),
    message_type TEXT DEFAULT 'agent_response',
    metadata JSON,
    timestamp TIMESTAMP DEFAULT (datetime('now', 'utc')),
    parent_message_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id)
);

-- Agent memory table: Private persistent storage
CREATE TABLE agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT,  -- NULL for global memory
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT (datetime('now', 'utc')),
    updated_at TIMESTAMP DEFAULT (datetime('now', 'utc')),
    expires_at TIMESTAMP,
    UNIQUE(agent_id, session_id, key),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Audit log table: Security and debugging
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT (datetime('now', 'utc')),
    event_type TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    resource TEXT,
    action TEXT,
    result TEXT,
    metadata JSON
);

-- Secure tokens table: Authentication token management (PRP-006)
CREATE TABLE secure_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id TEXT UNIQUE NOT NULL,
    encrypted_jwt BLOB NOT NULL,
    agent_id TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT secure_tokens_agent_id_not_empty CHECK (length(trim(agent_id)) > 0),
    CONSTRAINT secure_tokens_token_id_not_empty CHECK (length(trim(token_id)) > 0)
);

-- Schema versioning table
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

### Performance Indexes

```sql
-- Primary access patterns
CREATE INDEX idx_messages_session_time ON messages(session_id, timestamp);
CREATE INDEX idx_messages_sender ON messages(sender, timestamp);
CREATE INDEX idx_messages_visibility ON messages(visibility, session_id);

-- Agent memory lookups
CREATE INDEX idx_agent_memory_lookup ON agent_memory(agent_id, session_id, key);
CREATE INDEX idx_agent_memory_expiry ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;

-- Audit trail
CREATE INDEX idx_audit_agent ON audit_log(agent_id, timestamp);
CREATE INDEX idx_audit_session ON audit_log(session_id, timestamp);

-- Secure token lookups
CREATE INDEX idx_token_id ON secure_tokens(token_id);
CREATE INDEX idx_agent_expires ON secure_tokens(agent_id, expires_at);
CREATE INDEX idx_expires_cleanup ON secure_tokens(expires_at);
```

### SQLite Configuration

Critical settings for multi-agent concurrency:

```sql
PRAGMA foreign_keys = ON;            -- Critical: Enable foreign key constraints
PRAGMA journal_mode = WAL;           -- Write-Ahead Logging for concurrency
PRAGMA synchronous = NORMAL;         -- Balance performance and safety
PRAGMA cache_size = -8000;           -- 8MB cache per connection
PRAGMA temp_store = MEMORY;          -- Use memory for temp tables
PRAGMA mmap_size = 268435456;        -- 256MB memory mapping (production safe)
PRAGMA busy_timeout = 5000;          -- 5 second timeout for busy database
PRAGMA optimize;                     -- Enable query optimizer
```

## Memory System Design

### 1. Public Context (Blackboard)
- **Purpose**: Primary collaboration workspace
- **Visibility**: All agents can read and write
- **Storage**: `messages` table with `visibility='public'`
- **Access Pattern**: Most recent messages first
- **MCP Exposure**: Available via `session://{id}` resources

### 2. Private Notes (Agent Scratchpad)
- **Purpose**: Internal reasoning and draft responses
- **Visibility**: Only the creating agent
- **Storage**: `messages` table with `visibility='private'`
- **Use Cases**: Debugging, observation notes, draft content
- **Access Pattern**: Agent-filtered queries

### 3. Agent Memory (Persistent KV Store)
- **Purpose**: State persistence across calls
- **Visibility**: Only the owning agent
- **Storage**: `agent_memory` table
- **Scope**: Global or session-scoped
- **Features**: TTL expiration, metadata support

## MCP Resource Model

### Resource URI Schemes

1. **Session Resources**: `session://{session_id}`
   - Contains public messages in chronological order
   - Supports real-time subscriptions
   - JSON format with message array

2. **Agent Memory Resources**: `agent://{agent_id}/memory`
   - Private key-value store for agent
   - Organized by scope (global/session)
   - Only accessible by owning agent

### Resource Structure

```json
{
  "uri": "session://session_abc123",
  "name": "Feature Planning Session",
  "mimeType": "application/json",
  "content": {
    "session": {
      "id": "session_abc123",
      "purpose": "Plan authentication feature",
      "created_at": "2025-01-15T10:30:00+00:00",
      "created_by": "claude-main"
    },
    "messages": [
      {
        "id": 1,
        "sender": "claude-main",
        "content": "Starting authentication feature planning",
        "timestamp": "2025-01-15T10:30:00+00:00",
        "visibility": "public",
        "metadata": {}
      }
    ],
    "message_count": 1,
    "last_updated": "2025-01-15T10:30:00+00:00"
  }
}
```

## MCP Tool Definitions

### Core Tools

1. **create_session**
   ```python
   async def create_session(
       purpose: str = Field(description="Purpose of the session"),
       metadata: Optional[Dict[str, Any]] = Field(default=None)
   ) -> Dict[str, Any]
   ```

2. **add_message**
   ```python
   async def add_message(
       session_id: str = Field(description="Session ID"),
       content: str = Field(description="Message content"),
       visibility: str = Field(default="public", description="public, private, or agent_only"),
       metadata: Optional[Dict[str, Any]] = Field(default=None)
   ) -> Dict[str, Any]
   ```

3. **search_context**
   ```python
   async def search_context(
       session_id: str = Field(description="Session ID"),
       query: str = Field(description="Search query"),
       fuzzy_threshold: float = Field(default=60.0, description="Minimum similarity score"),
       limit: int = Field(default=10, description="Maximum results")
   ) -> Dict[str, Any]
   ```

4. **set_memory/get_memory**
   ```python
   async def set_memory(
       key: str = Field(description="Memory key"),
       value: Any = Field(description="Value to store"),
       session_id: Optional[str] = Field(default=None),
       expires_in: Optional[int] = Field(default=None)
   ) -> Dict[str, Any]
   ```

## Architecture Decision Records

### ADR-001: SQLite with WAL Mode
**Decision**: Use SQLite with WAL (Write-Ahead Logging) mode for data persistence.

**Rationale**:
- Enables concurrent reads while writing
- Simpler deployment than PostgreSQL
- ACID compliance with good performance
- File-based storage suitable for single-server deployment

**Consequences**:
- Limited to single-server deployment
- May need migration to PostgreSQL for high-scale scenarios
- Requires proper backup strategy for WAL files

### ADR-002: FastMCP Framework
**Decision**: Use FastMCP as the MCP server implementation framework.

**Rationale**:
- Most Pythonic MCP implementation
- Native async/await support
- Built-in Pydantic validation
- In-memory testing capabilities
- Minimal boilerplate code

**Consequences**:
- Dependency on relatively new framework
- Excellent development experience and performance
- Easy integration with existing FastAPI patterns

### ADR-003: Three-Tier Memory System
**Decision**: Implement public context, private notes, and agent memory as separate tiers.

**Rationale**:
- Addresses multi-agent privacy concerns
- Enables both collaboration and private reasoning
- Flexible scope management (global vs session)
- Clear separation of concerns

**Consequences**:
- More complex query patterns
- Requires careful permission management
- Enables sophisticated agent interaction patterns

### ADR-004: Session-Scoped Resources
**Decision**: Expose sessions as first-class MCP resources with URI scheme `session://{id}`.

**Rationale**:
- Natural fit for MCP resource model
- Enables real-time subscriptions
- Clear resource boundaries
- Standard MCP client compatibility

**Consequences**:
- Resource subscriptions increase server complexity
- Excellent real-time collaboration support
- Standard MCP tooling compatibility

## Database Connection Patterns

### DatabaseManager Usage

The system uses a singleton `DatabaseManager` for all database operations:

```python
from shared_context_server.database import get_db_connection, utc_now, utc_timestamp

# Standard connection pattern
async with get_db_connection() as conn:
    cursor = await conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    result = await cursor.fetchone()
```

### UTC Timestamp Management

Always use explicit UTC timestamps for multi-agent coordination:

```python
from datetime import datetime, timezone
from shared_context_server.database import utc_now, utc_timestamp, parse_utc_timestamp

# Creating timestamps
current_time = utc_now()  # Returns datetime.now(timezone.utc)
timestamp_str = utc_timestamp()  # Returns ISO string with +00:00

# Parsing timestamps from database
parsed_time = parse_utc_timestamp("2025-01-15T10:30:00+00:00")

# Database insertions with UTC timestamps
await conn.execute(
    """
    INSERT INTO messages (session_id, sender, content, timestamp)
    VALUES (?, ?, ?, ?)
    """,
    (session_id, sender, content, utc_timestamp())
)
```

### Connection Context Management

The `DatabaseManager` handles:
- WAL mode configuration for concurrency
- Foreign key constraint enforcement
- Connection pooling and lifecycle
- PRAGMA optimization settings
- Schema validation and recovery

```python
from shared_context_server.database import get_database_manager, initialize_database

# Application startup
await initialize_database()

# Health checks
db_manager = get_database_manager()
stats = db_manager.get_stats()
```

## Integration Patterns

### Agent Connection Flow

1. **Authentication**: Agent authenticates with Bearer token
2. **Discovery**: Agent discovers available tools and resources
3. **Session Management**: Agent creates or joins sessions
4. **Context Sharing**: Agent adds messages to public context
5. **Private Operations**: Agent uses private notes and memory
6. **Real-time Updates**: Agent subscribes to session changes

### Multi-Agent Collaboration

1. **Blackboard Pattern**: Agents read from and write to shared public context
2. **Event Notifications**: MCP subscriptions notify agents of changes
3. **Privacy Controls**: Agents can use private notes for internal reasoning
4. **State Persistence**: Agents maintain state via memory system
5. **Audit Trail**: All operations logged for debugging and security

## Performance Characteristics

### Target Performance
Target performance with optimizations (see Performance Optimization Guide for detailed metrics):
- Session creation: < 10ms (target)
- Message insertion: < 20ms (target)
- Message retrieval (50 messages): < 30ms (target)
- Fuzzy search (1000 messages): < 100ms (target with RapidFuzz)
- Concurrent agents: 20+ (target)

### Optimization Strategies
- Connection pooling with DatabaseManager singleton
- RapidFuzz for fuzzy search (5-10x faster than difflib)
- TTL caching for hot sessions
- Cursor-based pagination
- Async/await throughout

## Security Architecture

### Authentication
- JWT tokens with MCP audience validation
- Agent-specific credentials and permissions
- Token refresh mechanism

### Authorization
- Role-based access control (RBAC)
- Session-level permissions
- Visibility controls for messages

### Data Protection
- Input sanitization and validation
- SQL injection prevention
- XSS protection
- Audit logging

## Deployment Architecture

### Development
- Standalone MCP server with stdio transport
- SQLite file database
- Local testing with FastMCP TestClient

### Production
- HTTP transport for remote access
- Connection pooling and monitoring
- Backup strategy for SQLite files
- Rate limiting and security headers

## References

- Model Context Protocol Specification: https://modelcontextprotocol.io/specification
- FastMCP Documentation: https://github.com/jlowin/fastmcp
- SQLite WAL Mode: https://sqlite.org/wal.html
- Blackboard Pattern: https://en.wikipedia.org/wiki/Blackboard_(design_pattern)

## Related Guides

- Framework Integration Guide - FastMCP implementation patterns
- Security & Authentication Guide - Detailed security implementation
- Performance Optimization Guide - Speed improvements and monitoring
- Data Validation Guide - Pydantic models and validation
- Error Handling Guide - Comprehensive error management
