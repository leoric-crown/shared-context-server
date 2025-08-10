# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The year is 2025.

## Repository Overview

This is the **Shared Context Server** project - a centralized memory store enabling multiple AI agents (Claude, Gemini, etc.) to collaborate on complex tasks through shared conversational context. The system implements a RESTful "Context as a Service" pattern following blackboard architecture principles.

## Current Status & Roadmap

**System Readiness**: 5% complete - Fresh repository with comprehensive planning documentation. Ready for MVP implementation phase.

### ✅ Completed Infrastructure
- **Planning Documentation**: Comprehensive MVP patterns and advanced research documentation
- **Claude Framework**: Multi-agent coordination system with research-backed customizations
- **Architecture Design**: RESTful API design with SQLite persistence and async patterns
- **Research Foundation**: FastAPI best practices, multi-agent patterns, and blackboard architecture analysis

### 🎯 Current Milestone: MVP Implementation
- **Phase 1**: Core API endpoints (POST /sessions, POST /sessions/{id}/messages, GET /sessions/{id})
- **Phase 2**: SQLite database schema and async operations with FastAPI + Pydantic validation
- **Phase 3**: Agent integration patterns and basic authentication for multi-agent access

### 📋 Future Milestones
- **Production Scale**: PostgreSQL/Redis integration, tiered memory architecture, memory distillation
- **Advanced Features**: Authentication/authorization (OAuth2), agent role-based access, procedural memory (skills library)

## Context-Enriched Decision Making Protocol

- **Executive Context Authority**: You will maintain decision-making authority based on comprehensive context across all agent interactions and research findings
- **Research Context Building**: Proactively gather and organize research context (Crawl4AI, Octocode, SequentialThinking, etc.) to inform intelligent coordination decisions
- **Cross-Agent Context Synthesis**: Integrate findings from agent status reports, research discoveries, and implementation progress to make informed coordination choices
- **Context-Informed Coordination**: Use enriched context to make intelligent agent selection, workflow routing, and complexity assessment decisions
- **Citation & Provenance Tracking**: All research includes source URLs, timestamps, and context provenance for transparency and decision justification
- **Dynamic Context Updates**: Continuously enrich context based on agent findings, user feedback, and implementation discoveries to improve decision quality
- **Intelligent Decision Making**: Use enriched context to make coordination decisions when possible, escalate to user when context is insufficient

## Environment & Setup

### Prerequisites & Key Dependencies
- **Python 3.10+** with **uv** (ultra-fast Python package manager) for dependency management
- **Core Libraries**:
  - **FastMCP** (MCP server framework for tool definitions and async handlers)
  - **aiosqlite** (async SQLite operations for non-blocking database access)
  - **RapidFuzz** (high-performance fuzzy string matching for search)
  - **Pydantic** (data validation and settings management using type hints)
  - **httpx** (async HTTP client for agent integration testing)

### Environment Variables
```bash
# Essential configuration for shared context server
DATABASE_URL="sqlite:///./chat_history.db"  # SQLite database path
API_KEY="your-secure-api-key"               # Authentication for agent access
LOG_LEVEL="INFO"                            # Logging level (DEBUG, INFO, WARNING, ERROR)
CORS_ORIGINS="*"                            # CORS origins for web clients
```

### Setup & Installation
```bash
# Install uv (ultra-fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies including development tools
uv sync --all-extras

# Run development server
uv run python -m shared_context_server.scripts.dev

# Run tests
uv run pytest tests/ -v

# Run quality checks
uv run ruff check
uv run mypy src/
uv run pre-commit run --all-files
```

### Critical Requirements
- **UTC Timestamps**: System uses UTC throughout for message timestamps and session coordination
- **File Permissions**: Write access to current directory for SQLite database file creation
- **Storage**: SQLite database stored in project root (`./chat_history.db`) with automatic schema initialization
- **Runtime Support**: Python 3.10+ with async/await support for FastMCP and aiosqlite operations

## Core Architecture

### Data Organization
- **Session-Based Structure**: Complete session isolation with unique session IDs eliminating cross-session interference
- **Database Schema**: Single `chat_history` table with session_id, sender, content, timestamp fields for efficient querying
- **Agent Integration**: Smart agent identification and message routing with automatic session management

