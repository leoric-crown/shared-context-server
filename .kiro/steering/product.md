# Product Overview

## What is Shared Context MCP Server?

A centralized memory store enabling multiple AI agents (Claude, Gemini, etc.) to collaborate on complex tasks through shared conversational context using the Model Context Protocol (MCP).

## Core Value Proposition

**Multi-Agent Collaboration**: Enables AI agents to work together on complex projects by sharing context, maintaining state, and coordinating activities through a centralized blackboard architecture.

## Key Features

### Three-Tier Memory System
- **Public Context**: Shared workspace visible to all agents (blackboard pattern)
- **Private Notes**: Agent-specific scratchpad for internal reasoning
- **Agent Memory**: Persistent key-value store with TTL support and scope management

### MCP-Native Integration
- Sessions exposed as MCP resources (`session://{id}`)
- Real-time updates via resource subscriptions
- 15+ operational MCP tools for session and memory management
- Standard MCP authentication and security

### Production-Ready Architecture
- **Performance**: <10ms session creation, <20ms message ops, <30ms queries
- **Concurrency**: 20+ concurrent agents with SQLite WAL mode
- **Security**: JWT authentication, role-based permissions, audit logging
- **Reliability**: Connection pooling, multi-level caching, comprehensive error handling

## Target Users

### Primary: AI Agent Developers
- Building multi-agent systems with Claude, Gemini, or custom agents
- Need shared context and coordination between agents
- Require persistent memory across agent interactions

### Secondary: Development Teams
- Using AI agents for code development, testing, and documentation
- Need agents to collaborate on complex projects
- Want audit trails and session management

## Use Cases

### Software Development
- **Code Review**: Multiple agents collaborate on reviewing pull requests
- **Feature Development**: Agents coordinate on planning, implementation, and testing
- **Documentation**: Agents share context while generating and updating docs

### Multi-Agent Workflows
- **AutoGen Integration**: Persistent memory for multi-agent conversations
- **CrewAI Coordination**: Role-based agent crews with shared context
- **LangChain Workflows**: Multi-agent workflows with persistent memory

### Research and Analysis
- **Information Gathering**: Agents share findings and build on each other's work
- **Report Generation**: Collaborative document creation with multiple perspectives
- **Data Analysis**: Agents coordinate on complex analytical tasks

## Current Status

**Phase 4 Complete: Production Ready**
- ✅ 443 tests with 85%+ coverage across all modules
- ✅ Performance optimization with connection pooling and caching
- ✅ Complete API documentation with 12+ MCP tools
- ✅ Integration guides for AutoGen, CrewAI, LangChain
- ✅ Security implementation with JWT and audit logging
- ✅ Production deployment guides for Docker/Kubernetes

## Competitive Advantages

1. **MCP-Native**: Built specifically for the Model Context Protocol standard
2. **Multi-Agent Focus**: Designed from ground up for agent collaboration
3. **Privacy Controls**: Sophisticated visibility system for agent privacy
4. **Performance**: Optimized for real-time multi-agent interactions
5. **Production Ready**: Comprehensive testing, monitoring, and deployment support

## Technical Foundation

- **Framework**: FastMCP (most Pythonic MCP implementation)
- **Database**: SQLite with WAL mode for concurrent access
- **Search**: RapidFuzz for 5-10x faster fuzzy search
- **Caching**: Multi-level TTL caching for performance
- **Security**: JWT tokens, input sanitization, audit logging
