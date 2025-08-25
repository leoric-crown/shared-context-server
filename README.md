# Shared Context Server

[![CI](https://github.com/leoric-crown/shared-context-server/workflows/CI/badge.svg)](https://github.com/leoric-crown/shared-context-server/actions)
[![Docker](https://github.com/leoric-crown/shared-context-server/workflows/Build%20and%20Publish%20Docker%20Image/badge.svg)](https://github.com/leoric-crown/shared-context-server/actions)
[![GHCR](https://img.shields.io/badge/ghcr.io-leoric--crown%2Fshared--context--server-blue?logo=docker)](https://github.com/leoric-crown/shared-context-server/pkgs/container/shared-context-server)
[![codecov](https://codecov.io/gh/leoric-crown/shared-context-server/graph/badge.svg?token=07ZITBOAZ7)](https://codecov.io/gh/leoric-crown/shared-context-server)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Trigger CI after GitHub Actions infrastructure issues -->

## Content Navigation

| Symbol | Meaning | Time Investment |
|--------|---------|----------------|
| 🚀 | Quick start | 2-5 minutes |
| ⚙️ | Configuration | 10-15 minutes |
| 🔧 | Deep dive | 30+ minutes |
| 💡 | Why this works | Context only |
| ⚠️ | Important note | Read carefully |

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

---

## 🚀 Try It Now (2 minutes)

### One-Command Docker Setup

```bash
docker run -d --name shared-context-server -p 23456:23456 \
  -e API_KEY="$(openssl rand -base64 32)" \
  -e JWT_SECRET_KEY="$(openssl rand -base64 32)" \
  -e JWT_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" \
  ghcr.io/leoric-crown/shared-context-server:latest
```

### Quick Test
```bash
# Connect with Claude Code
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]}'
claude mcp list  # Should show: ✓ Connected

# View the dashboard
open http://localhost:23456/ui/  # Real-time session monitoring
```

### 📊 Web Dashboard (MVP)
Real-time monitoring interface for agent collaboration:
- **Live session overview** with active agent counts
- **Real-time message streaming** without page refreshes
- **Session isolation visualization** to track multi-agent workflows
- **Performance monitoring** for collaboration efficiency

💡 **Perfect for**: Monitoring agent handoffs, debugging collaboration flows, and demonstrating multi-agent coordination to stakeholders.

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
```python
# Via Claude Code or any MCP client
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]}'

# Direct API usage
import httpx
client = httpx.AsyncClient()
session = await client.post("http://localhost:23456/mcp/tool/create_session",
                           json={"purpose": "agent collaboration"})
```

⚠️ **Framework Integration Status**: Direct MCP protocol tested. CrewAI, AutoGen, and LangChain integrations are conceptual - we welcome community contributions to develop and test these patterns.

**➡️ Next**: [MCP Integration Examples](./docs/integration-guide.md)

---

## ⚙️ Framework Examples

### Code Review Pipeline
1. **Security Agent** finds vulnerabilities → shares findings
2. **Performance Agent** builds on security context → optimizes safely
3. **Documentation Agent** documents complete solution

💡 **Why this works**: Each agent builds on discoveries instead of duplicating work.

### Research & Implementation
1. **Research Agent** gathers requirements → shares insights
2. **Architecture Agent** designs using research → documents decisions
3. **Developer Agent** implements with full context

**More examples**: [Collaborative Workflows Guide](./docs/integration-guide.md#collaborative-workflows)

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
<summary>Core Design Principles</summary>

### Session-Based Isolation
**What**: Each collaborative task gets its own workspace
**Why**: Prevents cross-contamination while enabling rich collaboration within teams

### Message Visibility Controls
**What**: Four-tier system (public/private/agent-only/admin-only)
**Why**: Granular information sharing - agents can have private working memory and shared discoveries

### MCP Protocol Integration
**What**: Model Context Protocol compliance for universal compatibility
**Why**: Works with any MCP-compatible framework without custom integration code

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
make help    # Show all available commands
make dev     # Start development server with hot reload
make test    # Run tests with coverage
make quality # Run all quality checks
```

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