### Component & Service Systems
- **Session Manager**: Full session lifecycle management with auto-cleanup and SQLite persistence for message history
- **Smart Coordination**: HTTP request/response with async patterns, FastAPI automatic validation and error handling
- **Multi-Agent Integration**: RESTful API endpoints supporting Claude, Gemini, and custom agents with bearer token authentication
- **Database Operations**: Async SQLite operations with aiosqlite for non-blocking I/O and concurrent agent access

### Data System & Types
- **Message Format**: JSON entries with `sender`, `content`, `timestamp` fields, supports structured agent responses
- **Flexible Structure**: session_id (required), sender (required), content (required), timestamp (auto-generated)
- **Message Categories**: human_input (user messages), agent_response (AI responses), system_status (coordination), tool_output (function results)

## Key API Endpoints

Core RESTful endpoints for agent integration:
- `POST /sessions` - Creates new session and returns session_id (required for all operations)
- `POST /sessions/{id}/messages` - Adds message to session with sender and content validation
- `GET /sessions/{id}` - Retrieves complete message history for session
- `GET /sessions/{id}/messages?limit=N` - Retrieves recent N messages (pagination support)
- `DELETE /sessions/{id}` - Cleanup session and associated messages (optional)
- `GET /health` - Health check endpoint for monitoring
- `GET /docs` - FastAPI automatic API documentation

## Development Standards & Guidelines

### Core Principles
- **Component-Centric Design**: All functionality built around unified interactive components with persistent state
- **Manual-First + Enhancement**: Core workflows work manually; automated assistance is optional and additive
- **Data Preservation**: Zero-loss data using SQLite persistence with async operations
- **Progressive Enhancement**: Build core functionality first, add advanced features incrementally
- **Context-Enriched Executive Authority**: Main Claude maintains decision-making authority using comprehensive context across agent tasks and research findings to make intelligent coordination decisions

### Quality Standards
- **File Size Limit**: Maximum 500 lines per code file, 1000 lines per test file
- **UTC Timestamps**: Always use `datetime.now(timezone.utc)` for system operations
- **Testing**: pytest unit tests required for all new code, behavioral tests for integration
- **📸 Screenshot Requirements**: Screenshot capture recommended for UI changes with before/after visual validation
- **Code Quality**: `ruff check` and `mypy` must pass before commits
- **Component Integration**: Always integrate with Session Manager for state persistence
- **Service Infrastructure**: Use existing FastMCP server and FastAPI patterns

### Implementation Standards
- **Follow PRP specifications exactly** - match detailed specifications in `PRPs/` directory
- **Leverage existing infrastructure** - Session Manager, FastMCP Server, SQLite Database
- **Agent Coordination**: Use intelligent coordination based on detected scope and complexity, with structured status reporting and escalation triggers for architecture issues, test failures, security concerns, file size violations, dependency conflicts, integration failures

**Comprehensive Standards**: `.claude/development-standards.md`, comprehensive test coverage with pytest

## Testing & Quality Assurance

📋 **Comprehensive Testing**: Multi-layered testing approach with unit, integration, behavioral, and performance tests.

### Testing Requirements
- **Unit Tests**: Individual component testing with pytest
- **Integration Tests**: Multi-component workflow testing
- **Behavioral Tests**: End-to-end agent interaction testing
- **Performance Tests**: RapidFuzz search and database performance

### Testing Commands
- `pytest` - Run all tests with default parallel execution (auto-configured)
- `pytest tests/unit/` - Run only unit tests
- `pytest tests/integration/` - Run only integration tests
- `pytest tests/behavioral/` - Run only behavioral/end-to-end tests
- `pytest -m "not slow"` - Skip slow tests
- `pytest -n 4` - Run with specific number of parallel workers
- `pytest --cov=src` - Run with coverage reporting
- `pytest -k "test_name"` - Run specific test by name pattern
- `pytest -x` - Stop on first failure
- `pytest --lf` - Run only last failed tests

### Quality Commands
- `ruff check` - Code linting and style checks
- `mypy src/` - Type checking
- `pre-commit run --all-files` - Run all quality checks

