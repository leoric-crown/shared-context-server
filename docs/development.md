# Development Setup

Complete development environment setup and workflows for the Shared Context MCP Server.

## Quick Start (30 seconds)

```bash
# 1. Start hot reload server
make dev
# or: uv run python -m shared_context_server.scripts.dev

# 2. Configure Claude Code (in another terminal)
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]}'

# 3. Verify connection
claude mcp list
# Should show: shared-context-server: ... - ✓ Connected

# 4. Test tools in Claude Code session
# @shared-context-server create_session purpose="Test"
```

## What You Get

- 🔥 **Hot Reload**: Edit any `.py` file → server restarts automatically in 1-2 seconds
- 🔗 **MCP Integration**: Tools available in Claude Code immediately
- 🛡️ **Stable**: Client connection persists through restarts
- 📝 **Logging**: All activity logged with automatic rotation (10MB max, 5 backups)

## Architecture

### Components

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │  MCP Proxy  │    │   Server    │
│ (Claude/VS) │◄──►│ (mcp-proxy) │◄──►│ (FastMCP)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
   STDIO/MCP        HTTP ↔ STDIO        Streamable HTTP
```

### How It Works

1. **File Watcher**: `watchdog` monitors `src/shared_context_server/` recursively
2. **Debouncing**: 1-second debounce prevents excessive restarts
3. **Process Management**: Old server terminated, new server spawned
4. **Connection Bridging**: `mcp-proxy` maintains client connection during restart
5. **Transport Translation**: Converts between Streamable HTTP ↔ STDIO

## File Structure

```
src/shared_context_server/
├── server.py          # Main server (edit this)
├── tools.py           # MCP tools (edit this)
├── database.py        # DB operations
├── config.py          # Configuration
└── scripts/
    └── dev.py         # Hot reload server
```

## MCP Client Setup

### Claude Code (Recommended)

```bash
# Install mcp-proxy (required for HTTP transport bridge)
uv tool install mcp-proxy

# Add server configuration
claude mcp add-json shared-context-server '{
  "command": "mcp-proxy",
  "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]
}'

# Verify connection
claude mcp list
# Should show: shared-context-server: ... - ✓ Connected

# Test tools
claude mcp tools shared-context-server
```

**Usage Example:**
```bash
# In Claude Code session
@shared-context-server create_session purpose="Development testing"
@shared-context-server add_message session_id="..." content="Test message"
```

### VS Code with MCP Extension

1. **Install MCP Extension**: Search for "MCP" in VS Code extensions
2. **Configure Server**: Add to VS Code settings.json:

```json
{
  "mcp.servers": {
    "shared-context-server": {
      "command": "mcp-proxy",
      "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]
    }
  }
}
```

3. **Restart VS Code**: Reload window to pick up configuration
4. **Verify Connection**: Check MCP status in VS Code status bar

## Configuration

### Environment Variables

```bash
# Required
MCP_TRANSPORT=http              # Use HTTP transport
HTTP_PORT=23456                 # Server port (default: 23456)

# Optional
HTTP_HOST=localhost             # Server host (default: localhost)
MCP_SERVER_NAME=custom-name     # Server name (default: shared-context-server)
DATABASE_PATH=./dev.db          # Database path
API_KEY=dev-key-123            # API key for development
LOG_LEVEL=DEBUG                 # Logging level
```

### Development Server Options

```bash
# Start with custom configuration
uv run python -m shared_context_server.scripts.dev --help

# Validate environment
uv run python -m shared_context_server.scripts.dev --validate

# Show server info
uv run python -m shared_context_server.scripts.dev --info

# Use custom config file
uv run python -m shared_context_server.scripts.dev --config-file .env.dev
```

## Development Workflow

### Daily Development

```bash
# 1. Validate environment (first time setup)
make validate                   # or: uv run python -m shared_context_server.scripts.dev --validate

# 2. Start development environment
make dev                        # or: uv run python -m shared_context_server.scripts.dev

# 3. Make your changes
# Edit files in src/shared_context_server/

# 4. Watch automatic restart
# Server restarts on file save (1-2 seconds)

# 5. Test in Claude Code
# @shared-context-server create_session purpose="Testing changes"

# 6. Run quality checks
make quality                    # or: uv run ruff check && uv run mypy src/ && uv run pytest
```

### Key Commands

| Command | Purpose |
|---------|---------|
| `make dev` | Start development server with hot reload |
| `make test` | Run full test suite with coverage |
| `make quality` | Run all quality checks (lint + type + security) |
| `claude mcp list` | Check MCP connection status |
| `claude mcp tools shared-context-server` | List available tools |
| `tail -f logs/dev-server.log` | Monitor server logs |

## Troubleshooting

### Common Issues

#### Server Won't Start
```bash
# Check if port is in use
lsof -i :23456

# Kill existing processes
pkill -f "shared_context_server"

# Start with different port
HTTP_PORT=8001 make dev
# or: HTTP_PORT=8001 uv run python -m shared_context_server.scripts.dev
```

#### MCP Connection Failed
```bash
# Verify mcp-proxy is installed
which mcp-proxy

# Install if missing
uv tool install mcp-proxy

# Test direct connection
curl http://localhost:23456/mcp/
```

#### Hot Reload Not Working
```bash
# Check file watcher permissions
ls -la src/shared_context_server/

# Verify watchdog installation
uv pip list | grep watchdog

# Check logs for file change events
# Look for: "🔄 File changed: ..." messages
```

### Debug Commands

```bash
# Check server health
curl http://localhost:23456/mcp/

# Test proxy connection
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | \
  mcp-proxy --transport=streamablehttp http://localhost:23456/mcp/

# Enable debug logging
LOG_LEVEL=DEBUG make dev
# or: LOG_LEVEL=DEBUG uv run python -m shared_context_server.scripts.dev
```

### Quick Fixes

| Problem | Solution |
|---------|----------|
| Port in use | `lsof -ti :23456 \| xargs kill -9` |
| Connection failed | Check `which mcp-proxy` and install if missing |
| Hot reload not working | Check file permissions and logs |
| Tools not available | Restart Claude Code |

## Database Management

```bash
# Use separate dev database
export DATABASE_PATH="./dev_chat_history.db"

# Reset database on restart (optional)
export DEV_RESET_DATABASE_ON_START=true

# Backup important data
cp chat_history.db chat_history.backup.db
```

## Best Practices

### Code Quality
- Run `make quality` before committing
- Use type hints for all functions
- Write tests for new features
- Follow existing code patterns

### Performance Tips
- Hot reload only watches Python files in `src/`
- Server restart is lightweight (~1-2 seconds)
- Use separate dev database to avoid conflicts
- Use non-standard ports to avoid conflicts

### Development Security
- Use development API keys only
- Never commit real secrets
- Test with minimal permissions first
- Validate all inputs thoroughly

## Testing

### Running Tests

```bash
# All tests
make test                       # or: uv run pytest

# Specific test categories
uv run pytest tests/unit/      # Unit tests only
uv run pytest tests/behavioral/ # Integration tests
uv run pytest -k "test_name"   # Specific test

# With coverage
uv run pytest --cov=src --cov-report=html
```

### Test Development
- Write behavioral tests for new MCP tools
- Test hot reload scenarios
- Validate client integration
- Include error handling tests

## Next Steps

1. **Explore Tools**: Use `claude mcp tools shared-context-server` to see available tools
2. **Build Features**: Add new tools and test with hot reload
3. **Test Integration**: Try multi-agent workflows
4. **Monitor Performance**: Watch logs for optimization opportunities
5. **Production Setup**: Use production deployment when ready
