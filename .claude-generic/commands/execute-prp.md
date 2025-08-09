# Execute Product Requirement Prompt (PRP)

Implement features using intelligent coordination that respects project architecture and provides consistent, high-quality outcomes.

## PRP File: $ARGUMENTS (from {{ WORKFLOW.ACTIVE_DIR }}/)

## 🎯 Intelligent Coordination Approach

**Core Principle**: Default to coordination-aware implementation that respects architectural integration, component coordination, and context preservation. Let content and context drive agent selection, not user routing decisions.

### Automatic Workflow Detection

The framework intelligently analyzes your PRP content and context to provide appropriate coordination:

- **File Pattern Analysis**: Detects which components are affected (services, data handling, UI, integration)
- **Content Scope Analysis**: Understands feature complexity, architectural impact, and integration requirements
- **Context Awareness**: Considers existing project state, active work, and component coordination needs
- **Quality Requirements**: Automatically applies appropriate testing, documentation, and validation

### Architecture-Centric Integration by Default

All work assumes and preserves the project's foundational architecture:
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

### Phase 1: Analysis & Planning (5-10 min)
1. **Content Analysis**: Automatically detect scope, complexity, and integration requirements
2. **Agent Selection**: Choose appropriate agent coordination based on detected needs
3. **Research Context**: Leverage any pre-provided research or initiate MCP research as needed
4. **Architecture Validation**: Ensure architectural approach and integration awareness

### Phase 2: Implementation Coordination (Variable Duration)
1. **Context-Rich Agent Handoffs**: Provide comprehensive context to selected agents
2. **Quality Gate Monitoring**: Ensure standards are maintained throughout implementation
3. **Integration Verification**: Validate that changes work within existing architecture
4. **Progress Tracking**: Monitor implementation progress and coordinate between agents when needed

### Phase 3: Quality Validation & Completion (10-15 min)
1. **Comprehensive Testing**: Behavioral testing with integration point validation
2. **Architecture Integration**: Ensure all components work together properly
3. **Documentation Review**: Verify user-facing changes are properly documented
4. **Final Quality Check**: Linting, type checking, and architectural compliance

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

## 🎯 Completion

Implementation is complete when:
1. All PRP requirements are functionally implemented
2. Architecture integration is verified working
3. Quality gates pass (tests, linting, documentation)
4. User acceptance criteria from PRP are met
5. No regressions in existing functionality

**Implementation Philosophy**: Leverage intelligent coordination to deliver high-quality features that integrate seamlessly with existing architecture while maintaining project standards and patterns.