## Hot Reload Development Setup

### Quick Start (30 seconds)
```bash
# 1. Start hot reload server
MCP_TRANSPORT=http HTTP_PORT=8000 uv run python -m shared_context_server.scripts.dev

# 2. Configure Claude Code (in another terminal)
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:8000/mcp/"]}'

# 3. Verify connection
claude mcp list  # Should show: ✓ Connected

# 4. Edit any .py file → server restarts automatically
```

### Development Features
- **🔥 Hot Reload**: Automatic server restart on file changes (1-2 second restart)
- **📁 File Watching**: Monitors all Python files in `src/shared_context_server/` recursively
- **🔗 Connection Stability**: MCP clients maintain connection through server restarts
- **⚡ Fast Development**: Edit → Save → Test cycle with no manual restart needed
- **🛡️ Transport Bridge**: `mcp-proxy` bridges HTTP ↔ STDIO for client compatibility

### Documentation
- **Quick Start**: `docs/dev-quick-start.md` - 30-second setup guide
- **Full Guide**: `docs/development-setup.md` - Comprehensive development documentation
- **Troubleshooting**: Common issues and solutions included

## CLI Commands Available

### Development Commands
- **Run Development Server**: `uv run python -m shared_context_server.scripts.dev` - Start the MCP development server with hot reload
- **Validate Environment**: `uv run python -m shared_context_server.scripts.dev --validate` - Check development environment setup
- **Server Info**: `uv run python -m shared_context_server.scripts.dev --info` - Display server configuration and status
- **Install Dependencies**: `uv sync --all-extras` - Install all project dependencies including dev tools
- **Run Tests**: `uv run pytest` - Execute full test suite with parallel execution (auto-configured)

### Quality Assurance Commands
- **Lint Code**: `uv run ruff check` - Run linting checks on codebase
- **Format Code**: `uv run ruff format` - Auto-format code to standards
- **Type Check**: `uv run mypy src/` - Run type checking on source code
- **Pre-commit Hooks**: `uv run pre-commit run --all-files` - Run all quality checks
- **Test Coverage**: `uv run pytest tests/ --cov=src --cov-report=html` - Generate test coverage report

### Development Tools
- **Database Reset**: Environment variable `DEV_RESET_DATABASE_ON_START=true` - Reset database on server start
- **Debug Mode**: Environment variable `DEBUG=true` - Enable detailed logging
- Use `uv run python -m shared_context_server.scripts.dev --help` for detailed command information

---

## References

### Agent System
- `.claude/agents/developer.md` - Research-first implementation (MCP tools)
- `.claude/agents/tester.md` - Modern testing (behavioral, pytest)
- `.claude/agents/refactor.md` - Safety-first refactoring specialist
- `.claude/agents/docs.md` - User-focused documentation
- `.claude/agents/task-coordinator.md` - Multi-phase orchestration

### Tech Guides
- `.claude/tech-guides/core-architecture.md` - Foundational system design, database schema, and MCP resource models
- `.claude/tech-guides/framework-integration.md` - FastMCP server implementation patterns and tool definitions
- `.claude/tech-guides/testing.md` - Comprehensive testing patterns: behavioral, unit, integration, and multi-agent
- `.claude/tech-guides/security-authentication.md` - JWT authentication, RBAC, input sanitization, and audit logging
- `.claude/tech-guides/performance-optimization.md` - RapidFuzz search, connection pooling, caching, and monitoring
- `.claude/tech-guides/data-validation.md` - Pydantic models, validation rules, and type safety
- `.claude/tech-guides/error-handling.md` - Error hierarchy, circuit breakers, recovery patterns, and logging

### Standards
- `.claude/development-standards.md` - Code quality, testing, file limits
- `pyproject.toml` - Complete project configuration with ruff, mypy, and pytest settings

### Key Architecture Notes
- **⚠️ UTC Timestamps Critical**: Always use `datetime.now(timezone.utc)` for system coordination
- **FastMCP Integration**: FastMCP server pattern with tool definitions and async handlers
- **Progressive Enhancement**: Core functionality first, advanced features incrementally

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
