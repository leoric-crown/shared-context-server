# PRP-028: MCP Inspector CLI Compatibility Fix

---
session_id: session_662d0098fea64d15
session_purpose: "PRP creation: Analyzing planning context from session_0802bb5bba9a43c8"
created_date: 2025-08-28T18:52:00.000Z
stage: "2-prps"
planning_source: session_0802bb5bba9a43c8
planning_session_id: session_0802bb5bba9a43c8
prp_number: "028"
feature_name: "mcp-inspector-cli-compatibility-fix"
---

## Research Context & Architectural Analysis

### Research Integration
**Comprehensive Investigation Complete**: The planning session conducted a thorough technical investigation of MCP Inspector CLI compatibility issues with our shared-context-server. Root cause analysis identified authentication middleware as the core blocker.

**Key Technical Findings**:
- **Problem**: FastMCP server requires API key authentication for ALL requests, including built-in MCP protocol methods like `tools/list`
- **Root Cause**: `validate_api_key_header(ctx)` blocks all unauthenticated requests, but MCP Inspector CLI doesn't send API key headers for standard protocol methods
- **Solution Validated**: FastMCP middleware system can selectively bypass authentication for safe discovery methods

### Architectural Scope
**Integration Points Analyzed**:
- **FastMCP Server Foundation** (`core_server.py`): Clean middleware integration point identified
- **Authentication System** (`auth_secure.py`): Current validation pattern requires all requests to have API key
- **Tool Registration** (`core_server.py`): No changes needed - middleware intercepts before tool execution

**Existing Patterns Leveraged**:
- FastMCP middleware system with comprehensive hooks (`on_request`, `on_message`, etc.)
- Standard MCP protocol method identification patterns
- Existing security validation functions for custom tools

## Implementation Specification

### Core Requirements
**Authentication Middleware Implementation**:
- Create `MCPAuthenticationMiddleware` class that selectively bypasses authentication
- Whitelist safe MCP protocol methods: `initialize`, `tools/list`, `resources/list`, `prompts/list`, `ping`
- Maintain full authentication requirements for custom business logic tools
- Provide clear debug logging for authentication decisions

**Integration Requirements**:
- Integrate middleware into existing FastMCP server instance in `core_server.py`
- Ensure backward compatibility - no changes to existing tool validation logic
- Maintain all existing security features for custom tools

**Documentation Requirements**:
- Update `docs/mcp-inspector-guide.md` with working MCP Inspector CLI examples
- Remove outdated CLI syntax that doesn't work
- Provide troubleshooting guide for authentication requirements

### Integration Points

#### 1. New Middleware Module (`src/shared_context_server/mcp_auth_middleware.py`)
```python
class MCPAuthenticationMiddleware(Middleware):
    """Bypass auth for MCP protocol, require auth for custom tools."""

    # No auth required for protocol methods
    MCP_PROTOCOL_METHODS = {
        "initialize", "tools/list", "resources/list",
        "resources/templates/list", "prompts/list", "ping"
    }

    async def on_request(self, context: MiddlewareContext, call_next):
        # Allow MCP protocol methods without authentication
        if context.method in self.MCP_PROTOCOL_METHODS:
            return await call_next(context)

        # Require authentication for custom tools
        if not self.validate_auth(context):
            raise McpError("Authentication required")

        return await call_next(context)
```

#### 2. Core Server Integration (`src/shared_context_server/core_server.py`)
```python
# After line 37, add middleware integration:
from .mcp_auth_middleware import MCPAuthenticationMiddleware

# Add middleware to FastMCP server
mcp.add_middleware(MCPAuthenticationMiddleware())
```

### Data Model Changes
**No Data Model Changes Required**: This is purely a middleware/authentication enhancement that doesn't affect database schemas or data structures.

### Interface Requirements
**Command Line Interface Enhancement**:
- Enable working MCP Inspector CLI commands: `npx @modelcontextprotocol/inspector --cli uv run python -m shared_context_server.scripts.cli --transport stdio --method tools/list`
- Maintain existing web UI and HTTP API functionality
- No changes to existing tool interfaces or parameters

## Quality Requirements

