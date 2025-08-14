# Feature Request: Dynamic Usage Guidance Tool

## Overview

**Tool Name**: `get_usage_guidance`

**Purpose**: Provide dynamic, JWT access-level appropriate instructions for shared-context-server usage in multi-agent environments.

**Priority**: High - Required for secure multi-agent coordination in Claude Multi-Agent Framework

## Problem Statement

The shared-context-server supports sophisticated JWT-based RBAC with multiple access levels (Admin, Agent, Read-Only), but users and agents need contextual guidance on:
- What operations they can perform at their access level
- How to coordinate multi-agent workflows securely
- What security boundaries exist and why
- How to properly distribute and manage JWT tokens

Currently, users must manually determine their capabilities and operational patterns, leading to potential security boundary violations and suboptimal usage patterns.

## Proposed Solution

A context-aware MCP tool that analyzes the caller's current JWT authentication context and returns tailored operational guidance matching their permission level and role.

## Technical Specification

### Tool Definition

**Tool Name**: `get_usage_guidance`

**Parameters**:
```json
{
  "auth_token": {
    "type": "string",
    "required": false,
    "description": "JWT token to analyze. If not provided, uses current request context"
  },
  "guidance_type": {
    "type": "string",
    "enum": ["operations", "coordination", "security", "troubleshooting"],
    "required": false,
    "default": "operations",
    "description": "Type of guidance requested"
  }
}
```

### Response Format

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
    "available_operations": [
      {
        "tool": "add_message",
        "description": "Add message with visibility controls",
        "usage_pattern": "add_message(session_id, content, visibility='public')",
        "permissions_required": ["write"],
        "best_practices": [
          "Use appropriate visibility level for handoffs",
          "Include metadata for agent coordination context"
        ]
      },
      {
        "tool": "set_memory",
        "description": "Store agent-specific memory with scoping",
        "usage_pattern": "set_memory(key, value, session_id, expires_in)",
        "permissions_required": ["write"],
        "best_practices": [
          "Use session scoping for handoff data",
          "Set appropriate TTL for temporary context"
        ]
      }
    ],
    "coordination_instructions": {
      "role_description": "Session implementation coordinator + LTM pattern validator",
      "handoff_patterns": [
        "set_memory for persistent agent state during handoffs",
        "add_message with agent_only visibility for coordination",
        "search_context to load previous agent work"
      ],
      "escalation_triggers": [
        "Architecture issues requiring admin intervention",
        "Security boundary violations",
        "Token expiry or refresh failures"
      ]
    },
    "security_boundaries": [
      "Cannot generate tokens for other agents",
      "Limited to session-scoped memory operations",
      "Must respect message visibility controls",
      "Cannot access admin-only performance metrics"
    ],
    "next_steps": [
      "Authenticate with your assigned token using auth_token parameter",
      "Load context using search_context and get_memory with your agent_id",
      "Execute role-specific tasks within permission boundaries",
      "Use refresh_token before token expiry"
    ]
  },
  "examples": {
    "typical_workflow": [
      "1. search_context(session_id, query='previous development work')",
      "2. get_memory(key='architectural_decisions', session_id)",
      "3. add_message(session_id, content='Implementation progress', visibility='public')",
      "4. set_memory(key='handoff_state', value=implementation_data, session_id)"
    ]
  }
}
```

## Access Level Behaviors

### ADMIN Level Response
When caller has admin-level JWT token:
- **Coordination Instructions**: How to generate and distribute JWT tokens to agents
- **Multi-Agent Patterns**: Workflow coordination across multiple agents
- **Override Capabilities**: When and how to use admin visibility overrides
- **Performance Monitoring**: Access to get_performance_metrics and system health
- **Token Management**: Full authenticate_agent capabilities for creating agent tokens

### AGENT Level Response
When caller has agent-level JWT token:
- **Role-Specific Operations**: Instructions tailored to agent type (developer, tester, etc.)
- **Available Tools**: Filtered list of tools matching agent permissions
- **Handoff Protocols**: How to coordinate with other agents through context sharing
- **Token Refresh**: How to use refresh_token to maintain authentication
- **Boundary Enforcement**: Clear explanation of what operations are forbidden

### READ_ONLY Level Response
When caller has read-only JWT token:
- **Search Operations**: Available search_context and get_messages capabilities
- **Visibility Limitations**: What message visibility levels are accessible
- **Monitoring Role**: How to observe without modification
- **No Write Operations**: Clear explanation of read-only boundaries

## Implementation Requirements

### Security Considerations
- **Server-Side Validation**: All JWT validation must occur server-side
- **No Token Leakage**: Tool responses must not expose JWT tokens or sensitive auth data
- **Permission Enforcement**: Guidance must accurately reflect current JWT permissions
- **Audit Trail**: Tool usage should be logged for security monitoring

### Performance Requirements
- **Fast Response**: Sub-50ms response time for guidance generation
- **Caching**: Cache guidance responses per access level to reduce computation
- **Minimal Overhead**: JWT validation should reuse existing authentication infrastructure

### Integration Requirements
- **MCP Compatibility**: Follow existing shared-context-server MCP tool patterns
- **Error Handling**: Graceful handling of expired, invalid, or missing tokens
- **Version Compatibility**: Support for future JWT claim extensions

## Use Cases

### Use Case 1: Main Claude Multi-Agent Coordination
```python
# Main Claude starting multi-agent workflow
admin_token = authenticate_agent(agent_id="main_claude", agent_type="admin")
guidance = get_usage_guidance(guidance_type="coordination")
# Returns: Admin-level instructions for generating agent tokens and coordinating workflows

