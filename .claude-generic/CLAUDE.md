# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The year is 2025.

## Repository Overview

This is the **[ADAPT: Project name from repository analysis and conversation]** project - [ADAPT: Project description based on detected purpose and user input]. The system [ADAPT: Project purpose and value proposition from conversation].

## Current Status & Roadmap

**System Readiness**: [ADAPT: Project completion percentage from user conversation]% complete - [ADAPT: Current status description based on user input].

### ✅ [ADAPT: Completed Infrastructure - adapt based on detected architecture and project maturity]
- **[ADAPT: Main Component Name]**: [ADAPT: Component description based on detected architecture]
- **[ADAPT: Data Component Name]**: [ADAPT: Data handling description based on detected patterns]  
- **[ADAPT: Service Component Name]**: [ADAPT: Service layer description based on detected integration]
- **[ADAPT: Interface Component Name]**: [ADAPT: Interface description based on detected UI/API patterns]

### 🎯 [ADAPT: Current Milestone based on user conversation about current work and goals]
- **Phase 1**: [ADAPT: Current phase description from user input]
- **Phase 2**: [ADAPT: Next phase description from user input]
- **Phase 3**: [ADAPT: Final phase description from user input]

### 📋 [ADAPT: Future Milestones - include if user provides roadmap information]
- **[ADAPT: Next Milestone]**: [ADAPT: Next milestone description from user planning]
- **[ADAPT: Future Milestone]**: [ADAPT: Future milestone description from user vision]

## Context-Enriched Decision Making Protocol

- **Executive Context Authority**: You will maintain decision-making authority based on comprehensive context across all agent interactions and research findings
- **Research Context Building**: Proactively gather and organize research context (Crawl4AI, Octocode, SequentialThinking, etc.) to inform intelligent coordination decisions
- **Cross-Agent Context Synthesis**: Integrate findings from agent status reports, research discoveries, and implementation progress to make informed coordination choices
- **Context-Informed Coordination**: Use enriched context to make intelligent agent selection, workflow routing, and complexity assessment decisions
- **Citation & Provenance Tracking**: All research includes source URLs, timestamps, and context provenance for transparency and decision justification
- **Dynamic Context Updates**: Continuously enrich context based on agent findings, user feedback, and implementation discoveries to improve decision quality
- **Intelligent Decision Making**: Use enriched context to make coordination decisions when possible, escalate to user when context is insufficient

## Environment & Setup

### Prerequisites & Key Dependencies
- **[ADAPT: Detected programming language and version]** with **[ADAPT: Detected package manager]** (recommended)
- **Core Libraries**: [ADAPT: List of main libraries/frameworks detected in project analysis - include name and purpose for each]

### Environment Variables
```bash
# [ADAPT: Configuration section - include only if environment variables detected]
# [ADAPT: Environment variables based on detected services and integrations]
# Examples: DATABASE_URL, API_KEY, LOG_LEVEL, etc.
```

### Setup & Installation
```bash
# [ADAPT: Installation command based on detected package manager]
# Examples: "npm install", "pip install -e .", "cargo build"

# [ADAPT: Verification command based on detected CLI structure]
# Examples: "npm run dev --help", "python main.py --help", "./target/release/app --help"
```

### Critical Requirements
- **UTC Timestamps**: [ADAPT: Include only if time-based functionality detected - system uses UTC throughout for coordination]
- **File Permissions**: [ADAPT: Write access requirements based on detected data storage patterns]
- **Storage**: [ADAPT: Default storage locations based on detected data persistence patterns]
- **Runtime Support**: [ADAPT: Runtime requirements based on detected dependencies and environment needs]

## Core Architecture

### Data Organization
- **Self-Contained Structure**: Complete directory structure per {{ DATA.ENTITY_TYPE }} with `{{ DATA.CONFIG_FILE }}` eliminating global registry complexity
- **Legacy Support**: Flexible file discovery for both standard (`{{ DATA.STANDARD_PATH }}/`) and legacy (`{{ DATA.LEGACY_PATH }}/`) locations
- **Interactive Selection**: Smart {{ DATA.ENTITY_TYPE }} selection with auto-detection

### Component & Service Systems
- **{{ ARCHITECTURE.MAIN_MANAGER }}**: Full state persistence, auto-save, recovery with {{ ARCHITECTURE.COORDINATOR }} for multi-component coordination
- **Smart Coordination**: {{ ARCHITECTURE.COORDINATION_TIMEOUT }} timeouts with graceful cleanup, performance thresholds ({{ ARCHITECTURE.PERFORMANCE_THRESHOLD_1 }} ≤{{ ARCHITECTURE.THRESHOLD_1 }}, {{ ARCHITECTURE.PERFORMANCE_THRESHOLD_2 }} >{{ ARCHITECTURE.THRESHOLD_2 }})
- **{{ ARCHITECTURE.SERVICE_INTEGRATION }}**: Production services with {{ ARCHITECTURE.SERVICE_PATTERN }}, provider fallback chain ({{ ARCHITECTURE.PRIMARY_PROVIDER }} → {{ ARCHITECTURE.SECONDARY_PROVIDER }} → {{ ARCHITECTURE.TERTIARY_PROVIDER }})
- **{{ ARCHITECTURE.SERVICE_WORKFLOWS }}**: Component-integrated with {{ ARCHITECTURE.PROCESSING_TYPE }} processing, {{ ARCHITECTURE.MANAGEMENT_TYPE }} management, and {{ ARCHITECTURE.COORDINATION_PATTERN }} coordination patterns

