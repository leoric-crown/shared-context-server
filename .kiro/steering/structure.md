# Project Structure & Organization

## Repository Layout

```
shared-context-server/
├── src/shared_context_server/          # Main application code
│   ├── __init__.py                     # Package initialization
│   ├── server.py                       # FastMCP server and MCP tools
│   ├── models.py                       # Pydantic data models (1000+ lines)
│   ├── database.py                     # Database operations and connection management
│   ├── config.py                       # Configuration management with BaseSettings
│   ├── auth.py                         # JWT authentication and authorization
│   ├── tools.py                        # MCP tool definitions
│   ├── scripts/                        # Utility scripts
│   │   ├── dev.py                      # Hot reload development server
│   │   └── cli.py                      # Command-line interface
│   └── utils/                          # Utility modules
│       ├── caching.py                  # Multi-level caching implementation
│       ├── performance.py              # Performance monitoring
│       └── llm_errors.py               # LLM-optimized error messages
├── tests/                              # Test suite (443 tests, 85%+ coverage)
│   ├── conftest.py                     # Test fixtures and modern database testing
│   ├── unit/                           # Unit tests for individual functions
│   ├── integration/                    # Integration tests for components
│   ├── behavioral/                     # End-to-end behavioral tests
│   ├── security/                       # Security-specific tests
│   └── performance/                    # Performance benchmarks
├── docs/                               # Comprehensive documentation
│   ├── api-reference.md                # Complete API documentation
│   ├── dev-quick-start.md              # 30-second development setup
│   ├── development-setup.md            # Detailed development guide
│   ├── integration-guide.md            # AutoGen, CrewAI, LangChain examples
│   ├── troubleshooting.md              # Common issues and solutions
│   └── production-deployment.md        # Docker/Kubernetes deployment
├── .claude/                            # Claude-specific configuration
│   └── tech-guides/                    # Detailed technical guides
│       ├── core-architecture.md        # System architecture and database schema
│       ├── framework-integration.md    # FastMCP implementation patterns
│       ├── data-validation.md          # Pydantic models and validation
│       ├── error-handling.md           # Comprehensive error management
│       ├── performance-optimization.md # Performance patterns and monitoring
│       ├── security-authentication.md  # Security implementation
│       └── testing.md                  # Testing patterns and strategies
├── migrations/                         # Database schema migrations
├── logs/                               # Application logs
├── .kiro/steering/                     # Kiro steering documents
├── pyproject.toml                      # Project configuration and dependencies
├── .env.example                        # Environment configuration template
└── README.md                           # Project overview and quick start
```

## Core Module Organization

### src/shared_context_server/

#### server.py - FastMCP Server Implementation
- **Primary Role**: MCP server setup and tool definitions
- **Key Components**:
  - FastMCP server initialization with lifespan management
  - 15+ MCP tool implementations (create_session, add_message, search_context, etc.)
  - Database connection pooling setup
  - Agent identity extraction from context
- **Pattern**: Each MCP tool follows consistent error handling and response format
- **Dependencies**: Uses database.py for operations, models.py for validation

#### models.py - Comprehensive Data Models (1000+ lines)
- **Primary Role**: Pydantic v2 models for all data validation
- **Key Components**:
  - Core models: SessionModel, MessageModel, AgentMemoryModel
  - Request/Response models for all MCP tools
  - Validation utilities and sanitization functions
  - Error response models with detailed validation feedback
- **Pattern**: All models include comprehensive field validation, sanitization, and security checks
- **Critical**: Moved validation from SQL CHECK constraints to Pydantic for better error messages

#### database.py - Database Operations
- **Primary Role**: Database connection management and operations
- **Key Components**:
  - DatabaseManager class with connection pooling
  - Schema initialization and migration support
  - Optimized SQLite configuration (WAL mode, performance pragmas)
  - Connection factory with performance settings
- **Pattern**: All operations use connection pooling and proper error handling
- **Performance**: Configured for 20+ concurrent agents with WAL mode

#### config.py - Configuration Management
- **Primary Role**: Environment-based configuration with validation
- **Key Components**:
  - Hierarchical configuration sections (database, security, operational, development)
  - Pydantic BaseSettings for type-safe configuration
  - Environment variable validation with helpful error messages
  - Production vs development configuration support
- **Pattern**: All configuration validated at startup with clear error messages

#### auth.py - Authentication & Authorization
- **Primary Role**: JWT authentication and agent identity management
- **Key Components**:
  - JWT token generation and validation with MCP audience validation
  - AgentIdentity class with permission checking
  - Role-based access control (RBAC) implementation
  - Token refresh and blacklisting support
- **Security**: Prevents token reuse attacks with audience validation

### utils/ - Utility Modules

#### caching.py - Multi-Level Caching
- **Components**: TTL cache, LRU eviction, layered caching strategy
- **Performance**: 10-100x improvement for hot data access
- **Pattern**: Different TTL values for different data types

#### performance.py - Performance Monitoring
- **Components**: Operation timing, performance metrics collection, slow operation detection
- **Integration**: Decorator-based monitoring with statistics reporting

#### llm_errors.py - LLM-Optimized Error Messages
- **Purpose**: Error messages designed for LLM consumption with recovery suggestions
- **Pattern**: Structured error responses with actionable guidance

## Testing Architecture

### Modern Database Testing Infrastructure
- **Approach**: Real SQLite databases instead of mocks for better test fidelity
- **Benefits**: Tests survive schema changes, test actual database constraints
- **Pattern**: Each test gets isolated database with complete schema

