# PRP-001: Phase 0 - Project Foundation

**Document Type**: Product Requirement Prompt
**Created**: 2025-08-10
**Phase**: 0 (Foundation)
**Timeline**: 4 hours
**Priority**: Critical Foundation
**Status**: Ready for Execution

---

## Research Context & Architectural Analysis

### Planning Integration
**Source**: Final Decomposed Implementation Plan, Technical Implementation Plan, Strategic Vision
**Research Foundation**: Comprehensive multi-agent planning with specialized agents for technical setup, testing strategy, and documentation requirements
**Strategic Context**: Session-native design for multi-agent collaboration with MCP-first integration, competing against mem0's manual run_id management with built-in isolation boundaries

### Architectural Scope
**MCP Server Foundation**: FastMCP framework with stdio transport, async/await patterns, Pydantic validation
**Database Architecture**: SQLite with WAL mode for 20+ concurrent agents, aiosqlite async operations, UTC timestamp standardization
**Multi-Agent Coordination**: Session isolation boundaries, agent identity extraction, audit logging foundation
**Development Excellence**: Modern Python tooling (uv, pyproject.toml), quality gates (ruff, mypy), automated testing foundation

### Existing Patterns to Leverage
**Core Architecture Guide**: Complete database schema, MCP resource models, performance optimization patterns
**Framework Integration Guide**: FastMCP implementation patterns, connection pooling, server lifecycle management
**Development Standards**: File size limits (500 lines code, 1000 lines tests), UTC timestamp requirements, quality gate enforcement

---

## Implementation Specification

### Core Requirements

#### 1. Environment Configuration System
```bash
# Required Environment Variables
DATABASE_URL="sqlite:///./chat_history.db"
API_KEY="your-secure-api-key-here"
LOG_LEVEL="INFO"
CORS_ORIGINS="*"
MCP_SERVER_NAME="shared-context-server"
MCP_SERVER_VERSION="1.0.0"
ENVIRONMENT="development"
```

**Implementation Details**:
- `.env.example` for documentation (committed to repo)
- `.env` for actual secrets (added to `.gitignore`)
- `python-dotenv` integration for environment loading
- Environment validation with clear error messages
- Security best practices: no hardcoded secrets, proper .gitignore configuration

#### 2. Modern Python Tooling Stack
**Primary Tools**:
- **uv**: Modern Python package management (`uv init --python 3.11`)
- **pyproject.toml**: Centralized project configuration
- **ruff**: Fast Python linting and formatting
- **mypy**: Static type checking
- **python-dotenv**: Environment variable management

**Dependencies Required**:
```toml
[dependencies]
fastmcp = ">=2.0.0"
aiosqlite = ">=0.19.0"
rapidfuzz = ">=3.0.0"
pydantic = ">=2.0.0"
python-dotenv = ">=1.0.0"
httpx = ">=0.25.0"

[dev-dependencies]
pytest = ">=7.0.0"
pytest-asyncio = ">=0.21.0"
pytest-xdist = ">=3.0.0"
ruff = ">=0.1.0"
mypy = ">=1.0.0"
```

#### 3. Project Structure Standards
```
shared-context-server/
├── src/shared_context_server/
│   ├── __init__.py
│   ├── server.py          # FastMCP server setup
│   ├── database.py        # SQLite schema and operations
│   ├── models.py          # Pydantic models
│   └── tools.py           # MCP tool implementations
├── tests/
│   ├── unit/              # Unit tests with FastMCP TestClient
│   ├── integration/       # Multi-agent integration tests
│   └── performance/       # Performance benchmarking
├── docs/
│   ├── api.md            # MCP API documentation
│   └── integration.md    # Agent integration guides
├── scripts/
│   ├── dev.py            # Development server
│   └── migrate.py        # Database migrations
├── pyproject.toml        # Project configuration
├── .env.example          # Environment template
└── .github/workflows/    # CI/CD pipeline
```

