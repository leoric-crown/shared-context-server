# MCP Toolkit Architecture

Practical guide for MCP tool integration in the Claude Multi-Agent Framework, based on production patterns from the shared context server implementation.

## Essential MCP Tools

### Shared Context Server (Core Coordination)

- **Purpose**: Multi-agent collaboration and session-based memory
- **Key Tools**: `create_session`, `add_message`, `set_memory`, `search_context`
- **Usage**: Session coordination, agent handoffs, progress tracking

### Research Tools

- **Crawl4AI**: Documentation scraping (`mcp__crawl4ai__md`)
- **Octocode**: GitHub code search (`mcp__octocode__githubSearchCode`)
- **Brave Search**: Web research (`mcp__brave-search__brave_web_search`)
- **Sequential Thinking**: Complex analysis (`mcp__sequential-thinking__sequentialthinking`)

### Development Tools

- **Pieces**: Long-term memory (`mcp__pieces__ask_pieces_ltm`, `mcp__pieces__create_pieces_memory`)
- **Playwright**: Browser automation (`mcp__playwright__browser_*`)
- **GitHub**: Repository management (`mcp__github__*`)
- **Semgrep**: Security analysis (`mcp__semgrep__*`)

## Shared Context Server Production Implementation

Based on the working shared context server implementation:

### Authentication & Sessions

```python
# Create session for feature development
session = await create_session({
    "purpose": "Feature: User authentication system",
    "metadata": {"complexity": "moderate"}
})

# Agent coordination through messages
await add_message(session_id, {
    "content": "Research complete: OAuth2 patterns identified",
    "visibility": "public",  # All agents see
    "metadata": {"phase": "research", "completion": 100}
})
```

### Memory Management

```python
# Session-scoped memory for immediate coordination
await set_memory("implementation_status", {
    "auth_endpoints": "complete",
    "token_validation": "in_progress"
}, session_id=session_id)

# Global memory for cross-project patterns
await set_memory("architecture_patterns", {
    "auth_pattern": "JWT with refresh tokens",
    "database_pattern": "SQLAlchemy with async"
}, session_id=None)  # Global scope
```

### Search & Context Retrieval

```python
# Fuzzy search with RapidFuzz (2-3ms performance)
results = await search_context(session_id, "authentication implementation", {
    "fuzzy_threshold": 70,
    "limit": 10
})

# Agent-specific context filtering
dev_updates = await search_by_sender(session_id, "developer_agent")
```

## Pieces Long-Term Memory Integration

### Memory Creation

```python
await create_pieces_memory({
    "summary_description": "OAuth2 Authentication Implementation",
    "summary": """
    ## Implementation Summary
    Successfully implemented OAuth2 with JWT tokens and refresh rotation.

    ## Key Decisions
    - Framework: FastAPI with python-jose
    - Security: PKCE flow + state parameter
    - Storage: Redis for session management
    """,
    "project": "/Users/username/myproject",
    "files": ["src/auth/oauth.py", "tests/test_auth.py"],
    "externalLinks": ["https://datatracker.ietf.org/doc/html/rfc7636"]
})
```

### Context Retrieval

```python
patterns = await ask_pieces_ltm({
    "question": "How did we implement OAuth2 in previous projects?",
    "topics": ["authentication", "oauth2", "fastapi"],
    "related_questions": [
        "What security patterns worked?",
        "What testing strategies were effective?"
    ]
})
```

## Core Command Memory Strategy

**3 checkpoints per command for comprehensive knowledge preservation:**

### `/plan-feature` Memory Checkpoints

**START**: Load similar patterns from Pieces + check session context

```python
similar_patterns = await ask_pieces_ltm({
    "question": f"How have we implemented {feature_category} features?",
    "topics": ["feature-planning", project_tech_stack],
})
session_context = await search_context(session_id, f"feature planning {feature_name}")
```

**MID**: Store research findings in session memory

```python
await set_memory("research_findings", {
    "documentation_patterns": crawl4ai_results,
    "similar_implementations": octocode_results,
    "architectural_decisions": sequential_thinking_analysis
}, session_id=session_id)
```

**END**: Preserve knowledge in Pieces + archive session

```python
await create_pieces_memory({
    "summary_description": f"Feature Planning: {feature_name}",
    "summary": f"Requirements: {requirements}\nDecisions: {decisions}",
    "project": current_project_path,
    "files": [f"PRPs/1-planning/{feature_name}/"]
})
```

### `/create-prp` Memory Checkpoints

**START**: Load planning context + PRP patterns

```python
planning_context = await get_memory("planning_complete", session_id=session_id)
prp_patterns = await ask_pieces_ltm({
    "question": f"What PRP structures worked for {feature_category}?",
    "topics": ["prp-creation", "implementation-planning"]
})
```

**MID**: Store PRP structure decisions

```python
await set_memory("prp_structure", {
    "task_breakdown": task_list,
    "agent_assignments": agent_roles,
    "quality_gates": validation_criteria
}, session_id=session_id)
```

**END**: Document PRP in Pieces

```python
await create_pieces_memory({
    "summary_description": f"PRP: {feature_name} Implementation Plan",
    "summary": f"Tasks: {tasks}\nCoordination: {workflow}",
    "files": [f"PRPs/2-prps/{feature_name}.md"]
})
```

### `/run-prp` Memory Checkpoints

**START**: Load PRP context + implementation patterns

```python
prp_context = await get_memory("prp_ready", session_id=session_id)
implementation_patterns = await ask_pieces_ltm({
    "question": f"How have we implemented {feature_category} features?",
    "topics": ["implementation", project_tech_stack]
})
```

**MID**: Track progress coordination

```python
await set_memory("implementation_progress", {
    "completed_tasks": completed_list,
    "active_agents": agent_status,
    "test_results": test_status
}, session_id=session_id)
```

**END**: Archive complete implementation

```python
await create_pieces_memory({
    "summary_description": f"Feature Complete: {feature_name}",
    "summary": f"Implementation: {overview}\nLessons: {insights}",
    "files": all_modified_files,
    "externalLinks": [f"PRPs/3-completed/{feature_name}.md"]
})
```

## Memory Strategy Benefits

### Immediate Coordination (Shared Context Server)

- Real-time agent handoffs with \<30ms message operations
- Session continuity if interrupted
- Cross-agent visibility with 4-tier permissions

### Long-term Intelligence (Pieces)

- Pattern recognition across projects
- Never lose implementation insights
- Cross-project learning

### Checkpoint Advantages

- **START**: Load relevant context, avoid reinventing
- **MID**: Coordinate progress, enable handoffs
- **END**: Preserve knowledge, establish patterns

This dual memory approach ensures both immediate productivity and long-term intelligence.
