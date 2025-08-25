# MCP Resources, Prompts & Templates Enhancement Plan - v1.1.1

---
session_id: session_736d275a2551468f
session_purpose: "Feature planning: MCP Resources, Prompts & Templates Enhancement for v1.1.1"
created_date: 2025-08-25T21:12:01.349Z
updated_date: 2025-08-25T22:45:00.000Z
stage: "1-planning"
target_release: "1.1.1"
---

## Executive Summary

The shared-context-server currently has excellent tool coverage (15 tools) but lacks essential MCP primitives that would significantly improve agent usability and workflow automation. This plan addresses critical gaps in resources (0), prompts (0), and resource templates (only 2 basic) through a focused, minimal implementation that provides immediate value without over-engineering.

## Problem Statement

### Current State Analysis (via MCP Inspector)
- ✅ **Tools**: 15 comprehensive tools for multi-agent coordination - excellent coverage
- ❌ **Resources**: 0 static resources - agents cannot discover server capabilities
- ❌ **Prompts**: 0 prompts - no user-facing workflow automation
- ⚠️ **Resource Templates**: Only 2 basic templates (`session://{session_id}`, `agent://{agent_id}/memory`) - limited dynamic resource access

### Impact on Agent Experience
- **Discovery Problem**: Agents have no way to explore server capabilities through MCP resources
- **Workflow Gap**: No pre-built automation prompts for common multi-agent coordination tasks
- **Limited Context Access**: Insufficient parameterized resource access patterns

## Research Context & Best Practices

### MCP Protocol Research Sources
- **MCP Specification 2025-06-18**: Official protocol documentation and examples ✅ **ANALYZED**
- **FastMCP Documentation & Codebase**: Production MCP server framework patterns ✅ **ANALYZED**
- **MCP Blog "Prompts for Automation"**: Real-world workflow automation examples ✅ **ANALYZED**
- **Shared Context Server Codebase**: Existing patterns and architectural constraints ✅ **ANALYZED**
- **Paws-on-MCP Implementation**: Production server with full MCP 2025-03-26 compliance ✅ **ANALYZED**
- **MCP-UI SDK**: Resource UI patterns and client interaction models ✅ **ANALYZED**

### Current MCP Ecosystem Reality (August 2025)

**Client Support Status:**
- **Claude Code**: Full support for resources (`@` mentions), prompts (`/mcp__server__prompt` commands), templates
- **VS Code**: Full MCP support since v1.102, resources via "Add Context > MCP Resources", prompts as `/mcp.server.prompt`
- **Other IDEs**: Varying levels of support, most have basic tool calling but limited resources/prompts

**Production Server Analysis:**
- **Webflow MCP Server**: Explicitly states "does not include prompts or resources... due to limited client support" (legacy position)
- **Paws-on-MCP**: Full implementation with 15 resources, 14 prompts, 9 tools (proves client support exists)
- **Most servers**: Still tool-focused, but resources/prompts are now viable for client consumption

### Key Research Validation: JWT-Aware Resources Pattern ✅

**MCP Specification Evidence:**
- Resources **MUST** validate access tokens (OAuth 2.1 integration)
- Resources receive full authentication context via Bearer tokens
- Dynamic content based on user permissions is standard practice
- FastMCP Context injection pattern: `context_kwarg = find_kwarg_by_type(self.fn, kwarg_type=Context)`

**CRITICAL AUTHENTICATION ARCHITECTURE:**
- **Two-Token System**: API Key (MCP headers) + JWT Token (agent permissions)
- **API Key**: Static authentication for MCP client connection (header: `Authorization: API_KEY`)
- **JWT Token**: Dynamic per-request agent authentication (tool parameter: `auth_token`)
- **Context Access**: Resources need to extract JWT from request context, not just MCP headers

**Architectural Confirmation:**
- Moving usage guidance from tool → resource is **CORRECT** and **MCP-COMPLIANT**
- JWT-aware resources align with MCP security model perfectly
- **Implementation Note**: Must handle dual-token extraction pattern in resource context
- Better discoverability and performance than tool-based approach

### Key MCP Patterns Discovered

#### Resources (Application-Controlled Context)
- **Purpose**: Provide contextual data that LLMs can reference
- **Control Model**: Application decides what context to include
- **Client Access**: Claude Code (`@server://info`), VS Code ("Add Context > MCP Resources")
- **Best Practices**: Descriptive URIs, metadata (mimeType, description, size), annotations (audience, priority, timestamps)
- **Real Examples**: `hackernews://top/10`, `github://trending/python/daily`, `status://server`

