# PRP-001: MCP Resources, Prompts & Templates Enhancement

---
session_id: session_2a15d8946bdc442e
session_purpose: "PRP creation: MCP Resources, Prompts & Templates Enhancement v1.1.1"
created_date: 2025-08-25T22:54:00.000Z
stage: "2-prps"
target_release: "1.1.1"
planning_source: PRPs/1-planning/1.1.1-mcp-enhancement/mcp-resources-prompts-templates-enhancement.md
planning_session_id: session_736d275a2551468f
complexity_assessment: moderate
recommended_agent: cfw-developer
---

## Research Context & Architectural Analysis

### Research Integration

**MCP Ecosystem Validation (August 2025)**:
- **Client Support Reality**: Claude Code and VS Code v1.102+ provide full MCP resource/prompt support via `@mentions` and `/mcp` commands
- **Production Server Analysis**: Paws-on-MCP demonstrates viability with 15 resources, 14 prompts, proving client ecosystem maturation
- **Strategic Timing**: Most production servers remain tool-focused, creating early adopter advantage opportunity

**Authentication Architecture Validation**:
- **Dual-Token System**: API Key (MCP headers) + JWT Token (agent permissions) - MCP-compliant pattern
- **JWT-Aware Resources**: Validated as following MCP security model with proper permission boundaries
- **Context Extraction**: FastMCP Context injection patterns established in existing `admin_resources.py`

**FastMCP Integration Research**:
- **Resource Pattern**: `@mcp.resource()` decorator with context parameter `ctx: Any = None`
- **Prompt Pattern**: `@mcp.prompt()` decorator with parameter validation and autocompletion
- **Registration System**: Modular approach in `core_server.py:139-158` supports easy extension

### Architectural Scope

**Current State Analysis**:
- ✅ **15 MCP Tools**: Comprehensive multi-agent coordination coverage
- ❌ **0 Resources**: No agent discovery capability through MCP primitives
- ❌ **0 Prompts**: No user-facing workflow automation
- ⚠️ **2 Basic Templates**: Limited dynamic resource access patterns

**Integration Points Identified**:
- `src/shared_context_server/core_server.py:139-158` - Tool registration system ready for extension
- `src/shared_context_server/admin_resources.py:136-416` - Resource patterns and JWT context handling established
- **ResourceNotificationManager**: Real-time update system already implemented for new resources

### Existing Patterns to Leverage

**JWT Context Handling** (`admin_resources.py:146-153`):
```python
# Extract agent_id from MCP context
if ctx is not None:
    agent_id = getattr(ctx, "agent_id", None)
    if agent_id is None:
        agent_id = f"agent_{ctx.session_id[:8]}"
```

**Resource Registration** (`admin_resources.py:136`):
```python
@mcp.resource("session://{session_id}")
async def get_session_resource(session_id: str, ctx: Any = None) -> Resource:
```

**FastMCP Response Pattern** (`admin_resources.py:233-239`):
```python
return TextResource(
    uri=AnyUrl(f"session://{session_id}"),
    name=f"Session: {session['purpose']}",
    description=f"Shared context session with {len(messages)} visible messages",
    mime_type="application/json",
    text=json.dumps(content, indent=2, ensure_ascii=False),
)
```

## Implementation Specification

### Core Requirements

**Minimal 3-2-1 Pattern Implementation**:

**3 Resources**:
1. **`server://info`** - Static server capabilities discovery
2. **`docs://tools`** - Static tool documentation and usage examples
3. **`docs://usage`** - JWT-aware usage guidance (deferred to Phase 4)

**2 Prompts**:
1. **`setup-collaboration`** - Initialize multi-agent session workflow
2. **`debug-session`** - Session analysis and troubleshooting automation

**1 Enhanced Template**:
- **`session://{session_id}/messages/{limit}`** - Parameterized message retrieval with pagination

### Integration Points

