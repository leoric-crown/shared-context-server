# Docker Setup Guide

## Quick Start

**Default (Production-like):**
```bash
git clone <repository-url> && cd shared-context-server
echo "API_KEY=$(openssl rand -base64 32)" > .env
docker compose up -d
docker exec shared-context-server shared-context-server client-config claude
```

**Development (Hot Reload):**
```bash
git clone <repository-url> && cd shared-context-server
echo "API_KEY=$(openssl rand -base64 32)" > .env
make docker
```

## Commands

```bash
# Default setup
docker compose up -d                    # Start
docker compose down                     # Stop
docker compose logs -f                  # View logs

# Development setup
make docker                            # Start with hot reload
docker compose -f docker-compose.dev.yml down  # Stop

# Health checks
curl http://localhost:23456/health      # HTTP server
curl http://localhost:34567/health      # WebSocket server
docker exec shared-context-server shared-context-server status
```

## Client Configuration

```bash
# Get client-specific config
docker exec shared-context-server shared-context-server client-config claude
docker exec shared-context-server shared-context-server client-config cursor

# Manual setup
# MCP: http://localhost:23456/mcp/
# WebSocket: ws://localhost:34567
# Command: mcp-proxy --transport=streamablehttp http://localhost:23456/mcp/
```

## Configuration

**Required:**
```bash
API_KEY=your-secure-32-character-key
```

**Optional:**
```bash
HTTP_PORT=23456
WEBSOCKET_PORT=34567
LOG_LEVEL=INFO
MAX_SESSIONS_PER_AGENT=100
```

**Setup Comparison:**
- **Default**: Isolated storage, production-ready, `docker compose up -d`
- **Development**: Hot reload, shared database, source mounting, `make docker`

## Data Backup

**Default (Docker volumes):**
```bash
docker run --rm -v shared-context-server_shared-context-data:/data \
  -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz -C /data .
```

**Development (Shared file):**
```bash
cp chat_history.db chat_history.db.backup
```

## Development

```bash
# Hot reload development
make docker

# Build locally
docker compose build
docker compose -f docker-compose.dev.yml build

# Multi-architecture build
docker buildx build --platform linux/amd64,linux/arm64 .
```

## Troubleshooting

```bash
# Check logs
docker compose logs shared-context-server

# Common fixes:
# - Port conflicts: Change HTTP_PORT/WEBSOCKET_PORT in .env
# - Invalid API_KEY: Generate secure key
# - Reset database: docker volume rm shared-context-server_shared-context-data
# - Resource issues: docker stats shared-context-server

# Health checks
curl http://localhost:23456/health
curl http://localhost:34567/health
curl http://localhost:23456/mcp/
```

## Advanced

```bash
# Multiple instances (different ports)
HTTP_PORT=23457 WEBSOCKET_PORT=34568 docker compose up -d

# Container-to-container access
# MCP: http://shared-context-server:23456/mcp/
# WebSocket: ws://shared-context-server:34567

# Security: Generate secure API_KEY, use HTTPS proxy in production
```
