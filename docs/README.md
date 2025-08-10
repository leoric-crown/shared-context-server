# Shared Context MCP Server Documentation

Welcome to the Shared Context MCP Server documentation! This server enables multiple AI agents to collaborate through shared conversational context.

## 📚 Documentation Index

### 🚀 Getting Started
- **[Development Quick Start](./dev-quick-start.md)** - Get up and running in 30 seconds
- **[Development Setup Guide](./development-setup.md)** - Comprehensive development documentation
- **[Production Setup](../README.md#production)** - Production deployment guide

### 🔥 Hot Reload Development
Our development setup provides true hot reload with automatic server restart on file changes:

```bash
# Start hot reload server
MCP_TRANSPORT=http HTTP_PORT=8000 uv run python -m shared_context_server.scripts.dev

# Configure Claude Code
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:8000/mcp/"]}'

# Edit any .py file → server restarts automatically in 1-2 seconds
```

### 🔗 MCP Client Integration
- **Claude Code**: Best development experience with integrated MCP support
- **VS Code**: Use MCP extension for tool integration
- **Custom Clients**: HTTP API and direct MCP protocol support

### 🛠️ Development Tools
- **File Watching**: Monitors `src/shared_context_server/` recursively
- **Process Management**: Automatic server restart on changes
- **Connection Stability**: Clients maintain connection through restarts
- **Transport Bridging**: `mcp-proxy` handles protocol translation

## 📖 Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │  MCP Proxy  │    │   Server    │
│ (Claude/VS) │◄──►│ (mcp-proxy) │◄──►│ (FastMCP)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
   STDIO/MCP        HTTP ↔ STDIO        Streamable HTTP
```

### Key Components
- **Server**: FastMCP with Streamable HTTP transport
- **Proxy**: `mcp-proxy` bridges HTTP ↔ STDIO for client compatibility
- **Watcher**: `watchdog` monitors files and manages server restarts
- **Client**: Claude Code, VS Code, or custom MCP clients

## 🎯 Quick Reference

### Essential Commands
| Command | Purpose |
|---------|---------|
| `MCP_TRANSPORT=http uv run python -m shared_context_server.scripts.dev` | Start hot reload server |
| `claude mcp list` | Check connection status |
| `uv run ruff check` | Code linting |
| `uv run mypy src/` | Type checking |
| `uv run pytest tests/` | Run tests |

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_TRANSPORT` | `stdio` | Transport type (use `http` for dev) |
| `HTTP_PORT` | `8000` | Server port |
| `HTTP_HOST` | `localhost` | Server host |
| `DATABASE_PATH` | `./chat_history.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging level |

## 🔧 Troubleshooting

### Common Issues
- **Port in use**: `lsof -ti :8000 | xargs kill -9`
- **Connection failed**: Install `mcp-proxy` with `uv tool install mcp-proxy`
- **Hot reload not working**: Check file permissions and logs
- **Tools not available**: Restart Claude Code or check proxy connection

### Debug Commands
```bash
# Check server health
curl http://localhost:8000/mcp/

# Test proxy connection
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | \
  mcp-proxy --transport=streamablehttp http://localhost:8000/mcp/

# Enable debug logging
LOG_LEVEL=DEBUG uv run python -m shared_context_server.scripts.dev
```

## 🤝 Contributing

1. **Setup Development**: Follow [Development Quick Start](./dev-quick-start.md)
2. **Make Changes**: Edit files with automatic hot reload
3. **Quality Checks**: Run `uv run ruff check && uv run mypy src/ && uv run pytest tests/`
4. **Test Integration**: Verify MCP tools work in Claude Code
5. **Submit PR**: Include tests and documentation updates

## 📞 Support

- **Issues**: [GitHub Issues](../../issues)
- **Documentation**: This docs directory
- **Development**: See [Development Setup](./development-setup.md)
- **Architecture**: See [CLAUDE.md](../CLAUDE.md) for system overview

---

**Happy coding!** 🚀 The hot reload development setup makes building and testing MCP servers fast and enjoyable.
