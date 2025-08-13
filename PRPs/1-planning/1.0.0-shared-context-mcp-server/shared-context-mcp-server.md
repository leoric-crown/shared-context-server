# Feature Planning: Shared Context MCP Server

**Created**: 2025-01-09
**Type**: Technical Implementation
**Complexity**: Moderate (Phase 1 MVP)
**Estimated Duration**: 2-3 days

## Executive Summary

Build a **Shared Context Server** that exposes multi-agent collaboration memory through the Model Context Protocol (MCP). This server will act as a centralized "blackboard" where AI agents can read and write shared context during complex PRP executions, solving the critical problem of context loss and lack of auditability when Claude Code orchestrates sub-agents.

## Problem Statement

### Current Pain Points

1. **Context Loss**: When Claude Code calls sub-agents during PRP execution, context is lost between agent boundaries
2. **No Audit Trail**: No visibility into what each agent did, decided, or discovered during execution
3. **Coordination Challenges**: Agents can't build on each other's work or understand prior decisions
4. **Debugging Difficulty**: Hard to trace issues when multiple agents are involved in implementation

### Solution Value

- **Persistent Shared Memory**: All agents read/write to the same context store
- **Complete Audit Trail**: Every agent action, decision, and output is logged
- **Real-time Collaboration**: Agents can see updates from other agents immediately
- **MCP-Native Integration**: Works seamlessly with any MCP-enabled LLM

## Requirements

### Functional Requirements

#### Core Capabilities

1. **Session Management**

   - Create isolated session contexts for each coding session / PRD execution
   - Track session lifecycle (active, completed, archived)
   - Support concurrent sessions without interference

2. **Tiered Memory Architecture**

   - **Public Messages**: Shared context visible to all agents (blackboard)
   - **Private Notes**: Agent-specific messages within sessions
   - **Agent Memory**: Key-value store for persistent agent state
   - Support visibility controls (public/private)
   - Optional expiration for temporary memory

3. **Message Storage**

   - Store agent messages with sender, content, timestamp
   - Support structured metadata (files modified, tests run, decisions made)
   - Maintain message ordering and causality chains
   - Visibility filtering (public vs private)

4. **MCP Integration**

   - Expose sessions as MCP resources (`session://{id}`)
   - Provide MCP tools for both public and private operations
   - Support resource subscriptions for real-time updates

5. **Multi-Agent Support**
   - Unique agent identification and authentication
   - Agent-specific permissions (read/write/admin)
   - Isolated private memory spaces per agent
   - Audit trail of all agent actions

### Non-Functional Requirements

1. **Performance**

   - < 100ms response time for read/write operations
   - Support 10+ concurrent agent connections
   - Handle message histories up to 1000 messages

2. **Reliability**

   - SQLite persistence with ACID guarantees
   - Graceful handling of connection failures
   - Automatic session cleanup after inactivity

3. **Security**
   - Bearer token authentication for agents
   - Input sanitization to prevent injection
   - Audit logging of all operations

## Technical Architecture

### Technology Stack

- **Framework**: FastAPI + FastMCP
- **Database**: SQLite (async with aiosqlite)
- **Protocol**: Model Context Protocol (MCP)
- **Validation**: Pydantic models
- **Testing**: pytest + pytest-asyncio

### System Components

```
┌─────────────────────────────────────────────┐
│            MCP Client (Agents)              │
└─────────────┬───────────────────────────────┘
              │ MCP Protocol
┌─────────────▼───────────────────────────────┐
│         Shared Context MCP Server           │
├──────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────────────┐    │
│  │ MCP Tools  │  │  MCP Resources     │    │
│  └─────┬──────┘  └────────┬───────────┘    │
│        │                   │                │
│  ┌─────▼───────────────────▼───────────┐   │
│  │     Session Manager                 │   │
│  └─────────────┬───────────────────────┘   │
│                │                            │
│  ┌─────────────▼───────────────────────┐   │
│  │     SQLite Database                 │   │
│  └─────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

### Database Schema

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    purpose TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_type TEXT DEFAULT 'agent_response',
    visibility TEXT DEFAULT 'public',  -- 'public' or 'private'
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT,  -- Optional: can be session-specific or global
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional expiration
    UNIQUE(agent_id, session_id, key),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_agent_memory ON agent_memory(agent_id, session_id);
```

### MCP Interface

#### Tools

**Public Context Tools:**

1. `create_session(purpose)` → session_id
2. `add_message(session_id, sender, content, metadata, visibility='public')` → message
3. `get_message(session_id, message_id)` → message
4. `get_context(session_id, limit, offset, include_private=False)` → messages[]
5. `search_context(session_id, query, fuzzy_threshold, limit)` → messages[]
6. `list_sessions(active_only)` → sessions[]

**Private Memory Tools:** 7. `set_memory(key, value, session_id=None, expires_in=None)` → success 8. `get_memory(key, session_id=None)` → value 9. `list_memory(session_id=None, pattern=None)` → keys[] 10. `delete_memory(key, session_id=None)` → success 11. `add_private_note(session_id, content, metadata)` → message

#### Resources

- Pattern: `session://{session_id}`
- Content: JSON array of session messages
- Subscriptions: Real-time updates on message additions

## Implementation Plan

### Phase 1: Core Infrastructure (Day 1)

1. **Project Setup**

   ```bash
   pip install fastapi fastmcp aiosqlite pydantic pytest pytest-asyncio
   ```

