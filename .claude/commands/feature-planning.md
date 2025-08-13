# Feature Planning Command

## Description

Initiates a collaborative, multi-phase process to define, research, and plan any type of development work. This general-purpose command transforms high-level user requests **or existing planning documents** into detailed, implementation-ready plans through conversation, automated research, and structured analysis.

**Core Principles:**

- **KISS (Keep It Simple, Stupid)**: Always favor the simplest solution that meets requirements
- **YAGNI (You Aren't Gonna Need It)**: Build only what's needed now, not what might be needed later
- **Minimal Viable Implementation**: Start with the smallest working solution
- **Quality Balance**: Simple doesn't mean sloppy - maintain code quality, security, and architectural consistency

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
    - `PRPs/1-planning/` (recent planning sessions)
    - `PRPs/3-completed/` (completed work for context)
    - `docs/` (all strategic and process guides)
    - `CLAUDE.md`, `README.md`, `SECURITY.md`
2.  **Load Technical Standards**: Read the content of all tech guides to understand established patterns and best practices:
    - `.claude/tech-guides/core-architecture.md`
    - `.claude/tech-guides/framework-integration.md`
    - `.claude/tech-guides/testing.md`
    - `.claude/tech-guides/security-authentication.md`
    - `.claude/tech-guides/performance-optimization.md`
    - `.claude/tech-guides/data-validation.md`
    - `.claude/tech-guides/error-handling.md`
    - `.claude/tech-guides/ci.md`
3.  **Analyze Codebase Structure**: Read the output of a tree-like command listing the structure of `src/` to understand the current FastMCP server architecture.
4.  **Synthesize Initial Knowledge**: Create an internal summary of the Shared Context MCP Server's purpose, multi-agent coordination patterns, and recent development trajectory.

### Phase 2: Interactive Planning & Refinement (User-Facing)

**Goal**: To collaboratively validate, refine, or discover requirements using an adaptive conversational approach with strong KISS/YAGNI focus.

1.  **Input Analysis**: The command first determines if a detailed planning document was provided as the primary input.

2.  **Simplicity-First Questions**: Before diving into requirements, always ask:

    - _"What's the absolute minimum that would solve this problem?"_
    - _"Can we solve this with existing functionality first?"_
    - _"What would the simplest possible version look like?"_
    - _"How can we keep this simple while following our established patterns?"_

3.  **Adaptive Conversation Flow**: Based on the input analysis, the command selects one of two paths:

    ***

    **Path A: Plan Refinement & Validation** (if a detailed plan was provided)

    The goal is to validate and simplify the existing plan.

    - **Confirm Understanding**: _"I have reviewed the provided document, '[Input Document Name]'. My understanding is that it outlines a [summary of plan]. Is this correct?"_
    - **Simplicity Challenge**: _"Looking at this plan, what's the absolute minimum we could build that would still solve the core problem?"_
    - **YAGNI Review**: _"Which parts of this plan are 'nice to have' vs 'must have' for the first working version?"_
    - **Existing Solutions**: _"Can we solve any of this with our current FastMCP tools and database schema?"_
    - **Finalize Minimal Scope**: _"What's the smallest version that would provide real value to users?"_

    ***

    **Path B: Discovery from Scratch** (if no detailed plan was provided)

    The goal is to elicit requirements. The command will identify the planning type and use the appropriate question set below.

    **For Product Planning:**

    - **Core Problem**: _"What's the one specific problem this solves? (Not multiple problems)"_
    - **Minimal User**: _"Who is the primary user and what's the simplest thing they need?"_
    - **Success Criteria**: _"What's the minimum that would make this valuable?"_
    - **YAGNI Check**: _"What features can we skip for version 1?"_

    **For Technical Planning:**

    - **Simplest Solution**: _"What's the most straightforward way to solve this?"_
    - **Existing Tools**: _"Can we use our current FastMCP tools and SQLite schema?"_
    - **Minimal Changes**: _"What's the smallest change that would work?"_
    - **Architecture Fit**: _"How does this fit with our established patterns and code style?"_
    - **Quality Considerations**: _"What's the simplest approach that maintains our security and performance standards?"_

    **For Enhancement Planning:**

    - **Core Pain Point**: _"What's the one biggest limitation we need to fix?"_
    - **Minimal Fix**: _"What's the simplest change that would improve this?"_
    - **Backward Compatibility**: _"How do we keep this simple while maintaining compatibility?"_
    - **Incremental Approach**: _"Can we improve this in small, simple steps?"_

    **For Investigation Planning:**

    - **Single Question**: _"What's the one specific question we need to answer?"_
    - **Minimal Research**: _"What's the least amount of research that would give us confidence?"_
    - **Simple Success**: _"What's the simplest way to know we have enough information?"_

    **For Bug Fix Planning:**

    - **Root Cause**: _"What's the simplest explanation for this issue?"_
    - **Minimal Reproduction**: _"What's the shortest way to reproduce this?"_
    - **Simple Fix**: _"What's the most straightforward solution?"_

    ***

4.  **Simplicity Validation**: Before concluding, always confirm:

    - _"Is this the simplest solution that could work?"_
    - _"Are we building only what's needed now?"_
    - _"Can we make this even simpler?"_
    - _"Does this maintain our code quality and architectural consistency?"_

5.  **Conclude with Agreement**: The conversation ends only when a clear, mutually agreed-upon set of **minimal** validated requirements is achieved.

### Phase 3: Minimal Research (Internal, Tool-Based)

**Goal**: To find the **simplest existing solutions** and avoid reinventing the wheel.

1.  **Existing Solutions First**: Before any external research, thoroughly search the local codebase:

    - Look for similar functionality that already exists
    - Find patterns we can reuse or extend simply
    - Identify existing tools that solve part of the problem

2.  **Focused External Research** (always):

    - **octocode**: Look for minimal, proven implementations that follow good practices
    - **brave-search**: Industry-standard simple solutions with quality considerations
    - **Ref**: Fetch documentation for relevant frameworks and technologies
    - **Balance**: Simple solutions that maintain security, performance, and maintainability

3.  **Simplicity-Focused Bundle**: Consolidate findings emphasizing:
    - Simplest working solutions that follow established patterns
    - Existing tools we can leverage or extend cleanly
    - Minimal changes that maintain code quality
    - Architectural consistency with current design

### Phase 4: Minimal Planning Document Creation (Internal)

**Goal**: To create the simplest possible planning document that enables implementation.

1.  **Always Use Simple Template**: Default to the basic planning template unless absolutely necessary

    - **Prefer**: Simple, actionable plans
    - **Avoid**: Over-detailed specifications

2.  **Minimal Document Content**:

    - **Problem Statement**: One clear problem we're solving
    - **Minimal Solution**: Simplest approach that works within our architecture
    - **Existing Tools**: What we can reuse or extend
    - **Quality Considerations**: How we maintain security, performance, and code standards
    - **Implementation Steps**: Smallest possible increments
    - **YAGNI Notes**: What we're explicitly NOT building

3.  **Simplicity Review**: Ensure the plan is:
    - Clear and actionable
    - Minimal but complete
    - Focused on immediate needs only
    - Consistent with established architecture and code quality standards

### Phase 5: Expert Review & Approval (Collaborative)

**Goal**: To get technical validation and approval from specialized agents before finalizing the plan.

1.  **Share Plan with Expert Agents**: Present the minimal planning document to both:

    - **@agent-developer**: For technical feasibility, architecture alignment, and implementation approach
    - **@agent-tester**: For testability, quality assurance considerations, and testing strategy

2.  **Request Structured Feedback**: Ask each agent to evaluate:

    - **Technical Soundness**: Does this align with our established patterns and architecture?
    - **Implementation Feasibility**: Are the proposed steps realistic and achievable?
    - **Quality Considerations**: Does this maintain our security, performance, and code standards?
    - **Testing Strategy**: Is this plan testable and does it include appropriate quality gates?
    - **Simplicity Validation**: Is this truly the minimal viable solution?

3.  **Collaborative Refinement**:

    - Address any concerns or suggestions from the expert agents
    - Refine the plan based on technical feedback
    - Ensure consensus on the approach before proceeding

4.  **Approval Gate**: The plan proceeds to Phase 6 only when both agents provide explicit approval or the concerns are resolved to their satisfaction. However, if there are mixed signals from the expert agents or you determine the task formulation is still unclear, an optional user validation step should occur before Phase 6:
    - **Mixed Signals**: When @agent-developer and @agent-tester provide conflicting feedback or recommendations
    - **Unclear Requirements**: When research and/or expert feedback reveal fundamental gaps in the task definition
    - **Scope Ambiguity**: When agents suggest significantly different approaches or interpretations
    - **User Clarification**: Present the conflicting feedback and ask the user to clarify priorities, resolve conflicts, or provide additional context
    - **Refined Planning**: Use the user's clarification to refine the plan and re-submit for expert review if necessary

### Phase 6: Final Validation & Planning Output (User-Facing)

**Goal**: To get final user sign-off on the expert-validated, minimal, actionable planning document.

1.  **Present the Expert-Validated Plan**: Show the simple, focused planning document that has been reviewed and approved by the expert agents.
2.  **Simplicity Confirmation**: _"Here is the minimal planning document based on our conversation and expert review. This focuses on the simplest solution that solves the core problem while maintaining our quality standards. Does this capture what we need to build first?"_
3.  **Expert Validation Summary**: _"This plan has been reviewed and approved by @agent-developer for technical feasibility and @agent-tester for quality assurance."_
4.  **YAGNI Reminder**: _"Note that this plan intentionally excludes [list of excluded features] - we can add these later if needed."_
5.  **Incorporate Final Revisions** and **Save the Final Document** to `PRPs/1-planning/`.
6.  **Simple Implementation Guidance**: Provide clear, minimal next steps for implementation.

## Completion

The command is complete when the final, user-approved **minimal** planning document is saved to the project planning directory. The plan should represent the simplest possible solution that solves the core problem, with clear notes about what we're NOT building (YAGNI).
