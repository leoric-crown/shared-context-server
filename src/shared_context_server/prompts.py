"""
MCP Prompts for Shared Context Server Workflow Automation.

Provides user-facing prompts that automate common multi-agent workflows,
session setup, conversational collaboration, and troubleshooting operations.

Prompts:
- setup-collaboration: Initialize multi-agent collaboration with advanced conversational protocols
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
    expert_roles: str,
    collaboration_type: str = "committee",
    session_id: str | None = None,
    iteration_rounds: str = "3",
    project_name: str | None = None,
    ctx: Any = None,  # noqa: ARG001
) -> GetPromptResult:
    """
    Initialize a multi-agent collaboration session with advanced conversational protocols.

    This comprehensive prompt combines session creation, JWT token generation, and
    research-based iterative dialogue patterns for effective multi-agent coordination.
    Based on research from Anthropic, OpenAI, Google, and academic sources.

    Args:
        purpose: Description of the collaboration session purpose
        expert_roles: Comma-separated expert roles (e.g., "performance-architect,implementation-expert,validation-expert")
        collaboration_type: Type of collaboration (committee, debate, peer-review) - default: "committee"
        session_id: Optional existing session ID to use
        iteration_rounds: Number of iterative rounds (default: "3")
        project_name: Optional project name for metadata (backward compatibility)
        ctx: MCP context for authentication
    """

    # Parse expert roles
    roles = [role.strip() for role in expert_roles.split(",") if role.strip()]
    if not roles:
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text="Error: At least one expert role must be specified.",
                    ),
                )
            ]
        )

    # Validate iteration rounds
    try:
        rounds = int(iteration_rounds)
        if rounds < 1 or rounds > 10:
            rounds = 3
    except ValueError:
        rounds = 3

    # Generate conversational collaboration setup
    timestamp = datetime.now(timezone.utc).timestamp()
    instructions = f"""# Conversational Multi-Agent Collaboration Setup

## Collaboration Configuration
**Purpose**: {purpose}
**Type**: {collaboration_type}
**Expert Roles**: {", ".join(roles)}
**Iteration Rounds**: {rounds}
**Session**: {session_id if session_id else "New session required"}

## Authentication Gateway Pattern (CRITICAL)

### 1. Unique Token Provisioning
```
# Orchestrator (Admin permissions for coordination)
orchestrator_token = authenticate_agent(
    agent_id="orchestrator_main_{timestamp:.0f}",
    agent_type="admin"
)

"""

    # Generate unique authentication for each expert role following established pattern
    for i, role in enumerate(roles):
        role_clean = role.replace("-", "_").replace(" ", "_").lower()
        agent_id = f"agent_{role_clean}_{i + 1:03d}"  # Sequential pattern for audit consistency
        instructions += f"""
# {role.title()} Expert (Unique token required)
{role_clean}_token = authenticate_agent(
    agent_id="{agent_id}",
    agent_type="claude"
)
"""

    instructions += """
```

## Conversational Collaboration Protocols

### Iterative Dialogue Pattern (Based on Academic Research)

**Round Structure**: Each round follows Explain-Question-Refine pattern
1. **Expert Analysis**: Initial focused analysis with specific findings
2. **Cross-Expert Questioning**: Agents ask clarifying questions to each other
3. **Iterative Refinement**: Solutions evolve through dialogue
4. **Checkpoint Integration**: Orchestrator synthesizes and guides next round

### Agent Conversation Instructions

#### For Expert Agents:
**CRITICAL**: You are participating in iterative dialogue, NOT delivering monologues.

**Conversation Protocol**:
- **Ask Questions**: When analysis seems incomplete, ask specific questions
- **Seek Clarification**: Challenge assumptions and request deeper detail
- **Build on Responses**: Integrate other experts' insights into your analysis
- **Iterate Solutions**: Refine your recommendations based on discussion

**Example Conversational Patterns**:
- "Performance Architect: I see database bottlenecks. Implementation Expert: Can you quantify the query complexity?"
- "Implementation Expert: Your solution assumes X. Have you considered Y constraint?"
- "Validation Expert: The testing approach needs clarification on Z. Can you elaborate?"

#### For Orchestrator Agent:
**CRITICAL**: Facilitate conversation, don't just collect individual outputs.

**Orchestration Protocol**:
1. **LAUNCH EXPERTS IN PARALLEL**: Use multiple Task tool calls in single message for concurrent collaboration
2. **Token Refresh Between Rounds**: Refresh expert tokens before each new round to prevent authentication failures
3. **Round Initiation**: "[Expert Role]: Focus on [specific aspect]. Ask questions if you need clarification from other experts."
4. **Question Facilitation**: "[Expert A] asked about X. [Expert B], please respond and feel free to ask follow-up questions."
5. **Synthesis Checkpoints**: "Based on the discussion, I'm seeing [patterns]. Let's proceed to next round with [specific focus]."
6. **Conversation Threading**: "[Expert C], you mentioned Y earlier. How does [Expert A's] new insight change your approach?"

