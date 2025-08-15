# Shared-Context-Server Bug Reports & Feature Requests

**Date:** 2025-08-14
**Reporter:** Claude Framework Integration Testing
**Testing Context:** Comprehensive exploration for Claude Multi-Agent Framework integration

---

## Bug Report #1: Message Threading Parent-Child Relationships Not Implemented

### Summary
Message threading functionality appears to be partially implemented but not functional. Parent-child message relationships cannot be established through the `parent_message_id` parameter.

### Expected Behavior
- `add_message` tool should accept `parent_message_id` parameter to create threaded conversations
- Messages should maintain parent-child relationships for organized conversation flows
- Message retrieval should preserve and display threading structure
- Threading should work across different agents within same session

### Actual Behavior
- `parent_message_id` parameter causes validation errors when used
- Error: `Input validation error: '226' is not valid under any of the given schemas`
- No threading relationships are established between messages
- Messages appear as flat list without hierarchical structure

### Steps to Reproduce
1. Create a session and add a parent message (store returned message_id)
2. Attempt to add a reply message with `parent_message_id` set to the parent's ID
3. Observe validation error regardless of data type (integer, string)

### Test Case Details
```
Parent Message ID: 226 (returned from successful message creation)
Attempted Parent References:
- parent_message_id: 226 (integer)
- parent_message_id: "226" (string)
Both result in: Input validation error: '226' is not valid under any of the given schemas
```

### Impact
- **High Impact for Framework Integration**: Threading is crucial for multi-agent workflow coordination
- Prevents organized conversation flows in complex multi-phase tasks
- Forces flat message structure which reduces context clarity
- Affects user experience in framework command coordination

### Workaround
Use message metadata to reference related messages:
```json
{
  "metadata": {
    "reply_to_message_id": 226,
    "conversation_thread": "feature_planning_thread"
  }
}
```

### Additional Context
- All other message functionality works correctly (visibility, search, metadata)
- Session management and message storage are stable
- This appears to be a feature that was designed but never fully implemented

---

## Feature Request #1: Role-Based Agent-Only Message Visibility

### Summary
Current `agent_only` message visibility is too restrictive for multi-agent frameworks. Messages should be visible to agents with the same role/purpose, not just the exact same agent identity.

### Current Behavior
- `agent_only` messages are visible only to the exact same agent (`agent_id` + `agent_type`)
- Different instances of the same agent role cannot see each other's coordination messages
- Prevents effective role-based coordination in multi-agent systems

### Requested Behavior
**Option A: Role-Based Visibility (Preferred)**
- `agent_only` messages visible to agents with same `agent_type`
- Example: All `agent_type: "claude"` agents can see each other's `agent_only` messages
- Maintains isolation from different agent types (e.g., `claude` vs `gemini`)

**Option B: Custom Role Tags**
- Add optional `role` parameter to agent authentication
- `agent_only` messages visible to agents with same `role` value
- More granular control: `role: "developer"` vs `role: "tester"`

### Use Case: Claude Framework Integration
The Claude Framework uses 5 specialized agents:
- `claude_framework_developer` (multiple instances)
- `claude_framework_tester` (multiple instances)
- `claude_framework_refactor`
- `claude_framework_docs`
- `claude_framework_coordinator`

**Need:** Developer agent instances should coordinate through `agent_only` messages without exposing details to tester/docs agents.

### Current Test Results
```
Agent 1: framework_developer_agent_1 (agent_type: "claude")
Agent 2: framework_developer_agent_2 (agent_type: "claude")
Agent 3: framework_tester_agent (agent_type: "gemini")

Visibility Matrix (Current):
- Agent 1 sees: Only own agent_only messages
- Agent 2 sees: Only own agent_only messages
- Agent 3 sees: No agent_only messages from Agent 1 or 2

Desired Visibility Matrix:
- Agent 1 sees: Own + Agent 2 agent_only messages (same role)
- Agent 2 sees: Own + Agent 1 agent_only messages (same role)
- Agent 3 sees: No agent_only messages from Agent 1 or 2 (different role)
```

### Business Impact
- **Critical for Multi-Agent Frameworks**: Enables proper role-based coordination
- Reduces need for `public` messages that expose internal coordination to users
- Maintains security isolation between different agent roles
- Enables scalable multi-instance agent deployments

### Proposed Implementation
**Authentication Enhancement:**
```json
{
  "agent_id": "framework_developer_instance_1",
  "agent_type": "claude",
  "role": "developer",  // NEW: Optional role field
  "requested_permissions": ["read", "write"]
}
```

**Message Visibility Logic:**
- `private`: Only sender agent (`agent_id` + `agent_type`)
- `agent_only`: All agents with same `role` (if provided) or same `agent_type` (fallback)
- `public`: All agents
- `admin_only`: Admin permission required

### Alternative Workarounds
**Current:** Use `public` messages for role coordination (exposes to users)
**Metadata-based:** Use message metadata for role filtering (requires custom search logic)

### Priority
**Medium** - This would improve multi-agent coordination efficiency. Public messages provide viable workaround for cross-role coordination.

---

## Feature Request #2: Role-Based Memory Sharing and Access Control

### Summary
Current memory system enforces complete isolation between all agents by design. This feature request proposes optional memory sharing capabilities to enable convenient role-based collaboration in multi-agent frameworks.

