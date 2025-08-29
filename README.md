# Shared Context Server

[![CI](https://github.com/leoric-crown/shared-context-server/workflows/CI/badge.svg)](https://github.com/leoric-crown/shared-context-server/actions)
[![Docker](https://github.com/leoric-crown/shared-context-server/workflows/Build%20and%20Publish%20Docker%20Image/badge.svg)](https://github.com/leoric-crown/shared-context-server/actions)
[![GHCR](https://img.shields.io/badge/ghcr.io-leoric--crown%2Fshared--context--server-blue?logo=docker)](https://github.com/leoric-crown/shared-context-server/pkgs/container/shared-context-server)
[![PyPI version](https://badge.fury.io/py/shared-context-server.svg)](https://pypi.org/project/shared-context-server/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/shared-context-server)](https://pypi.org/project/shared-context-server/)
[![codecov](https://codecov.io/gh/leoric-crown/shared-context-server/graph/badge.svg?token=07ZITBOAZ7)](https://codecov.io/gh/leoric-crown/shared-context-server)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Trigger CI after GitHub Actions infrastructure issues -->

## Content Navigation

| Symbol | Meaning        | Time Investment |
| ------ | -------------- | --------------- |
| 🚀     | Quick start    | 2-5 minutes     |
| ⚙️     | Configuration  | 10-15 minutes   |
| 🔧     | Deep dive      | 30+ minutes     |
| 💡     | Why this works | Context only    |
| ⚠️     | Important note | Read carefully  |

---

## 🎯 Quick Understanding (30 seconds)

**A shared workspace for AI agents to collaborate on complex tasks.**

**The Problem**: AI agents work independently, duplicate research, and can't build on each other's discoveries.

**The Solution**: Shared sessions where agents see previous findings and build incrementally instead of starting over.

```python
# Agent 1: Security analysis
session.add_message("security_agent", "Found SQL injection in user login")

# Agent 2: Performance review (sees security findings)
session.add_message("perf_agent", "Optimized query while fixing SQL injection")

# Agent 3: Documentation (has full context)
session.add_message("docs_agent", "Documented secure, optimized login implementation")
```

Each agent builds on previous work instead of starting over.

💡 **Uses MCP Protocol**: Model Context Protocol - the standard for AI agent communication (works with Claude Code, Gemini, VS Code, Cursor, and frameworks like CrewAI).

---

## 🎪 Multi-Expert Demo (30 seconds to start)

**See AI agents collaborate better than any individual agent could.**

```bash
# One command creates complete demo environment
scs setup demo
scs  # Start server, then try the magic prompt below in Claude Code
```

**The Magic Prompt** (copy to Claude Code):

```
I want to optimize this repository using our expert committee approach. Please start by having our Performance Architect analyze the codebase for bottlenecks.
```

**What Happens**: Three AI experts collaborate autonomously:

- **Performance Architect** → finds bottlenecks with evidence
- **Implementation Expert** → builds concrete solutions
- **Validation Expert** → creates testing strategy

Each expert builds on the previous expert's findings through persistent shared sessions. **No manual coordination required.**

💡 **Try asking Claude**: "Show me how the experts coordinated and what would this look like with a single agent instead?"

➡️ **[Complete Demo Guide](./examples/demos/multi-expert-optimization/README.md)** (transforms to "ALREADY DONE!" after setup)

---

## 🚀 Try It Now (2 minutes)

### ⚠️ **Important: Choose Your Deployment Method**

**Docker (Recommended for Multi-Client Collaboration):**

- ✅ **Shared context across all MCP clients** (Claude Code + Cursor + Windsurf)
- ✅ **Persistent service** - single server instance on port 23456
- ✅ **True multi-agent collaboration** - agents share sessions and memory
- 🎯 **Use when**: You want multiple tools to collaborate on the same tasks

**uvx (Quick Trial & Testing Only):**

- ⚠️ **Isolated per-client** - each MCP client gets its own separate instance
- ⚠️ **No shared context** - Claude Code and Cursor can't see each other's work
- ✅ **Quick testing** - perfect for trying features without Docker setup
- 🎯 **Use when**: Quick feature testing or learning the MCP tools in isolation

```bash
# 🐳 Docker: Multi-client shared collaboration (RECOMMENDED)
# ⚠️ Requires environment variables - see Step 1 below

# 📦 uvx: Isolated single-client testing only
# ⚠️ Requires API key - see Step 1 below
uvx shared-context-server --help
```

💡 **TL;DR**: Use Docker for real multi-agent work, uvx for quick testing only.

### Prerequisites Check (30 seconds)

**Choose your path**:

- ✅ **Docker** (recommended): `docker --version` works
- ✅ **uvx Trial**: `uvx --version` works (testing only)

### Environment Configuration Templates

**Choose your .env template** (for local development):

```bash
# 🚀 Quick Start (recommended) - Essential variables only
cp .env.minimal .env

# 🔧 Full Development - All development features
cp .env.example .env

# 🐳 Docker Deployment - Container-optimized paths
cp .env.docker .env
```

💡 **Most users want `.env.minimal`** - it contains only the 12 essential variables you actually need.

### Step 1: Generate Keys & Start Server

**🚀 One-Command Demo Setup (Recommended)**

```bash
# Experience multi-expert AI collaboration in 30 seconds
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
scs setup demo
# ↳ Creates complete demo environment with expert agents ready to collaborate
```

**🐳 Production Setup Alternative**

```bash
# For production deployment with Docker
scs setup docker
# ↳ Generates keys, shows Docker commands, creates .env file
```

**Option A: Docker Compose (Recommended)**

```bash
# After running the key generator above, choose your deployment:

# 🚀 Production (pre-built image from GHCR):
make docker
# OR: docker compose up -d

# 🔧 Development (with hot reload):
make dev-docker
# OR: docker compose -f docker-compose.dev.yml up -d

# 🏗️ Production (build locally):
make docker-local
# OR: docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
```

**Alternative: Raw Docker Commands**

```bash
# If you prefer docker run over docker compose:
docker run -d --name shared-context-server -p 23456:23456 \
  -e API_KEY="your-generated-api-key" \
  -e JWT_SECRET_KEY="your-generated-jwt-secret" \
  -e JWT_ENCRYPTION_KEY="your-generated-jwt-encryption-key" \
  ghcr.io/leoric-crown/shared-context-server:latest
```

**Option B: uvx Trial (Isolated Testing Only)**

```bash
# Generate keys first
scs setup uvx
# ↳ Shows the exact uvx command with generated keys

# Example output command to run:
API_KEY="generated-key" JWT_SECRET_KEY="generated-secret" \
  uvx shared-context-server --transport http

# ⚠️ IMPORTANT: Each MCP client gets isolated instances
# No shared context between Claude Code, Cursor, Windsurf
```

**Option C: Local Development**

```bash
# Full development setup
git clone https://github.com/leoric-crown/shared-context-server.git
cd shared-context-server
uv sync
scs setup
# ↳ Creates .env file and shows make dev command

make dev  # Starts with hot reload
```

### Step 2: Connect Your MCP Client

The key generation script shows the exact commands with your API key. Replace `YOUR_API_KEY_HERE` with your generated key:

```bash
# Claude Code (simple HTTP transport)
claude mcp add --transport http scs http://localhost:23456/mcp/ \
  --header "X-API-Key: YOUR_API_KEY_HERE"

# Gemini CLI
gemini mcp add scs http://localhost:23456/mcp -t http -H "X-API-Key: YOUR_API_KEY_HERE"

# Test connection
claude mcp list  # Should show: ✓ Connected
```

### VS Code Configuration

Add to your existing `.vscode/mcp.json` (create if it doesn't exist):

```json
{
  "servers": {
    "shared-context-server": {
      "type": "http",
      "url": "http://localhost:23456/mcp",
      "headers": { "X-API-Key": "YOUR_API_KEY_HERE" }
    }
  }
}
```

### Cursor Configuration

Add to your existing `.cursor/mcp.json` (create if it doesn't exist):

```json
{
  "mcpServers": {
    "shared-context-server": {
      "command": "mcp-proxy",
      "args": [
        "--transport=streamablehttp",
        "http://localhost:23456/mcp/",
        "--headers",
        "X-API-Key",
        "YOUR_API_KEY_HERE"
      ]
    }
  }
}
```

### Claude Desktop Configuration

Add to your existing `claude_desktop_config.json`:

On MacOS, you may have to provide explicity path to mcp-proxy.

Have not tested in Windows.

```json
{
  "scs": {
    "command": "/Users/YOUR_USER/.local/bin/mcp-proxy",
    "args": [
      "--transport=streamablehttp",
      "http://localhost:23456/mcp/",
      "--headers",
      "X-API-Key",
      "YOUR_API_KEY_HERE"
    ]
  }
}
```

### Step 3: Verify & Monitor

**📝 Note**: If you used `make docker-prod`, press Ctrl+C to exit the log viewer first, then run these commands in the same terminal.

```bash
# Test your setup (30 seconds)
# Method 1: Quick health check
curl http://localhost:23456/health

# Method 2: Create actual test session (see it in web UI!)
# If you have Claude Code with shared-context-server MCP tools:
# Run this in Claude: Create a session with purpose "README test setup"
# Expected: {"success": true, "session_id": "session_...", ...}

# Method 3: Test MCP tools discovery
npx @modelcontextprotocol/inspector --cli --method tools/list \
  -e API_KEY=$API_KEY \
  -e JWT_SECRET_KEY=$JWT_SECRET_KEY \
  -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli

# Expected: {"tools": [...]} (proves MCP tools are available)

# Method 4: For Docker deployment, test via HTTP endpoint
npx @modelcontextprotocol/inspector --cli --method tools/list \
  http://localhost:23456/mcp
```

```bash
# View the dashboard
open http://localhost:23456/ui/  # Real-time session monitoring
```

✅ **Success indicators**:

- Health endpoint returns `{"status": "healthy", ...}`
- Dashboard loads at http://localhost:23456/ui/ and shows active sessions
- MCP Inspector validation error (proves MCP protocol is working)
- MCP client shows `✓ Connected` status

### 📊 Web Dashboard (MVP)

Real-time monitoring interface for agent collaboration:

- **Live session overview** with active agent counts
- **Real-time message streaming** without page refreshes
- **Session isolation visualization** to track multi-agent workflows
- **Performance monitoring** for collaboration efficiency

💡 **Perfect for**: Monitoring agent handoffs, debugging collaboration flows, and demonstrating multi-agent coordination to stakeholders.

### 📦 PyPI Installation (Alternative Method)

The shared-context-server is also available on PyPI for quick testing:

```bash
# 📦 Install and try (creates isolated instances per client)
uvx shared-context-server --help
uvx shared-context-server --version

# ⚠️ For multi-client collaboration, use Docker instead
```

💡 **When to use PyPI/uvx**: Quick feature testing, learning MCP tools, single-client workflows only.

---

## 🔧 Choose Your Path

**Are you...**

```
├── 👨‍💻 Building a side project?
│   → [Simple Integration](#-simple-integration) (5 minutes)
│
├── 🏢 Planning enterprise deployment?
│   → [Enterprise Setup](#-enterprise-considerations) (15+ minutes)
│
├── 🎓 Researching multi-agent systems?
│   → [Technical Deep Dive](#-technical-architecture) (30+ minutes)
│
└── 🤔 Just evaluating the concept?
    → [Framework Integration Examples](#-framework-examples) (5 minutes)
```

---

## 🚀 Simple Integration

Works with existing tools you already use:

### Direct MCP Integration (Tested)

```bash
# Generate Claude Code configuration automatically
scs client-config claude -s user -c

# Or generate configuration for other MCP clients
scs client-config cursor -c     # Cursor IDE
scs client-config all -c        # All supported clients

# Direct MCP usage (use proper MCP client in production)
# Example shows concept - use mcp-proxy or MCP client libraries
import asyncio
from mcp_client import MCPClient  # Conceptual - use actual MCP client

async def create_session():
    client = MCPClient("http://localhost:23456/mcp/")
    return await client.call_tool("create_session", {"purpose": "agent collaboration"})
```

⚠️ **Framework Integration Status**: Direct MCP protocol tested. CrewAI, AutoGen, and LangChain integrations are conceptual - we welcome community contributions to develop and test these patterns.

**➡️ Next**: [MCP Integration Examples](./docs/integration-guide.md)

---

## ⚙️ Framework Examples

### Multi-Expert Code Optimization (Featured Demo)

1. **Performance Architect** analyzes codebase → identifies bottlenecks with evidence
2. **Implementation Expert** reads findings → develops concrete solutions
3. **Validation Expert** synthesizes both → creates comprehensive testing strategy

💡 **Why this works**: Experts ask clarifying questions and build on each other's insights through persistent sessions.

### Conversational vs Monologue Patterns

```
❌ Traditional: "Here are my findings" (isolated analysis)
✅ Advanced: "Based on your bottleneck analysis, I have questions about X constraint..." (collaborative)
```

### Research & Implementation Pipeline

1. **Research Agent** gathers requirements → shares insights
2. **Architecture Agent** questions research gaps → designs using complete context
3. **Developer Agent** implements with iterative feedback loop

**Demo these patterns**: Run `scs setup demo` to experience expert committees vs individual analysis.

**More examples**: [Collaborative Workflows Guide](./docs/integration-guide.md#collaborative-workflows)

**What works**: ✅ MCP clients (Claude Code, Gemini, VS Code, Cursor)
**What's conceptual**: 🔄 Framework patterns (CrewAI, AutoGen, LangChain) - community contributions welcome

---

## 🔧 What This Is / What This Isn't

### ✅ **What this MCP server provides**

- **Real-time collaboration substrate** for multi-agent workflows
- **Session isolation** with clean boundaries between different tasks
- **MCP protocol compliance** that works with any MCP-compatible agent framework
- **Infrastructure layer** that enhances existing orchestration tools

💡 **Why MCP protocol?** Universal compatibility - works with Claude Code, CrewAI, AutoGen, LangChain, and custom frameworks without vendor lock-in.

### ❌ **What this MCP server isn't**

- **Not a vector database** - Use Pinecone, Milvus, or Chroma for long-term storage
- **Not an orchestration platform** - Use CrewAI, AutoGen, or LangChain for task management
- **Not for permanent memory** - Sessions are for active collaboration, not archival

💡 **Why this approach?** We enhance your existing tools rather than replacing them - no need to rewrite your agent workflows.

---

## 🏢 Enterprise Considerations

<details>
<summary>⚙️ Production Setup & Scaling</summary>

### Development → Production Path

**Development (SQLite)**

- ✅ Zero configuration
- ✅ Perfect for prototyping
- ❌ Limited to ~5 concurrent agents

**Production (PostgreSQL)**

- ✅ High concurrency (20+ agents)
- ✅ Enterprise backup/recovery
- ❌ Requires database management

### Enterprise Features Roadmap

- **SSO Integration**: SAML/OIDC support planned
- **Audit Logging**: Enhanced compliance logging
- **High Availability**: Multi-node deployment
- **Advanced RBAC**: Attribute-based permissions

**Migration**: Start with SQLite, migrate when you hit concurrency limits.

</details>

<details>
<summary>🔧 Security & Compliance</summary>

### Current Security Features

- **JWT Authentication**: Role-based access control
- **Input Sanitization**: XSS and injection prevention
- **Secure Token Management**: Prevents JWT exposure vulnerabilities
- **Message Visibility**: Public/private/agent-only filtering

### Enterprise Security Roadmap

- **SSO Integration**: SAML, OIDC, Active Directory
- **Audit Trails**: SOX, HIPAA-compliant logging
- **Data Governance**: Retention policies, geographic residency
- **Advanced Encryption**: At-rest and in-transit encryption

</details>

---

## 🔧 Technical Architecture

<details>
<summary>🔄 Deployment Architecture: Docker vs uvx</summary>

### Docker Deployment (Multi-Client Shared Context)

```
┌─────────────────┐    ┌──────────────────────┐
│   Claude Code   │───▶│                      │
├─────────────────┤    │  Shared HTTP Server  │
│     Cursor      │───▶│   (port 23456)       │
├─────────────────┤    │                      │
│    Windsurf     │───▶│  • Single database   │
└─────────────────┘    │  • Shared sessions   │
                       │  • Cross-tool memory │
                       └──────────────────────┘
```

**✅ Enables**: True multi-agent collaboration, session sharing, persistent context

### uvx Deployment (Isolated Per-Client)

```
┌─────────────────┐    ┌─────────────────┐
│   Claude Code   │───▶│ Isolated Server │
└─────────────────┘    │ + Database #1   │
                       └─────────────────┘
┌─────────────────┐    ┌─────────────────┐
│     Cursor      │───▶│ Isolated Server │
└─────────────────┘    │ + Database #2   │
                       └─────────────────┘
┌─────────────────┐    ┌─────────────────┐
│    Windsurf     │───▶│ Isolated Server │
└─────────────────┘    │ + Database #3   │
                       └─────────────────┘
```

**⚠️ Limitation**: No cross-tool collaboration, separate contexts, testing only

💡 **Key Insight**: Docker provides the "shared" in shared-context-server, while uvx creates isolated silos.

</details>

<details>
<summary>Core Design Principles</summary>

### Session-Based Isolation

**What**: Each collaborative task gets its own workspace
**Why**: Prevents cross-contamination while enabling rich collaboration within teams

### Message Visibility Controls

**What**: Four-tier system (public/private/agent-only/admin-only)
**Why**: Granular information sharing - agents can have private working memory and shared discoveries

### MCP Protocol Integration

**What**: Model Context Protocol compliance with automated orchestration prompts
**Why**: Works with any MCP-compatible framework with built-in multi-agent collaboration patterns

### Advanced Orchestration Features

**What**: MCP prompts with parallel agent launches, token refresh patterns, and collaborative documentation
**Why**: Enables true conversational collaboration vs sequential monologues

</details>

<details>
<summary>Performance Characteristics</summary>

### Designed for Real-Time Collaboration

- **<30ms** message operations for smooth agent handoffs
- **2-3ms** fuzzy search across session history
- **20+ concurrent agents** per session
- **Session continuity** during agent switches

💡 **Why these targets?** Sub-30ms ensures imperceptible delays during agent handoffs, maintaining workflow momentum.

### Scalability Considerations

- **SQLite**: Development and small teams (<5 concurrent agents)
- **PostgreSQL**: Production deployments (20+ concurrent agents)
- **Connection pooling**: Built-in performance optimization
- **Multi-level caching**: >70% cache hit ratio for common operations

</details>

<details>
<summary>Database & Storage</summary>

### Architecture Decision: Database Choice

**SQLite for Development**

- ✅ Zero configuration
- ✅ Perfect for prototyping
- ❌ Single writer limitation

**PostgreSQL for Production**

- ✅ Multi-writer concurrency
- ✅ Enterprise backup/recovery
- ✅ Advanced indexing and performance
- ❌ Requires database administration

**Database Backend**

- **Unified**: SQLAlchemy Core (supports SQLite, PostgreSQL, MySQL)
- **Development**: SQLite with aiosqlite driver (fastest, simplest)
- **Production**: PostgreSQL/MySQL with async drivers (scalable, robust)

**Migration Path**: SQLAlchemy backend provides smooth transition to PostgreSQL when scaling needs arise.

💡 **Why this hybrid approach?** Optimizes for developer experience during development while supporting enterprise scale in production.

</details>

---

## 📖 Documentation & Next Steps

### 🟢 Getting Started Paths

- **[Integration Guide](./docs/integration-guide.md)** - CrewAI, AutoGen, LangChain examples
- **[Quick Reference](./docs/quick-reference.md)** - Commands and common tasks
- **[Development Setup](./docs/development.md)** - Local development environment

### 🟡 Production Deployment

- **[Docker Setup](./DOCKER.md)** - Container deployment guide
- **[API Reference](./docs/api-reference.md)** - All 15+ MCP tools with examples
- **[Troubleshooting](./docs/troubleshooting.md)** - Common issues and solutions

### 🔴 Advanced Topics

- **[Custom Integration](./docs/integration-guide.md#custom-agent-integration)** - Build your own MCP integration
- **[Production Deployment](./docs/production-deployment.md)** - Docker and scaling strategies

**All documentation**: [Documentation Index](./docs/README.md)

---

## 🚀 Development Commands

```bash
make help        # Show all available commands
make dev         # Start development server with hot reload
make test        # Run tests with coverage
make quality     # Run all quality checks
make docker      # Production Docker (GHCR image) → shows logs
make dev-docker  # Development Docker (local build + hot reload) → shows logs
# ⚠️ Both commands show live logs - press Ctrl+C to exit and continue setup
```

### SCS Setup Commands

```bash
scs setup                    # Basic setup: generate keys, create .env, show deployment options
scs setup demo               # 🎪 Create complete demo environment with expert agents
scs setup docker            # Generate keys + show Docker commands only
scs setup uvx                # Generate keys + show uvx commands only
scs setup export json       # Create .env file + export keys as JSON to stdout
```

💡 **For first-time users**: `scs setup demo` creates everything needed for the multi-expert collaboration experience.

<details>
<summary>⚙️ Direct commands without make</summary>

```bash
# Development
uv sync && uv run python -m shared_context_server.scripts.dev

# Testing
uv run pytest --cov=src

# Quality checks
uv run ruff check && uv run mypy src/
```

</details>

---

## License

MIT License - Open source software for the AI community.

---

_Built with modern Python tooling and MCP standards. Contributions welcome!_
