# Shared Context MCP Server
[![CI](https://github.com/leoric-crown/shared-context-server/workflows/CI/badge.svg)](https://github.com/leoric-crown/shared-context-server/actions)
[![codecov](https://codecov.io/gh/leoric-crown/shared-context-server/graph/badge.svg?token=07ZITBOAZ7)](https://codecov.io/gh/leoric-crown/shared-context-server)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A centralized memory store enabling multiple AI agents (Claude, Gemini, etc.) to collaborate on complex tasks through shared conversational context.

## Quick Setup

Choose your preferred setup method:

### 🐳 Docker (Recommended - Multi-Client Ready)

```bash
# Generate secure keys and start server
echo "API_KEY=$(openssl rand -base64 32)" > .env
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
chmod 600 .env
docker compose up -d

# Configure any MCP client
docker exec shared-context-server shared-context-server client-config claude
```

### 🔥 Development Mode (Hot Reload)

```bash
# Install dependencies
uv sync

# Start development server with hot reload
uv run python -m shared_context_server.scripts.dev

# Connect Claude Code
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]}'
```

### ⚡ Direct Run (Production)

```bash
# Install dependencies
uv sync

# Setup secure environment
echo "API_KEY=$(openssl rand -base64 32)" > .env
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
chmod 600 .env

# Run server
uv run shared-context-server --transport http --port 23456

# Connect Claude Code
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]}'
```

**Prerequisites**: Python 3.11+ and [uv](https://docs.astral.sh/uv/) package manager

See [DOCKER.md](./DOCKER.md) for complete Docker setup and troubleshooting.

## Development

### Quick Start
- 🚀 **30-second setup**: See [Development Quick Start](./docs/dev-quick-start.md)
- 📖 **Full guide**: See [Development Setup](./docs/development-setup.md)
- 🔥 **Hot Reload**: Automatic server restart on file changes
- 🔗 **MCP Integration**: Works with Claude Code, VS Code, and other MCP clients

### Available Commands
```bash
# Use Makefile for common tasks (recommended)
make help                 # Show all available commands
make dev                  # Start development server with hot reload
make test                 # Run tests with coverage
make quality              # Run all quality checks
make clean                # Clean caches and temp files

# Or run tools directly
uv run python -m shared_context_server.scripts.dev  # Dev server
uv run ruff check         # Linting
uv run ruff format        # Formatting
uv run mypy src/          # Type checking
uv run pytest tests/      # Run tests
```

### Quality Gates
```bash
# Use Makefile (recommended)
make quality              # Run all quality checks (lint + type + security)

# Or run manually
uv run ruff check . && uv run mypy . && uv run pytest
```

## Architecture

### Multi-Agent Infrastructure
- **FastMCP Server**: 15+ operational MCP tools with stdio transport
- **Session Isolation**: UUID-based session boundaries with lifecycle management
- **Message Visibility**: Public/private/agent_only/admin_only filtering with audit trails
- **JWT Authentication**: Role-based access control with secure token validation
- **Agent Coordination**: Session locking, presence tracking, coordination channels
- **Database Operations**: Async SQLite with optimized indexing and RapidFuzz search

## Status

🎉 **Phase 4 Complete**: Production Ready
- ✅ **Performance Optimization**: Connection pooling (5-50 connections), multi-level caching (>70% hit ratio)
- ✅ **Comprehensive Testing**: 666 tests, 88.30% coverage across all modules
- ✅ **LLM-Optimized Error Framework**: Actionable error messages with recovery suggestions
- ✅ **Complete API Documentation**: 12+ MCP tools fully documented with examples
- ✅ **Integration Guides**: AutoGen, CrewAI, LangChain with working examples
- ✅ **Troubleshooting Guide**: Common issues, diagnostics, and recovery procedures
- ✅ **Production Deployment**: Docker, Kubernetes, monitoring, and scaling guides
- ✅ **Security & Authentication**: JWT tokens, role-based permissions, audit logging
- ✅ **All Performance Targets Met**: <10ms session creation, <20ms message ops, <30ms queries

🚀 **Status**: **PRODUCTION READY** - Comprehensive documentation, tested integrations, optimized performance

## API Tools

### Authentication & Security
- `authenticate_agent` - JWT token generation with role-based permissions
- `get_audit_log` - Query comprehensive audit trail (admin only)

### Session Management
- `create_session` - Create isolated collaboration sessions
- `get_session` - Retrieve session info and message history
- `coordinate_session_work` - Lock/unlock sessions for coordinated work

### Message System
- `add_message` - Add messages with visibility controls (including admin_only)
- `get_messages` - Retrieve messages with agent-specific filtering
- `get_messages_advanced` - Advanced retrieval with admin visibility override
- `set_message_visibility` - Modify message visibility (owner/admin only)
- `search_context` - RapidFuzz-powered fuzzy search (2-3ms performance)
- `search_by_sender` - Find messages by specific sender
- `search_by_timerange` - Query messages within time window

### Agent Memory
- `set_memory` - Store values with TTL and scope management
- `get_memory` - Retrieve memory with automatic cleanup
- `list_memory` - Browse memory with filtering options

### Agent Coordination
- `register_agent_presence` - Track agent status and availability
- `coordinate_session_work` - Session locking for coordinated work
- `send_coordination_message` - Direct agent-to-agent messaging

### MCP Resources
- Session resources with real-time updates
- Agent memory resources with subscriptions
- Performance metrics resources (admin only)

## Authentication

### JWT Token Usage
```bash
# Authenticate and get JWT token
TOKEN=$(curl -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "my-agent", "agent_type": "claude", "api_key": "your-api-key"}' \
  | jq -r '.token')

# Use token in MCP requests
curl http://localhost:8000/mcp/tool/add_message \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"session_id": "session_abc123", "content": "Hello", "visibility": "admin_only"}'
```

### Permission Levels
- **read**: View public messages and session info
- **write**: Create sessions and add messages
- **admin**: Access admin_only messages, view audit logs, modify visibility

**Database**: SQLite with WAL mode, 20+ concurrent agent support
**Performance**: < 30ms API responses, 2-3ms RapidFuzz search
**Security**: JWT authentication, comprehensive audit logging, input validation

---

## Documentation

📖 **Complete Production Documentation**

- **[API Reference](./docs/api-reference.md)** - Complete reference for all 12+ MCP tools with request/response examples
- **[Integration Guide](./docs/integration-guide.md)** - AutoGen, CrewAI, LangChain integrations with working examples
- **[Troubleshooting Guide](./docs/troubleshooting.md)** - Common issues, diagnostics, and recovery procedures
- **[Development Setup](./docs/development-setup.md)** - Comprehensive development environment setup
- **[Quick Start](./docs/dev-quick-start.md)** - 30-second setup guide for development

### Framework Integration Examples

- **AutoGen**: Multi-agent conversations with shared context memory
- **CrewAI**: Role-based agent crews with coordination tools
- **LangChain**: Multi-agent workflows with persistent memory
- **Custom Agents**: Direct API integration with Python SDK patterns

### Production Features

- **Performance**: Connection pooling, multi-level caching, <100ms response times
- **Security**: JWT authentication, role-based permissions, audit logging
- **Scalability**: 20+ concurrent agents, PostgreSQL ready, Docker/K8s deployment
- **Monitoring**: Performance metrics, health checks, comprehensive logging
- **Recovery**: Database backup/restore, crash recovery, system reset procedures

---

Built with modern Python tooling and MCP standards.
