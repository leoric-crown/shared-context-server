# Feature Planning Command

## Description

**PRP Lifecycle Stage: 1-planning (Initial Planning)**

Initiates a collaborative, multi-phase process to define, research, and plan any type of development work. This general-purpose command transforms high-level user requests **or existing planning documents** into detailed, implementation-ready plans through conversation, automated research, and structured analysis.

**Lifecycle Position**: Entry point for the 1-plan → 2-prps → 3-completed workflow
**Output**: Planning documents saved to `PRPs/1-planning/`
**Next Stage**: Use `create-prp` to transform planning into implementation specifications

**Planning Types Supported:**

- **Product Planning**: User stories, personas, Jobs-to-be-Done (JTBD)
- **Technical Planning**: Architecture, integration points, technical specifications
- **Enhancement Planning**: Existing feature improvements, refactoring needs
- **Investigation Planning**: Research tasks, proof of concepts, exploration
- **Bug Fix Planning**: Issue analysis, root cause investigation, solution design

## Workflow

### Phase 1: Session Setup & Project Context Loading (Internal)

**Goal**: Create a planning session to preserve research and decisions, then build a foundational understanding of the project's current state, architecture, and conventions before engaging the user.

1. **Create Planning Session**: Create a shared-context session for this planning stage:
   - Purpose: "Feature planning: [brief description]"
   - Metadata: Include project name, planning date, and stage indicator
   - Use session to store all research findings, decisions, and patterns discovered during planning
2. **Load Strategic Documents**: Read the content of strategic files to understand the project's high-level goals and history:
   - `PRPs/1-planning/` (recent planning sessions)
   - `PRPs/2-prps/` (active work for context)
   - `docs/` (all strategic and process guides)
   - `CLAUDE.md`, `README.md`, `SECURITY.md`
3. **Load Technical Standards**: Read the content of all tech guides to understand established patterns and best practices:
   - `.claude/guides/` (all guides)
   - `.claude/guides/testing-architecture-stability.md`
   - `.claude/guides/development-standards.md`
   - `.claude/guides/shared-context-integration.md`
   - `.claude/guides/mcp-toolkit-architecture.md`
   - `.claude/guides/browser-automation.md`
4. **Analyze Codebase Structure**: Read the output of a tree-like command listing the structure of the source directory to understand the current architecture.
5. **Store Project Context**: Add loaded project context to the planning session:
   - Project structure and architectural patterns
   - Technical standards and conventions
   - Recent planning history and active work
6. **Synthesize Initial Knowledge**: Create an internal summary of the project's purpose, established patterns, and recent development trajectory.

### Phase 2: Interactive Planning & Refinement (User-Facing)

**Goal**: To collaboratively validate, refine, or discover requirements using an adaptive conversational approach.

1. **Input Analysis**: The command first determines if a detailed planning document was provided as the primary input.

2. **Adaptive Conversation Flow**: Based on the input analysis, the command selects one of two paths:

   ______________________________________________________________________

   **Path A: Plan Refinement & Validation** (if a detailed plan was provided)

   The goal is to validate and enrich the existing plan.

   - **Confirm Understanding**: *"I have reviewed the provided document, '[Input Document Name]'. My understanding is that it outlines a [summary of plan]. Is this correct?"*
   - **Challenge Assumptions**: *"The plan recommends [specific choice]. This aligns with our project's established patterns. Do you see any concerns with this approach for this specific component?"*
   - **Probe for Gaps**: *"The plan is comprehensive on the 'how,' but could we clarify the 'why'? What specific problem are we aiming to solve?"*
   - **Finalize Scope**: *"Are there any aspects of the proposed plan you'd like to adjust for the initial version?"*

   ______________________________________________________________________

   **Path B: Discovery from Scratch** (if no detailed plan was provided)

   The goal is to elicit requirements. The command will identify the planning type and use the appropriate question set below.

   **For Product Planning:**

   - **User Persona**: *"Who is the primary user? What are they trying to accomplish?"*
   - **Problem & JTBD**: *"What specific problem does this solve? What 'job' are they hiring this for?"*
   - **Success Criteria**: *"What does success look like from the user's perspective?"*

   **For Technical Planning:**

   - **Technical Goal**: *"What system capability or architecture do we need to build?"*
   - **Integration Points**: *"How does this connect with existing systems?"*
   - **Technical Constraints**: *"What are the performance, security, or scalability requirements?"*

   **For Enhancement Planning:**

   - **Current State**: *"What exists today and what are its limitations?"*
   - **Desired State**: *"What should the improved version accomplish?"*
   - **Constraints**: *"What must remain unchanged for compatibility?"*

   **For Investigation Planning:**

   - **Research Question**: *"What specific question are we trying to answer?"*
   - **Success Criteria**: *"How will we know when we have enough information?"*
   - **Scope Boundaries**: *"What's in scope vs. out of scope for this investigation?"*

   **For Bug Fix Planning:**

   - **Problem Statement**: *"What is the specific issue and its impact?"*
   - **Reproduction Steps**: *"How can we consistently reproduce the problem?"*
   - **Root Cause Hypothesis**: *"What do we think might be causing this?"*

   ______________________________________________________________________

