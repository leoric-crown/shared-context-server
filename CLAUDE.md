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

## Environment Variables

Key configuration:
```bash
API_KEY=your-key                # Required for MCP authentication
JWT_SECRET_KEY=your-secret      # Required for JWT signing
JWT_ENCRYPTION_KEY=fernet-key   # Required for token encryption
DATABASE_URL=path/to/db         # Optional (default: shared_context.db)
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

### WebSocket Integration

WebSocket server runs alongside FastAPI for real-time updates:
- Notifications sent via `websocket_notify()` helper
- Dashboard at `http://localhost:23456/ui/`
- Auto-reconnect with exponential backoff
