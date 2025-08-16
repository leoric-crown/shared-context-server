# Generate Product Requirement Prompt (PRP)

## Description

**PRP Lifecycle Stage: 2-prps (Specification Creation)**

Transform planning output into comprehensive, implementation-ready PRPs that preserve research context and provide intelligent coordination for project architecture.

**Lifecycle Position**: Transforms plans from `PRPs/1-planning/` into implementation specifications
**Input**: Planning documents from `PRPs/1-planning/`
**Output**: Implementation-ready PRPs saved to `PRPs/2-prps/`
**Next Stage**: Use `run-prp` to execute implementation with intelligent coordination

## Planning File: $ARGUMENTS

Input: Planning documents from `PRPs/1-planning/`\
Output: Implementation-ready PRPs in `PRPs/2-prps/001_feature-name.md` (auto-increment number)

## Workflow

### 🎯 Comprehensive PRP Generation Philosophy

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

### Phase 1: Session Setup & Planning Analysis & Context Extraction

#### 1. Create PRP Session

```markdown
- **Create shared-context session** for this PRP creation stage
- **Purpose**: "PRP creation: [feature name from planning]"
- **Metadata**: Include project name, PRP creation date, and planning source reference
- **Use session** to store all specification research, architectural analysis, and PRP decisions
```

#### 2. Deep Planning Analysis

```markdown
- **Read planning document completely**
- **Extract research context** (what investigations were already done)
- **Identify architectural scope** (component integration requirements)
- **Understand user requirements** and success criteria
- **Note constraints and dependencies** identified during planning
- **Store planning analysis** in PRP session for reference
```

#### 3. MCP Research Integration

```markdown
- **Crawl4AI**: Integrate relevant framework documentation research
- **Octocode**: Include proven implementation patterns from similar features
- **SequentialThinking**: Incorporate architectural decision analysis
- **Tech Guide References**: Connect with established project patterns
- **Store research discoveries** in PRP session with sources and timestamps
```

#### 4. Architectural Dependency Analysis

```markdown
- **Component Integration**: Identify required integration points
- **Data Flow**: Understand data transformation and persistence requirements
- **Service Dependencies**: External service coordination needs
- **Interface Requirements**: User interface and interaction patterns
- **Store architectural analysis** in PRP session for implementation reference
```

### Phase 2: Complexity Assessment & Agent Coordination Strategy

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
- **Recommend appropriate agent** based on context and complexity assessment
- **Suggest task-coordinator** for multi-component features requiring coordination
- **Use judgment** based on architectural scope and integration requirements
- **Consider complexity factors** like research depth, integration points, and risk level
- **Store coordination strategy** in PRP session with rationale and complexity assessment
```

### Phase 3: Comprehensive PRP Document Creation

#### Core PRP Structure

Use template structure adapted for project context:

```markdown
# PRP: [Feature Name]

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

### Phase 4: Final Validation & PRP Output

#### Quality Validation

```markdown
- **Completeness Check**: All sections contain actionable information
- **Context Richness**: Sufficient detail for intelligent agent coordination
- **Integration Clarity**: Clear architectural integration requirements
- **Success Criteria**: Measurable outcomes and validation approaches
```

#### File Generation

- **Naming Convention**: `001_feature-name.md` (increment from existing PRPs)

- **Location**: Save to `PRPs/2-prps/`

- **Session Metadata**: Include session information in the PRP document header:

  ```markdown
  ---
  session_id: [prp_session_id]
  session_purpose: "PRP creation: [feature name from planning]"
  created_date: [ISO timestamp]
  stage: "2-prps"
  planning_source: [path to planning document]
  planning_session_id: [planning_session_id if available]
  ---
  ```

- **Additional Metadata**: Include creation date, planning source, and research context

- **Store final PRP**: Add complete PRP document and session reference to PRP session:

  - Generated PRP content with all specifications
  - PRP session ID for future reference
  - Links to planning session if referenced

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
6. The PRP is saved to `PRPs/2-prps/` with proper naming and metadata

**Next Step**: Use `execute-prp` command to implement the generated PRP with intelligent coordination.
