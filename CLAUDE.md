# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Commands

### Development
```bash
make dev          # Start development server with hot reload (port 23456)
make validate     # Validate development environment
```

### Testing
```bash
make test         # Run tests with coverage (target: 84%+)
make test-quick   # Run tests without coverage (faster)
make test-backend # Test both database backends (aiosqlite & SQLAlchemy)
make test-all     # Run comprehensive test matrix
```

### Code Quality
```bash
make lint         # Run ruff linting with auto-fix
make format       # Format code with ruff
make type         # Type checking with mypy
make quality      # Run all quality checks (format, lint, type, pip-audit)
```

### Docker
```bash
make docker       # Full Docker lifecycle: stop → build → up → logs
```

## Architecture Overview

### Core Components

**src/shared_context_server/**
- `server.py` - FastMCP server with 15+ tools for multi-agent collaboration
- `database.py` & `database_sqlalchemy.py` - Dual backend system (aiosqlite/SQLAlchemy)
- `auth.py` - JWT authentication, role-based access control, audit logging
- `models.py` - Pydantic models for validation and serialization
- `tools.py` - MCP tools registry and metadata
- `websocket_server.py` - WebSocket support for real-time updates
- `scripts/dev.py` - Development server with hot reload

### Database Backends

The system supports two interchangeable backends:
- **aiosqlite** (default): Direct async SQLite, optimized for development
- **SQLAlchemy**: Future-ready for PostgreSQL/MySQL migration

Switch backends via environment variable:
```bash
USE_SQLALCHEMY=true make test  # Test with SQLAlchemy
USE_SQLALCHEMY=false make test # Test with aiosqlite (default)
```

### MCP Tools Architecture

Tools are organized by category:
- **Session Management**: create_session, get_session, add_message, get_messages
- **Search**: search_context (RapidFuzz), search_by_sender, search_by_timerange
- **Agent Memory**: set_memory, get_memory, list_memory (with TTL support)
- **Admin**: get_performance_metrics, get_usage_guidance

### Authentication Flow

1. MCP client provides API_KEY header
2. Server validates and generates JWT token via authenticate_agent tool
3. JWT contains agent_id, type, permissions (read/write/admin)
4. Tools check JWT for authorization based on visibility rules

### Message Visibility System

Four-tier visibility control:
- `public`: All agents can see
- `private`: Only sender can see
- `agent_only`: Only agents of same type
- `admin_only`: Requires admin JWT

## Testing Strategy

### Test Organization
- `tests/unit/` - Component isolation tests
- `tests/integration/` - Multi-component workflow tests
- `tests/behavioral/` - End-to-end user scenarios
- `tests/performance/` - Performance benchmarks
- `tests/security/` - Auth and isolation validation

### Running Specific Tests
```bash
pytest tests/unit/test_auth_jwt.py -v      # Single file
pytest tests/security/ -v                   # Category
pytest -k "test_jwt" -v                     # Pattern match
pytest -m "not slow" -v                     # Exclude slow tests
```

### Database Testing
Tests automatically use in-memory SQLite with WAL mode for isolation. Backend switching is tested via `test_simplified_backend_switching.py`.

### Authentication Architecture

**CURRENT**: Authentication uses ContextVar for perfect thread safety and automatic test isolation.

#### ContextVar Implementation
The `SecureTokenManager` uses Python's ContextVar system for thread-local token management:
- **Thread Safety**: Perfect isolation between concurrent requests without locks
- **Test Isolation**: Automatic cleanup between tests, no manual resets needed
- **Performance**: Zero overhead context switching
- **Simplicity**: No complex singleton management patterns required

#### Core Architecture
```python
from shared_context_server.auth_context import get_secure_token_manager

# Get thread-local token manager
manager = get_secure_token_manager()

# Each thread/context gets its own manager instance automatically
# No manual cleanup or reset required
```

#### Test Patterns (Simplified)

**1. Authentication Test Setup** (Current pattern):
```python
async def test_authentication_functionality(self, test_db_manager):
    # No reset needed - ContextVar handles isolation automatically

    # Set required environment variables
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-jwt-signing-123456"
    os.environ["JWT_ENCRYPTION_KEY"] = "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="

    # ... test logic
```

**2. Integration Test Pattern**:
```python
async def test_integration_with_auth(self, server_with_db, test_db_manager):
    with patch.dict(os.environ, {
        "API_KEY": "test-key",
        "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
        "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
    }, clear=False):
        # ... test logic (automatic isolation)
```

#### Migration Complete
- ✅ **Legacy singleton removed**: No more global state management
- ✅ **86 reset calls eliminated**: From 7 test files across the codebase
- ✅ **Thread safety improved**: ContextVar provides perfect isolation
- ✅ **Test complexity reduced**: No manual state management required
- ✅ **Performance maintained**: Zero overhead context switching

#### Backward Compatibility
Legacy functions remain available but are no-ops:
```python
# These functions exist for backward compatibility but do nothing
reset_secure_token_manager()  # No-op
set_test_mode(enabled)        # No-op
```

The `get_secure_token_manager()` function in `auth_secure.py` redirects to the ContextVar implementation.

## Environment Variables

Key configuration:
```bash
API_KEY=your-key                # Required for MCP authentication
JWT_SECRET_KEY=your-secret      # Required for JWT signing
JWT_ENCRYPTION_KEY=fernet-key   # Required for token encryption
DATABASE_URL=path/to/db         # Optional (default: chat_history.db)
USE_SQLALCHEMY=true/false       # Backend selection (default: false)
```

## Performance Targets

- Message operations: <30ms
- Fuzzy search: 2-3ms (RapidFuzz optimization)
- Concurrent agents: 20+ per session
- Cache hit ratio: >70%

## Common Development Patterns

### Adding a New MCP Tool

1. Define tool in `server.py` with FastMCP decorator
2. Add metadata to `tools.py` registry
3. Implement auth checks using `validate_agent_context_or_error`
4. Write unit test in `tests/unit/`
5. Add integration test in `tests/integration/`

### Database Schema Changes

1. Update schema in `database_*.sql` files
2. Modify both backends (`database.py` and `database_sqlalchemy.py`)
3. Run migration via `initialize_database(reset=True)` in dev
4. Test with `make test-backend`

### Gemini CLI MCP Schema Compatibility

**CRITICAL**: This is a recurring issue that has broken Gemini CLI compatibility 3 times.

**Problem**: Gemini CLI fails with "missing types in parameter schema" for metadata parameters.

**Root Cause**: Gemini CLI requires explicit JSON schema types for all parameters, cannot handle Union types.

**CORRECT PATTERN** for optional object parameters:
```python
metadata: Any = Field(
    default=None,
    description="Optional metadata (JSON object or null)",
    examples=[{"key": "value"}, None],
    json_schema_extra={"type": "object", "additionalProperties": True},
)
```

**Requirements**:
- Use `Any` type annotation (NOT `dict[str, Any] | None`)
- Add explicit `json_schema_extra={"type": "object", "additionalProperties": True}`
- Maintain `default=None` for optional behavior

**Files affected**: `session_tools.py`, `memory_tools.py` (any tool with metadata parameters)

### WebSocket Integration

WebSocket server runs alongside FastAPI for real-time updates:
- Notifications sent via `websocket_notify()` helper
- Dashboard at `http://localhost:23456/ui/`
- Auto-reconnect with exponential backoff

## Framework Guides

The `.claude/guides/` directory contains specialized documentation for multi-agent development patterns:

### Shared Context Integration
**File**: `.claude/guides/shared-context-integration.md`

Comprehensive patterns for multi-agent collaboration through the shared context server. Covers session-based coordination, agent handoff protocols, memory persistence patterns, and performance optimization strategies.

### MCP Toolkit Architecture
**File**: `.claude/guides/mcp-toolkit-architecture.md`

Production-ready MCP tool integration patterns based on the shared context server implementation. Includes dual-layer memory strategy, research tools coordination, and checkpoint management for framework commands.

### Development Standards
**File**: `.claude/guides/development-standards.md`

Critical development rules including file size limits (500 lines code, 1000 lines tests), testing requirements, browser automation standards, agent transparency protocols, and escalation triggers.

### Browser Automation
**File**: `.claude/guides/browser-automation.md`

Playwright MCP integration for behavioral testing, visual regression prevention, and research-first web development. Covers user story validation, responsive testing, and cross-device compatibility patterns.

### Testing Architecture & Stability
**File**: `.claude/guides/testing-architecture-stability.md`

Technical patterns for reliable test suites and dependency management. Covers dependency injection (preferred pattern), Enhanced Singleton Pattern (legacy), test organization, anti-patterns to avoid, and automated validation.


## Dual-Layer Memory System

When working with agents YOU MUST USE the sophisticated dual-layer memory architecture provided by shared-context-server and pieces MCP servers, combining immediate coordination with long-term intelligence preservation:

You MUST ALWAYS give agents a session id where they can participate AND a valid and non-expired JWT token with appropriate permissions

You SHOULD ALWAYS try to launch agents in parallel when the task allows for it, providing them a common session and valid JWT tokens and instructing them to collaborate through the session.

### Layer 1: Shared Context Server (Immediate Coordination)

**Purpose**: Real-time multi-agent collaboration and session-based memory
**Performance**: \<30ms message operations, 2-3ms fuzzy search
**Scope**: Current development session and task coordination

When starting a collaboration session with agents, YOU MUST create a new session using the session-context-server, and provide the newly created session ID as well as create JWT tokens (using the authenticate tool) for agents to write to that session.

In between agent calls and hand-offs, you can check session messages to get a better sense of what was done.

#### Core Capabilities
- **Session Management**: Create dedicated sessions for feature development tasks
- **Agent Handoffs**: Coordinate between different agent types with context preservation
- **Search & Discovery**: RapidFuzz-powered context search across session history
- **Memory Persistence**: Session-scoped memory with TTL support for immediate coordination
- **Visibility Controls**: 4-tier visibility system (public/private/agent_only/admin_only)

### Layer 2: Long-Term Project Knowledge

**Purpose**: Cross-project pattern recognition and breakthrough preservation
**Scope**: Historical context, architectural decisions, and learned patterns

#### Knowledge Preservation Strategy
**Note**: Pieces MCP server integration recommended for long-term memory. Current setup focuses on shared context server for immediate coordination.

#### Memory Checkpoints
Every major command should implement 3 checkpoints:
- **START**: Load relevant context from previous work
- **MID**: Store progress and coordination decisions
- **END**: Preserve knowledge and patterns for future reference

## Multi-Agent Authentication

### Authentication Gateway Pattern

Main Claude agent serves as the authentication gateway for the multi-agent framework:

**Authentication Flow:**
1. **Main Claude Only**: Uses `authenticate_agent` tool to obtain tokens
2. **Token Provisioning**: Passes tokens to subagents with appropriate `agent_type` and permissions
3. **Token Refresh**: Subagents can refresh their own tokens using `refresh_token` tool

**Agent Types & Permissions:**
- `claude`: Standard agent (read/write)
- `admin`: Framework coordination (read/write/admin/debug)
- `generic`: Read-only access
- `custom`: Configure via `PERMISSIONS_CONFIG_FILE`

**Usage Pattern:**
```python
# Main Claude provisions tokens
admin_token = await authenticate_agent(agent_id="coord_agent", agent_type="admin")
claude_token = await authenticate_agent(agent_id="dev_agent", agent_type="claude")

# Pass tokens to subagents for their operations
# Subagents use: refresh_token(current_token) when needed
```

**Key Requirement**: `agent_type="admin"` required for admin-level permissions.

- use uv run python instead of python3
- **CRITICAL**: All timestamps must use Unix format (`datetime.now(timezone.utc).timestamp()`) for consistent timezone display
