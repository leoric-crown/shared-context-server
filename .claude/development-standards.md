# Development Rules & Standards

This document provides comprehensive development standards for **Shared Context MCP Server**, including code structure, testing, documentation, and integration guidelines.

## Code Structure & Modularity

### Critical File Size Limits
- **CRITICAL: Never exceed file size limits - 500 lines for code files, 1000 lines for test files.** If a file approaches these limits:
  - Split into logical modules immediately
  - Use the refactor agent for systematic decomposition
  - Extract utilities, helpers, and constants
  - Create sub-packages for complex components

### MCP Server Organization
For complex MCP server modules:
- `mcp_server.py` - FastMCP server setup and coordination logic (max 200 lines)
- `tools.py` - MCP tool definitions and handlers (max 300 lines)
- `resources.py` - MCP resource providers (max 200 lines)
- `database.py` - aiosqlite operations and schema (max 200 lines)
- `models.py` - Pydantic data models and validation (max 200 lines)

### Module Organization
- **Organize code into clearly separated modules**, grouped by feature or responsibility
- **Use clear, consistent imports** (prefer relative imports within packages)
- **Use established environment configuration patterns** for your technology stack

## Testing & Reliability

### Test Coverage Requirements ⚠️ **PHASE-SPECIFIC COVERAGE TARGETS**

**Coverage Progression Targets**:
- **Current Baseline**: 54% total coverage (Phase 1/2 complete)
- **Phase 3 Target**: ≥70% total coverage required before implementation
- **Phase 4 Target**: ≥85% total coverage required before implementation
- **Module-Specific Targets**:
  - `server.py`: 56% → 75%+ (Phase 3), 85%+ (Phase 4)
  - `models.py`: 59% → 80%+ (Phase 3), 85%+ (Phase 4)
  - `database.py`: 80% → maintain 85%+ (excellent coverage)
  - New modules: Must achieve 85%+ coverage in development phase

**Testing Requirements**:
- **Always create behavioral tests for new MCP tools and resources** using FastMCP TestClient
- **After updating any logic**, check whether existing tests need to be updated
- **Tests should live in a `/tests` folder** with pytest structure:
  - **Unit tests**: Fast, isolated tests for pure functions
  - **Integration tests**: FastMCP tool and resource testing
  - **Behavioral tests**: Multi-agent coordination scenarios
  - Include at least: expected use, edge case, failure case

**Coverage Validation Commands**:
```bash
# Phase 3 coverage validation
uv run pytest tests/ --cov=src --cov-report=html --cov-fail-under=70

# Phase 4 coverage validation
uv run pytest tests/ --cov=src --cov-report=html --cov-fail-under=85
```

### Multi-Agent Testing Integration
- **MCP server tests should include multi-agent coordination scenarios** for behavior validation
- **Use FastMCP TestClient** for in-memory testing (100x faster than subprocess testing)
- **Session Isolation Testing**: Test concurrent agent access and proper isolation
- **UTC Timestamp Testing**: Verify consistent timestamp behavior across agents
- **Database Concurrency**: Test aiosqlite connection pooling under concurrent access

### Code Quality Enforcement ⚠️ **MANDATORY QUALITY GATES**

**Phase-Based Quality Requirements**:
- **Phase 3 (Multi-Agent)**: Must achieve ≥70% test coverage before implementation
- **Phase 4 (Production)**: Must achieve ≥85% test coverage before implementation
- **All Phases**: Zero linting errors and zero type checking errors required

**Mandatory Quality Commands** ⚠️ **MUST PASS BEFORE ANY PHASE**:
```bash
uv run ruff check .     # MANDATORY: Zero linting errors required
uv run mypy .           # MANDATORY: Zero type checking errors required
coverage report         # MANDATORY: Must achieve phase-specific coverage targets
```

**Quality Gate Enforcement**:
- **Run lint checks** with `ruff check --fix` and fix all blocking errors
- **Complexity warnings are non-blocking**: Note complexity issues but don't treat as blockers. **FIX ALL OTHER ERRORS**.
- **Consider refactoring**: Use complexity warnings as design feedback for potential improvements
- **Run type checks** with `mypy` and resolve all type annotations and errors
- **MANDATORY**: All agents that write code MUST validate lint and type compliance before checkpoints
- ❌ **Implementation MUST NOT proceed** if ruff check fails
- ❌ **Implementation MUST NOT proceed** if mypy type checking fails
- ❌ **Implementation MUST NOT proceed** if coverage is below phase targets
- ❌ **Phase completion MUST NOT be marked** until all quality gates pass

## Agent Transparency & Escalation Standards

### Structured Status Reporting Requirements
**All agents must return structured status objects after each significant phase:**

```json
{
  "status": "SUCCESS|BLOCKED|NEEDS_INPUT|ARCHITECTURE_ISSUE|ERROR",
  "completed_tasks": ["specific tasks completed"],
  "blocked_on": "exact issue preventing progress",
  "files_modified": ["absolute file paths"],
  "research_used": ["context sources referenced"],
  "escalation_reason": "why user intervention needed",
  "next_steps": ["recommended actions"],
  "checkpoint_reached": "phase completion status"
}
```

