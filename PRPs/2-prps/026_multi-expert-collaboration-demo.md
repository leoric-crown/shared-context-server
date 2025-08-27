# PRP-001: Multi-Expert Collaboration Demo

---
session_id: session_6cd47d370a2245d9
session_purpose: "PRP creation: Multi-Expert Collaboration Demo for shared-context-server 1.1.9 release"
created_date: 2025-08-27T03:35:00.000000+00:00
stage: "2-prps"
planning_source: PRPs/1-planning/1.1.9.1-multi-expert-demo/
planning_session_id: session_dd6ade04de0349ed
---

## Research Context & Architectural Analysis

### Research Integration
**Planning Foundation**: Comprehensive analysis from `PRPs/1-planning/1.1.9.1-multi-expert-demo/` including:
- **"3 Amigo Agents" Pattern**: Performance Architect → Implementation Expert → Validation Expert (coined by George Vetticaden)
- **Zero-Setup Philosophy**: Docker + pre-configured .env.demo + auto-approved MCP tools
- **Personal Project Focus**: Immediate user value through analysis of their own repositories
- **MCP Integration Research**: octocode for GitHub analysis, shared-context-server for coordination

**Framework Integration**:
- Proven YAML frontmatter + system prompt structure from Claude Code best practices
- "PROACTIVELY" keyword for autonomous agent delegation
- Sonnet model optimization for development-focused demo agents
- Visible handoff patterns crucial for demo success

### Architectural Scope
**Component Integration**: Clean addition leveraging existing infrastructure:
- **Docker Infrastructure**: Production-ready compose configuration with health checks
- **Authentication System**: JWT-based with role-based access control already implemented
- **MCP Tools**: All required coordination tools available (create_session, add_message, authenticate_agent)
- **HTTP Transport**: Stable endpoint at :23432/mcp/ with API key authentication

**Existing Patterns**:
- FastMCP server foundation with lazy loading optimization
- SQLAlchemy database with persistent volumes
- Environment variable templating in docker-compose.yml
- Auto-approval MCP configuration patterns

## Implementation Specification

### Core Requirements
**Primary Deliverable**: Complete `examples/demos/multi-expert-optimization/` directory showcase that transforms shared-context-server from "coordination infrastructure" into "AI expert committee optimizing real code."

