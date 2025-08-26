"""
MCP Prompts for Shared Context Server Workflow Automation.

Provides user-facing prompts that automate common multi-agent workflows,
session setup, and troubleshooting operations.

Prompts:
- setup-collaboration: Initialize multi-agent session with proper configuration
- debug-session: Analyze session state and provide troubleshooting guidance
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from mcp.types import GetPromptResult, PromptMessage, TextContent

from .core_server import mcp
from .database_manager import CompatibleRow, get_db_connection


@mcp.prompt("setup-collaboration")
async def setup_collaboration_prompt(
    purpose: str,
    agent_types: list[str] | None = None,
    project_name: str | None = None,
    ctx: Any = None,  # noqa: ARG001
) -> GetPromptResult:
    """
    Initialize a multi-agent collaboration session with proper configuration.

    This prompt automates the creation of collaboration sessions, JWT token
    generation for agents, and provides implementation guidance.

    Args:
        purpose: Description of the collaboration session purpose
        agent_types: List of agent types to provision (default: ["claude", "admin"])
        project_name: Optional project name for metadata
        ctx: MCP context for authentication
    """

    # Default agent types if not specified
    if agent_types is None:
        agent_types = ["claude", "admin"]

    # Validate agent types
    valid_types = ["claude", "gemini", "admin", "system", "test", "generic"]
    invalid_types = [t for t in agent_types if t not in valid_types]
    if invalid_types:
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Invalid agent types: {invalid_types}. Valid types: {valid_types}",
                    ),
                )
            ]
        )

    # Generate session creation metadata
    metadata = {
        "setup_date": datetime.now(timezone.utc).isoformat(),
        "agent_types_requested": agent_types,
        "setup_method": "prompt_automation",
    }

    if project_name:
        metadata["project"] = project_name

    # Create the collaboration setup instructions
    instructions = f"""# Multi-Agent Collaboration Setup

## Session Configuration
**Purpose**: {purpose}
**Agent Types**: {", ".join(agent_types)}
**Project**: {project_name or "Not specified"}

## Setup Commands

### 1. Create Collaboration Session
```
create_session(
    purpose="{purpose}",
    metadata={json.dumps(metadata, indent=2)}
)
```

### 2. Generate Agent Tokens
"""

    # Add token generation commands for each agent type
    for i, agent_type in enumerate(agent_types):
        agent_id = f"agent_{agent_type}_{i + 1}"
        instructions += f"""
**{agent_type.title()} Agent**:
```
authenticate_agent(
    agent_id="{agent_id}",
    agent_type="{agent_type}"
)
```
"""

    instructions += """
### 3. Agent Coordination Pattern

**Handoff Protocol**:
1. Main agent creates session and provisions tokens
2. Share session_id and JWT tokens with subagents
3. Agents coordinate through session messages with appropriate visibility
4. Use agent memory for persistent state between handoffs

**Message Visibility Guidelines**:
- `public`: Shared coordination and status updates
- `agent_only`: Agent-type specific coordination
- `private`: Internal agent state and debugging
- `admin_only`: System-level coordination (requires admin token)

### 4. Recommended Workflow

1. **Initialize**: Create session and authenticate agents
2. **Coordinate**: Use add_message for status updates and handoffs
3. **Persist**: Use set_memory for agent-specific state management
4. **Search**: Use search_context for finding relevant information
5. **Monitor**: Check session messages for coordination status

## Client Integration

**Claude Code**: Access via `@server://info` and use session for coordination
**VS Code**: Use MCP context menu for resource access and coordination
**Direct MCP**: Use mcp__shared-context-server__* tools directly

## Next Steps

Execute the commands above in sequence, then begin your collaboration workflow.
Session will be ready for multi-agent coordination with proper authentication.
"""

    return GetPromptResult(
        messages=[
            PromptMessage(
                role="user", content=TextContent(type="text", text=instructions)
            )
        ]
    )


@mcp.prompt("debug-session")
async def debug_session_prompt(session_id: str, ctx: Any = None) -> GetPromptResult:  # noqa: ARG001
    """
    Analyze session state and provide troubleshooting guidance.

    This prompt examines session health, message patterns, agent activity,
    and provides actionable debugging recommendations.

    Args:
        session_id: Session ID to analyze
        ctx: MCP context for authentication
    """

    try:
        async with get_db_connection() as conn:
            conn.row_factory = CompatibleRow

            # Get session information
            session_cursor = await conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            )
            session = await session_cursor.fetchone()

            if not session:
                return GetPromptResult(
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"❌ Session not found: {session_id}\n\nPlease verify the session ID and try again.",
                            ),
                        )
                    ]
                )

            # Get message statistics
            msg_cursor = await conn.execute(
                "SELECT COUNT(*) as total, visibility, sender FROM messages WHERE session_id = ? GROUP BY visibility, sender",
                (session_id,),
            )
            message_stats = await msg_cursor.fetchall()

            # Get recent messages
            recent_cursor = await conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT 10",
                (session_id,),
            )
            recent_messages = await recent_cursor.fetchall()

            # Analyze session health
            analysis = f"""# Session Debug Analysis: {session_id}