### Universal Escalation Triggers
**Agents must STOP and escalate (never work around) when encountering:**

#### Critical Issues (Immediate Escalation)
- **Architecture Flaws**: Design issues requiring user decisions or major changes
- **Security Concerns**: Any security-related issues requiring user approval
- **Data Loss Risk**: Operations that could compromise data integrity
- **File Size Violations**: Code exceeding limits (500 lines code, 1000 lines tests) before refactoring
- **Integration Failures**: Components that fundamentally don't work together

#### Quality Issues (Escalate After Initial Investigation)
- **Test Failures**: Fundamental logic errors indicating deeper problems (not simple bugs)
- **Dependency Conflicts**: Missing dependencies that agents cannot resolve
- **Performance Issues**: Code changes causing significant performance degradation
- **Breaking Changes**: Changes that break existing APIs or functionality

#### Research & Context Issues (Escalate When Research Insufficient)
- **Insufficient Context**: Critical information missing that affects implementation decisions
- **Contradictory Requirements**: Conflicting specifications that need user clarification
- **Technology Gaps**: Technologies or patterns not covered in established tech guides

### Agent Coordination Patterns

#### Single Agent Tasks (Direct Execution)
- **Simple MCP features** affecting 1-3 files
- **Bug fixes** with clear scope
- **API documentation updates**
- **Refactoring** within single MCP tools or resources

#### Multi-Agent Coordination (task-coordinator)
- **Complex MCP features** affecting 4+ files
- **Multi-agent coordination features**
- **Database schema modifications**
- **Features requiring multiple specializations (dev + test + docs)

## Integration & Architecture Standards

### MCP Server Integration Requirements
- All features must integrate with FastMCP server architecture patterns
- Maintain consistency with established aiosqlite and async/await approaches
- Support multi-agent coordination through shared sessions and proper isolation
- Use UTC timestamps for all time-based functionality (multi-agent coordination critical)

### Agent Memory Integration Pattern
- Use established three-tier memory architecture (public context, private notes, agent memory)
- Implement TTL expiration and memory fallback handling
- Ensure agent memory isolation and proper context sharing
- Include comprehensive multi-agent coordination testing

### Quality Integration Pattern
- Use existing quality infrastructure
- Follow established testing patterns
- Maintain code style and structure consistency
- Preserve context for future development

## Documentation Standards

### User-Facing Documentation Requirements
- **API Documentation**: Always include working examples
- **User Guides**: Step-by-step workflows for new features
- **Error Documentation**: Common issues and solutions
- **Integration Examples**: How features work with existing system

### Technical Documentation Requirements
- **Architecture Decisions**: Document significant architectural choices
- **Integration Patterns**: How components work together
- **Testing Approaches**: Explain testing strategies and patterns
- **Development Setup**: Keep setup instructions current

## Technology Stack Guidelines

### FastMCP Framework Patterns
- Follow established patterns for FastMCP server development (see `.claude/tech-guides/framework-integration.md`)
- Use FastMCP-specific best practices for tool and resource organization
- Leverage FastMCP TestClient for testing and validation
- Maintain consistency with async/await and Pydantic validation conventions

### External Service Integration
- Use consistent patterns for external service communication (refer to `.claude/tech-guides/error-handling.md`)
- Implement proper error handling and circuit breaker patterns
- Include appropriate timeout and retry logic for multi-agent scenarios
- Use httpx-based mocking for external service testing

### Performance Standards
- Database operations should use connection pooling (aiosqlite with WAL mode)
- Multi-agent coordination should not block individual agent operations
- Background processing should not interfere with agent workflows
- Memory usage should be reasonable for concurrent agent access patterns

## Success Criteria

### Code Quality Success ⚠️ **PHASE-SPECIFIC QUALITY STANDARDS**
- **All lint and type checks pass without warnings** (mandatory for all phases)
- **File size limits are respected** (500 lines code, 1000 lines tests)
- **Tests achieve phase-specific coverage targets**: 70% (Phase 3), 85% (Phase 4)
- **Code follows established patterns and conventions**
- **Performance benchmarks met** (Phase 4: <100ms API, 20+ agents, >70% cache hit)
- **Quality gates enforced before phase progression**

### Integration Success
- Features work seamlessly with existing MCP tools and resources
- No regressions in existing functionality
- External service integration is robust and well-tested with circuit breakers
- Multi-agent coordination maintains proper session isolation and data consistency

### Documentation Success
- New MCP tools and resources have user-facing documentation with working examples
- API changes are documented with FastMCP TestClient examples
- Multi-agent coordination patterns are clearly explained
- Setup and development docs remain current with dependency updates

Remember: **Quality over speed, simplicity over complexity, working solutions over elegant plans**. When in doubt, escalate for user guidance rather than making assumptions about requirements or architecture.
