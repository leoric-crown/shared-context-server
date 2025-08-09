# Feature Planning Command

## Description

Initiates a collaborative, multi-phase process to define, research, and plan any type of development work. This general-purpose command transforms high-level user requests **or existing planning documents** into detailed, implementation-ready plans through conversation, automated research, and structured analysis.

**Planning Types Supported:**
- **Product Planning**: User stories, personas, Jobs-to-be-Done (JTBD)
- **Technical Planning**: Architecture, integration points, technical specifications  
- **Enhancement Planning**: Existing feature improvements, refactoring needs
- **Investigation Planning**: Research tasks, proof of concepts, exploration
- **Bug Fix Planning**: Issue analysis, root cause investigation, solution design

## Workflow

### Phase 1: Full Project Context Loading (Internal)

**Goal**: To build a foundational understanding of the project's current state, architecture, and conventions before engaging the user.

1.  **Load Strategic Documents**: Read the content of strategic files to understand the project's high-level goals and history:
    -   `{{ WORKFLOW.PLANNING_DIR }}/` (recent planning sessions)
    -   `{{ WORKFLOW.ACTIVE_DIR }}/` (active work for context)
    -   `docs/` (all strategic and process guides)
    -   `CLAUDE.md`, `README.md`, `SECURITY.md`
2.  **Load Technical Standards**: Read the content of all tech guides to understand established patterns and best practices:
    -   `.claude/tech-guides/{{ GUIDES.TECH_GUIDE_1 }}.md`
    -   `.claude/tech-guides/{{ GUIDES.TECH_GUIDE_2 }}.md`
    -   `.claude/tech-guides/{{ GUIDES.TECH_GUIDE_3 }}.md`
    -   `.claude/tech-guides/testing-patterns.md`
    -   `.claude/tech-guides/framework-integration.md`
    -   `.claude/tech-guides/data-architecture.md`
3.  **Analyze Codebase Structure**: Read the output of a tree-like command listing the structure of `{{ PROJECT.SOURCE_DIR }}/` to understand the current architecture.
4.  **Synthesize Initial Knowledge**: Create an internal summary of the project's purpose, established patterns, and recent development trajectory.

### Phase 2: Interactive Planning & Refinement (User-Facing)

**Goal**: To collaboratively validate, refine, or discover requirements using an adaptive conversational approach.

1.  **Input Analysis**: The command first determines if a detailed planning document was provided as the primary input.

2.  **Adaptive Conversation Flow**: Based on the input analysis, the command selects one of two paths:

    ---
    **Path A: Plan Refinement & Validation** (if a detailed plan was provided)

    The goal is to validate and enrich the existing plan.
    - **Confirm Understanding**: *"I have reviewed the provided document, '[Input Document Name]'. My understanding is that it outlines a [summary of plan]. Is this correct?"*
    - **Challenge Assumptions**: *"The plan recommends [specific choice]. This aligns with our project's established patterns. Do you see any concerns with this approach for this specific component?"*
    - **Probe for Gaps**: *"The plan is comprehensive on the 'how,' but could we clarify the 'why'? What specific problem are we aiming to solve?"*
    - **Finalize Scope**: *"Are there any aspects of the proposed plan you'd like to adjust for the initial version?"*

    ---
    **Path B: Discovery from Scratch** (if no detailed plan was provided)

    The goal is to elicit requirements. The command will identify the planning type and use the appropriate question set below.

    **For Product Planning:**
    -   **User Persona**: *"Who is the primary user? What are they trying to accomplish?"*
    -   **Problem & JTBD**: *"What specific problem does this solve? What 'job' are they hiring this for?"*
    -   **Success Criteria**: *"What does success look like from the user's perspective?"*

    **For Technical Planning:**
    -   **Technical Goal**: *"What system capability or architecture do we need to build?"*
    -   **Integration Points**: *"How does this connect with existing systems?"*
    -   **Technical Constraints**: *"What are the performance, security, or scalability requirements?"*

    **For Enhancement Planning:**
    -   **Current State**: *"What exists today and what are its limitations?"*
    -   **Desired State**: *"What should the improved version accomplish?"*
    -   **Constraints**: *"What must remain unchanged for compatibility?"*

    **For Investigation Planning:**
    -   **Research Question**: *"What specific question are we trying to answer?"*
    -   **Success Criteria**: *"How will we know when we have enough information?"*
    -   **Scope Boundaries**: *"What's in scope vs. out of scope for this investigation?"*

    **For Bug Fix Planning:**
    -   **Problem Statement**: *"What is the specific issue and its impact?"*
    -   **Reproduction Steps**: *"How can we consistently reproduce the problem?"*
    -   **Root Cause Hypothesis**: *"What do we think might be causing this?"*
    ---

3.  **Conclude with Agreement**: The conversation ends only when a clear, mutually agreed-upon set of validated requirements is achieved.

### Phase 3: Deep Research (Internal, Tool-Based)

**Goal**: To enrich the **validated requirements** with further technical context.

1.  **Targeted Codebase Search**: Based on the conversation summary, use Grep and Glob tools to find relevant keywords, functions, or classes in the local codebase.
2.  **Comprehensive MCP Research** using research-validated approach:
    -   **crawl4ai**: Official documentation for current patterns
    -   **octocode**: Well-established implementations and proven patterns from successful repositories
    -   **sequential-thinking**: For complex architectural decisions requiring multi-step analysis
    -   **brave-search**: Industry standards and best practices research
3.  **Research Context Bundle Creation**: Consolidate findings into a structured bundle.

### Phase 4: Planning Document Creation (Internal)

**Goal**: To combine all gathered information into a formal planning document using progressive disclosure.

1.  **Select Template Based on Complexity**:
    -   **Simple/Moderate**: Use basic planning template (recommended)
    -   **Complex/Comprehensive**: Use detailed planning template
2.  **Document Content**:
    -   **Discovery Results**: Capture conversation outcomes
    -   **Research Context**: Key findings and integration points
    -   **Implementation Approach**: Complexity assessment and agent recommendations
3.  **Internal Review**: Ensure planning document is clear and actionable

### Phase 5: Final Validation & Planning Output (User-Facing)

**Goal**: To get final user sign-off on the standardized planning document.

1.  **Present the Planning Document**: Show the complete, structured planning document to the user.
2.  **Request Feedback**: *"Here is the standardized planning document based on our conversation. Does this accurately capture the scope and next steps?"*
3.  **Incorporate Revisions** and **Save the Final Document** to `{{PROJECT_PLANNING_DIR}}/`.
4.  **Implementation Guidance**: Provide clear next steps for implementation.

## Completion

The command is complete when the final, user-approved planning document is saved to the project planning directory.