#### 4. SQLite Database Foundation
**Schema Implementation** (from Core Architecture Guide):
```sql
-- Sessions table: Manages shared context workspaces
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    purpose TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT NOT NULL,
    metadata JSON,
    CONSTRAINT valid_session_id CHECK (id REGEXP '^[a-zA-Z0-9-_]{8,64}$')
);

-- Messages table: Stores all agent communications
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    visibility TEXT DEFAULT 'public' CHECK (visibility IN ('public', 'private', 'agent_only')),
    message_type TEXT DEFAULT 'agent_response',
    metadata JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_message_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id)
);

-- Agent memory table: Private persistent storage
CREATE TABLE agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(agent_id, session_id, key),
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Audit log table: Security and debugging
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    resource TEXT,
    action TEXT,
    result TEXT,
    metadata JSON
);
```

**Performance Configuration**:
```sql
PRAGMA journal_mode = WAL;           -- Enable concurrent reads/writes
PRAGMA synchronous = NORMAL;         -- Balance performance and safety
PRAGMA cache_size = -8000;           -- 8MB cache
PRAGMA temp_store = MEMORY;          -- Use memory for temp tables
PRAGMA mmap_size = 30000000000;      -- Memory-mapped I/O
PRAGMA busy_timeout = 5000;          -- 5 second timeout
PRAGMA optimize;                     -- Enable query optimizer
```

#### 5. Development Environment Setup
**Development Server**:
- FastMCP server with hot reload capability
- Structured logging with configurable levels
- Development scripts: `uv run dev`, `uv run test`, `uv run lint`
- FastMCP TestClient setup for in-memory testing (100x faster than subprocess)

### Integration Points

#### 1. MCP Server Foundation
- FastMCP server initialization with proper lifecycle management
- stdio transport configuration for MCP client communication
- Basic error handling and structured response patterns
- Context extraction for agent identity and authentication

#### 2. Database Operations
- Async SQLite operations with aiosqlite
- Connection initialization and schema creation
- Performance optimization with proper indexes and WAL mode
- UTC timestamp handling throughout data operations

#### 3. Quality Infrastructure
- Pre-commit hooks for automated quality gates
- CI/CD pipeline foundation with GitHub Actions
- Testing framework setup with FastMCP TestClient
- Code quality enforcement with ruff and mypy

### API Requirements

**Development Scripts** (pyproject.toml):
```toml
[tool.uv]
dev-dependencies = ["uvicorn", "fastapi"]

[project.scripts]
dev = "shared_context_server.scripts.dev:main"
test = "pytest tests/ -v"
lint = "ruff check . && mypy ."
format = "ruff format ."
migrate = "shared_context_server.scripts.migrate:main"
```

---

## Quality Requirements

### Testing Strategy
**Framework**: FastMCP TestClient for in-memory testing (100x performance improvement)
**Coverage Requirements**: Foundation for 85%+ line coverage, 80%+ branch coverage
**Test Categories**:
- **Unit Tests**: Database operations, environment loading, schema validation
- **Integration Tests**: FastMCP server startup, basic MCP protocol communication
- **Performance Tests**: Database connection establishment, concurrent access patterns

**Behavioral Testing Approach**:
```python
@pytest.fixture
async def test_client():
    """Create test client with in-memory database."""
    async with TestClient(mcp_server) as client:
        yield client

@pytest.mark.asyncio
async def test_database_foundation():
    """Verify database schema and configuration."""
    assert await db.execute("PRAGMA journal_mode").fetchone() == "wal"
    assert await db.execute("SELECT count(*) FROM sqlite_master").fetchone()[0] >= 4

@pytest.mark.asyncio
async def test_environment_configuration():
    """Verify environment variables load correctly."""
    assert os.getenv('DATABASE_URL') is not None
    assert os.getenv('MCP_SERVER_NAME') == 'shared-context-server'
```

### Documentation Needs
**Foundation Documentation**:
- **README.md**: Project setup, environment configuration, development workflow
- **API Documentation**: Basic FastMCP server structure and development patterns
- **Development Guide**: Modern tooling usage, quality gates, testing approach
- **Environment Guide**: Required variables, security considerations, configuration patterns

### Performance Considerations
**Foundation Performance Requirements**:
- Database schema creation: < 100ms
- Environment loading: < 10ms
- Development server startup: < 2 seconds
- Quality gate execution (lint/type check): < 30 seconds

