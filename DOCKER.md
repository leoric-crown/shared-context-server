# Docker Multi-Client Setup Guide

Run the Shared Context MCP Server as a persistent Docker container that multiple MCP clients can connect to simultaneously.

## Quick Start (30 seconds)

```bash
# 1. Clone and enter directory
git clone <repository-url>
cd shared-context-server

# 2. Generate secure keys
echo "API_KEY=$(openssl rand -base64 32)" > .env
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env

# 3. Start the server
docker compose up -d

# 4. Configure any MCP client (example with Claude)
docker exec shared-context-server shared-context-server client-config claude

# Output: claude mcp add shared-context-server "mcp-proxy --transport=streamablehttp http://localhost:23456/mcp/"
```

## Server Management

### Start/Stop/Restart
```bash
# Start server
docker compose up -d

# Stop server
docker compose down

# Restart server
docker compose restart

# View logs
docker compose logs -f

# Check status
docker exec shared-context-server shared-context-server status
```

### Health Monitoring
```bash
# Check if server is running
curl http://localhost:23456/health

# View server status
docker exec shared-context-server shared-context-server status

# Monitor container health
docker ps | grep shared-context-server
```

## Client Configuration

### Supported MCP Clients

Get configuration for your MCP client:

```bash
# Claude Code/Desktop
docker exec shared-context-server shared-context-server client-config claude

# Cursor
docker exec shared-context-server shared-context-server client-config cursor

# Windsurf
docker exec shared-context-server shared-context-server client-config windsurf

# VS Code
docker exec shared-context-server shared-context-server client-config vscode

# Generic client
docker exec shared-context-server shared-context-server client-config generic
```

### Manual Configuration

All clients connect to the same endpoint:
- **Server URL**: `http://localhost:23456/mcp/`
- **Command**: `mcp-proxy --transport=streamablehttp http://localhost:23456/mcp/`

## Configuration

### Environment Variables

Copy and customize the environment file:
```bash
cp .env.docker .env
```

Essential variables:
```bash
# Security (REQUIRED)
API_KEY=your-secure-32-character-key

# Server settings
HTTP_PORT=23456
LOG_LEVEL=INFO
ENVIRONMENT=production

# Resource limits
MAX_SESSIONS_PER_AGENT=100
MAX_MESSAGES_PER_SESSION=10000
```

### Production Configuration

For production, use the production compose file:
```bash
# Production deployment
docker compose -f docker-compose.prod.yml up -d
```

Key production differences:
- Uses published Docker images
- Enhanced security settings
- Resource limits and health checks
- Structured logging
- Automatic restarts

## Data Persistence

Database and logs persist in Docker volumes:

```bash
# View volumes
docker volume ls | grep shared-context

# Backup database
docker run --rm -v shared-context-server_shared-context-data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/database-backup.tar.gz -C /data .

# Restore database
docker run --rm -v shared-context-server_shared-context-data:/data \
  -v $(pwd):/backup alpine \
  tar xzf /backup/database-backup.tar.gz -C /data
```

## Multi-Platform Support

The Docker image supports multiple architectures:
- **linux/amd64** - Intel/AMD 64-bit (most servers, Intel Macs)
- **linux/arm64** - ARM 64-bit (Apple Silicon Macs, ARM servers)

Docker automatically selects the correct architecture.

## Development

### Hot Reload Development
```bash
# Start with development overrides
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
docker compose restart
```

### Building Locally
```bash
# Build image locally
docker compose build

# Build with no cache
docker compose build --no-cache

# Build specific architecture
docker buildx build --platform linux/amd64 -t shared-context-server:local .
```

## Troubleshooting

### Server Won't Start
```bash
# Check logs
docker compose logs shared-context-server

# Common issues:
# - Port 23456 already in use: Change HTTP_PORT in .env
# - Invalid API_KEY: Set secure key in .env
# - Permission issues: Check Docker volume permissions
```

### Client Connection Issues
```bash
# Verify server is accessible
curl http://localhost:23456/health

# Check if MCP endpoint is available
curl http://localhost:23456/mcp/

# Common issues:
# - Firewall blocking port 23456
# - Wrong host/port in client configuration
# - Server not running (docker compose ps)
```

### Database Issues
```bash
# Reset database (⚠️ deletes all data)
docker compose down
docker volume rm shared-context-server_shared-context-data
docker compose up -d

# Check database file permissions
docker exec shared-context-server ls -la /app/data/
```

### Performance Issues
```bash
# Monitor resource usage
docker stats shared-context-server

# Increase resource limits in docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 1G
#       cpus: '1.0'
```

## Security

### Production Security Checklist
- [ ] Generate secure API_KEY (≥32 characters)
- [ ] Set ENVIRONMENT=production
- [ ] Use docker-compose.prod.yml
- [ ] Restrict network access if needed
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

### Network Security
```bash
# Bind to localhost only (default)
HTTP_HOST=localhost

# Allow network access (⚠️ security risk)
HTTP_HOST=0.0.0.0

# Use reverse proxy for HTTPS in production
```

## Advanced Usage

### Multiple Instances
```bash
# Default instance runs on port 23456
# For a second instance, use a different port:
HTTP_PORT=23457 docker compose up -d

# Configure clients for the second instance
docker exec shared-context-server shared-context-server client-config claude --port 23457
```

### Container-to-Container Communication
```bash
# Access from another container in same network
# Use service name: http://shared-context-server:23456/mcp/
```

### Custom Image
```bash
# Build custom image with modifications
FROM ghcr.io/shared-context-server/server:latest
# Add custom configuration or tools
```

This Docker setup provides a robust, production-ready multi-client MCP server with minimal configuration required.