2. **Database Layer**

   - Database schema and models defined in `.claude/tech-guides/core-architecture.md`
   - Async operations using aiosqlitepool with connection pooling
   - Performance indexes and SQLite WAL configuration included

3. **Core Models**
   - Pydantic models and validation patterns in `.claude/tech-guides/data-validation.md`
   - Session, Message, and Agent Memory models with field validation
   - Security-focused input sanitization and response models

### Phase 2: MCP Server Implementation (Day 2)

1. **MCP Server Setup**

   - FastMCP server implementation patterns in `.claude/tech-guides/framework-integration.md`
   - Complete tool implementations with validation and error handling
   - Resource handlers with real-time subscription support
   - RapidFuzz search implementation for 5-10x performance improvement

**Implementation Patterns**: All MCP tool implementations, resource handlers, and FastMCP server setup patterns are documented in `.claude/tech-guides/framework-integration.md`. Key features include:

   - **RapidFuzz Search**: 5-10x performance improvement over difflib
   - **Connection Pooling**: aiosqlitepool for concurrent agent access
   - **Validation & Security**: Pydantic models with input sanitization
   - **Real-time Updates**: MCP resource subscriptions for live collaboration
   - **Memory Management**: Three-tier system (public, private, agent memory)

See tech guides for complete implementation details and best practices.

### Phase 3: Integration & Testing (Day 3)

1. **Authentication Middleware**

   - Bearer token validation
   - Agent identity extraction
   - Permission checking

2. **Testing Suite**

   - Comprehensive testing patterns in `.claude/tech-guides/testing.md`
   - FastMCP TestClient for 100x faster in-memory testing
   - Multi-agent behavioral testing scenarios
   - Performance benchmarking for concurrent usage

3. **Documentation**
   - API documentation
   - Agent integration guide
   - Configuration examples

## Success Criteria

### Functional Success

- [ ] Agents can create and join sessions
- [ ] Messages persist across agent boundaries
- [ ] Real-time updates via subscriptions work
- [ ] Complete audit trail is maintained

### Integration Success

- [ ] Works with Claude Code's agent framework
- [ ] Gemini agents can connect and participate
- [ ] MCP tools are discoverable by clients
- [ ] Resources are accessible via standard MCP

### Quality Gates

- [ ] All tests pass (>80% coverage)
- [ ] No security vulnerabilities
- [ ] Performance meets requirements
- [ ] Documentation is complete

## Risk Mitigation

### Technical Risks

1. **SQLite Concurrency**: Use WAL mode and connection pooling
2. **Message Ordering**: Use timestamps with microsecond precision
3. **Memory Growth**: Implement message pagination and cleanup

### Integration Risks

1. **MCP Compatibility**: Test with multiple MCP client implementations
2. **Agent Authentication**: Start simple, plan OAuth2 migration path
3. **Network Failures**: Implement retry logic and connection recovery

## Future Enhancements

### Phase 2 Features

- PostgreSQL for production scalability
- Redis caching for hot sessions
- Vector embeddings for semantic search
- Memory distillation and summarization

### Phase 3 Features

- Web UI for session visualization
- Metrics and monitoring dashboard
- Advanced permission models
- Workflow templates and skills library

## Agent Coordination Strategy

### Recommended Approach

Given our updated .claude/ setup with comprehensive tech guides, this should be implemented using **developer agent** with direct reference to our established patterns:

- **Core Architecture**: Database schema, MCP resource models, and system design patterns
- **Framework Integration**: FastMCP implementation with async/await, connection pooling, and testing
- **Testing Patterns**: Behavioral testing with multi-agent scenarios and performance validation
- **Data Validation**: Pydantic models, security, and error handling
- **Performance Optimization**: RapidFuzz search, caching, and monitoring

### Implementation Sequence

1. **Developer agent** implements core infrastructure following `.claude/tech-guides/framework-integration.md`
2. **Tester agent** validates using patterns from `.claude/tech-guides/testing.md`
3. Refine based on multi-agent integration testing
4. **Docs agent** updates documentation following established patterns

## References

### Documentation

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Project MVP Document](./SHARED_CONTEXT_SERVER_PATTERNS.md)
- [Advanced Research](./ADVANCED_RESEARCH_SHARED_CONTEXT_SERVER.md)
- [Market Research](./MARKET_RESEARCH.md)
- [Framework Integration Guide](./.claude/tech-guides/framework-integration.md)
- [Core Architecture Guide](./.claude/tech-guides/core-architecture.md)
- [Testing Guide](./.claude/tech-guides/testing.md)
- [Data Validation Guide](./.claude/tech-guides/data-validation.md)
- [Performance Optimization Guide](./.claude/tech-guides/performance-optimization.md)
- [Security & Authentication Guide](./.claude/tech-guides/security-authentication.md)
- [Error Handling Guide](./.claude/tech-guides/error-handling.md)

### Related PRPs

- Initial planning captured in `SHARED_CONTEXT_SERVER_PATTERNS.md`
- Architecture decisions in `ADVANCED_RESEARCH_SHARED_CONTEXT_SERVER.md`

## Next Steps

1. **Review & Approve**: Validate this planning document meets requirements
2. **Execute Implementation**: Use developer agent with this PRP
3. **Integration Testing**: Test with existing agent framework
4. **Team Rollout**: Update CLAUDE.md and train agents on usage