## Checkpoint-Driven Collaboration Workflow

### Round 1: Initial Discovery with Questioning
```
# Orchestrator initiates with specific guidance
add_message(
    session_id=session_id,  # Use the session_id from creation or parameter
    content="Round 1: [Expert Role] - Analyze [specific area]. Ask questions if you need clarification from other experts.",
    visibility="public",
    sender="orchestrator_main"
)

# Experts engage in dialogue, not monologue
# Performance Architect: "I found bottlenecks X, Y, Z. Implementation Expert: Is constraint A a factor?"
# Implementation Expert: "Constraint A affects approach B. Validation Expert: How should we test scenario C?"
```

### Round 2: Deep Investigation Through Dialogue
```
# Orchestrator guides deeper investigation based on Round 1 questions
add_message(
    session_id=session_id,  # Use the session_id from creation or parameter
    content="Round 2: Deep dive on [specific issues from Round 1]. Continue asking questions to refine understanding.",
    visibility="public",
    sender="orchestrator_main"
)

# Experts build on previous dialogue
# Continue questioning and refinement based on Round 1 discoveries
```

### Round 3: Solution Synthesis Through Collaboration
```
# Final collaborative synthesis
add_message(
    session_id=session_id,  # Use the session_id from creation or parameter
    content="Round 3: Final synthesis. Review complete conversation history and create integrated solution.",
    visibility="public",
    sender="orchestrator_main"
)
```

### Final Documentation Action
```
# Save detailed team findings to demonstrate collaborative value
# Create timestamped markdown file: team-analysis-[timestamp].md
# Include: session_id, cross-expert insights, dialogue evolution, collaborative breakthroughs
# Format: ## Session Context\n**Session ID**: {session_id}\n**Timestamp**: {timestamp}
```

## Conversation Quality Indicators

**Successful Conversational Collaboration**:
- ✅ Experts launched in parallel for concurrent collaboration
- ✅ Tokens refreshed between rounds to prevent auth failures
- ✅ Experts ask clarifying questions to each other
- ✅ Solutions evolve through iterative dialogue
- ✅ Cross-expert knowledge integration visible
- ✅ Orchestrator facilitates conversation flow
- ✅ Each round builds on previous discussions
- ✅ Detailed findings saved to timestamped markdown file

**Anti-Patterns to Avoid**:
- ❌ Individual monologues without interaction
- ❌ Experts ignoring other experts' contributions
- ❌ Orchestrator collecting outputs without facilitation
- ❌ No questions or clarifications between experts

## Implementation Commands

### Session Setup
"""

    # Add conditional session creation based on session_id parameter
    if session_id:
        instructions += f"""
**Using Existing Session**: {session_id}

The session is already configured. Proceed directly to expert agent coordination.
"""
    else:
        # Generate metadata with consistent timestamp format
        session_metadata = {
            "collaboration_type": collaboration_type,
            "expert_roles": roles,
            "iteration_rounds": rounds,
            "conversation_pattern": "iterative_dialogue",
            "setup_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if project_name:
            session_metadata["project"] = project_name

        instructions += f"""
**Create New Session**:
```
session_result = create_session(
    purpose="{purpose}",
    metadata={json.dumps(session_metadata, indent=2)}
)
# Save the session_id from session_result for use in subsequent commands
session_id = session_result["session_id"]
```
"""

    instructions += """
### Expert Agent Instructions Template
```
You are participating in conversational collaboration. Your role:

1. **Analyze**: Provide focused analysis on your expertise area
2. **Question**: Ask specific questions to other experts when you need clarification
3. **Respond**: Answer questions from other experts and integrate their insights
4. **Iterate**: Refine your solutions based on ongoing dialogue
5. **Collaborate**: Build on the evolving conversation, don't work in isolation

Session ID: {session_id if session_id else '[to_be_created]'}
Your Token: [unique_token_from_authentication]
Your Role: [specific_expert_role]

IMPORTANT: This is iterative dialogue, not individual report generation.
```

## Success Metrics

**Conversational Quality**:
- Number of cross-expert questions asked
- Solutions that reference other experts' insights
- Evidence of iterative refinement across rounds
- Orchestrator guidance effectiveness

**Collaboration Outcomes**:
- Higher solution quality than individual expert approaches
- Integration of multiple expert perspectives
- Identification of insights only possible through dialogue
- Clear progression from initial analysis to refined solutions

This setup ensures expert agents engage in iterative dialogue rather than delivering isolated analyses, following best practices from leading AI research organizations.
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