**Concurrent Agent Preparation**:
- WAL mode enables concurrent reads during writes
- Connection pooling preparation for aiosqlitepool integration
- Index creation for efficient multi-agent access patterns

---

## Coordination Strategy

### Recommended Approach: Direct Agent Assignment
**Complexity Assessment**: Foundation phase with clear, sequential steps
**File Count**: 8-12 files (project structure, configuration, basic database)
**Integration Risk**: Low (establishing patterns, not integrating with existing systems)
**Time Estimation**: 4 hours with clear validation criteria

**Agent Assignment**: **Developer Agent** for complete Phase 0 execution
**Rationale**: Foundation requires technical setup expertise, modern tooling configuration, and database architecture implementation - all core developer agent capabilities

### Implementation Phases

#### Phase 0.1: Environment & Tooling (1.5 hours)
**Steps**:
1. **Environment Configuration** (30 minutes): .env setup, security configuration
2. **Modern Tooling Setup** (1 hour): uv, pyproject.toml, ruff, mypy configuration

**Validation Checkpoints**:
```bash
# Environment validation
ls -la | grep -E "\.(env|gitignore)"
uv run python -c "import os; print(os.getenv('DATABASE_URL'))"

# Tooling validation
uv run python --version  # Python 3.11+
uv run ruff check .      # No linting errors
uv run mypy .           # Type checking passes
```

#### Phase 0.2: Structure & Database (2.5 hours)
**Steps**:
1. **Project Structure & Standards** (1 hour): Directory structure, file limits, CI/CD foundation
2. **Database Foundation** (1 hour): Schema implementation, WAL configuration, performance optimization
3. **Development Environment** (30 minutes): Hot reload, logging, testing setup

**Validation Checkpoints**:
```bash
# Structure validation
find . -name "*.py" | head -5  # Verify organized structure

# Database validation
uv run python -c "
import asyncio
import aiosqlite
async def test():
    async with aiosqlite.connect('./chat_history.db') as db:
        result = await db.execute('PRAGMA journal_mode')
        print(await result.fetchone())
asyncio.run(test())
"

# Development environment validation
uv run dev  # Server starts successfully
```

### Risk Mitigation

#### Technical Risks
**Environment Configuration Errors**: Clear validation scripts, comprehensive .env.example
**Dependency Conflicts**: Modern uv dependency resolution, explicit version constraints
**Database Setup Issues**: Step-by-step schema creation, validation queries, error handling
**Tooling Integration Problems**: Sequential setup with validation at each step

#### Quality Risks
**Inconsistent Standards**: Pre-commit hooks enforce standards automatically
**Missing Documentation**: Documentation requirements integrated into each step
**Testing Gaps**: FastMCP TestClient setup ensures testing foundation from start

### Dependencies & Prerequisites
**External Dependencies**: Python 3.11+, uv package manager
**System Requirements**: Write access to project directory, SQLite support
**Knowledge Prerequisites**: Modern Python development patterns, async/await basics
**Architectural Prerequisites**: None (this establishes the foundation)

---

## Success Criteria

### Functional Success
**Environment Configuration**:
- ✅ `.env.example` with all required variables documented
- ✅ `.env` properly configured and excluded from git
- ✅ `python-dotenv` loading working correctly
- ✅ Environment validation scripts functional

**Modern Tooling**:
- ✅ uv package management operational with Python 3.11+
- ✅ pyproject.toml with all required dependencies and scripts
- ✅ ruff linting and formatting working without errors
- ✅ mypy type checking passing with strict configuration

**Project Structure**:
- ✅ Organized directory structure following standards
- ✅ File size limits established and documented
- ✅ Pre-commit hooks configured and functional
- ✅ CI/CD pipeline foundation in place

**Database Foundation**:
- ✅ SQLite database with complete schema implementation
- ✅ WAL mode configured for concurrent agent access
- ✅ Performance optimization settings applied
- ✅ Database validation and migration system functional

**Development Environment**:
- ✅ FastMCP development server with hot reload
- ✅ Structured logging and debugging configuration
- ✅ Development scripts operational (`uv run dev`, `uv run test`)
- ✅ FastMCP TestClient setup for testing foundation

