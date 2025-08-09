# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The year is 2025.

## Repository Overview

This is the **Shared Context Server** project - a centralized memory store enabling multiple AI agents (Claude, Gemini, etc.) to collaborate on complex tasks through shared conversational context. The system implements a RESTful "Context as a Service" pattern following blackboard architecture principles.

## Current Status & Roadmap

**System Readiness**: 5% complete - Fresh repository with comprehensive planning documentation. Ready for MVP implementation phase.

### ✅ Completed Infrastructure
- **Planning Documentation**: Comprehensive MVP patterns and advanced research documentation
- **Claude Framework**: Multi-agent coordination system with research-backed customizations
- **Architecture Design**: RESTful API design with SQLite persistence and async patterns
- **Research Foundation**: FastAPI best practices, multi-agent patterns, and blackboard architecture analysis

### 🎯 Current Milestone: MVP Implementation
- **Phase 1**: Core API endpoints (POST /sessions, POST /sessions/{id}/messages, GET /sessions/{id})
- **Phase 2**: SQLite database schema and async operations with FastAPI + Pydantic validation
- **Phase 3**: Agent integration patterns and basic authentication for multi-agent access

### 📋 Future Milestones
- **Production Scale**: PostgreSQL/Redis integration, tiered memory architecture, memory distillation
- **Advanced Features**: Authentication/authorization (OAuth2), agent role-based access, procedural memory (skills library)

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
- **Python 3.9+** with **pip** and **requirements.txt** (recommended for dependency management)
- **Core Libraries**: 
  - **FastAPI** (high-performance async web framework with automatic validation)
  - **Pydantic** (data validation and settings management using type hints)
  - **aiosqlite** (async SQLite operations for non-blocking database access)
  - **httpx** (async HTTP client for agent integration testing)

### Environment Variables
```bash
# Essential configuration for shared context server
DATABASE_URL="sqlite:///./chat_history.db"  # SQLite database path
API_KEY="your-secure-api-key"               # Authentication for agent access
LOG_LEVEL="INFO"                            # Logging level (DEBUG, INFO, WARNING, ERROR)
CORS_ORIGINS="*"                            # CORS origins for web clients
```

### Setup & Installation
```bash
# Install dependencies
pip install "fastapi[standard]" aiosqlite pydantic httpx pytest pytest-asyncio

# Run development server
fastapi dev main.py

# Run tests
pytest tests/ -v
```

### Critical Requirements
- **UTC Timestamps**: System uses UTC throughout for message timestamps and session coordination
- **File Permissions**: Write access to current directory for SQLite database file creation
- **Storage**: SQLite database stored in project root (`./chat_history.db`) with automatic schema initialization
- **Runtime Support**: Python 3.9+ with async/await support for FastAPI and aiosqlite operations

## Core Architecture

### Data Organization
- **Session-Based Structure**: Complete session isolation with unique session IDs eliminating cross-session interference
- **Database Schema**: Single `chat_history` table with session_id, sender, content, timestamp fields for efficient querying
- **Agent Integration**: Smart agent identification and message routing with automatic session management

### Component & Service Systems
- **Session Manager**: Full session lifecycle management with auto-cleanup and SQLite persistence for message history
- **Smart Coordination**: HTTP request/response with async patterns, FastAPI automatic validation and error handling
- **Multi-Agent Integration**: RESTful API endpoints supporting Claude, Gemini, and custom agents with bearer token authentication
- **Database Operations**: Async SQLite operations with aiosqlite for non-blocking I/O and concurrent agent access

### Data System & Types
- **Message Format**: JSON entries with `sender`, `content`, `timestamp` fields, supports structured agent responses
- **Flexible Structure**: session_id (required), sender (required), content (required), timestamp (auto-generated)
- **Message Categories**: human_input (user messages), agent_response (AI responses), system_status (coordination), tool_output (function results)

## Key API Endpoints

Core RESTful endpoints for agent integration:
- `POST /sessions` - Creates new session and returns session_id (required for all operations)
- `POST /sessions/{id}/messages` - Adds message to session with sender and content validation
- `GET /sessions/{id}` - Retrieves complete message history for session
- `GET /sessions/{id}/messages?limit=N` - Retrieves recent N messages (pagination support)
- `DELETE /sessions/{id}` - Cleanup session and associated messages (optional)
- `GET /health` - Health check endpoint for monitoring
- `GET /docs` - FastAPI automatic API documentation
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