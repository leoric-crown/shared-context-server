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
uv run python -m shared_context_server.scripts.dev
```

## Development

### Available Commands
```bash
uv run python -m shared_context_server.scripts.dev    # Start development server
uv run python -m shared_context_server.scripts.dev --validate  # Validate environment
uv run ruff check .                                   # Lint code
uv run ruff format .                                  # Format code
uv run mypy .                                         # Type checking
uv run pytest                                         # Run tests
```

### Quality Gates
```bash
# Run all quality checks
uv run ruff check . && uv run mypy . && uv run pytest
```

## Architecture

- **FastMCP Server**: Model Context Protocol implementation
- **SQLite + WAL**: Concurrent agent access with performance optimization
- **Session Isolation**: Multi-agent collaboration with proper boundaries
- **UTC Timestamps**: Consistent time coordination

## Status

🎯 **Phase 0 Complete**: Foundation infrastructure ready
🚀 **Next**: Phase 1 - Core Infrastructure implementation

---

Built with modern Python tooling and MCP standards.
