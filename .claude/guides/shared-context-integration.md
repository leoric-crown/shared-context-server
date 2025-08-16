# Shared Context Server Integration

This guide provides patterns for integrating with the Shared Context Server for multi-agent collaboration through persistent memory and session-based coordination.

## Core Integration Principles

### Session-Based Collaboration

- Create dedicated sessions for each major development task or feature
- Use shared sessions to enable agents to build on each other's discoveries
- Implement agent handoff protocols through context preservation
- Maintain session isolation to prevent cross-task interference

### Multi-Agent Coordination

- Leverage shared context for incremental building instead of starting over
- Use visibility controls (public/agent_only/private) for strategic information sharing
- Implement context search to find relevant prior work instantly
- Store structured findings in session memory for future reference

## MCP Integration Patterns

### Basic Session Management

```python
# Agent workflow: Start shared session for task coordination
session = await client.post("/mcp/tool/create_session",
                          json={"purpose": "feature implementation: user authentication"})

# Add findings to shared context
await client.post("/mcp/tool/add_message",
                 json={
                     "session_id": session["session_id"],
                     "content": "Security analysis complete: Found SQL injection vulnerability in auth.py:42",
                     "visibility": "public"
                 })
```

### Agent Handoff Coordination

```python
# Previous agent shares context
await client.post("/mcp/tool/add_message",
                 json={
                     "session_id": session_id,
                     "content": "Developer agent findings: Implemented secure authentication with bcrypt hashing. Tests passing. Code ready for optimization review.",
                     "visibility": "agent_only"
                 })

# Next agent searches context before starting
search_results = await client.post("/mcp/tool/search_context",
                                 json={
                                     "session_id": session_id,
                                     "query": "authentication security implementation"
                                 })
```

### Memory Persistence Patterns

```python
# Store structured findings for complex coordination
await client.post("/mcp/tool/set_memory",
                 json={
                     "key": "architecture_decisions",
                     "value": {
                         "auth_pattern": "JWT with refresh tokens",
                         "security_measures": ["bcrypt", "rate_limiting", "CSRF_protection"],
                         "performance_optimizations": ["connection_pooling", "query_caching"]
                     },
                     "session_id": session_id
                 })
```

## Agent Integration Workflows

### Multi-Phase Development Coordination

#### Phase 1: Research & Analysis

```markdown
Agent: researcher
Action: Analyze requirements and gather context
Output: Research findings in shared session with tagged visibility

Session Message: "Research complete: Authentication requirements include OAuth2, MFA support, and session management. Security standards: OWASP compliance required."
```

#### Phase 2: Architecture & Design

```markdown
Agent: architect
Input: Search shared context for research findings
Action: Design system architecture with context awareness
Output: Architecture decisions stored in session memory

Session Message: "Architecture designed: JWT-based auth with Redis session store. Integrates with existing user management system. Security scan patterns implemented."
```

#### Phase 3: Implementation

```markdown
Agent: developer
Input: Load architecture decisions from session memory
Action: Implement with full context of previous findings
Output: Implementation progress with code references

Session Message: "Implementation 80% complete: Auth endpoints implemented, tests passing. Integration point: UserService.authenticate() updated to use new JWT flow."
```

#### Phase 4: Quality Assurance

```markdown
Agent: tester
Input: Search context for implementation details and security requirements
Action: Test with awareness of all previous findings
Output: Test results and validation

Session Message: "Testing complete: All security requirements validated. Performance tests show 50ms average response time. Edge cases for concurrent sessions handled."
```

### Context-Aware Error Resolution

#### Problem Discovery

```python
# Agent discovers issue and shares context
await add_message(session_id, {
    "content": "Error found: Database deadlock in concurrent authentication attempts. Affects user login under load.",
    "visibility": "public"
})
```

#### Solution Coordination

```python
# Multiple agents coordinate solution with shared context
# 1. Search for related context
related_context = await search_context(session_id, "authentication concurrent database")

# 2. Build on previous findings
await add_message(session_id, {
    "content": "Solution implemented: Added database connection pooling and retry logic. Based on architecture decision for Redis session store, also implemented session failover.",
    "visibility": "public"
})
```

