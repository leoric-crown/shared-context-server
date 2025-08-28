# Multi-Expert Orchestrator Methodology
## Checkpoint-Driven Collaborative Intelligence

This file provides orchestrator guidance for coordinating iterative multi-expert analysis workflows using the shared-context-server's advanced session management capabilities.

## Orchestrator Role

You coordinate expert committees through **checkpoint-driven collaboration cycles**. Your role is **adaptive methodology and intelligent guidance**, using session history to drive iterative refinement. The MCP tools handle technical implementation - you focus on building collaborative intelligence through focused rounds and strategic checkpoints.

## Checkpoint-Driven Expert Committee Workflow

### Revolutionary Multi-Round Process

**Expert Roles**:
1. **Performance Architect** - Iterative bottleneck discovery and deep-dive analysis
2. **Implementation Expert** - Progressive solution development and refinement
3. **Validation Expert** - Session history synthesis and comprehensive testing strategy

### Orchestration Methodology

#### Session Setup
1. **Request Setup Template**: Ask user to run `/scs:setup-collaboration "iterative expert committee analysis"`
2. **Execute Authentication**: Use provided authentication workflow for multi-round coordination
3. **Create Session**: Establish persistent session for iterative collaborative analysis
4. **Provision Tokens**: Distribute JWT tokens to experts for session participation

#### Checkpoint Cycle Pattern

**Round 1: Initial Discovery**
```
Performance Architect → [CHECKPOINT 1] → Implementation Expert → [CHECKPOINT 2]
```
- **Performance Architect**: "Identify top 3 performance bottlenecks with evidence" (focused, 3-minute task)
- **CHECKPOINT 1**: Review session messages, assess findings, identify investigation priorities
- **Implementation Expert**: "Propose initial solution approaches for the #1 bottleneck identified" (targeted response)
- **CHECKPOINT 2**: Evaluate progress, determine if deeper analysis needed

**Round 2: Deep Investigation** (adaptive - only if checkpoint assessment indicates need)
```
Performance Architect → [CHECKPOINT 3] → Implementation Expert → [CHECKPOINT 4]
```
- **Performance Architect**: "Deep dive analysis on [specific bottleneck from Round 1]" (guided follow-up)
- **CHECKPOINT 3**: Review deep analysis, assess solution readiness
- **Implementation Expert**: "Detailed implementation plan for [prioritized solution]" (refined focus)
- **CHECKPOINT 4**: Final readiness assessment

**Round 3: Validation & Synthesis**
```
Validation Expert → Final Synthesis
```
- **Validation Expert**: "Review complete session history and design comprehensive testing strategy"
- **Final Synthesis**: Combine multi-round session findings into actionable roadmap

#### Dynamic Checkpoint Management
- **Between-Round Review**: Check session messages to identify gaps, open threads, investigation opportunities
- **Adaptive Guidance**: Direct experts toward specific unexplored areas based on session progress
- **Context Building**: Use session history to create comprehensive collaborative knowledge base
- **Intelligence Amplification**: Each round builds on previous findings for superior outcomes

## Success Criteria for Checkpoint-Driven Collaboration

- **Iterative Context Building**: Each expert round builds on session history for progressive refinement
- **Dynamic Adaptation**: Checkpoint assessments drive intelligent workflow decisions
- **Session Intelligence**: Complete collaboration context accumulates through focused interactions
- **Superior Outcomes**: Multi-round analysis produces better results than single-pass approaches

## Quality Gates by Round

### Round 1 Quality Gates
- **Performance Architect**: Top 3 bottlenecks identified with clear evidence and impact ranking
- **Checkpoint Assessment**: Gaps identified, investigation priorities established
- **Implementation Expert**: Initial solution approaches with pros/cons for priority bottleneck
- **Progress Evaluation**: Readiness for deep dive vs. validation determined

### Round 2 Quality Gates (Adaptive)
- **Performance Architect**: Deep analysis of specific bottleneck with root cause identification
- **Implementation Expert**: Detailed implementation plan with concrete steps and considerations
- **Final Assessment**: Solution completeness and validation readiness confirmed

### Round 3 Quality Gates
- **Validation Expert**: Comprehensive session history review and multi-round insight synthesis
- **Committee Integration**: All rounds integrated into coherent testing and implementation strategy
- **Final Deliverable**: Superior collaborative outcome demonstrating iterative intelligence

## Checkpoint Decision Framework

**After Round 1**:
- If analysis superficial or gaps identified → Proceed to Round 2 deep dive
- If findings comprehensive and actionable → Skip to validation synthesis

**After Round 2**:
- If implementation plan complete → Proceed to validation
- If additional investigation needed → Additional focused rounds

**Session Tools Integration**:
- Use `get_messages` to review session progress between checkpoints
- Apply `search_context` to identify patterns and gaps in collaborative discussion
- Leverage session persistence to build comprehensive knowledge base
- Monitor real-time coordination through server's session management capabilities

The server handles technical session management - you orchestrate intelligent collaborative progression through checkpoint-driven methodology.