#### Prompts (User-Controlled Templates)
- **Purpose**: Pre-built workflow automation that users can trigger
- **Control Model**: Users explicitly select and invoke prompts
- **Client Access**: Claude Code (`/mcp__server__prompt`), VS Code (`/mcp.server.prompt`)
- **Best Practices**: User-facing commands, parameter autocompletion, resource embedding, workflow automation
- **Real Examples**: `analyze_tech_trends`, `project_research`, `code_review_assistant`

#### Resource Templates (Parameterized Resources)
- **Purpose**: Dynamic resource generation using URI patterns with variables
- **Control Model**: Scalable alternative to static resources
- **Best Practices**: URI templates with parameters, autocompletion, hierarchical data patterns
- **Real Examples**: `session://{session_id}/messages/{limit}`, `sampling://{type}/{count}`

## Proposed Implementation

### Scope: Focused Minimal Enhancement

**2 Easy Win Static Resources + 1 Complex Resource:**

1. **`server://info`** - Basic server capabilities discovery ✅ **EASY WIN**
   - Server name, version, available capabilities
   - Tool count and categories summary
   - Static content, fast response
   - **Priority**: Phase 1 - Immediate implementation

2. **`docs://tools`** - Tool reference for agents ✅ **EASY WIN**
   - Comprehensive tool documentation
   - Usage examples and parameter schemas
   - Static content derived from existing tool metadata
   - **Priority**: Phase 1 - Immediate implementation

3. **`docs://usage`** - JWT-aware usage guidance ⚠️ **COMPLEX - DEFERRED**
   - **Critical Design**: Must respect permission boundaries like existing `get_usage_guidance` tool
   - Dynamic content based on agent's JWT permissions (ADMIN/AGENT/READ_ONLY)
   - **Research Validation**: MCP compliant but requires dual-token context handling
   - **Priority**: Phase 4 - Defer until static resources and prompts are complete

**2 Core Workflow Prompts:**

1. **`setup-collaboration`** - Initialize multi-agent session
   - Creates session, provides coordination guidance
   - Parameters: session purpose, agent types involved
   - Autocompletion for common session purposes

2. **`debug-session`** - Analyze session issues
   - Session performance analysis and troubleshooting
   - Parameters: session_id, analysis_type
   - Embeds session resource data for context

**1 Enhanced Template:**

- **`session://{session_id}/messages/{limit}`** - Parameterized message retrieval
  - Extends existing session template with limit parameter
  - Enables efficient message pagination
  - Autocompletion for session_id values

## Technical Architecture

### Integration with Existing System

**File Structure:**
- `src/shared_context_server/resources.py` (NEW) - Static resources implementation
- `src/shared_context_server/prompts.py` (NEW) - Workflow automation prompts
- `src/shared_context_server/admin_resources.py` (EXTEND) - Enhanced templates
- Update `core_server.py` to register new components

**Security Considerations:**
- JWT-aware `docs://usage` resource maintains existing permission boundaries
- Resources respect 4-tier visibility system (public/private/agent_only/admin_only)
- Prompts include proper parameter validation and sanitization

**Testing Strategy:**
- Unit tests for each resource and prompt
- Integration tests for MCP inspector validation
- Security tests for JWT-aware resource access
- Performance tests for resource response times

### Implementation Phases ⚠️ **REVISED PRIORITY ORDER**

**Phase 1: Easy Wins - Static Resources** (Immediate Value)
- ✅ `server://info` - Basic server capabilities (static, simple)
- ✅ `docs://tools` - Tool documentation (static, derives from existing metadata)
- Validate with MCP inspector before proceeding

**Phase 2: User Workflow Automation** (High Value)
- Implement 2 core prompts with parameter validation
- Add autocompletion support
- Test user workflow scenarios

**Phase 3: Enhanced Templates** (Dynamic Access)
- Extend message template with limit parameter
- Add autocompletion for session_id
- Performance optimization

**Phase 4: Complex JWT-Aware Resource** (Deferred - Complex)
- ⚠️ `docs://usage` - JWT-aware usage guidance (requires dual-token context handling)
- Focus on easier wins first, tackle complex authentication mapping last
- Keep existing `get_usage_guidance` tool as primary method

## Success Criteria

