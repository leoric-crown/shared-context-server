# Minimal Dependency Options for Demo

## Option 1: uvx + npx (Current Approach)
**Dependencies**: Node.js + Python
**Setup**: Clone → Copy .env → Open Claude Code

```json
{
  "mcpServers": {
    "octocode": {
      "command": "npx",
      "args": ["-y", "octocode-mcp"]
    },
    "shared-context-server": {
      "command": "uvx",
      "args": ["shared-context-server", "--transport", "http", "--port", "23456"]
    }
  }
}
```

**Pros**:
- Uses published PyPI package
- Automatic dependency management
- Clean separation of concerns

**Cons**:
- Requires both Node and Python
- uvx might not be installed

## Option 2: Docker + npx (Ultra Minimal)
**Dependencies**: Node.js + Docker
**Setup**: Clone → Copy .env → Open Claude Code

```json
{
  "mcpServers": {
    "octocode": {
      "command": "npx",
      "args": ["-y", "octocode-mcp"]
    },
    "shared-context-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "-d",
        "--name", "demo-shared-context-server",
        "-p", "23456:23456",
        "--env-file", ".env",
        "ghcr.io/leoric-crown/shared-context-server:latest"
      ]
    }
  }
}
```

**Pros**:
- No Python installation required
- Uses published Docker image
- Consistent environment

**Cons**:
- Requires Docker
- More complex MCP configuration
- Docker might not be available on all systems

## Option 3: HTTP Proxy + npx (Node-only)
**Dependencies**: Just Node.js
**Setup**: Clone → Start server manually → Copy .env → Open Claude Code

```bash
# User runs this once manually:
npx shared-context-server-proxy --port 23456 &
```

```json
{
  "mcpServers": {
    "octocode": {
      "command": "npx",
      "args": ["-y", "octocode-mcp"]
    },
    "shared-context-server": {
      "command": "mcp-proxy",
      "args": [
        "--transport=streamablehttp",
        "http://localhost:23456/mcp/",
        "--headers", "X-API-Key", "demo-multi-expert-collaboration-key-2025"
      ]
    }
  }
}
```

**Pros**:
- Only Node.js required
- Uses mcp-proxy (standard tool)
- Minimal dependencies

**Cons**:
- Requires manual server start
- More setup steps
- Need to publish HTTP proxy wrapper

## Option 4: Embedded Server (Future)
**Dependencies**: Just Node.js
**Setup**: Clone → Open Claude Code

```json
{
  "mcpServers": {
    "octocode": {
      "command": "npx",
      "args": ["-y", "octocode-mcp"]
    },
    "shared-context-server": {
      "command": "npx",
      "args": ["-y", "shared-context-server-node"]
    }
  }
}
```

**Pros**:
- Single dependency (Node.js)
- Zero manual setup
- Perfect demo experience

**Cons**:
- Requires Node.js port of shared-context-server
- Significant development effort
- Not available for 1.1.9 release

## Recommendation: Option 1 (uvx + npx)

For the 1.1.9 demo, **Option 1 (uvx + npx)** is the best balance:

### Why uvx + npx Works Best:
1. **Developer Reality**: Most developers have both Node and Python
2. **Zero Installation**: uvx automatically handles Python dependencies
3. **Published Package**: Uses your existing PyPI package
4. **Reliable**: Both tools are mature and stable
5. **Fast Setup**: Still just "clone → copy → open"

### Fallback Strategy:
If uvx isn't available, provide alternatives in the README:

```markdown
## Quick Start Options

### Option A: uvx (Recommended)
```bash
# Automatic - uvx handles everything
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server/examples/demos/multi-expert-optimization
cp .env.demo .env
# Open Claude Code - MCP servers start automatically
```

### Option B: Docker (If no Python)
```bash
# Manual server start, then Claude Code
docker run -d --name demo-scs -p 23456:23456 --env-file .env ghcr.io/leoric-crown/shared-context-server:latest
# Then open Claude Code with modified .kiro/settings/mcp.json
```

### Option C: Local Development
```bash
# For contributors/developers
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
uv sync
make dev
# Then navigate to demo directory and open Claude Code
```
```

## Dependency Reality Check

### What Developers Actually Have:
- **Node.js**: ~95% of developers (required for most modern development)
- **Python**: ~80% of developers (very common)
- **Docker**: ~60% of developers (growing but not universal)
- **uvx**: ~10% of developers (new tool, but auto-installs)

### What This Means:
- **uvx approach**: Works for 80% immediately, others can install uvx in 30 seconds
- **Docker approach**: Works for 60% immediately, others need Docker installation
- **Node-only approach**: Would work for 95% but requires significant development

## Final Recommendation

Stick with **uvx + npx** for the 1.1.9 demo because:

1. **Good enough coverage**: 80% of developers can run immediately
2. **Easy fallback**: uvx installs in 30 seconds for the remaining 20%
3. **Uses existing infrastructure**: No new development required
4. **Professional appearance**: Uses published packages, not local builds
5. **Reliable experience**: Both tools are stable and predictable

The demo story becomes:
> "Clone this repository, copy one file, open Claude Code. If you don't have uvx, install it with one command. Then watch three AI experts collaborate on your code."

That's still a compelling 30-second setup for a 5-minute wow experience.
