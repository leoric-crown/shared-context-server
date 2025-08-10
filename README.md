# Shared Context MCP Server

A centralized memory store enabling multiple AI agents (Claude, Gemini, etc.) to collaborate on complex tasks through shared conversational context.

## Quick Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. **Clone and setup**:
```bash
git clone <your-repo-url>
cd shared-context-server
```

2. **Install with uv**:
```bash
uv sync
```

3. **Setup environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run development server**:
```bash
# Start with hot reload
MCP_TRANSPORT=http HTTP_PORT=8000 uv run python -m shared_context_server.scripts.dev
```

5. **Connect Claude Code**:
```bash
# Install mcp-proxy and configure Claude Code
uv tool install mcp-proxy
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:8000/mcp/"]}'
claude mcp list  # Verify connection
```

## Development

### Quick Start
- 🚀 **30-second setup**: See [Development Quick Start](./docs/dev-quick-start.md)
- 📖 **Full guide**: See [Development Setup](./docs/development-setup.md)
- 🔥 **Hot Reload**: Automatic server restart on file changes
- 🔗 **MCP Integration**: Works with Claude Code, VS Code, and other MCP clients

### Available Commands
```bash
# Development server (with hot reload)
MCP_TRANSPORT=http uv run python -m shared_context_server.scripts.dev

# Validation and info
uv run python -m shared_context_server.scripts.dev --validate
uv run python -m shared_context_server.scripts.dev --info

# Code quality
uv run ruff check           # Linting
uv run ruff format          # Formatting
uv run mypy src/           # Type checking
uv run pytest tests/      # Run tests
```

### Quality Gates
```bash
# Run all quality checks
uv run ruff check . && uv run mypy . && uv run pytest
```

## Architecture

### Core Infrastructure (Phase 1)
- **FastMCP Server**: 4 operational MCP tools with stdio transport
- **Session Isolation**: UUID-based session boundaries with lifecycle management
- **Message Visibility**: Public/private/agent_only filtering with audit trails
- **Agent Authentication**: MCP context extraction with API key validation
- **Database Operations**: Async SQLite with optimized indexing patterns

## Status

🎯 **Phase 1 Complete**: Core Infrastructure ready
- ✅ FastMCP server with 4 core tools operational
- ✅ Session management with UUID generation
- ✅ Message storage with visibility controls
- ✅ Agent identity and authentication middleware
- ✅ Audit logging and security validation

🚀 **Next**: Phase 2 - Essential Features implementation

## API Tools

### Session Management
- `create_session` - Create isolated collaboration sessions
- `get_session` - Retrieve session info and message history

### Message System
- `add_message` - Add messages with visibility controls
- `get_messages` - Retrieve messages with agent-specific filtering

**Authentication**: Basic API key authentication
**Database**: SQLite with WAL mode, concurrent agent support
**Performance**: < 30ms response times for core operations

---

Built with modern Python tooling and MCP standards.