### Technical Success ⚠️ **REVISED TARGETS**
- **Phase 1 Target**: MCP inspector shows 2 static resources (server://info, docs://tools)
- **Phase 2 Target**: 2 prompts added (setup-collaboration, debug-session)
- **Phase 3 Target**: 1 enhanced template (session messages with limit)
- **Phase 4 Target**: JWT-aware `docs://usage` resource (if complexity permits)
- All implemented components pass comprehensive test suite (unit/integration/security)
- Performance impact < 5ms for resource access

### User Experience Success
- **Claude Code**: Resources accessible via `@server://info`, prompts as `/mcp__shared-context-server__setup-collaboration`
- **VS Code**: Resources via "Add Context > MCP Resources", prompts as `/mcp.shared-context-server.debug-session`
- **Multi-Agent Sessions**: Enhanced coordination through workflow automation
- **Performance**: <5ms resource access, real-time prompt invocation

### Validation Approach
- **Client Testing**: Claude Code (`@` and `/` functionality), VS Code (context menu and chat commands)
- **Real User Scenarios**: Multi-agent session setup, debugging workflows, capability discovery
- **Security Validation**: JWT permission boundaries for different resource access levels
- **Performance Benchmarking**: Resource response times vs existing tool calls

## Risk Mitigation

### Technical Risks ⚠️ **REQUIRES CAREFUL IMPLEMENTATION**
- **Dual-Token Context Handling**: ⚠️ **COMPLEX** - Must extract JWT token from MCP context, not just bearer token headers
- **Authentication Flow**: API Key validates MCP client → JWT Token provides agent permissions → Resource extracts both
- **Context Mapping**: Need to map between FastMCP Context and our dual-token system
- **Performance Impact**: Monitor resource access performance, implement caching if needed
- **Breaking Changes**: ✅ **NO RISK** - Keep existing `get_usage_guidance` tool for backward compatibility during transition

### Implementation Risks
- **Scope Creep**: Stick to minimal 3-2-1 pattern (3 resources, 2 prompts, 1 template)
- **Over-engineering**: Focus on essential functionality, test before expanding
- **Security Gaps**: Thorough security review of JWT-aware resource implementation

## Implementation Roadmap

### Ready for `/create-prp`
This planning document is complete and ready for PRP creation with the following implementation phases:

1. **Phase 1 PRP**: Static Resources Implementation (`server://info`, `docs://tools`)
   - **Scope**: Two easy-win static resources for immediate agent discovery
   - **Files**: Create `src/shared_context_server/resources.py`
   - **Testing**: Unit tests, MCP inspector validation

2. **Phase 2 PRP**: Workflow Prompts Implementation (`setup-collaboration`, `debug-session`)
   - **Scope**: Two core prompts for multi-agent coordination automation
   - **Files**: Create `src/shared_context_server/prompts.py`
   - **Testing**: User workflow scenarios, client integration testing

3. **Phase 3 PRP**: Enhanced Templates (`session://{session_id}/messages/{limit}`)
   - **Scope**: Extend existing template system with pagination
   - **Files**: Enhance `src/shared_context_server/admin_resources.py`
   - **Testing**: Performance optimization, autocompletion validation

4. **Phase 4 PRP**: JWT-Aware Resources (`docs://usage`) - **OPTIONAL/DEFERRED**
   - **Scope**: Complex authentication-aware resource (only if needed)
   - **Dependencies**: Phases 1-3 complete and validated
   - **Risk**: High complexity, defer until core functionality proven

### Immediate Next Steps
1. **Create Phase 1 PRP**: Static resources implementation
2. **Establish performance baseline**: Current tool response time metrics
3. **Set up MCP inspector testing environment**: Validate resource discovery
4. **Security review**: JWT extraction patterns for resource context

## Conclusion

This focused enhancement addresses critical usability gaps in the shared-context-server's MCP implementation while respecting existing architectural patterns and security boundaries. The minimal scope (3-2-1 pattern) provides immediate value for agent discovery and user workflow automation without over-engineering or compromising the server's proven multi-agent coordination capabilities.

### Ecosystem Timing & Strategic Position

**Market Reality (August 2025)**: Client ecosystem has matured sufficiently to support full MCP primitives. While legacy servers like Webflow still cite "limited client support," newer implementations like Paws-on-MCP demonstrate that resources and prompts are now viable for production use.

**Strategic Advantage**: This implementation positions shared-context-server among the early adopters of complete MCP primitive coverage while most production servers remain tool-focused. The timing aligns perfectly with client capability maturation in Claude Code and VS Code.

**User Impact**: Real users can immediately benefit from:
- **Claude Code**: `@server://info` for discovery, `/setup-collaboration` for automation
- **VS Code**: Resource context menus, prompt slash commands
- **Multi-agent workflows**: Coordinated session management with reduced manual setup