### Test Categories
```
tests/
├── unit/                    # 60% - Business logic, validation, utilities
├── integration/             # 30% - MCP tools, database operations, API endpoints
├── behavioral/              # 10% - End-to-end user journeys, multi-agent scenarios
├── security/                # Security-specific tests (auth, validation, injection)
└── performance/             # Performance benchmarks and optimization validation
```

### Key Testing Patterns
- **FastMCP Testing**: Use `call_fastmcp_tool()` helper to handle FieldInfo defaults
- **Database Testing**: Use `test_db_manager` fixture for isolated real databases
- **Mock Context**: Use `MockContext` objects (not dictionaries) for agent identity
- **Agent Isolation**: Test multi-agent scenarios with shared sessions but isolated memory

## Configuration Patterns

### Environment Configuration Hierarchy
1. **`.env` file**: Primary configuration source
2. **Environment variables**: Override .env values
3. **Default values**: Fallback defaults in Pydantic models
4. **Validation**: All configuration validated at startup

### Critical Environment Variables
```bash
# Required
API_KEY=your-secure-api-key-replace-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key

# Database
DATABASE_PATH=./chat_history.db
DATABASE_MAX_CONNECTIONS=20

# Server
MCP_TRANSPORT=http
HTTP_PORT=23456

# Performance
LOG_LEVEL=INFO
ENABLE_PERFORMANCE_MONITORING=true
```

## Development Workflow

### Hot Reload Development
```bash
# Start development server with automatic restart on file changes
MCP_TRANSPORT=http HTTP_PORT=23456 uv run python -m shared_context_server.scripts.dev
```

### Code Quality Pipeline
```bash
# Run all quality checks
uv run ruff check .          # Linting
uv run ruff format .         # Formatting
uv run mypy src/             # Type checking
uv run pytest tests/         # Testing

# Quality gates (all must pass)
uv run ruff check . && uv run mypy . && uv run pytest
```

### Testing Workflow
```bash
# Run specific test categories
uv run pytest tests/unit/              # Unit tests only
uv run pytest tests/behavioral/        # Behavioral tests only
uv run pytest -m "not slow"            # Skip slow tests
uv run pytest --cov=src --cov-report=html  # With coverage report
```

## Documentation Structure

### Technical Documentation Hierarchy
1. **README.md**: Project overview and quick start
2. **docs/dev-quick-start.md**: 30-second development setup
3. **docs/development-setup.md**: Comprehensive development guide
4. **docs/api-reference.md**: Complete API documentation with examples
5. **.claude/tech-guides/**: Detailed technical implementation guides

### Integration Documentation
- **docs/integration-guide.md**: AutoGen, CrewAI, LangChain integration examples
- **docs/troubleshooting.md**: Common issues and diagnostic procedures
- **docs/production-deployment.md**: Docker, Kubernetes, monitoring setup

## Architectural Patterns

### Three-Tier Memory Architecture
```
Public Context (Blackboard)     # messages table, visibility='public'
├── Private Notes (Scratchpad)  # messages table, visibility='private'
└── Agent Memory (KV Store)     # agent_memory table, TTL support
```

### MCP Resource Model
```
session://{session_id}          # Session resources with real-time updates
agent://{agent_id}/memory       # Agent memory resources (private)
```

### Database Schema Pattern
- **Core Tables**: sessions, messages, agent_memory, audit_log
- **Performance Indexes**: Optimized for common query patterns
- **Constraints**: Moved from SQL to Pydantic for better error handling
- **Concurrency**: SQLite WAL mode for 20+ concurrent agents

## Security Architecture

### Input Validation Pipeline
1. **Pydantic Models**: Type validation and field constraints
2. **Custom Validators**: Business logic validation and sanitization
3. **SQL Parameters**: Parameterized queries prevent injection
4. **Output Sanitization**: Clean responses for client consumption

### Authentication Flow
1. **JWT Generation**: With MCP audience validation
2. **Token Validation**: Audience, expiration, signature verification
3. **Agent Identity**: Extract permissions and role information
4. **Authorization**: Check permissions for each operation

## Performance Architecture

### Critical Performance Optimizations
1. **Connection Pooling**: aiosqlitepool (2-20 connections)
2. **RapidFuzz Search**: 5-10x faster than difflib
3. **Multi-Level Caching**: Session, message, search, memory caches
4. **SQLite WAL Mode**: Concurrent reads with single writer
5. **Async/Await**: Non-blocking operations throughout

### Monitoring Integration
- **Performance Metrics**: Operation timing and statistics
- **Cache Statistics**: Hit rates and performance data
- **Database Monitoring**: Connection pool usage and query performance
- **Error Tracking**: Comprehensive audit logging

## Migration and Evolution

### Database Migrations
- **Location**: `migrations/` directory
- **Pattern**: Numbered migration files with rollback support
- **Example**: `002_add_sender_type_column.py`

### Schema Evolution Strategy
- **Pydantic Models**: Handle schema changes gracefully
- **Database Testing**: Real databases ensure migration compatibility
- **Backward Compatibility**: Maintain API compatibility during transitions

## Best Practices

### Code Organization
- **Single Responsibility**: Each module has clear, focused purpose
- **Dependency Injection**: Use connection pooling and configuration injection
- **Error Boundaries**: Comprehensive error handling at module boundaries
- **Type Safety**: Full type hints with mypy validation

### Testing Organization
- **Test Isolation**: Each test gets clean database state
- **Real Dependencies**: Use real databases and connections where possible
- **Behavioral Focus**: Test what the system does, not how it does it
- **Performance Validation**: Include performance benchmarks in test suite