### Integration Success
**MCP Foundation**: Basic FastMCP server structure prepared for tool implementation
**Multi-Agent Preparation**: Database schema supports session isolation and agent identity
**Quality Infrastructure**: Testing and validation framework ready for feature development
**Security Foundation**: Environment configuration and input validation patterns established

### Quality Gates
**Code Quality**:
```bash
uv run ruff check .     # No linting errors
uv run mypy .           # No type checking errors
uv run test            # Basic foundation tests pass
```

**Performance Benchmarks**:
- Database schema creation: < 100ms
- Development server startup: < 2 seconds
- Quality gate execution: < 30 seconds

**Documentation Completeness**:
- README.md with setup instructions
- Environment configuration guide
- Development workflow documentation
- API structure documentation foundation

### Validation Checklist

#### ✅ Environment Configuration
- [ ] `.env.example` exists with all required variables
- [ ] `.env` properly configured and in `.gitignore`
- [ ] Environment loading functional with validation
- [ ] Security best practices followed

#### ✅ Modern Tooling
- [ ] uv package management working with Python 3.11+
- [ ] pyproject.toml complete with dependencies and scripts
- [ ] ruff linting/formatting configured and passing
- [ ] mypy type checking configured and passing

#### ✅ Project Structure
- [ ] Directory structure organized according to standards
- [ ] File size limits documented and enforced
- [ ] Pre-commit hooks configured and functional
- [ ] CI/CD pipeline foundation established

#### ✅ Database Foundation
- [ ] SQLite schema implemented with all required tables
- [ ] WAL mode and performance optimizations applied
- [ ] Database validation and connection testing functional
- [ ] UTC timestamp handling properly configured

#### ✅ Development Environment
- [ ] FastMCP development server with hot reload working
- [ ] Logging and debugging properly configured
- [ ] Development scripts functional and tested
- [ ] FastMCP TestClient setup and operational

---

## Implementation Notes

### Critical Success Factors
1. **Sequential Validation**: Each step must be validated before proceeding to avoid compound errors
2. **Modern Tooling First**: uv and pyproject.toml establish foundation for all subsequent development
3. **Security From Start**: Environment configuration and .gitignore setup prevent credential exposure
4. **Quality Infrastructure**: Linting, type checking, and testing foundation enables high-quality development
5. **Database Performance**: WAL mode and performance optimization critical for multi-agent concurrency

### Common Pitfalls to Avoid
1. **❌ Hardcoded Configuration**: Always use environment variables for configuration
2. **❌ Missing .gitignore**: Ensure `.env` is properly excluded from version control
3. **❌ Dependency Version Issues**: Use explicit version constraints in pyproject.toml
4. **❌ Schema Validation Skip**: Always verify database schema creation with validation queries
5. **❌ Performance Configuration Skip**: WAL mode and optimization settings are critical for concurrency

### Post-Phase Integration
**Preparation for Phase 1**:
- FastMCP server structure ready for tool implementation
- Database schema supports session and message management
- Agent identity and authentication patterns established
- Testing framework ready for behavioral test development

---

## References

### Planning Documents
- [Final Decomposed Implementation Plan](../1-planning/shared-context-mcp-server/FINAL_DECOMPOSED_IMPLEMENTATION_PLAN.md)
- [Developer Technical Plan](../1-planning/shared-context-mcp-server/developer-technical-plan.md)
- [Strategic Vision & Architectural Decision](../../STRATEGIC_VISION_AND_ARCHITECTURAL_DECISION.md)

### Architecture Guides
- [Core Architecture Guide](../../.claude/tech-guides/core-architecture.md) - Database Schema, MCP Resource Models
- [Framework Integration Guide](../../.claude/tech-guides/framework-integration.md) - FastMCP Implementation Patterns
- [Development Standards](../../.claude/development-standards.md) - Quality Requirements, File Limits

### External References
- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Modern Python Development with uv](https://docs.astral.sh/uv/)
- [SQLite WAL Mode Documentation](https://sqlite.org/wal.html)

---

**Ready for Execution**: Phase 0 foundation implementation
**Next Phase**: Phase 1 - Core Infrastructure (FastMCP server, session management, message storage)
**Coordination**: Direct developer agent assignment for complete Phase 0 execution
