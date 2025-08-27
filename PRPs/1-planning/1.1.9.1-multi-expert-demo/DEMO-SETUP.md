# Multi-Expert Collaboration Demo Setup

Quick setup guide for the shared-context-server multi-expert collaboration demo.

## Requirements

- **Docker & Docker Compose** - For running the shared-context-server
- **Node.js** - For octocode MCP server (GitHub repository analysis)
- **GitHub Authentication** - For repository access

## Setup Instructions

### 1. Clone and Navigate
```bash
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
```

### 2. Set Environment Variables
Copy the demo credentials template:
```bash
cp .env.demo .env
```

Verify the demo credentials are set:
```bash
cat .env
# Should show:
# API_KEY=demo-multi-expert-collaboration-key-2025
# JWT_SECRET_KEY=demo-jwt-secret-for-expert-committee-showcase-demo
# JWT_ENCRYPTION_KEY=demo-fernet-key-for-multi-agent-coordination-demo
# HTTP_PORT=23432
# WEBSOCKET_PORT=34543
```

### 3. Configure GitHub Authentication
**Choose ONE option:**

**Option A: GitHub CLI (Recommended)**
```bash
gh auth login
```

**Option B: Environment Variable**
```bash
export GITHUB_TOKEN="your_github_personal_access_token"
```

**Option C: Authorization Header**
```bash
export Authorization="Bearer your_github_personal_access_token"
```

### 4. Start the Server
```bash
docker compose up -d
```

Verify the server is running:
```bash
curl -H "X-API-Key: demo-multi-expert-collaboration-key-2025" \
     http://localhost:23432/mcp/ | head -5
```

### 5. Launch Demo
Open Claude Code in this directory - the `.mcp.json` configuration will automatically:
- Connect to the HTTP server with API key authentication
- Enable octocode for GitHub repository analysis
- Auto-approve common tools for smooth demo flow

## Demo Usage

### Start Multi-Expert Analysis
```
I want to optimize this repository using our expert committee approach.
Please start by having our Performance Architect analyze the codebase
for bottlenecks and optimization opportunities.
```

### Expected Flow
1. **Performance Architect** - Analyzes repository structure and identifies bottlenecks
2. **Implementation Expert** - Proposes concrete optimization solutions
3. **Validation Expert** - Designs testing and success criteria
4. **Coordination** - Experts build on each other's findings through shared session

## Architecture

```
Claude Code
    ↓ (STDIO)
octocode-mcp ← GitHub API
    ↓ (HTTP + API Key)
shared-context-server ← Docker
    ↓ (WebSocket)
Dashboard UI (localhost:23432/ui/)
```

## Troubleshooting

### Server Not Starting
```bash
# Check Docker status
docker compose ps

# View server logs
docker compose logs -f
```

### GitHub Authentication Failed
```bash
# Test GitHub access
gh auth status
# or
curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

### MCP Connection Issues
```bash
# Verify server responds
curl -H "X-API-Key: demo-multi-expert-collaboration-key-2025" \
     http://localhost:23432/mcp/

# Check Claude Code MCP status
# Look for shared-context-server in Claude Code > Settings > MCP
```

### Port Conflicts
If port 23432 is in use, modify `.env`:
```bash
echo "HTTP_PORT=23457" >> .env
echo "WEBSOCKET_PORT=23458" >> .env
docker compose up -d --force-recreate
```

## Cleanup
```bash
# Stop demo
docker compose down

# Remove containers and volumes
docker compose down -v
```

## Files Created
- `.mcp.json` - Claude Code MCP server configuration
- `DEMO-SETUP.md` - This setup guide

## Next Steps
After successful setup, try the demo with different repositories:
- Your own projects for personalized insights
- Popular open source projects (microsoft/vscode, facebook/react)
- The shared-context-server itself for meta-analysis
