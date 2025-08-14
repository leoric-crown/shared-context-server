# PRP-014: Dynamic Usage Guidance Tool

**Status**: Ready for Implementation
**Created**: 2025-01-14
**Planning Source**: `PRPs/1-planning/1.0.3-dynamic-usage-guidance.md`
**Type**: MCP Tool Feature - Agent Coordination Enhancement

## Research Context & Architectural Analysis

### Research Integration
**Planning Research Completed**: Comprehensive planning document validated by expert agents
- ✅ **@agent-developer**: "Perfect architecture alignment, 95% reuse of existing infrastructure, realistic 1-day timeline"
- ✅ **@agent-tester**: "Solid foundation with comprehensive testing requirements identified"

**MCP Research Findings**:
- Established JWT authentication patterns using `JWTAuthenticationManager` (auth.py:63-217)
- Proven FastMCP tool patterns with `@mcp.tool()` decorator (server.py)
- Existing tool registry system with metadata support (tools.py:64-108)
- Enterprise-grade error handling with LLM-friendly responses (utils/llm_errors.py)

**Architectural Scope**: Single MCP tool addition leveraging 95% existing infrastructure
- **Integration Complexity**: LOW - Single tool using established patterns
- **File Count Impact**: 3-4 files (server.py, tools.py, new test file)
- **Risk Assessment**: LOW RISK - No database schema changes, proven patterns

### Existing Patterns
**FastMCP Tool Pattern**:
```python
@mcp.tool()
async def existing_tool_example(
    ctx: Context,
    auth_token: Optional[str] = None,
    param: str = Field(description="Parameter description")
) -> dict[str, Any]:
    agent_context = await extract_agent_context(ctx, auth_token)
    # Implementation using established patterns
    return create_success_response(data)
```

**JWT Authentication Pattern**:
- `extract_agent_context(ctx, auth_token)` - Existing JWT validation
- `AgentIdentity` with permission checking - Role-based access control
- Audit logging for security events - `audit_log_auth_event()`

**Tool Registry Integration**:
```python
TOOL_REGISTRY = {
    "get_usage_guidance": ToolMetadata(
        name="get_usage_guidance",
        category=ToolCategory.SERVER_UTILITIES,
        description="Get contextual operational guidance based on JWT access level",
        tags=["guidance", "permissions", "operations", "security"]
    )
}
```

## Implementation Specification

### Core Requirements

**Primary MCP Tool**: `get_usage_guidance`
- **Purpose**: Provide JWT access-level appropriate operational guidance for multi-agent coordination
- **Parameters**: `auth_token: Optional[str]`, `guidance_type: str = "operations"`
- **Returns**: Structured guidance response based on access level (ADMIN/AGENT/READ_ONLY)

**Guidance Types**:
1. **operations**: Available tools + usage patterns + permission requirements
2. **coordination**: Multi-agent workflow instructions + handoff patterns + escalation triggers
3. **security**: Permission boundaries + security best practices + token management
4. **troubleshooting**: Common issues + recovery procedures + debugging steps

**Access Level Mapping**:
```python
def determine_access_level(permissions: list[str]) -> str:
    if "admin" in permissions:
        return "ADMIN"     # Can generate tokens, access all resources
    elif "write" in permissions:
        return "AGENT"     # Can read/write, coordinate with other agents
    else:
        return "READ_ONLY" # Can only read public resources
```

### Integration Points

**FastMCP Server Integration** (`server.py`):
- Add `@mcp.tool()` decorated function following established patterns
- Use existing `extract_agent_context(ctx, auth_token)` for JWT validation
- Return responses using established error handling patterns

**Authentication Integration** (`auth.py`):
- Leverage existing `JWTAuthenticationManager` for token validation
- Use existing permission system (read, write, admin, debug)
- Integrate with audit logging via `audit_log_auth_event()`

**Tool Registry Integration** (`tools.py`):
- Add metadata to `TOOL_REGISTRY` with proper categorization
- Include tool in discovery functions for dynamic tool listing
- Set appropriate permission requirements and tags

### Database Changes
**None Required**: This is a computation-only tool using existing authentication infrastructure. No database schema modifications needed.

### API Requirements