### Testing Strategy
**Behavioral Testing Approach**:
1. **MCP Inspector CLI Validation**: Verify `tools/list`, `resources/list`, `prompts/list` work without authentication
2. **Security Regression Testing**: Ensure custom tools (`create_session`, `add_message`, etc.) still require authentication
3. **Integration Testing**: Full MCP Inspector workflow validation with discovery and tool execution
4. **Backward Compatibility Testing**: Verify existing API key and JWT token authentication still works

**Test Coverage Requirements**:
- Unit tests for `MCPAuthenticationMiddleware` class
- Integration tests for MCP Inspector CLI compatibility
- Security validation tests to prevent auth bypass for sensitive operations
- Documentation validation tests for working examples

### Documentation Needs
**Technical Documentation**:
- Update MCP Inspector guide with accurate, tested CLI examples
- Document authentication requirements for different method types
- Provide troubleshooting guide for authentication failures

**Developer Documentation**:
- Middleware architecture explanation for future maintenance
- Security model documentation for the selective authentication approach
- Integration examples for adding new MCP protocol methods

### Performance Considerations
**Minimal Performance Impact**:
- Middleware adds ~1-2ms overhead per request for method lookup
- No impact on existing tool performance or database operations
- Authentication bypass reduces CPU overhead for discovery methods

## Coordination Strategy

### Recommended Approach: **Direct Agent Implementation**
**Rationale**: This is a focused, well-scoped implementation with clear requirements and minimal integration complexity.

**Agent Type Recommendation**: `cfw-developer`
- **Research-First Approach**: Aligns with completed investigation and solution design
- **Security Focus**: Emphasizes careful implementation of security-sensitive middleware
- **Testing Integration**: Will validate both functionality and security requirements

### Implementation Phases
1. **Phase 1**: Implement `MCPAuthenticationMiddleware` class with selective authentication logic
2. **Phase 2**: Integrate middleware into FastMCP server instance
3. **Phase 3**: Comprehensive testing - MCP Inspector CLI compatibility and security validation
4. **Phase 4**: Documentation updates with working examples and troubleshooting guide
5. **Phase 5**: Security audit - verify no regressions in custom tool authentication

### Risk Mitigation
**Low Risk Implementation**:
- **Isolated Changes**: Middleware layer intercepts requests before existing validation
- **Backward Compatibility**: No breaking changes to existing functionality
- **Security Validation**: Comprehensive testing ensures no auth bypass for sensitive operations
- **Rollback Strategy**: Middleware can be easily disabled if issues arise

### Dependencies
**Prerequisites**:
- Current FastMCP server architecture (already in place)
- Existing authentication system (no changes required)
- Planning session investigation results (completed)

**No External Dependencies**: All implementation uses existing FastMCP features and patterns.

## Success Criteria

### Functional Success
**MCP Inspector CLI Functionality**:
- ✅ `npx @modelcontextprotocol/inspector --cli uv run python -m shared_context_server.scripts.cli --transport stdio --method tools/list` works without authentication
- ✅ `tools/list`, `resources/list`, `prompts/list` methods return complete results
- ✅ MCP Inspector web UI continues to work (existing functionality preserved)

### Integration Success
**Security Model Validation**:
- ✅ Custom tools (`create_session`, `add_message`, etc.) still require authentication
- ✅ JWT token authentication works for elevated permissions
- ✅ API key authentication maintained for HTTP transport clients
- ✅ No security regressions in existing functionality

### Quality Gates
**Testing and Documentation**:
- ✅ Comprehensive test coverage for middleware functionality
- ✅ Security validation tests pass
- ✅ Documentation updated with accurate, working examples
- ✅ MCP Inspector guide provides clear troubleshooting guidance

---

`★ Insight ─────────────────────────────────────`
This PRP represents a classic "research-first" implementation where thorough investigation identified the exact root cause and solution approach. The selective authentication middleware pattern is a common architectural solution for protocol compatibility while maintaining security boundaries.
`─────────────────────────────────────────────────`

**Next Step**: Use `run-prp` command to implement this PRP with the recommended cfw-developer agent coordination.