3. **Conclude with Agreement**: The conversation ends only when a clear, mutually agreed-upon set of validated requirements is achieved.

4. **Store Planning Decisions**: Add all conversation outcomes and decisions to the planning session:

   - User requirements and success criteria
   - Planning decisions and rationale
   - Constraints and dependencies identified
   - Scope agreements and validation outcomes

### Phase 3: Deep Research (Internal, Tool-Based)

**Goal**: To enrich the **validated requirements** with further technical context.

1. **Targeted Codebase Search**: Based on the conversation summary, use Grep and Glob tools to find relevant keywords, functions, or classes in the local codebase.
2. **Comprehensive MCP Research** using research-validated approach:
   - **crawl4ai**: Official documentation for current patterns
   - **octocode**: Well-established implementations and proven patterns from successful repositories
   - **sequential-thinking**: For complex architectural decisions requiring multi-step analysis
   - **brave-search**: Industry standards and best practices research
3. **Research Context Bundle Creation**: Consolidate findings into a structured bundle.
4. **Store Research Findings**: Add all research discoveries to the planning session:
   - MCP tool research results with sources and timestamps
   - Codebase patterns and integration points discovered
   - Technical context and architectural insights
   - Implementation approaches and best practices found

### Phase 4: Planning Document Creation (Internal)

**Goal**: To combine all gathered information into a formal planning document using progressive disclosure.

1. **Select Template Based on Complexity**:
   - **Simple/Moderate**: Use basic planning template (recommended)
   - **Complex/Comprehensive**: Use detailed planning template
2. **Document Content**:
   - **Discovery Results**: Capture conversation outcomes
   - **Research Context**: Key findings and integration points
   - **Implementation Approach**: Complexity assessment and agent recommendations
3. **Internal Review**: Ensure planning document is clear and actionable

### Phase 5: Final Validation & Planning Output (User-Facing)

**Goal**: To get final user sign-off on the standardized planning document.

1. **Present the Planning Document**: Show the complete, structured planning document to the user.

2. **Request Feedback**: *"Here is the standardized planning document based on our conversation. Does this accurately capture the scope and next steps?"*

3. **Incorporate Revisions** and **Save the Final Document** to `PRPs/1-planning/`.

4. **Add Session Metadata**: Include session information in the planning document header:

   ```markdown
   ---
   session_id: [planning_session_id]
   session_purpose: "Feature planning: [brief description]"
   created_date: [ISO timestamp]
   stage: "1-planning"
   ---
   ```

5. **Store Final Planning**: Add planning document and session reference to session:

   - Final planning document content
   - Planning session ID for future reference
   - Implementation guidance and next steps

6. **Implementation Guidance**: Provide clear next steps for implementation.

## Success Criteria

### Context Loading Success

- All strategic documents and tech guides are read and synthesized
- Project structure and patterns are understood
- Initial knowledge base is established for informed planning

### Interactive Planning Success

- User requirements are clearly captured and validated
- Planning conversation reaches mutual agreement
- All ambiguities and gaps are resolved through adaptive questioning
- Scope and constraints are clearly defined

### Research Integration Success

- Relevant codebase patterns are identified through targeted search
- MCP research provides valuable technical context:
  - **Crawl4AI**: Official documentation patterns discovered
  - **Octocode**: Proven implementation examples found
  - **SequentialThinking**: Complex architectural decisions analyzed
  - **Brave Search**: Industry best practices researched
- Research findings are consolidated into structured bundle

### Planning Document Success

- Complete, actionable planning document created
- Complexity assessment and agent recommendations included
- All conversation outcomes and research context preserved
- Document structure appropriate for implementation phase

### User Experience Success

- User maintains control over all planning decisions
- Conversation flow adapts to user input style and detail level
- Final planning document accurately reflects user intent
- Clear next steps provided for implementation

## Completion

The command is complete when the final, user-approved planning document is saved to PRPs/1-planning/ with comprehensive research context and clear implementation guidance.