## Session Overview
**Purpose**: {session["purpose"] if session["purpose"] else "Not specified"}
**Created**: {session["created_at"] if session["created_at"] else "Unknown"}
**Created By**: {session["created_by"] if session["created_by"] else "Unknown"}
**Metadata**: {json.dumps(session["metadata"] or {}, indent=2)}

## Message Activity Analysis
"""

            if message_stats:
                total_messages = sum(stat["total"] for stat in message_stats)
                analysis += f"**Total Messages**: {total_messages}\n\n"

                # Group by visibility
                visibility_counts: dict[str, int] = {}
                sender_counts: dict[str, int] = {}

                for stat in message_stats:
                    visibility = stat["visibility"]
                    sender = stat["sender"]
                    count = stat["total"]

                    visibility_counts[visibility] = (
                        visibility_counts.get(visibility, 0) + count
                    )
                    sender_counts[sender] = sender_counts.get(sender, 0) + count

                analysis += "**Message Distribution by Visibility**:\n"
                for visibility, count in visibility_counts.items():
                    analysis += f"- {visibility}: {count} messages\n"

                analysis += "\n**Message Distribution by Sender**:\n"
                for sender, count in sender_counts.items():
                    analysis += f"- {sender}: {count} messages\n"

            else:
                analysis += "**No messages found** - Session may be inactive or recently created.\n"

            # Recent activity
            analysis += "\n## Recent Activity (Last 10 Messages)\n"
            if recent_messages:
                for msg in recent_messages[-3:]:  # Show last 3 for brevity
                    content_preview = (
                        msg["content"][:100] + "..."
                        if len(msg["content"]) > 100
                        else msg["content"]
                    )
                    analysis += f"- **{msg['sender']}** ({msg['visibility']}): {content_preview}\n"
            else:
                analysis += "No recent messages found.\n"

            # Health assessment and recommendations
            analysis += "\n## Health Assessment & Recommendations\n"

            if not message_stats:
                analysis += """
**Status**: 🟡 **Inactive Session**
- Session exists but no messages have been exchanged
- **Recommendation**: Verify agents are properly authenticated and using correct session_id

**Troubleshooting Steps**:
1. Verify session_id is correct
2. Check agent JWT tokens are valid (use refresh_token if expired)
3. Test with a simple add_message call
"""
            elif len(sender_counts) == 1:
                analysis += """
**Status**: 🟡 **Single Agent Activity**
- Only one agent is active in this session
- **Recommendation**: Verify other agents have proper session access

**Troubleshooting Steps**:
1. Check if other agents have valid JWT tokens
2. Verify agents are using correct session_id
3. Test agent connectivity with add_message
"""
            else:
                analysis += """
**Status**: 🟢 **Active Multi-Agent Session**
- Multiple agents are successfully collaborating
- Message exchange is happening across visibility levels

**Optimization Opportunities**:
1. Monitor message visibility distribution for efficiency
2. Use agent memory for persistent state between handoffs
3. Leverage search_context for finding relevant information
"""

            # Common issues and solutions
            analysis += """
## Common Issues & Solutions

**Authentication Issues**:
- Use `refresh_token` if JWT tokens have expired
- Verify API_KEY is set correctly in environment
- Check agent_type permissions match required operations

**Visibility Issues**:
- Ensure agents use appropriate visibility levels
- `admin_only` requires admin-level JWT tokens
- `agent_only` messages only visible to same agent type

**Performance Issues**:
- Large message counts may slow search operations
- Consider archiving old sessions for performance
- Use memory tools for frequently accessed data

**Integration Issues**:
- Verify MCP client supports resource and prompt primitives
- Check resource URIs are properly formatted
- Validate client-side context integration

## Debug Commands

**Test Session Access**:
```
get_session(session_id="{session_id}")
```

**Search Recent Activity**:
```
search_context(session_id="{session_id}", query="recent activity", limit=5)
```

**Check Agent Memory**:
```
list_memory(session_id="{session_id}")
```
"""

            return GetPromptResult(
                messages=[
                    PromptMessage(
                        role="user", content=TextContent(type="text", text=analysis)
                    )
                ]
            )

    except Exception as e:
        error_analysis = f"""# Session Debug Error

❌ **Error analyzing session {session_id}**

**Error**: {str(e)}

## Troubleshooting Steps

1. **Verify Session ID**: Ensure the session_id is correct and exists
2. **Check Database Connectivity**: Verify database is accessible
3. **Authentication**: Ensure you have proper permissions to access session data
4. **Database State**: Check if database is properly initialized

## Recovery Commands

**List Available Sessions**:
```
# Use appropriate tool to list sessions based on your access level
```

**Create New Session** (if needed):
```
create_session(purpose="Debug recovery session")
```
"""

        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user", content=TextContent(type="text", text=error_analysis)
                )
            ]
        )