**MCP Tool Interface**:
```python
@mcp.tool()
async def get_usage_guidance(
    ctx: Context,
    auth_token: Optional[str] = Field(
        default=None,
        description="JWT token to analyze. If not provided, uses current request context"
    ),
    guidance_type: str = Field(
        default="operations",
        description="Type of guidance: operations, coordination, security, troubleshooting"
    )
) -> dict[str, Any]:
```

**Response Format**:
```json
{
  "success": true,
  "access_level": "ADMIN|AGENT|READ_ONLY",
  "agent_info": {
    "agent_id": "claude_framework_developer",
    "agent_type": "claude",
    "permissions": ["read", "write", "refresh_token"],
    "expires_at": "2025-08-14T21:18:52Z",
    "can_refresh": true
  },
  "guidance": {
    "available_operations": [...],
    "coordination_instructions": {...},
    "security_boundaries": [...],
    "next_steps": [...]
  },
  "examples": {
    "typical_workflow": [...]
  }
}
```

## Quality Requirements

### Testing Strategy
**Enhanced Security Testing** (based on @agent-tester feedback):

**Critical Security Tests**:
```python
class TestUsageGuidanceSecurity:
    async def test_jwt_audience_validation(self):
        """Test tool rejects tokens with wrong audience."""

    async def test_permission_escalation_prevention(self):
        """Test tool doesn't leak higher permission guidance."""

    async def test_token_boundary_enforcement(self):
        """Test guidance respects actual JWT permissions."""

    async def test_malformed_token_handling(self):
        """Test proper error responses for invalid tokens."""
```

**Multi-Agent Workflow Testing**:
```python
async def test_multi_agent_coordination_workflow(self):
    """Test complete multi-agent workflow with different JWT access levels."""
    # Admin generates tokens, gets coordination guidance
    # Agents get role-specific guidance within their boundaries
    # Verify guidance is properly scoped to access levels
```

**Performance Validation**:
- Guidance generation: <50ms (per expert feedback)
- JWT validation: <10ms (reusing existing auth patterns)
- Tool registry lookups: <5ms (dictionary access)

### Documentation Needs
**MCP Tool Documentation**:
- Add to FastMCP tool registry with comprehensive descriptions
- Include usage examples for each access level and guidance type
- Document integration patterns for multi-agent coordination

**Agent Integration Examples**:
```python
# Example: Agent understanding operational boundaries
my_guidance = await get_usage_guidance()
# Returns: Agent-specific operational instructions, available tools, handoff patterns

# Example: Admin coordinating multi-agent workflow
admin_guidance = await get_usage_guidance(guidance_type="coordination")
# Returns: Admin-level instructions for generating agent tokens and coordinating workflows
```

### Performance Considerations
**Concurrent Agent Access**:
- Stateless operation supports high concurrency
- No database operations required (computation-only)
- Leverages existing connection pooling for any audit logging

**Response Optimization**:
- Tool registry lookups are O(1) dictionary operations
- Simple permission mapping without complex computation
- Future caching can be added if response times exceed targets

## Coordination Strategy

### Recommended Approach: **Direct Agent Assignment**
**Complexity Analysis**:
- **File Count Impact**: 3-4 files (low complexity)
- **Integration Complexity**: Single tool using established patterns
- **Time Estimate**: 1 day implementation (validated by expert review)
- **Risk Level**: LOW - No architectural changes required

**Optimal Agent**: `@agent-developer`
**Rationale**:
- Perfect architecture alignment with existing FastMCP patterns
- Single tool implementation within developer agent expertise
- No complex coordination needed for straightforward feature addition
- Expert validation confirms technical feasibility and approach

### Implementation Phases
**Phase 1: Core Implementation** (6 hours)
1. Add tool definition to FastMCP server (1 hour)
2. Implement core logic using existing auth patterns (2 hours)
3. Create response generators for each guidance type (3 hours)

**Phase 2: Integration & Testing** (2 hours)
1. Add to tool registry with metadata (30 minutes)
2. Write comprehensive unit tests (1 hour)
3. Integration testing with JWT scenarios (30 minutes)