**New File Requirements**:
- `src/shared_context_server/resources.py` (NEW) - Static resources implementation
- `src/shared_context_server/prompts.py` (NEW) - Workflow automation prompts
- Modify `src/shared_context_server/core_server.py:156-158` - Register new components
- Extend `src/shared_context_server/admin_resources.py` - Enhanced message template

**Registration Pattern Updates** (`core_server.py:139-154`):
```python
def _register_mcp_components() -> None:
    """Register all MCP components including tools, resources, and prompts."""
    try:
        from . import (
            admin_tools,  # noqa: F401
            auth_tools,  # noqa: F401
            memory_tools,  # noqa: F401
            search_tools,  # noqa: F401
            session_tools,  # noqa: F401
            resources,  # noqa: F401 (NEW)
            prompts,  # noqa: F401 (NEW)
        )
```

### Data Model Changes

**No Database Schema Changes Required**:
- Static resources derive from existing server metadata
- Tool documentation leverages existing tool registry patterns
- Prompts operate on existing session/memory data structures
- Enhanced templates use existing message table structure

### Interface Requirements

**Client Access Patterns**:

**Claude Code**:
- Resources: `@server://info`, `@docs://tools`
- Prompts: `/mcp__shared-context-server__setup-collaboration`, `/mcp__shared-context-server__debug-session`

**VS Code**:
- Resources: "Add Context > MCP Resources > server://info"
- Prompts: `/mcp.shared-context-server.setup-collaboration`

**Resource Response Format**:
```json
{
  "server_info": {
    "name": "shared-context-server",
    "version": "1.1.1",
    "capabilities": ["tools", "resources", "prompts", "resource_templates"]
  },
  "tools": {
    "count": 15,
    "categories": ["session", "memory", "search", "auth", "admin"]
  }
}
```

## Quality Requirements

### Testing Strategy

**Unit Testing**:
- `tests/unit/test_resources.py` - Static resource content validation
- `tests/unit/test_prompts.py` - Prompt parameter validation and workflow logic
- `tests/unit/test_enhanced_templates.py` - Template parameter handling

**Integration Testing**:
- MCP Inspector validation for resource discovery
- Client integration testing (Claude Code `@mentions`, VS Code context menu)
- End-to-end prompt workflow validation

**Security Testing**:
- JWT-aware resource permission boundary validation
- Prompt parameter sanitization testing
- Resource access control verification

### Documentation Needs

**User-Facing Documentation**:
- Update README.md with new MCP capabilities discovery section
- Add client integration examples for Claude Code and VS Code
- Workflow automation guide for new prompts

**API Documentation**:
- Resource schema documentation for `server://info` and `docs://tools`
- Prompt parameter specifications and examples
- Enhanced template usage patterns

### Performance Considerations

**Performance Targets**:
- Resource access: <5ms response time
- Prompt invocation: Real-time execution
- Template rendering: <10ms for message pagination

**Optimization Strategies**:
- Static resource caching for `server://info` and `docs://tools`
- Lazy loading for tool documentation generation
- Database query optimization for enhanced message templates

## Coordination Strategy

### Recommended Approach

**Agent Recommendation: cfw-developer**

**Rationale**:
- **Research-First Approach**: Extensive research foundation already established in planning phase
- **Pattern Following**: Excellent at implementing features following established architectural patterns
- **Code Quality Focus**: Ensures proper integration with existing FastMCP patterns and JWT security
- **Testing Integration**: Strong emphasis on comprehensive testing including MCP inspector validation

**Implementation Approach**:
- **Single Agent Coordination**: Moderate complexity with clear architectural patterns makes single-agent approach optimal
- **Phase-Based Validation**: Implement and validate Phase 1 (static resources) before proceeding to prompts/templates
- **MCP Inspector Integration**: Use MCP inspector for real-time validation during development

### Implementation Phases

**Phase 1: Static Resources** (Immediate Value)
- Implement `server://info` and `docs://tools` resources
- Update core server registration
- Validate with MCP inspector
- **Success Criteria**: MCP inspector shows 2 new resources

