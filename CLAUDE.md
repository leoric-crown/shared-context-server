# CLAUDE.md

Quick reference for shared-context-server development.

## Commands

```bash
# Setup
uv run shared-context-server setup # Sets up working .env file (does not overwrite pre-existing env files, instead creates .env.generated)
# Development
make dev          # Start server (port from .env file)
make validate     # Check environment

# Testing
make test         # Run tests with coverage (with coverage target from pyproject.toml)
make test-quick   # Run tests without coverage

# Version Management
make version-bump BUMP=patch    # 1.1.5 → 1.1.6
make version-bump BUMP=minor    # 1.1.5 → 1.2.0
make version-bump BUMP=major    # 1.1.5 → 2.0.0

# Quality
make lint         # Ruff auto-fix
make format       # Code formatting
make type         # MyPy check
make quality      # All quality checks

# Docker
make docker-dev   # Build container locally and launch server with hot reload
make docker-local # Force rebuild and launch container (no hot reload)
make docker       # Production deployment
```

## Test Commands

```bash
uv run pytest tests/unit/test_auth_jwt.py -v      # Single file
uv run pytest tests/security/ -v                  # Category
uv run pytest -k "test_jwt" -v                    # Pattern match
uv run pytest -m "not slow" -v                    # Skip slow tests
uv run pytest -n auto                             # Parallel execution (default)
```

## Environment Variables

```bash
API_KEY=your-key                # Required for MCP auth
JWT_SECRET_KEY=your-secret      # Required for JWT signing
JWT_ENCRYPTION_KEY=fernet-key   # Required for token encryption
DATABASE_URL=path/to/db         # Optional (default: chat_history.db)
```

## Architecture Quick Reference

**Core Files:**
- `server.py` - FastMCP server with multi-agent tools
- `database_sqlalchemy.py` - SQLAlchemy backend (SQLite/PostgreSQL/MySQL)
- `auth.py` - JWT auth with role-based access
- `websocket_server.py` - Real-time updates

**Message Visibility:**
- `public` - All agents see
- `private` - Only sender sees
- `agent_only` - Same agent type only
- `admin_only` - Admin JWT required

## Multi-Agent Patterns

**Shared Context Server Session Creation:**
- Make sure the first tool you call from shared-context-server is get_usage_guidance
- Create session ID + JWT tokens for agents
- Pass unique pairs of ID + JWT to each unique agent to enable collaboration
- Check session messages between handoffs

## Critical Gotchas

**Gemini CLI Compatibility:**
```python
# CORRECT - Gemini CLI requires explicit types
metadata: Any = Field(
    default=None,
    json_schema_extra={"type": "object", "additionalProperties": True}
)

# WRONG - Breaks Gemini CLI
metadata: dict[str, Any] | None = None
```

**Testing:**
- Use `uv run pytest -n auto` (-n auto is default) (NOT `--dist=loadscope`)
- ContextVar handles test isolation automatically
- No manual auth resets needed

**Performance Targets:**
- Message ops: <30ms
- Fuzzy search: 2-3ms
- Concurrent agents: 20+/session

## Commands Reference

**Python:** Use `uv run python` (not `python3`)
**Timestamps:** Use Unix format (`datetime.now(timezone.utc).timestamp()`)
**MCP Discovery:** `npx @modelcontextprotocol/inspector --cli`
For shared-context-server MCP examples, see `.claude/guides/mcp-toolkit-architecture.md

## Detailed Documentation

See `.claude/guides/` for comprehensive patterns:
- `shared-context-integration.md` - Multi-agent coordination
- `development-standards.md` - Code standards & file limits
- `testing-architecture-stability.md` - Test patterns
- `mcp-toolkit-architecture.md` - MCP integration patterns

WebUI debug logs: enable with `?debug=1`, `window.SCS_DEBUG=true`, or `localStorage.setItem('scs_debug','1')`.
