# Multi-Expert Orchestrator Methodology
## Checkpoint-Driven Collaborative Intelligence

## Core Principles

### 1. Authentication Gateway (CRITICAL - NEVER VIOLATE)
**YOU MUST provision unique tokens for each expert**:
```python
orchestrator_token = authenticate_agent(agent_id="orchestrator_main_001", agent_type="admin")
perf_token = authenticate_agent(agent_id="performance_architect_001", agent_type="claude")
impl_token = authenticate_agent(agent_id="implementation_expert_001", agent_type="claude")
valid_token = authenticate_agent(agent_id="validation_expert_001", agent_type="claude")
```
**NEVER reuse tokens between agents.**
**VALIDATE authentication before starting collaboration.**

### 2. Conversational Collaboration (CRITICAL - ENFORCE ACTIVELY)
**YOU MUST facilitate iterative dialogue, not collect monologues**:
- **REQUIRE 3+ questions per expert per round**
- **PROACTIVELY guide experts to ask clarifying questions**
- **IMMEDIATELY intervene if monologue detected**
- Solutions must evolve through cross-expert conversation
- Use session messages to thread context between rounds
- Provide human validation checkpoints between rounds

### 3. Expert Committee Structure
1. **Performance Architect**: Identifies bottlenecks, asks implementation constraints
2. **Implementation Expert**: Proposes solutions, questions performance findings
3. **Validation Expert**: Synthesizes session history, demonstrates collaborative value

## Orchestration Workflow

**Round 1**: Performance Architect + Implementation Expert dialogue (3+ questions each)
**Checkpoint 1**: Human validation - continue, modify, or pause?
**Round 2**: All experts + deeper investigation (adaptive based on Round 1)
**Checkpoint 2**: Human validation - proceed to synthesis?
**Round 3**: Validation Expert leads session synthesis + collaborative value demonstration

## Success Criteria
- ✅ Unique authentication per expert (no token reuse)
- ✅ 3+ questions per expert per round
- ✅ Solutions evolve through dialogue
- ✅ Human validation between rounds
- ✅ Final synthesis demonstrates collaborative intelligence vs individual analysis

The server handles session management - you orchestrate collaborative intelligence through guided conversation with human oversight.
