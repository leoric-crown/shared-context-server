# Quick Reference Guide

Essential commands, environment variables, and troubleshooting for the Shared Context MCP Server.

## Development Commands

### Core Commands
```bash
# Start development server with hot reload
make dev
uv run python -m shared_context_server.scripts.dev

# Run all tests with coverage
make test
uv run pytest --cov=src --cov-report=html

# Run all quality checks (lint + type + security)
make quality
uv run ruff check && uv run mypy src/ && uv run pip-audit
```

### Installation & Setup
```bash
# Install all dependencies
uv sync --dev

# Install MCP proxy for client connections
uv tool install mcp-proxy

# Validate development environment
make validate
uv run python -m shared_context_server.scripts.dev --validate

# Show all available make targets
make help
```

### Code Quality
```bash
# Format code
make format
uv run ruff format

# Lint code with auto-fix
make lint
uv run ruff check --fix

# Type checking
make type
uv run mypy src

# Pre-commit hooks
make pre-commit
uv run pre-commit run
```

### Testing
```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit/

# Behavioral/integration tests
uv run pytest tests/behavioral/

# Specific test
uv run pytest -k "test_name"

# With coverage report
uv run pytest --cov=src --cov-report=term-missing
```

## Environment Variables

### Required for Development
```bash
MCP_TRANSPORT=http              # Use HTTP transport for development
HTTP_PORT=23456                 # Server port (default: 23456)
```

### Optional Configuration
```bash
HTTP_HOST=localhost             # Server host (default: localhost)
MCP_SERVER_NAME=shared-context  # Server name identifier
DATABASE_PATH=./chat_history.db # SQLite database location
LOG_LEVEL=INFO                  # Logging level (DEBUG, INFO, WARNING, ERROR)
API_KEY=dev-key-123            # API key for authentication
JWT_SECRET_KEY=your-jwt-secret  # JWT signing key
JWT_ENCRYPTION_KEY=your-fernet  # Encryption key for sensitive data
```

### Development Options
```bash
DEV_RESET_DATABASE_ON_START=true    # Reset database on server start
DEBUG=true                          # Enable debug mode
CORS_ORIGINS=*                      # CORS origins for web clients
```

## MCP Client Setup

### Claude Code
```bash
# Add server configuration
claude mcp add-json shared-context-server '{
  "command": "mcp-proxy",
  "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]
}'

# Verify connection
claude mcp list

# List available tools
claude mcp tools shared-context-server
```

### VS Code Settings
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

## Docker Quick Commands

### Development with Docker
```bash
# Start with Docker Compose
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Full lifecycle (stop → build → up → logs)
make docker
```

### Production Docker
```bash
# Pull latest image
docker pull ghcr.io/leoric-crown/shared-context-server:latest

# Run with environment variables
docker run -d --name shared-context-server \
  -p 23456:23456 \
  -e API_KEY="$(openssl rand -base64 32)" \
  -e JWT_SECRET_KEY="$(openssl rand -base64 32)" \
  -e JWT_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  ghcr.io/leoric-crown/shared-context-server:latest
```

## Common Ports & URLs

### Development URLs
- **Server**: http://localhost:23456
- **MCP Endpoint**: http://localhost:23456/mcp/
- **Health Check**: http://localhost:23456/health
- **API Docs**: http://localhost:23456/docs

### Default Ports
- **HTTP Server**: 23456
- **Alternative Dev**: 8000, 8001

## Troubleshooting Checklist

### 🔴 Quick Fixes

**Port busy**: `kill $(lsof -t -i :23456)` or `HTTP_PORT=8001 make dev`
**Bad API keys**: Use the exact commands from README Step 1
**Docker issues**: Start Docker Desktop or `sudo systemctl start docker`

### Server Issues
```bash
# Check if port is in use
lsof -i :23456

# Kill existing processes
pkill -f "shared_context_server"

# Start with different port
HTTP_PORT=8001 make dev
```

### Connection Issues
```bash
# Verify mcp-proxy installation
which mcp-proxy

# Install if missing
uv tool install mcp-proxy

# Test server health
curl http://localhost:23456/mcp/

# Test MCP connection
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | \
  mcp-proxy --transport=streamablehttp http://localhost:23456/mcp/
```

### Hot Reload Issues
```bash
# Check file permissions
ls -la src/shared_context_server/

# Verify watchdog installation
uv pip list | grep watchdog

# Enable debug logging
LOG_LEVEL=DEBUG make dev
```

### Database Issues
```bash
# Check database file
ls -la *.db

# Reset development database
rm -f dev_chat_history.db

# Use separate dev database
export DATABASE_PATH="./dev.db"
```

## API Authentication

### Generate Secure Keys
```bash
# API key
openssl rand -base64 32

# JWT secret key
openssl rand -base64 32

# Encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### JWT Token Usage
```bash
# Get authentication token
TOKEN=$(curl -X POST http://localhost:23456/authenticate \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "my-agent", "agent_type": "claude", "api_key": "your-api-key"}' \
  | jq -r '.token')

# Use token in requests
curl http://localhost:23456/mcp/tool/add_message \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"session_id": "session_123", "content": "Hello"}'
```

## File Locations

### Important Files
- **Dependencies**: `pyproject.toml` - Python dependencies and tools config
- **Environment**: `.env` - Environment variables (create manually)
- **Database**: `chat_history.db` - SQLite database (auto-created)
- **Logs**: `logs/` - Development and application logs

### Source Structure
```
src/shared_context_server/
├── server.py           # Main FastMCP server
├── tools.py            # MCP tool implementations
├── database.py         # SQLite operations
├── config.py           # Configuration management
├── auth.py            # Authentication & authorization
└── scripts/
    └── dev.py         # Development server
```

## Performance Monitoring

### Key Metrics
- **Session creation**: < 10ms
- **Message operations**: < 20ms
- **Search queries**: < 30ms (2-3ms with RapidFuzz)
- **Concurrent agents**: 20+ supported

### Monitoring Commands
```bash
# Check server status
curl http://localhost:23456/health

# Monitor logs in real-time
tail -f logs/dev-server.log

# Database size
ls -lh *.db

# Memory usage
ps aux | grep shared_context_server
```

## Development Cleanup

### Clean Build Artifacts
```bash
# Use Makefile (with confirmation prompt)
make clean

# Manual cleanup
rm -rf __pycache__ .pytest_cache .ruff_cache .mypy_cache
rm -rf htmlcov/ coverage.xml .coverage
rm -rf *.db test_*.db
rm -rf logs/
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
```