**Essential Components**:
1. **Expert Persona Files** (.claude/agents/*.md):
   - performance-architect.md: Bottleneck analysis and optimization strategy design
   - implementation-expert.md: Code pattern analysis and concrete solution implementation
   - validation-expert.md: Testing strategy and success criteria development

2. **Zero-Friction Setup**:
   - README.md with clone → copy → run → wow instructions
   - .env.demo with safe demo credentials
   - demo.mcp.json with HTTP transport + auto-approvals pre-configured

3. **Demo Presentation Materials**:
   - demo-script.md with timing, talking points, and user prompts
   - Clear troubleshooting section for common auth/setup issues

### Integration Points
**MCP Server Coordination**:
- **shared-context-server**: Session management, agent authentication, coordination
- **octocode-mcp**: GitHub repository analysis and code pattern discovery
- **HTTP Transport**: API key authentication with auto-approved tool sets

**Docker Integration**:
- Leverages existing ghcr.io/leoric-crown/shared-context-server:latest image
- Uses established environment variable templating
- No modifications to core docker-compose.yml required

### Data Model Changes
**No database changes required** - leverages existing:
- Session management with UUID isolation
- Agent authentication with persistent agent_id memory
- Message storage with visibility controls (public/private/agent_only)
- Memory persistence for expert knowledge accumulation

### Interface Requirements
**User Interaction Pattern**:
```markdown
User Input: "I want to optimize this repository using our expert committee approach.
Please start by having our Performance Architect analyze the codebase for bottlenecks
and optimization opportunities."

Expected Flow:
1. Performance Architect (3 min): Repository analysis with octocode integration
2. Implementation Expert (3 min): Concrete solutions based on architect findings
3. Validation Expert (2 min): Testing strategy and success criteria
4. Visible Coordination: Session messages show expert handoffs and knowledge building
```

**Demo Success Interface**: 5-minute experience showing:
- Autonomous expert coordination through shared sessions
- Personal project analysis with immediately actionable insights
- Clear ROI demonstration (3 coordinated experts vs single agent)

## Quality Requirements

### Testing Strategy
**Phase-Based Validation**:

**Phase 1 - Infrastructure Testing**:
- Docker setup verification (docker compose up → health check passes)
- MCP connection testing (shared-context-server + octocode both connect)
- GitHub authentication validation (gh auth status or GITHUB_TOKEN test)

**Phase 2 - Expert Coordination Testing**:
- Individual persona testing with real repositories
- Inter-expert handoff validation through shared sessions
- Autonomous delegation verification ("PROACTIVELY" keyword functionality)
- Memory persistence testing (agent_id consistency across sessions)

**Phase 3 - Demo Flow Testing**:
- Complete zero-setup experience (clone → copy → run)
- Multiple repository types (personal projects, popular open source)
- Fallback scenario testing (self-analysis without GitHub access)
- Timing validation (8-minute total demo including setup)

### Documentation Needs
**User-Facing Documentation**:
- README.md with zero-friction setup (30-second instructions)
- demo-script.md for consistent presentation experience
- Troubleshooting guide for GitHub auth and Docker issues

**Integration Documentation**:
- MCP configuration explanation (.mcp.json structure)
- Expert persona customization guidance
- Alternative use case documentation (popular repos, web audits)

### Performance Considerations
**Demo Performance Requirements**:
- Setup time: <30 seconds (clone, copy, docker up)
- Expert analysis time: <8 minutes total (3+3+2 minute expert phases)
- Session coordination: <30ms message operations (existing performance)
- Memory operations: <10ms per expert knowledge storage

**Resource Requirements**:
- Docker: 512MB memory, 0.5 CPU (existing limits)
- GitHub API: Standard rate limits (5000 requests/hour)
- MCP connections: 2 concurrent servers (shared-context + octocode)

## Coordination Strategy

### Recommended Approach: **Direct Implementation (cfw-developer)**
**Rationale**:
- **File Count**: Medium scope (8-12 files, clean addition to codebase)
- **Integration Complexity**: Low-medium (leverages existing infrastructure)
- **No Architectural Changes**: Uses established patterns and tools
- **Clear Deliverables**: Well-defined file creation with proven templates

### Implementation Phases
**Phase 1: Directory Structure & Core Configuration** (1 hour)
- Create examples/demos/multi-expert-optimization/ directory structure
- Copy and customize .env.demo with demo-safe credentials
- Configure demo.mcp.json with HTTP transport + auto-approvals
- Create foundational README.md structure

**Phase 2: Expert Persona Development** (2-3 hours)
- Develop performance-architect.md with:
  - Bundle analysis, render cycle review, database optimization focus
  - octocode integration for repository structure analysis
  - Session coordination with handoff to implementation expert
- Create implementation-expert.md with:
  - Code pattern analysis and concrete optimization proposals
  - Repository-specific solution development
  - Coordination with validation expert for testing approach
- Build validation-expert.md with:
  - Testing strategy based on actual tech stack analysis
  - Performance benchmarking and success criteria
  - Comprehensive expert committee summary

**Phase 3: Demo Materials & Validation** (1 hour)
- Complete demo-script.md with user prompts and timing guidance
- Add comprehensive troubleshooting to README.md
- Create sample coordination outputs (optional but valuable)
- Integration testing across multiple repository types

### Risk Mitigation
**Primary Risks & Mitigations**:
1. **GitHub Auth Failure During Demos**:
   - Self-analysis fallback (analyze shared-context-server itself)
   - Pre-tested credential examples in documentation
   - Clear auth troubleshooting in README.md

2. **Expert Coordination Appearing Chaotic**:
   - Clear demo script with timing expectations
   - Visible progress indicators through session messages
   - "PROACTIVELY" keyword for clean expert handoffs

3. **Setup Friction Killing Demo**:
   - Pre-configured .env.demo with safe dummy credentials
   - Docker health checks with clear error messages
   - 30-second setup requirement with fallback instructions

### Dependencies
**Prerequisites**:
- Docker and Docker Compose installed
- Node.js for octocode-mcp execution
- GitHub authentication (gh CLI or GITHUB_TOKEN)

**Integration Requirements**:
- No changes to shared-context-server core code
- Compatible with existing docker-compose.yml configuration
- Uses established MCP tool auto-approval patterns

## Success Criteria

### Functional Success
**Core Behaviors That Must Work**:
- ✅ **Zero-Setup Experience**: `git clone → cp .env.demo .env → docker compose up → open Claude Code` works in <30 seconds
- ✅ **Expert Coordination**: Performance Architect → Implementation Expert → Validation Expert handoffs through shared sessions
- ✅ **Repository Analysis**: octocode integration provides real GitHub repository insights
- ✅ **Autonomous Operation**: Experts coordinate without manual routing using "PROACTIVELY" delegation
- ✅ **Persistent Memory**: agent_id consistency maintains expert knowledge across demo sessions

### Integration Success
**System Integration Validation**:
- ✅ **MCP Transport**: HTTP endpoint at :23432/mcp/ with API key authentication functions reliably
- ✅ **Docker Integration**: Uses existing production image without core code modifications
- ✅ **Tool Auto-Approval**: Pre-configured .mcp.json enables smooth coordination without permission prompts
- ✅ **Fallback Scenarios**: Self-analysis works when GitHub authentication unavailable
- ✅ **Multi-Repository Support**: Works with personal projects, popular open source, and shared-context-server itself

### Quality Gates
**Testing & Validation Requirements**:
- ✅ **Infrastructure Testing**: Docker setup, MCP connections, GitHub auth all validated
- ✅ **Coordination Testing**: Expert handoffs and shared session knowledge building verified
- ✅ **Demo Flow Testing**: Complete 5-8 minute demo experience with multiple repository types
- ✅ **Documentation Completeness**: README.md enables successful setup by new users
- ✅ **Performance Targets**: <30s setup, <8min expert analysis, <30ms session operations

**Release Readiness Criteria**:
- All expert personas tested with real repository analysis
- Demo script provides consistent presentation experience
- Troubleshooting documentation covers common failure scenarios
- Integration with shared-context-server 1.1.9 release materials complete

---

**Implementation Recommendation**: Assign to cfw-developer agent for direct implementation following the three-phase approach outlined above. The clear scope, established patterns, and existing infrastructure make this suitable for focused development rather than task-coordinator orchestration.

**Estimated Implementation Time**: 3-5 hours total across all phases with integration testing.

**Next Step**: Execute this PRP using `execute-prp` command with cfw-developer agent coordination.