### Risk Mitigation
**Low Risk Profile**: Builds entirely on proven infrastructure
- Uses existing JWT authentication (no new security patterns)
- Follows established FastMCP tool patterns (no framework changes)
- Single tool addition (minimal surface area for issues)
- No database schema changes (no migration risks)

**Quality Gates**:
- Expert validation ✅ (completed)
- Security testing (comprehensive JWT boundary validation)
- Performance validation (<50ms response time)
- Integration testing (multi-agent coordination scenarios)

### Dependencies
**Required** (All Available):
- ✅ JWT authentication system (`auth.py:JWTAuthenticationManager`)
- ✅ FastMCP server framework (`server.py:@mcp.tool()` patterns)
- ✅ Tool registry system (`tools.py:TOOL_REGISTRY`)
- ✅ Error handling utilities (`utils/llm_errors.py`)

**Optional** (Available):
- ✅ Database connection for audit logging (existing infrastructure)
- ✅ Performance monitoring (existing patterns available)

## Success Criteria

### Functional Success
**MCP Operations Must Work**:
- ✅ All guidance types (operations, coordination, security, troubleshooting) return appropriate responses
- ✅ Access level detection correctly maps JWT permissions to ADMIN/AGENT/READ_ONLY
- ✅ Response format matches specification for all guidance types and access levels
- ✅ Error handling provides helpful, actionable guidance for invalid tokens or parameters

**JWT Integration Success**:
- ✅ Server-side JWT validation using existing authentication infrastructure
- ✅ No token leakage in responses (security boundary enforcement)
- ✅ Audit logging for all guidance requests (security monitoring)
- ✅ Permission boundaries properly enforced (no privilege escalation)

### Integration Success
**Multi-Agent Coordination Verification**:
- ✅ Agents can autonomously understand their operational boundaries
- ✅ Guidance enables proper multi-agent workflow coordination
- ✅ Security boundaries prevent unauthorized operation attempts
- ✅ Tool integrates seamlessly with existing FastMCP server architecture

**Performance Success**:
- ✅ <50ms guidance generation for all guidance types
- ✅ <10ms JWT validation (reusing existing auth patterns)
- ✅ Concurrent agent access without performance degradation

### Quality Gates
**Security Validation**:
- ✅ Zero JWT authentication bypasses or privilege escalation incidents
- ✅ Comprehensive security testing covers all token scenarios
- ✅ Permission boundary enforcement prevents unauthorized access
- ✅ Audit trail captures all guidance requests for security monitoring

**Testing Validation**:
- ✅ Unit tests cover all guidance types and access levels
- ✅ Integration tests validate multi-agent coordination workflows
- ✅ Security tests prevent token leakage and privilege escalation
- ✅ Performance tests validate response time targets

**Code Quality**:
- ✅ Uses established FastMCP patterns (no architectural deviations)
- ✅ Integrates with existing error handling (consistent LLM responses)
- ✅ Tool registry integration with proper metadata
- ✅ Comprehensive documentation with usage examples

## Implementation Context

### YAGNI Implementation Focus
**Building Now** (Essential for Multi-Agent Coordination):
- ✅ Complete guidance types (operations, coordination, security, troubleshooting)
- ✅ JWT access level detection and permission mapping
- ✅ Security boundary enforcement and audit logging
- ✅ Structured response format with actionable guidance

**Explicitly NOT Building** (Can Add Later):
- ❌ Response caching optimization (add if performance becomes an issue)
- ❌ Complex permission hierarchies (existing 4 levels sufficient)
- ❌ Persistent guidance customization (static responses work fine)
- ❌ Advanced analytics/metrics (basic audit logging sufficient)

### Expert Validation Summary
**Technical Validation** ✅:
- Perfect architecture alignment with existing patterns
- 95% infrastructure reuse, minimal new code required
- Realistic implementation timeline with proven dependencies

**Testing Validation** ✅:
- Comprehensive security testing requirements identified
- Multi-agent workflow testing scenarios defined
- Performance targets established and achievable

**Ready for Implementation**: All dependencies available, approach validated, risks mitigated.

---

**Next Step**: Execute this PRP using `/execute-prp` with direct agent assignment to `@agent-developer` for efficient, expert-validated implementation.
