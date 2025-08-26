# Docker Setup Guide

## Quick Start

**Production Setup (Recommended):**
```bash
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
cp .env.minimal .env

# Generate secure keys and update .env:
API_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
JWT_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# Then manually update .env file with these values

make docker-prod  # Uses GHCR pre-built image
```

**Development Setup (Hot Reload):**
```bash
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
cp .env.minimal .env
# Generate secure keys (same commands as above)

make docker  # Builds locally + hot reload
```

## Environment Setup

**Required**: Copy minimal template and generate keys
```bash
# Use minimal template (only essential variables)
cp .env.minimal .env

# Generate secure keys
API_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
JWT_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Update .env with these values
```

## Commands

### Production (GHCR Image)
```bash
make docker-prod                       # Start production deployment
docker compose down                     # Stop
docker compose logs -f                 # View logs
```

### Development (Local Build + Hot Reload)
```bash
make docker                            # Start development environment
docker compose -f docker-compose.dev.yml down  # Stop
```

### Manual Docker Compose
```bash
# Production (uses GHCR image)
docker compose up -d                   # Start
docker compose down                    # Stop

# Development (local build)
docker compose -f docker-compose.dev.yml up -d  # Start
docker compose -f docker-compose.dev.yml down   # Stop
```

### Client Configuration
```bash
# Get MCP client setup commands
docker exec shared-context-server shared-context-server client-config claude
docker exec shared-context-server shared-context-server client-config cursor

# Check server status
docker exec shared-context-server shared-context-server status
```

## Health Checks

```bash
curl http://localhost:23456/health      # HTTP server
curl http://localhost:34567/health      # WebSocket server
curl http://localhost:23456/mcp/        # MCP endpoint
```

## Configuration

### Environment Variables (.env file)
```bash
# Required Security
API_KEY=your-secure-api-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ENCRYPTION_KEY=your-fernet-key

# Optional
HTTP_PORT=23456
WEBSOCKET_PORT=34567
LOG_LEVEL=INFO
MCP_CLIENT_HOST=localhost
```

### Setup Comparison
- **Production**: `make docker-prod` - GHCR image, isolated storage, production defaults
- **Development**: `make docker` - Local build, hot reload, shared database, debug logging

## Data Management

### Backup (Production volumes)
```bash
docker run --rm -v shared-context-server_shared-context-data:/data \
  -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz -C /data .
```

### Backup (Development shared files)
```bash
cp chat_history.db chat_history.db.backup
```

### Reset Database
```bash
# Production
docker volume rm shared-context-server_shared-context-data

# Development
rm chat_history.db
```

## Troubleshooting

### Common Issues
```bash
# Check logs
docker compose logs shared-context-server

# Port conflicts
# Solution: Change HTTP_PORT/WEBSOCKET_PORT in .env

# Invalid API keys
# Solution: Regenerate using commands from Environment Setup

# Resource issues
docker stats shared-context-server
```

### Multiple Instances
```bash
# Run on different ports
HTTP_PORT=23457 WEBSOCKET_PORT=34568 docker compose up -d
```

### Container Networking
```bash
# Container-to-container access:
# MCP: http://shared-context-server:23456/mcp/
# WebSocket: ws://shared-context-server:34567
```