## Framework Command Integration

### Session Initialization in Commands

```bash
# feature-planning.md - Initialize shared session
session_id=$(mcp_tool create_session '{"purpose": "Feature planning: [FEATURE_NAME]"}')
echo "Created shared session: $session_id"

# Add planning findings to shared context
mcp_tool add_message "{
    \"session_id\": \"$session_id\",
    \"content\": \"Planning complete: [FEATURE_DESCRIPTION]\",
    \"visibility\": \"public\"
}"
```

### Agent Coordination Patterns

```bash
# execute-prp.md - Use shared context for agent coordination
# Load previous context before starting
context_search=$(mcp_tool search_context "{
    \"session_id\": \"$session_id\",
    \"query\": \"architecture implementation progress\"
}")

# Store coordination findings
mcp_tool set_memory "{
    \"key\": \"coordination_checkpoints\",
    \"value\": {\"phase\": \"implementation\", \"agents_involved\": [\"developer\", \"tester\"]},
    \"session_id\": \"$session_id\"
}"
```

## Performance Optimization

### Context Search Efficiency

- Use specific query terms for faster context retrieval (2-3ms response time)
- Leverage RapidFuzz fuzzy search for finding related context
- Implement context caching for frequently accessed patterns
- Use visibility filters to scope searches appropriately

### Session Management

- Create new sessions for distinct development tasks
- Clean up completed sessions to maintain performance
- Use session-scoped memory for task-specific coordination
- Implement automatic session archival for long-running projects

### Memory Management

```python
# Efficient memory patterns for large projects
await set_memory("current_sprint_goals", sprint_data, session_id=session_id, expires_in=604800)  # 1 week
await set_memory("architecture_patterns", arch_data, session_id=None)  # Global, permanent
```

## Integration with Agent Templates

### Agent Template Enhancement

```yaml
# Enhanced agent template with shared context integration
---
name: context-aware-developer
description: Implementation specialist with shared context coordination. Use proactively for development tasks requiring multi-agent context.
tools: Read, Edit, Bash, mcp__shared-context-server__search_context, mcp__shared-context-server__add_message
---

You are a context-aware development agent that leverages shared session memory.

Before starting any task:
1. Search shared context for relevant prior work
2. Load session memory for architecture decisions
3. Coordinate with findings from other agents

When completing tasks:
1. Share significant findings in session context
2. Store structured decisions in session memory
3. Tag handoff points for subsequent agents

Integration patterns:
- Use search_context before implementing to avoid duplicating work
- Use add_message to share progress and findings
- Use set_memory for decisions that affect future development
```

## Best Practices

### Context Organization

- Use descriptive session purposes for easy identification
- Implement consistent tagging for different types of findings
- Structure memory keys hierarchically (e.g., `architecture.auth.jwt_config`)
- Use visibility controls strategically (public for handoffs, agent_only for coordination)

### Agent Coordination

- Start each agent task with context search
- End each agent task with findings sharing
- Use memory for persistent decisions across long-running sessions
- Implement explicit handoff protocols between agent types

### Session Lifecycle

- Initialize sessions at the start of feature development
- Maintain session continuity throughout multi-phase work
- Archive completed sessions with summary findings
- Clean up experimental or abandoned sessions

## Success Criteria

### Effective Multi-Agent Collaboration

- Agents build incrementally on each other's discoveries
- Context is preserved across agent handoffs
- No duplication of research or implementation work
- Coordinated decision-making with full context awareness

### Performance Efficiency

- Fast context search and retrieval (\<30ms)
- Efficient session management without memory bloat
- Smart caching for frequently accessed patterns
- Optimal memory usage for long-running projects

### Framework Integration Success

- Seamless integration with existing agent workflows
- Enhanced coordination without workflow disruption
- Improved quality through context-aware decision making
- Measurable reduction in duplicate work across agents

Remember: **Shared context enables intelligence through coordination**. Use the server as the memory substrate that allows agents to build on each other's work rather than starting from scratch.
