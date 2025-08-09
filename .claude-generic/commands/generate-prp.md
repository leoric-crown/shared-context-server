# Generate Product Requirement Prompt (PRP)

Transform planning output into comprehensive, implementation-ready PRPs that preserve research context and provide intelligent coordination for project architecture.

## Planning File: $ARGUMENTS

Input: Planning documents from `{{ WORKFLOW.PLANNING_DIR }}/`  
Output: Implementation-ready PRPs in `{{ WORKFLOW.ACTIVE_DIR }}/{{ PRP.NUMBER }}_feature-name.md`

## 🎯 Comprehensive PRP Generation Philosophy

**Core Principle**: Create rich, context-aware PRPs that provide enough information for intelligent coordination without requiring user routing decisions. Every PRP should contain sufficient context for agents to make intelligent decisions about scope, complexity, and architectural integration requirements.

### Research-First Approach

All PRPs are generated with comprehensive research and context analysis:

1. **Planning Context Integration**: Extract all research, decisions, and constraints from planning documents
2. **Architectural Context**: Analyze integration requirements with existing components and systems
3. **MCP Research Integration**: Incorporate relevant research findings from Crawl4AI, Octocode, and SequentialThinking
4. **Codebase Analysis**: Understand existing patterns, integration points, and architectural dependencies
5. **Quality Context**: Include testing approaches, documentation requirements, and validation needs

### Architecture-Aware Integration

All PRPs are generated with the project's foundational architecture in mind:
- **Component Coordination**: Multi-component awareness and integration requirements
- **Data Preservation**: Established data handling patterns and consistency guarantees
- **Service Integration**: External service coordination and provider management
- **Interface State Management**: User interface consistency and coordination patterns

## 📋 PRP Generation Process

### Phase 1: Planning Analysis & Context Extraction (10-15 min)

#### 1. Deep Planning Analysis
```markdown
- **Read planning document completely**
- **Extract research context** (what investigations were already done)
- **Identify architectural scope** (component integration requirements)
- **Understand user requirements** and success criteria
- **Note constraints and dependencies** identified during planning
```

#### 2. MCP Research Integration  
```markdown
- **Crawl4AI**: Integrate relevant framework documentation research
- **Octocode**: Include proven implementation patterns from similar features
- **SequentialThinking**: Incorporate architectural decision analysis
- **Tech Guide References**: Connect with established project patterns
```

#### 3. Architectural Dependency Analysis
```markdown
- **Component Integration**: Identify required integration points
- **Data Flow**: Understand data transformation and persistence requirements
- **Service Dependencies**: External service coordination needs
- **Interface Requirements**: User interface and interaction patterns
```

### Phase 2: Complexity Assessment & Agent Coordination Strategy (5-10 min)

#### Intelligent Complexity Detection
```markdown
**File Count Impact**: Number of files likely to be modified
**Integration Complexity**: Cross-component coordination requirements  
**Research Depth**: Amount of additional investigation needed
**Risk Assessment**: Potential for architectural changes or breaking changes
**Time Estimation**: Realistic implementation timeline
```

#### Smart Agent Coordination Recommendations
```markdown
- **Simple Features** (1-3 files, <2 hours): Direct agent assignment
- **Moderate Features** (4-8 files, 2-8 hours): task-coordinator for workflow management
- **Complex Features** (9+ files, >8 hours): Multi-phase coordination with checkpoints
- **Architectural Changes**: Always recommend task-coordinator for complex coordination
```

### Phase 3: Comprehensive PRP Document Creation (15-20 min)

#### Core PRP Structure
Use template structure adapted for project context:

```markdown
# PRP: {{FEATURE_NAME}}

## Research Context & Architectural Analysis
**Research Integration**: [Findings from planning and MCP research]
**Architectural Scope**: [Component integration requirements]
**Existing Patterns**: [Relevant established patterns to leverage]

## Implementation Specification
**Core Requirements**: [What must be built]
**Integration Points**: [How this connects with existing architecture]  
**Data Model Changes**: [Any data structure modifications needed]
**Interface Requirements**: [User interaction patterns]

## Quality Requirements
**Testing Strategy**: [Behavioral testing approach and coverage]
**Documentation Needs**: [User-facing docs and API documentation]
**Performance Considerations**: [Any performance or scalability requirements]

## Coordination Strategy
**Recommended Approach**: [Direct agent vs task-coordinator coordination]
**Implementation Phases**: [Logical breakdown for complex features]
**Risk Mitigation**: [Strategies for managing identified risks]
**Dependencies**: [Prerequisites and integration requirements]

## Success Criteria
**Functional Success**: [What behaviors must work correctly]
**Integration Success**: [How we verify proper system integration]
**Quality Gates**: [Testing, documentation, and validation requirements]
```

#### Context Preservation
- **Research Provenance**: Include sources and timestamps for research findings
- **Decision Rationale**: Explain architectural and design decisions
- **Assumption Documentation**: Clearly state assumptions for future validation
- **Integration Requirements**: Detailed component integration specifications

### Phase 4: Final Validation & PRP Output (5 min)

#### Quality Validation
```markdown
- **Completeness Check**: All sections contain actionable information
- **Context Richness**: Sufficient detail for intelligent agent coordination
- **Integration Clarity**: Clear architectural integration requirements
- **Success Criteria**: Measurable outcomes and validation approaches
```

#### File Generation
- **Naming Convention**: `{{NUMBER}}_feature-name.md` (increment from existing PRPs)
- **Location**: Save to `{{PROJECT_ACTIVE_DIR}}/`
- **Metadata**: Include creation date, planning source, and research context

## 🔧 Advanced PRP Features

### Context-Aware Agent Routing
Each PRP includes intelligent coordination recommendations:
- **Scope Analysis**: File count, integration complexity, research needs
- **Agent Recommendations**: Which agents are optimal for different phases
- **Coordination Requirements**: When task-coordinator should orchestrate work
- **Quality Gates**: Testing and validation checkpoints

### Research Context Integration
PRPs preserve and enhance planning research:
- **MCP Research Findings**: Integrated framework documentation and proven patterns
- **Architectural Analysis**: Deep integration requirements analysis  
- **Pattern Recognition**: Connection to established project patterns
- **Risk Analysis**: Potential challenges and mitigation strategies

### Implementation Intelligence
PRPs provide rich implementation context:
- **Existing Code Patterns**: References to similar implementations in codebase
- **Integration Templates**: Code patterns for common integration needs
- **Testing Approaches**: Specific testing strategies for the feature type
- **Documentation Requirements**: Targeted documentation needs and examples

## 📊 Success Metrics

- **Research Integration**: All planning research is preserved and enhanced in PRPs
- **Context Richness**: PRPs contain sufficient detail for intelligent agent coordination
- **Architectural Awareness**: Integration requirements are clearly specified
- **Quality Focus**: Testing and validation approaches are well-defined
- **Coordination Intelligence**: Agent routing recommendations optimize workflow efficiency

## 🎯 Completion Criteria

A PRP is complete when:
1. All planning context has been analyzed and integrated
2. Comprehensive research context is included
3. Architectural integration requirements are clearly specified  
4. Agent coordination strategy is recommended based on complexity analysis
5. Success criteria are measurable and validation approaches are defined
6. The PRP is saved to `{{PROJECT_ACTIVE_DIR}}/` with proper naming and metadata

**Next Step**: Use `execute-prp` command to implement the generated PRP with intelligent coordination.