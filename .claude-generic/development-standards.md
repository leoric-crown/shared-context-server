# Development Rules & Standards

This document provides comprehensive development standards for {{PROJECT_NAME}}, including code structure, testing, documentation, and integration guidelines.

## Code Structure & Modularity

### Critical File Size Limits
- **CRITICAL: Never exceed file size limits - 500 lines for code files, 1000 lines for test files.** If a file approaches these limits:
  - Split into logical modules immediately
  - Use the refactor agent for systematic decomposition
  - Extract utilities, helpers, and constants
  - Create sub-packages for complex components

### Component Organization
For complex components this looks like:
- `component.py` - Main component definition and coordination logic (max 200 lines)
- `handlers.py` - Event handlers and processing functions (max 300 lines)
- `utils.py` - Helper functions and utilities (max 200 lines)
- `models.py` - Data models and validation (max 200 lines)

### Module Organization
- **Organize code into clearly separated modules**, grouped by feature or responsibility
- **Use clear, consistent imports** (prefer relative imports within packages)
- **Use established environment configuration patterns** for your technology stack

## Testing & Reliability

### Test Coverage Requirements
- **Always create unit tests for new features** (functions, classes, components, etc)
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it
- **Tests should live in a `/tests` folder** mirroring the main app structure
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### Visual Validation Integration (When Available)
- **UI tests should include visual validation** for regression detection
- **Use appropriate testing frameworks** for your UI technology
- **Screenshot Test Organization**: Use appropriate test markers for tests that capture visual state
- **Tiered Test Strategy**: Follow test importance levels (Critical → Development → Optional)
- **Resource Optimization**: Use smart caching and deduplication to optimize performance

### Code Quality Enforcement
- **Run lint checks** with appropriate tools and fix all blocking errors
- **Complexity warnings are non-blocking**: Note complexity issues but don't treat as blockers. **FIX ALL OTHER ERRORS**.
- **Consider refactoring**: Use complexity warnings as design feedback for potential improvements
- **Run type checks** (if applicable) and resolve all type annotations and errors
- **MANDATORY**: All agents that write code MUST validate lint and type compliance before checkpoints

## Agent Transparency & Escalation Standards

### Structured Status Reporting Requirements
**All agents must return structured status objects after each significant phase:**

```json
{
  "status": "SUCCESS|BLOCKED|NEEDS_INPUT|ARCHITECTURE_ISSUE|ERROR",
  "completed_tasks": ["specific tasks completed"],
  "blocked_on": "exact issue preventing progress",
  "files_modified": ["absolute file paths"],
  "research_used": ["context sources referenced"],
  "escalation_reason": "why user intervention needed",
  "next_steps": ["recommended actions"],
  "checkpoint_reached": "phase completion status"
}
```

### Universal Escalation Triggers
**Agents must STOP and escalate (never work around) when encountering:**

#### Critical Issues (Immediate Escalation)
- **Architecture Flaws**: Design issues requiring user decisions or major changes
- **Security Concerns**: Any security-related issues requiring user approval
- **Data Loss Risk**: Operations that could compromise data integrity
- **File Size Violations**: Code exceeding limits (500 lines code, 1000 lines tests) before refactoring
- **Integration Failures**: Components that fundamentally don't work together

#### Quality Issues (Escalate After Initial Investigation)
- **Test Failures**: Fundamental logic errors indicating deeper problems (not simple bugs)
- **Dependency Conflicts**: Missing dependencies that agents cannot resolve
- **Performance Issues**: Code changes causing significant performance degradation
- **Breaking Changes**: Changes that break existing APIs or functionality

#### Research & Context Issues (Escalate When Research Insufficient)
- **Insufficient Context**: Critical information missing that affects implementation decisions
- **Contradictory Requirements**: Conflicting specifications that need user clarification
- **Technology Gaps**: Technologies or patterns not covered in established tech guides

### Agent Coordination Patterns

#### Single Agent Tasks (Direct Execution)
- **Simple features** affecting 1-3 files
- **Bug fixes** with clear scope
- **Documentation updates**
- **Refactoring** within single components

#### Multi-Agent Coordination (task-coordinator)
- **Complex features** affecting 4+ files
- **Cross-component integration**
- **Architecture modifications**
- **Features requiring multiple specializations (dev + test + docs)**

## Integration & Architecture Standards

### Component Integration Requirements
- All features must integrate with existing architecture patterns
- Maintain consistency with established data handling approaches
- Support multi-component coordination when applicable
- Use UTC timestamps for all time-based functionality

### Service Integration Pattern
- Use established service integration patterns
- Implement provider fallback and error handling
- Ensure service context is preserved appropriately
- Include comprehensive integration testing

### Quality Integration Pattern
- Use existing quality infrastructure
- Follow established testing patterns
- Maintain code style and structure consistency
- Preserve context for future development

## Documentation Standards

### User-Facing Documentation Requirements
- **API Documentation**: Always include working examples
- **User Guides**: Step-by-step workflows for new features
- **Error Documentation**: Common issues and solutions
- **Integration Examples**: How features work with existing system

### Technical Documentation Requirements
- **Architecture Decisions**: Document significant architectural choices
- **Integration Patterns**: How components work together
- **Testing Approaches**: Explain testing strategies and patterns
- **Development Setup**: Keep setup instructions current

## Technology Stack Guidelines

### Framework Patterns
- Follow established patterns for your primary framework
- Use framework-specific best practices for component organization
- Leverage framework testing and validation tools
- Maintain consistency with framework conventions

### External Service Integration
- Use consistent patterns for external service communication
- Implement proper error handling and fallback strategies
- Include appropriate timeout and retry logic
- Mock external services in testing

### Performance Standards
- File operations should be efficient and well-cached
- UI updates should be responsive and not block user interaction
- Background processing should not interfere with user workflows
- Memory usage should be reasonable for typical workloads

## Success Criteria

### Code Quality Success
- All lint and type checks pass without warnings
- File size limits are respected
- Tests have appropriate coverage for functionality
- Code follows established patterns and conventions

### Integration Success
- Features work seamlessly with existing components
- No regressions in existing functionality
- External service integration is robust and well-tested
- UI changes maintain consistency with existing interface

### Documentation Success
- New features have user-facing documentation
- API changes are documented with examples
- Integration patterns are clearly explained
- Setup and development docs remain current

Remember: **Quality over speed, simplicity over complexity, working solutions over elegant plans**. When in doubt, escalate for user guidance rather than making assumptions about requirements or architecture.