**Phase 2: Workflow Prompts** (High User Value)
- Implement `setup-collaboration` and `debug-session` prompts
- Add parameter validation and autocompletion
- Test client integration scenarios
- **Success Criteria**: Prompts accessible via Claude Code and VS Code

**Phase 3: Enhanced Templates** (Dynamic Access)
- Extend `session://{session_id}/messages/{limit}` template
- Add autocompletion for session_id parameter
- Performance optimization and caching
- **Success Criteria**: Parameterized message access working

**Phase 4: JWT-Aware Resources** (Optional/Deferred)
- Implement `docs://usage` with permission-aware content
- Complex dual-token context handling
- **Risk Mitigation**: Only proceed if Phases 1-3 validate successfully

### Risk Mitigation

**Technical Risk Management**:
- **Dual-Token Context**: Start with static resources to validate FastMCP context patterns
- **Breaking Changes**: Maintain existing tool functionality throughout implementation
- **Performance Impact**: Implement caching early, monitor response times

**Implementation Risk Management**:
- **Scope Control**: Strict adherence to 3-2-1 minimal pattern
- **Phase Gates**: Validate each phase before proceeding to next
- **Backward Compatibility**: Keep existing `get_usage_guidance` tool active

### Dependencies

**Prerequisites**:
- FastMCP 0.3+ patterns (already established in codebase)
- JWT authentication system (fully implemented)
- Database and session management (production ready)

**Integration Dependencies**:
- `core_server.py` registration system
- `admin_resources.py` resource patterns
- Existing tool metadata in `tools.py`

## Success Criteria

### Functional Success

**Resource Discovery**:
- MCP Inspector shows 2-3 new resources depending on phase completion
- Claude Code `@server://info` provides server capability information
- VS Code context menu includes shared-context-server resources

**Workflow Automation**:
- `/mcp__shared-context-server__setup-collaboration` creates and configures multi-agent sessions
- `/mcp__shared-context-server__debug-session` provides session analysis and troubleshooting
- Prompts include proper parameter validation and user guidance

**Enhanced Access**:
- `session://{session_id}/messages/{limit}` template provides parameterized message retrieval
- Template includes session_id autocompletion from existing sessions
- Performance meets <10ms target for message pagination

### Integration Success

**MCP Compliance**:
- All resources follow FastMCP 0.3+ patterns
- JWT context extraction works correctly with dual-token system
- Resource notifications integrate with existing ResourceNotificationManager

**Client Integration**:
- Claude Code: Resources via `@mentions`, prompts via `/mcp__server__prompt` commands
- VS Code: Resources via context menu, prompts via `/mcp.server.prompt` commands
- Both clients show proper autocompletion for template parameters

**Architectural Consistency**:
- New components follow established codebase patterns
- JWT security boundaries maintained
- No breaking changes to existing tool functionality

### Quality Gates

**Testing Requirements**:
- Unit test coverage >90% for new components
- Integration tests for all client interaction scenarios
- Security tests for JWT-aware resource access patterns
- Performance benchmarks meet <5ms resource access target

**Documentation Validation**:
- User guides updated with new capability discovery workflows
- API documentation complete for all new resources and prompts
- Client integration examples tested and verified

**Security Validation**:
- JWT permission boundaries tested across all access levels
- Resource access control verified for different agent types
- Prompt parameter sanitization confirmed secure

### Validation Approach

**Development Validation**:
- MCP Inspector integration for real-time resource discovery testing
- Local client testing with Claude Code and VS Code integrations
- Performance profiling during development to ensure targets met

**User Acceptance Criteria**:
- Multi-agent session setup time reduced through prompt automation
- Agent capability discovery improved through resource access
- Enhanced message access patterns working efficiently

**Production Readiness**:
- All quality gates passed
- Performance benchmarks met
- Security review completed
- Client compatibility verified

This PRP provides a comprehensive, research-backed implementation plan for enhancing the shared-context-server with essential MCP primitives while maintaining architectural consistency and security standards. The phased approach allows for validation at each step and provides clear success criteria for measuring implementation effectiveness.