### Current Behavior
- **Complete Memory Isolation**: Each agent (`agent_id` + `agent_type`) has completely isolated memory namespace
- **No Cross-Agent Access**: Agents cannot access, view, or modify each other's memory
- **Identical Key Isolation**: Multiple agents can use identical key names without conflict or visibility
- **Both Scopes Isolated**: Isolation applies to both global and session-scoped memory

### Test Results: Memory Isolation Verification
```
Test Setup:
- Agent 1: framework_developer_agent_1 (agent_type: "claude")
- Agent 2: different_developer_agent (agent_type: "claude")
- Agent 3: framework_tester_agent (agent_type: "gemini")

Memory Operation Test:
1. Agent 1 sets: key="role_coordination.developer_shared_state", value={...}
2. Agent 2 attempts access: "Memory not found"
3. Agent 2 sets same key: Successfully creates separate memory
4. Agent 1 retrieves: Still sees original value (unchanged)
5. Agent 2 retrieves: Sees only their own value

Result: Complete namespace isolation confirmed
```

### Requested Behavior
**Option A: Role-Based Shared Memory (Preferred)**
- Add optional `shared` parameter to `set_memory` with role-based access control
- Shared memories accessible to agents with same `agent_type` or custom `role`
- Maintains private memory for agent-specific state

**Option B: Explicit Memory Sharing**
- Add `share_memory` tool to explicitly grant access to specific agents/roles
- Granular control over which memories are shared vs private
- Audit trail of memory sharing permissions

**Option C: Workspace-Based Memory**
- Add `workspace` concept for shared memory pools
- Agents join workspaces to access shared memory space
- Clean separation between private and collaborative memory

### Use Case: Claude Framework Integration

**Current Challenge:**
```
Multi-Agent Workflow Scenario:
1. Developer Agent 1: Implements feature, stores progress in private memory
2. Developer Agent 2: Needs to continue implementation, must coordinate via messages
3. Tester Agent: Needs implementation context, accesses via session messages
4. Coordinator Agent: Tracks progress through session message coordination

Current Reality: Coordination works through session messages but shared memory would be more convenient
```

**Desired Workflow State Sharing:**
```json
Shared Memory Structure:
{
  "workflow.feature_123.state": {
    "current_phase": "implementation",
    "progress": 0.7,
    "assigned_agents": ["developer_1", "developer_2"],
    "shared_context": {...}
  },
  "workflow.feature_123.implementation": {
    "files_modified": ["src/auth.py", "tests/auth_test.py"],
    "tests_status": "passing",
    "next_steps": [...]
  }
}

Access Control:
- Developers: Read/Write access to implementation details
- Testers: Read access to implementation, Write access to test results
- Coordinator: Read access to all, Write access to workflow state
```

### Business Impact
- **Convenience Enhancement**: Would enable more efficient shared state management
- **Alternative Exists**: Session-based coordination through messages provides viable workaround
- **Developer Experience**: Shared memory would be more intuitive than message-based state passing
- **Performance Optimization**: Direct memory access potentially faster than message-based coordination

### Proposed Implementation

**Enhanced Memory API:**
```json
set_memory with sharing:
{
  "key": "workflow.shared_state",
  "value": {...},
  "access_control": {
    "visibility": "role_shared",  // private, role_shared, public
    "allowed_roles": ["developer", "coordinator"],
    "permissions": {
      "developer": ["read", "write"],
      "coordinator": ["read"]
    }
  }
}
```

**Backward Compatibility:**
- Default behavior remains private (no breaking changes)
- Existing private memories unaffected
- Opt-in sharing through new parameters

### Security Considerations
- **Access Control**: Fine-grained permissions per role/agent
- **Audit Trail**: Track memory access and modifications
- **Data Isolation**: Maintain security boundaries between different frameworks
- **Session Boundaries**: Shared memory should respect session isolation

### Alternative Workarounds
**Viable Current Approaches:**
- **Session Messages**: Use public/agent_only messages in shared sessions for coordination
- **Long-lived Sessions**: Sessions can persist for entire workflows (hours/days)
- **Message-based State**: Pass state through messages with search for discovery
- **Session Memory + Message Coordination**: Combine approaches for optimal workflow management

**These approaches work well but shared memory would provide a more intuitive developer experience.**

### Priority
**Low-Medium** - This is a convenience enhancement that would improve developer experience. Session-based coordination provides viable alternatives for multi-agent frameworks.

### Additional Context
- Memory persistence across authentication confirmed ✅
- TTL and lifecycle management work correctly ✅
- Search and organization patterns work well ✅
- Only missing: Cross-agent memory visibility and sharing

---

## Testing Environment Details

**MCP Server:** shared-context-server
**Testing Framework:** Claude Code with comprehensive exploration methodology
**Test Coverage:**
- Authentication & Identity System ✅
- Message System (visibility, search, threading) ⚠️
- Memory System (scoping, TTL, organization) ✅
- Multi-Agent Coordination Patterns ⚠️

**Related Documentation:**
- Full exploration results: `tech-guides/shared-context-integration.md`
- Framework integration patterns documented with workarounds for current limitations

## Contact
**Integration Team:** Claude Framework Development
**Testing Date:** 2025-08-14
**Follow-up:** Available for additional testing, implementation validation, or clarification of requirements.
