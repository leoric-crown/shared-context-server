# Development Quick Start

## TL;DR - Get Started in 30 seconds

```bash
# 1. Start hot reload server
uv run python -m shared_context_server.scripts.dev

# 2. Configure Claude Code (in another terminal)
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:8000/mcp/"]}'

# 3. Verify connection
claude mcp list
# Should show: shared-context-server: ... - ✓ Connected

# 4. Test tools in Claude Code session
# @shared-context-server create_session purpose="Test"
```

## What You Get

- 🔥 **Hot Reload**: Edit any `.py` file → server restarts automatically
- 🔗 **MCP Integration**: Tools available in Claude Code immediately
- ⚡ **Fast**: 1-2 second restart time
- 🛡️ **Stable**: Client connection persists through restarts
- 📝 **Logging**: All activity logged to `logs/dev-server.log` with automatic rotation (10MB max, 5 backups)

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

## Key Commands

| Command | Purpose |
|---------|---------|
| `uv run python -m shared_context_server.scripts.dev` | Start dev server |
| `claude mcp list` | Check connection status |
| `claude mcp tools shared-context-server` | List available tools |
| `tail -f logs/dev-server.log` | Monitor server logs |
| `uv run ruff check` | Code linting |
| `uv run mypy src/` | Type checking |
| `uv run pytest tests/` | Run tests |

## Environment Variables

```bash
# Essential
MCP_TRANSPORT=http
HTTP_PORT=8000

# Optional
DATABASE_PATH=./dev.db
LOG_LEVEL=DEBUG
API_KEY=dev-123
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port in use | `lsof -ti :8000 \| xargs kill -9` |
| Connection failed | Check `which mcp-proxy` and install if missing |
| Hot reload not working | Check file permissions and logs |
| Tools not available | Restart Claude Code |

## Next Steps

1. **Read Full Guide**: [Development Setup](./development-setup.md)
2. **Explore Tools**: Try the MCP tools in Claude Code
3. **Make Changes**: Edit server code and watch hot reload
4. **Build Features**: Add new tools and test immediately

---

**Need help?** Check the [Development Setup Guide](./development-setup.md) for detailed instructions.