### Data System & Types
- **{{ DATA.FORMAT }}**: Entries with `{{ DATA.TYPE_FIELD }}` fields ({{ DATA.TYPE_1 }}, {{ DATA.TYPE_2 }}, {{ DATA.TYPE_3 }}), supports detailed hierarchy or {{ DATA.SIMPLE_TYPE }} data
- **Flexible Structure**: {{ DATA.REQUIRED_TYPES }} (required), {{ DATA.OPTIONAL_TYPES }} (optional, can use "{{ DATA.DEFAULT_OPTION }}")
- **{{ DATA.CATEGORY_NAME }}**: {{ DATA.TYPE_1 }} ({{ DATA.TYPE_1_DESC }}), {{ DATA.TYPE_2 }} ({{ DATA.TYPE_2_DESC }}), {{ DATA.TYPE_3 }} ({{ DATA.TYPE_3_DESC }}), {{ DATA.TYPE_4 }} ({{ DATA.TYPE_4_DESC }}), {{ DATA.TYPE_5 }} ({{ DATA.TYPE_5_DESC }})

## Key Data Fields

Core data structure for manual and automated enhancement:
- `{{ FIELDS.KEY_FIELD_1 }}` - {{ FIELDS.FIELD_1_DESC }} (required)
- `{{ FIELDS.KEY_FIELD_2 }}` - {{ FIELDS.FIELD_2_DESC }} OR "{{ FIELDS.DEFAULT_VALUE_2 }}"
- `{{ FIELDS.KEY_FIELD_3 }}` - {{ FIELDS.FIELD_3_DESC }} OR "{{ FIELDS.DEFAULT_VALUE_3 }}"
- `{{ FIELDS.KEY_FIELD_4 }}` - {{ FIELDS.FIELD_4_DESC }} (user editable)
- `{{ FIELDS.KEY_FIELD_5 }}` - {{ FIELDS.FIELD_5_DESC }} (user editable)
- `{{ FIELDS.KEY_FIELD_6 }}` - {{ FIELDS.FIELD_6_VALUES }}
- `{{ FIELDS.KEY_FIELD_7 }}` - {{ FIELDS.FIELD_7_DESC }} (0.0-1.0, when {{ FIELDS.CONDITION_7 }})
- `{{ FIELDS.KEY_FIELD_8 }}` - {{ FIELDS.FIELD_8_DESC }}
- `{{ FIELDS.KEY_FIELD_9 }}` - {{ FIELDS.FIELD_9_DESC }}

## Development Standards & Guidelines

### Core Principles  
- **Component-Centric Design**: All functionality built around unified interactive components with persistent state
- **Manual-First + Enhancement**: Core workflows work manually; automated assistance is optional and additive
- **Data Preservation**: Zero-loss data using {{ ARCHITECTURE.DATA_PRESERVATION_SYSTEM }} architecture
- **Progressive Enhancement**: Build core functionality first, add advanced features incrementally
- **Context-Enriched Executive Authority**: Main Claude maintains decision-making authority using comprehensive context across agent tasks and research findings to make intelligent coordination decisions

### Quality Standards
- **File Size Limit**: Maximum 500 lines per code file, 1000 lines per test file
- **UTC Timestamps**: Always use `datetime.now(timezone.utc)` for system operations
- **Testing**: {{ TESTING.FRAMEWORK }} unit tests required for all new code, visual validation for UI changes
- **📸 Screenshot Requirements**: Screenshot capture recommended for UI changes with before/after visual validation
- **Code Quality**: `{{ QUALITY.LINT_COMMAND }}` and `{{ QUALITY.TYPE_CHECK_COMMAND }}` must pass before commits
- **Component Integration**: Always integrate with {{ ARCHITECTURE.MAIN_MANAGER }} for state persistence
- **Service Infrastructure**: Use existing {{ ARCHITECTURE.SERVICE_TYPE }} and component integration patterns

### Implementation Standards
- **Follow PRP specifications exactly** - match detailed specifications in `{{ WORKFLOW.PRP_DIRECTORY }}/` directory
- **Leverage existing infrastructure** - {{ ARCHITECTURE.MAIN_MANAGER }}, {{ ARCHITECTURE.COORDINATOR }}, {{ ARCHITECTURE.DATA_SYSTEM }}
- **Agent Coordination**: Use intelligent coordination based on detected scope and complexity, with structured status reporting and escalation triggers for architecture issues, test failures, security concerns, file size violations, dependency conflicts, integration failures

