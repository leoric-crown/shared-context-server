# Execute Product Requirement Prompt (PRP)

## Description

**PRP Lifecycle Stage: 3-completed (Implementation & Completion)**

Implement features using intelligent coordination that respects project architecture and provides consistent, high-quality outcomes.

**Lifecycle Position**: Executes PRPs from `PRPs/2-prps/` through to completion
**Input**: Implementation specifications from `PRPs/2-prps/`
**Output**: Completed features with archival to `PRPs/3-completed/`
**Completion**: Feature is production-ready with full quality validation

## PRP File: $ARGUMENTS (from PRPs/2-prps/)

## Workflow

### 🎯 Intelligent Coordination Approach

**Core Principle**: Default to coordination-aware implementation that respects architectural integration, component coordination, and context preservation. Let content and context drive agent selection, not user routing decisions.

### Automatic Workflow Detection

The framework intelligently analyzes your PRP content and context to provide appropriate coordination:

- **File Pattern Analysis**: Detects which components are affected (services, data handling, UI, integration)
- **Content Scope Analysis**: Understands feature complexity, architectural impact, and integration requirements
- **Context Awareness**: Considers existing project state, active work, and component coordination needs
- **Quality Requirements**: Automatically applies appropriate testing, documentation, and validation

### Architecture-Centric Integration by Default

All work assumes and preserves the multi-agent framework's foundational architecture:

- **UTC Timestamps**: Consistent time coordination across all operations
- **Component Integration**: Multi-component coordination and state preservation
- **Data Preservation**: Established data handling patterns with change tracking
- **Service Context Sharing**: Context preservation and coordination patterns
- **State Management**: Interface and component consistency

## 🤖 Intelligent Agent Coordination

Based on content analysis and architectural requirements, agents are automatically selected:

### Core Coordination Team

- **developer**: Research-first implementation with architectural awareness
- **tester**: Behavioral testing with integration validation
- **refactor**: Safety-first improvements when file size or complexity triggers
- **docs**: User-focused documentation when new features or APIs created
- **task-coordinator**: Multi-phase orchestration for complex architectural changes

### Smart Agent Selection Logic

```
Content Analysis Results → Agent Selection:

• Code implementation needed → developer (always)
• UI changes detected → tester (behavioral + visual regression)
• Files >500 lines → refactor (automatic safety trigger)
• New user-facing features → docs (consideration prompt)
• Architecture changes → task-coordinator (multi-phase orchestration)
• Service integration work → specialized integration validation
• Component coordination → enhanced coordination checks
```

## 📋 Standard Execution Workflow

### Phase 1: Session Setup & Analysis & Planning

1. **Create Implementation Session**: Create a shared-context session for this implementation stage:
   - Purpose: "Implementation: [feature name from PRP]"
   - Metadata: Include project name, implementation date, and PRP source reference
   - Use session to store all implementation progress, coordination decisions, and outcomes
2. **Content Analysis**: Automatically detect scope, complexity, and integration requirements
3. **Agent Selection**: Choose appropriate agent coordination based on detected needs
4. **Research Context**: Leverage any pre-provided research or initiate MCP research as needed
5. **Architecture Validation**: Ensure architectural approach and integration awareness
6. **Store Analysis Results**: Add PRP analysis and coordination strategy to implementation session

### Phase 2: Implementation Coordination (Variable Duration)

1. **Context-Rich Agent Handoffs**: Provide comprehensive context to selected agents
2. **Quality Gate Monitoring**: Ensure standards are maintained throughout implementation
3. **Integration Verification**: Validate that changes work within existing architecture
4. **Progress Tracking**: Monitor implementation progress and coordinate between agents when needed
5. **Store Implementation Progress**: Add ongoing progress, decisions, and coordination outcomes to session:
   - Agent coordination decisions and handoffs
   - Implementation milestones and progress updates
   - Quality gate results and validation outcomes
   - Integration testing results and architectural compliance

### Phase 3: Quality Validation & Completion

1. **Comprehensive Testing**: Behavioral testing with integration point validation
2. **Architecture Integration**: Ensure all components work together properly
3. **Documentation Review**: Verify user-facing changes are properly documented
4. **Final Quality Check**: Linting, type checking, and architectural compliance
5. **Store Completion Results**: Add final validation outcomes and completion status to session:
   - Final testing results and quality gate status
   - Architecture integration validation
   - Documentation completion and user experience validation
   - Production readiness assessment

## 🔧 Context-Aware Coordination Features

### Research Context Integration

- **Pre-Research Utilization**: Use research context from PRP generation to avoid duplicate work
- **Targeted MCP Research**: Additional research only when specific implementation details are needed
- **Context Preservation**: Maintain research findings throughout implementation coordination

### Architectural Awareness

- **Integration Point Detection**: Automatically identify required integration work
- **Component Coordination**: Ensure multi-component features work together seamlessly
- **State Management**: Preserve and coordinate application state appropriately
- **Service Dependencies**: Handle external service coordination and fallback scenarios

### Quality Integration

- **Behavioral Testing Focus**: Test what the software does, not how it's implemented
- **Integration Testing**: Verify components work together correctly
- **Visual Validation**: Screenshot capture for UI changes (when tooling is available)
- **Documentation Generation**: User-focused documentation for public features