developer_token = authenticate_agent(agent_id="claude_framework_developer", ...)
# Pass developer_token to agent during launch
```

### Use Case 2: Agent Understanding Operational Boundaries
```python
# Agent receives token from Main Claude and needs guidance
my_guidance = get_usage_guidance()
# Returns: Agent-specific operational instructions, available tools, handoff patterns
```

### Use Case 3: Troubleshooting Authentication Issues
```python
# Any caller experiencing issues
help_info = get_usage_guidance(guidance_type="troubleshooting")
# Returns: Access-level appropriate debugging steps and resolution guidance
```

### Use Case 4: Security Boundary Validation
```python
# Before attempting sensitive operation
guidance = get_usage_guidance(guidance_type="security")
# Returns: Current security boundaries and validation of proposed operation
```

## Expected Benefits

### Security Benefits
- **RBAC Enforcement**: Prevents accidental privilege escalation through clear boundary communication
- **Token Management**: Proper JWT lifecycle management through guided workflows
- **Audit Compliance**: Clear documentation of what each access level can perform

### Usability Benefits
- **Self-Documenting**: System provides its own usage instructions contextually
- **Reduced Errors**: Clear operational patterns prevent common mistakes
- **Faster Onboarding**: New agents/users quickly understand their capabilities

### Maintenance Benefits
- **Dynamic Documentation**: Instructions stay current with permission changes
- **Centralized Logic**: Single source of truth for operational patterns
- **Extensible**: Easy to add new guidance types or access levels

## Testing Requirements

### Unit Tests
- JWT validation with various token types and expiry states
- Access level determination accuracy
- Response format validation across all access levels

### Integration Tests
- Multi-agent workflow coordination through guidance
- Token refresh scenarios
- Security boundary enforcement

### Security Tests
- Privilege escalation prevention
- Token leakage prevention
- Invalid token handling

## Implementation Timeline

**Phase 1** (Week 1): Core tool implementation with basic access level detection
**Phase 2** (Week 2): Comprehensive guidance generation for all access levels
**Phase 3** (Week 3): Integration testing with multi-agent workflows
**Phase 4** (Week 4): Security testing and production deployment

## Success Metrics

- **Security**: Zero privilege escalation incidents in multi-agent workflows
- **Usability**: 95% reduction in authentication-related support requests
- **Performance**: Sub-50ms response time for guidance generation
- **Adoption**: 100% usage in Claude Multi-Agent Framework integration

## Additional Notes

This tool is critical for the secure implementation of multi-agent AI workflows in enterprise environments. The dynamic guidance approach ensures that as the shared-context-server evolves, operational instructions remain accurate and security boundaries are properly enforced.

The tool should be designed with extensibility in mind to support future authentication patterns and agent types as the multi-agent ecosystem grows.