**Comprehensive Standards**: `.claude/development-standards.md`, `.claude/workflows/{{ WORKFLOW.VISUAL_WORKFLOW_NAME }}.md`

## {{ VISUAL.VALIDATION_SECTION_TITLE }}

📸 **Recommended**: Screenshot capture for UI changes during agent development for visual validation.

### Agent Requirements
- **developer**: Screenshot capture recommended for UI implementations and modifications
- **tester**: Visual regression testing and validation when appropriate
- **refactor**: Screenshots when refactoring affects UI components  
- **docs**: Visual validation when documenting UI features

### Key Commands
- `{{ VISUAL.COMMAND_1 }}` - Most useful for detecting UI changes
- Screenshots recommended for: UI layout changes, component state changes, user interaction flows, modal changes, interface modifications

**Complete Documentation**: `.claude/workflows/{{ WORKFLOW.VISUAL_WORKFLOW_NAME }}.md`

## CLI Commands Available

### Core Commands
- **{{ CLI.COMMAND_1.NAME }}**: `{{ PROJECT.NAME }} {{ CLI.COMMAND_1.SYNTAX }}` - {{ CLI.COMMAND_1.DESC }}
- **{{ CLI.COMMAND_2.NAME }}**: `{{ PROJECT.NAME }} {{ CLI.COMMAND_2.SYNTAX }}` - {{ CLI.COMMAND_2.DESC }}
- **{{ CLI.COMMAND_3.NAME }}**: `{{ PROJECT.NAME }} {{ CLI.COMMAND_3.SYNTAX }}` - {{ CLI.COMMAND_3.DESC }}
- **{{ CLI.COMMAND_4.NAME }}**: `{{ PROJECT.NAME }} {{ CLI.COMMAND_4.SYNTAX }}` - {{ CLI.COMMAND_4.DESC }}
- **{{ CLI.COMMAND_5.NAME }}**: `{{ PROJECT.NAME }} {{ CLI.COMMAND_5.SYNTAX }}` - {{ CLI.COMMAND_5.DESC }}

### Planned Interface Commands (Not Implemented)
Unified interface slash commands: `/{{ CLI.SLASH_1 }}`, `/{{ CLI.SLASH_2 }}`, `/{{ CLI.SLASH_3 }}`, `/{{ CLI.SLASH_4 }}`, `/{{ CLI.SLASH_5 }}`, `/{{ CLI.SLASH_6 }}`, `/{{ CLI.SLASH_7 }}`, `/{{ CLI.SLASH_8 }}`

### Automation Tools
- `{{ CLI.AUTOMATION_TOOL_1 }}` - {{ CLI.AUTOMATION_DESC_1 }}
- Use `{{ PROJECT.NAME }} --help` or `{{ PROJECT.NAME }} <command> --help` for detailed command information

---

## References

### Agent System
- `.claude/agents/developer.md` - Research-first implementation (MCP tools)
- `.claude/agents/tester.md` - Modern testing (behavioral, {{ TESTING.FRAMEWORK_NAME }})
- `.claude/agents/refactor.md` - Safety-first refactoring specialist
- `.claude/agents/docs.md` - User-focused documentation
- `.claude/agents/task-coordinator.md` - Multi-phase orchestration

### Tech Guides
- `.claude/tech-guides/{{ GUIDES.TECH_GUIDE_1 }}.md` - {{ GUIDES.GUIDE_1_DESC }}
- `.claude/tech-guides/{{ GUIDES.TECH_GUIDE_2 }}.md` - {{ GUIDES.GUIDE_2_DESC }}
- `.claude/tech-guides/{{ GUIDES.TECH_GUIDE_3 }}.md` - {{ GUIDES.GUIDE_3_DESC }}
- `.claude/tech-guides/testing-patterns.md` - {{ GUIDES.TESTING_DESC }}
- `.claude/tech-guides/framework-integration.md` - {{ GUIDES.INTEGRATION_DESC }}
- `.claude/tech-guides/data-architecture.md` - {{ GUIDES.DATA_DESC }}

### Standards
- `.claude/development-standards.md` - Code quality, testing, file limits
- `.claude/workflows/{{ WORKFLOW.VISUAL_WORKFLOW_NAME }}.md` - {{ WORKFLOW.WORKFLOW_DESC }}

### Key Architecture Notes
- **⚠️ UTC Timestamps Critical**: Always use `datetime.now(timezone.utc)` for system coordination
- **{{ ARCHITECTURE.PATTERN_NAME }}**: {{ ARCHITECTURE.PATTERN_DESC }} integration required
- **Progressive Enhancement**: Core functionality first, advanced features incrementally

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.