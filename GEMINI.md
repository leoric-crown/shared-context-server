# GEMINI.md - Gemini CLI Context

Instructions for Gemini CLI when working with the Shared Context Server project.

## Project Context

**Shared Context Server**: Production-ready centralized memory store enabling multiple AI agents (Claude, Gemini, etc.) to collaborate through shared conversational context.

**Status**: Phase 4 Complete - Production Ready
- 15+ MCP tools operational
- 88%+ test coverage (666 tests)
- Docker deployment ready
- Comprehensive documentation

## Gemini-Specific Setup

### Quick Setup for Gemini
```bash
# Install dependencies with uv (recommended Python package manager)
uv sync --dev

# Start development server
uv run python -m shared_context_server.scripts.dev

# Run tests
uv run pytest tests/ -v

# Quality checks
uv run ruff check && uv run mypy src/
```

### Key Differences from CLAUDE.md
- **Package Manager**: Use `uv` instead of other package managers for consistency
- **Port**: Default development port is 23456
- **Commands**: Use `make help` to see all available commands

## Essential Commands

```bash
# See all available commands
make help

# Development
make dev      # Start development server with hot reload
make test     # Run tests with coverage
make quality  # Run all quality checks
make clean    # Clean caches and temp files
```

## Technology Stack

- **Python 3.11+** with **uv** package manager
- **FastMCP** server with MCP tools
- **SQLite** with aiosqlite (async operations)
- **Pydantic** for data validation
- **JWT authentication** with role-based permissions

## Core Files

- **CLAUDE.md** - Complete project instructions and architecture
- **docs/development.md** - Development setup and workflows
- **docs/quick-reference.md** - Commands and environment variables
- **pyproject.toml** - Dependencies and tool configuration

## Development Standards

- **UTC timestamps** for all operations: `datetime.now(timezone.utc)`
- **File limits**: 500 lines code, 1000 lines tests
- **Testing required**: Unit and behavioral tests with pytest
- **Quality gates**: `make quality` must pass before commits
- **FastMCP patterns**: Use existing server and tool patterns
