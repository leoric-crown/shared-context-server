# Generic Multi-Agent Claude Framework

This is a generic version of our proven multi-agent framework for Claude Code. It provides a complete system for intelligent agent coordination, context-enriched decision making, and high-quality development workflows.

## Framework Overview

### 5-Agent System
- **developer**: Research-first implementation with zero-error tolerance
- **tester**: Behavioral testing with modern patterns
- **refactor**: Safety-first code improvements
- **docs**: User-focused documentation
- **task-coordinator**: Multi-phase orchestration for complex work

### Smart Defaults Framework
- **Context-Enriched Decision Making**: Comprehensive context drives intelligent coordination
- **Progressive Disclosure**: Simple tasks stay simple, complex tasks get proper structure
- **Research-First Approach**: MCP tool integration for informed decisions
- **Quality Gates**: Consistent standards across all development work

## Installation

1. Copy `.claude-generic/` contents to your project's `.claude/` directory
2. Customize the `CLAUDE.md` template with your project details
3. Update tech guides with your specific technology stack
4. Configure development standards for your project requirements

## Quick Start

### 1. Customize CLAUDE.md
Replace template variables in `CLAUDE.md`:
```markdown
{{PROJECT_NAME}} → your-project-name
{{PROJECT_DESCRIPTION}} → brief description
{{PRIMARY_LANGUAGE}} → python/javascript/etc
{{PACKAGE_MANAGER}} → npm/pip/cargo/etc
```

### 2. Update Tech Guides
Customize `.claude/tech-guides/` for your stack:
- `framework-integration.md` - Your primary framework patterns
- `testing-patterns.md` - Testing tools and approaches
- `data-architecture.md` - Data handling patterns

### 3. Configure Development Standards
Update `.claude/development-standards.md`:
- File size limits (default: 500 lines code, 1000 lines tests)
- Quality tools (linting, type checking)
- Integration patterns for your architecture

## Core Features

### Intelligent Agent Coordination
```markdown
# Simple tasks (1-3 files, <2 hours)
Direct agent execution with smart defaults

# Moderate tasks (4-8 files, 2-8 hours)  
task-coordinator manages workflow with checkpoints

# Complex tasks (9+ files, >8 hours)
Multi-phase coordination with user approval gates
```

### Research-First Development
- **Crawl4AI**: Official documentation scraping
- **Octocode**: Proven implementation patterns from GitHub
- **SequentialThinking**: Multi-step architectural analysis
- **Context Preservation**: Research findings maintained across agents

### Quality Standards
- **Behavioral Testing**: Test what software does, not how
- **Visual Validation**: Screenshot capture for UI changes (when available)
- **Code Quality**: Automatic linting and type checking
- **Documentation**: User-focused guides with working examples

## Command System

### Planning & Implementation Workflow
1. **Feature Planning** (`/claude/commands/feature-planning.md`)
   - Interactive requirement discovery
   - Research integration
   - Context-aware planning

2. **PRP Generation** (`/claude/commands/generate-prp.md`)
   - Transform plans to implementation-ready specifications
   - Intelligent complexity assessment
   - Agent coordination recommendations

3. **PRP Execution** (`/claude/commands/execute-prp.md`)
   - Coordinate implementation across agents
   - Quality gates and validation
   - Context preservation throughout

## Agent Specializations

### Developer Agent
- **Research-First**: MCP tools for pattern discovery
- **KISS/DRY/YAGNI**: Simple, working solutions over complexity
- **Zero-Error Tolerance**: Fix issues immediately, never work around
- **Integration Aware**: Seamless integration with existing architecture

### Tester Agent  
- **Behavioral Focus**: Test behavior, not implementation
- **Modern Tools**: Use established testing frameworks appropriately
- **Visual Validation**: Screenshot capture for UI regression detection
- **Fast & Reliable**: Unit tests <1s, integration tests <5s

### Refactor Agent
- **Safety-First**: Zero-regression tolerance with incremental changes
- **Research-Driven**: Study proven refactoring patterns before changes
- **File Size Enforcement**: Mandatory refactoring when files exceed limits
- **Quality Preservation**: All tests must pass after refactoring

### Docs Agent
- **User-Focused**: Documentation serves users solving problems
- **Example-Driven**: Working code examples for all features
- **Error-Inclusive**: Document common problems and solutions
- **Testable Examples**: All code examples must actually work

### Task Coordinator
- **3-Checkpoint Workflow**: Plan → Implement → Complete
- **Context Preservation**: Maintain information across phases
- **Quality Gates**: Standards maintained throughout coordination
- **User Control**: Clear approval gates, no surprise implementations

## Framework Customization

### Technology Stack Integration
Update these files for your stack:
```
.claude/tech-guides/
├── framework-integration.md     # Your primary framework
├── testing-patterns.md         # Your testing tools
├── data-architecture.md        # Your data patterns
└── [custom-guides].md          # Stack-specific guides
```

### Development Standards
Configure in `.claude/development-standards.md`:
- Quality tools (eslint/ruff/etc)
- File size limits
- Testing requirements
- Integration patterns

### Command Customization
Adapt commands in `.claude/commands/`:
- Update directory paths for your project structure
- Modify workflow steps for your development process
- Customize quality gates for your standards

## Success Metrics

### Framework Effectiveness
- **Context-Driven Decisions**: Agents make intelligent choices based on comprehensive context
- **Quality Consistency**: All development work meets established standards
- **User Control**: Clear approval gates without overwhelming routing decisions
- **Knowledge Preservation**: Research and context maintained across all work

### Development Quality
- **Zero Regressions**: Changes don't break existing functionality
- **Fast Feedback**: Quality issues caught early in development
- **Maintainable Code**: Easy to understand and modify
- **User-Focused Outcomes**: Features solve real user problems

## Migration from Existing Projects

### From Basic Claude Setup
1. Copy agent definitions to `.claude/agents/`
2. Add command system to `.claude/commands/`
3. Update `CLAUDE.md` with Context-Enriched Decision Making Protocol
4. Configure tech guides for your stack

### From Track-Based Systems
1. Replace routing complexity with Smart Defaults framework
2. Consolidate agent definitions using proven patterns
3. Implement context-enriched coordination
4. Remove user routing decisions in favor of intelligent defaults

## Support & Customization

### Common Customizations
- **New Technology Stack**: Update tech guides and development standards
- **Different Project Structure**: Modify command directory paths
- **Custom Quality Tools**: Update development standards configuration
- **Additional Agents**: Follow established agent patterns for new specializations

### Framework Evolution
This framework is based on production experience with complex development workflows. The patterns have been validated through real project delivery and can be adapted to virtually any technology stack or project structure.

The key insight: **Intelligence through context, not complexity through routing**. Let comprehensive context drive agent coordination decisions rather than burdening users with workflow routing choices.

---

**Framework Version**: Based on Testinator Onboard production system  
**Agent Patterns**: Validated through 88% complete system delivery  
**Quality Standards**: Proven through zero-regression refactoring and behavioral testing