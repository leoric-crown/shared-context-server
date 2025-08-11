# Execute Product Requirement Prompt (PRP)

Implement features using intelligent coordination that respects project architecture and provides consistent, high-quality outcomes.

## PRP File: $ARGUMENTS (from PRPs/2-prps/)

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
- **UTC Timestamps**: Consistent time coordination across all MCP operations
- **FastMCP Integration**: MCP tool and resource coordination with async patterns
- **Multi-Agent Coordination**: Shared context sessions and agent memory isolation
- **Database Operations**: aiosqlite with connection pooling for concurrent agent access
- **Memory Architecture**: Three-tier memory system (public context, private notes, agent memory)

## 🤖 Intelligent Agent Coordination

Based on content analysis and architectural requirements, agents are automatically selected:

### Core Coordination Team
- **developer**: Research-first FastMCP implementation with async/await patterns
- **tester**: Behavioral testing with FastMCP TestClient and multi-agent scenarios
- **refactor**: Safety-first improvements when file size or complexity triggers
- **docs**: User-focused MCP server documentation and API examples
- **task-coordinator**: Multi-phase orchestration for complex MCP server features

### Smart Agent Selection Logic
```
Content Analysis Results → Agent Selection:

• FastMCP implementation needed → developer (always)
• MCP tool/resource changes → tester (behavioral + multi-agent testing)
• Files >500 lines → refactor (automatic safety trigger)
• New MCP server features → docs (API documentation + examples)
• Database schema changes → task-coordinator (multi-phase orchestration)
• Multi-agent coordination → specialized testing and validation
• External service integration → enhanced fallback and error handling
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
- **Behavioral Testing Focus**: Test MCP tools and resources behavior, not implementation
- **Multi-Agent Testing**: Verify concurrent agent access and session isolation
- **FastMCP TestClient**: In-memory testing patterns for rapid feedback
- **API Documentation**: User-focused MCP server documentation and examples

## 🚀 Advanced Coordination Scenarios

### Complex MCP Server Features
For multi-agent coordination features affecting 4+ files or requiring >8 hours of work:
1. **task-coordinator** orchestrates multi-phase MCP implementation
2. **Phased approach**: Plan → Implement → Test Multi-Agent → Validate
3. **Quality gates**: Checkpoints at each phase with user approval
4. **Context preservation**: Maintain MCP server architecture and agent coordination patterns

### Database Schema Modifications
For changes affecting core MCP server architecture or multi-agent patterns:
1. **Architecture-first analysis**: Understand impact on multi-agent coordination
2. **Incremental approach**: Small, safe database migrations with validation
3. **Multi-agent testing**: Comprehensive testing of concurrent access patterns
4. **Rollback planning**: Clear rollback strategy for database schema changes

### Agent Memory Integration Work
For agent memory systems or external service coordination:
1. **Memory pattern analysis**: Use established three-tier memory architecture
2. **Fallback strategy**: Implement memory fallback and TTL expiration handling
3. **Context isolation**: Ensure proper agent memory isolation and sharing
4. **Behavioral testing**: FastMCP TestClient testing for memory operations

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
6. **Move completed PRP to PRPs/3-completed/** for archival

**Implementation Philosophy**: Leverage intelligent coordination to deliver high-quality features that integrate seamlessly with existing architecture while maintaining project standards and patterns.