## 🚀 Advanced Coordination Scenarios

### Complex Feature Implementation

For multi-component features affecting 4+ files or requiring >8 hours of work:

1. **task-coordinator** orchestrates multi-phase implementation
2. **Phased approach**: Plan → Implement → Integrate → Validate
3. **Quality gates**: Checkpoints at each phase with user approval
4. **Context preservation**: Maintain architectural context across phases

### Architectural Modifications

For changes affecting core architecture or integration patterns:

1. **Architecture-first analysis**: Understand impact before implementation
2. **Incremental approach**: Small, safe changes with validation at each step
3. **Integration testing**: Comprehensive testing of integration points
4. **Rollback planning**: Clear rollback strategy if integration issues arise

### Service Integration Work

For external service integration or provider coordination:

1. **Provider pattern analysis**: Use established service integration patterns
2. **Fallback strategy**: Implement provider fallback and error handling
3. **Context sharing**: Ensure service context is preserved appropriately
4. **Integration testing**: Mock-based testing for external service behavior

## 📊 Success Criteria

### Functional Success

- All specified features work as defined in the PRP
- Integration points function correctly with existing architecture
- Error scenarios are handled gracefully with appropriate user feedback
- Performance meets established project standards

### Architectural Success

- Changes integrate seamlessly with existing component coordination patterns
- Service integration follows established patterns and includes proper fallback
- State management maintains consistency with existing architecture
- UTC timestamp usage is consistent throughout (when time-based functionality is involved)

### Quality Success

- All tests pass including new behavioral tests for implemented features
- Code quality tools (linting, type checking) pass without warnings
- File size limits are respected (500 lines for code, 1000 for tests)
- Documentation is created for user-facing features

## Success Criteria

### Content Analysis Success

- PRP content is thoroughly analyzed for scope and complexity
- Integration requirements and architectural impact assessed
- Appropriate agent coordination strategy selected automatically
- Research context from PRP generation is preserved and utilized

### Implementation Coordination Success

- Agents receive comprehensive context for informed decision-making
- Multi-phase coordination manages complex features effectively
- Quality gates are monitored and maintained throughout implementation
- Integration verification ensures components work together properly

### Quality Validation Success

- All tests pass including new behavioral tests for implemented features
- Code quality tools (linting, type checking) pass without warnings
- File size limits are respected (500 lines for code, 1000 for tests)
- Documentation is created for user-facing features

### Architecture Integration Success

- Changes integrate seamlessly with existing project architecture
- Component coordination and state management patterns preserved
- Service dependencies and external integrations handled correctly
- No regressions in existing functionality

### User Experience Success

- All PRP requirements are functionally implemented
- User acceptance criteria from PRP are met
- Implementation matches planned scope and quality standards
- Features work as intended from user perspective

## Completion & Archival Process

### Phase 4: Completion Validation & Archival

**Goal**: Finalize implementation and archive completed work for future reference.

#### 4.1 Final Quality Validation

- **All Success Criteria Met**: Verify functional, architectural, quality, and user experience success
- **Production Readiness**: Confirm feature is ready for production deployment
- **Documentation Complete**: Ensure all user-facing documentation is finalized
- **Quality Gates Passed**: All tests, linting, and type checking completed successfully

#### 4.2 PRP Archival Process

1. **Create Completion Summary**: Document implementation outcomes and lessons learned

2. **Archive to 3-completed**: Move completed PRP from `PRPs/2-prps/` to `PRPs/3-completed/`

3. **Update Session Metadata**: Add implementation session information to the archived PRP header:

   ```markdown
   ---
   session_id: [prp_session_id]
   session_purpose: "PRP creation: [feature name]"
   created_date: [ISO timestamp]
   stage: "3-completed"
   planning_source: [path to planning document]
   planning_session_id: [planning_session_id if available]
   implementation_session_id: [implementation_session_id]
   implementation_purpose: "Implementation: [feature name]"
   completed_date: [ISO timestamp]
   quality_status: [passed/failed]
   ---
   ```

4. **Update Archive Metadata**: Include completion date, implementation approach, and quality metrics

5. **Reference Documentation**: Create any additional reference documentation for future similar features

6. **Store Implementation Session**: Add final implementation session reference and outcomes:

   - Complete implementation history and decisions
   - Implementation session ID for future reference
   - Lessons learned and patterns discovered
   - Quality metrics and validation results

#### 4.3 Lifecycle Completion

- **Pipeline Advancement**: PRP successfully moved through 1-plan → 2-prps → 3-completed
- **Knowledge Preservation**: Implementation patterns and lessons learned captured for future reference
- **Quality Assurance**: Feature meets all established project standards and user requirements

## Completion

Implementation is complete when all success criteria are met, the feature is ready for production use with comprehensive quality validation, and the PRP is properly archived in `PRPs/3-completed/`.

**Implementation Philosophy**: Leverage intelligent coordination to deliver high-quality features that integrate seamlessly with existing architecture while maintaining project standards and patterns.

**Next Steps**: Use `check-progress` to monitor the PRP lifecycle or `plan-feature` to begin planning the next feature.
