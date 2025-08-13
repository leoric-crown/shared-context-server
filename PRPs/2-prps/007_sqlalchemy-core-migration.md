# PRP-007: SQLAlchemy Core Database Migration

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-12
**Planning Source**: PRPs/1-planning/database-adapter-pattern/database-adapter-pattern.md
**Status**: Implementation Ready
**Priority**: High - Technical Debt Prevention
**Estimated Effort**: 15-20 days
**Complexity Level**: High - Architectural Change

---

## Research Context & Architectural Analysis

### Research Integration
**Planning Research Foundation**: Comprehensive feasibility analysis comparing custom database adapter patterns vs SQLAlchemy Core, with expert developer consultation validating SQLAlchemy Core as the optimal approach.

**Expert Technical Validation**: 20+ year developer assessment confirmed SQLAlchemy Core provides:
- Minimal performance overhead (<1ms vs direct SQL)
- Battle-tested connection pooling for multi-agent concurrent access
- Automatic database compatibility (183 SQL operations across 19 files)
- Industry-standard Alembic migrations
- Lower risk evolutionary change vs revolutionary rewrite

**Decision Rationale**: Rejected custom adapter pattern due to:
- Interface design inadequacy for 778-line DatabaseManager complexity
- Effort underestimation (realistic 36-49 days vs claimed 15-22)
- Performance degradation with multiple abstraction layers
- High maintenance burden for custom database-specific code

### Architectural Scope
**MCP Server Integration Requirements**:
- Preserve <30ms operation performance for real-time agent collaboration
- Maintain connection pooling for 20+ concurrent agents
- Support session isolation and multi-agent data access patterns
- Integrate with existing FastMCP tool and resource patterns
- Preserve UTC timestamp operations for agent coordination

**Existing Architecture to Preserve**:
- 778-line `DatabaseManager` class with optimized PRAGMA settings
- SQLite WAL mode enforcement and connection pooling
- Schema validation and recovery mechanisms
- 183 SQL operations across database, server, and testing modules
- Integration with FastMCP async/await patterns

### Existing Patterns to Leverage
**FastMCP Integration Patterns**:
- `@asynccontextmanager` database connection patterns
- Async/await operations for non-blocking agent access
- UTC timestamp utilities (`utc_now()`, `utc_timestamp()`)
- Error handling hierarchy (`DatabaseError`, `DatabaseConnectionError`)

**Database Schema Patterns**:
- Multi-table schema (sessions, messages, agent_memory, audit_log, secure_tokens)
- Foreign key constraints and referential integrity
- Trigger-based automatic timestamp updates
- Performance indexes for multi-agent access patterns

---

## Implementation Specification

### Core Requirements
**Primary MCP Tools/Resources**: Update existing database operations, no new MCP tools required

**SQLAlchemy Core Implementation**:
```python
# New database/sqlalchemy_manager.py
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

class SQLAlchemyDatabaseManager:
    """Unified database manager with SQLAlchemy Core."""

    def __init__(self, database_url: str):
        # Support: sqlite+aiosqlite://, postgresql+asyncpg://, mysql+aiomysql://
        engine_kwargs = self._get_engine_config(database_url)
        self.engine = create_async_engine(database_url, **engine_kwargs)
        self.metadata = MetaData()

    async def execute_query(self, query: str, params: dict = None) -> List[Dict]:
        """Execute SELECT query with automatic connection management."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]

    async def execute_update(self, query: str, params: dict = None) -> int:
        """Execute INSERT/UPDATE/DELETE with transaction support."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return result.rowcount
```

**Schema Migration with Alembic**:
```python
# alembic/env.py integration
def run_migrations():
    """Run migrations with multi-database support."""
    database_url = context.get_x_argument(as_dictionary=True).get('database_url')
    config = context.config
    config.set_main_option('sqlalchemy.url', database_url)

    with engine_from_config(config.get_section(config.config_ini_section)) as engine:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()
```

### Integration Points
**Database Module Integration** (`src/shared_context_server/database.py`):
- Replace current `DatabaseManager` with `SQLAlchemyDatabaseManager`
- Preserve all utility functions (`utc_now`, `health_check`, `cleanup_expired_data`)
- Maintain existing connection management patterns
- Keep database-specific optimizations (SQLite PRAGMA settings)

**Server Module Integration** (`src/shared_context_server/server.py`):
- Update imports to use new database manager
- Preserve all 29 SQL operations in server module
- Maintain FastMCP tool integration patterns
- Keep async/await operation patterns

**Configuration Integration** (`src/shared_context_server/config.py`):
```python
class DatabaseConfig(BaseModel):
    database_url: str = Field(
        default="sqlite+aiosqlite:///./chat_history.db",
        description="SQLAlchemy database URL"
    )
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    enable_query_logging: bool = Field(default=False, description="Enable SQL logging")
```

### Database Changes
**Schema Migration Strategy**:
- Convert existing `database.sql` to SQLAlchemy Table definitions
- Create initial Alembic migration from current schema
- Implement database-specific schema variations for PostgreSQL/MySQL
- Preserve all existing indexes, triggers, and constraints

**No Breaking Schema Changes**: Migration preserves all existing data and relationships

### API Requirements
**MCP Server Endpoints**: No changes to existing MCP tool endpoints
**Agent Coordination Patterns**: Preserve all existing session isolation and agent memory patterns

---

## Quality Requirements

### Testing Strategy
**FastMCP TestClient Behavioral Testing**:
- Comprehensive test coverage for all 183 SQL operations
- Cross-database compatibility testing (SQLite, PostgreSQL, MySQL)
- Performance benchmarking to validate <30ms operations
- Connection pool testing for 20+ concurrent agents
- Schema migration testing (forward/backward compatibility)

**Multi-Agent Coverage**:
- Session isolation testing across multiple concurrent agents
- Agent memory persistence and TTL functionality
- Audit logging under concurrent access
- Search functionality with RapidFuzz integration

**Test Implementation Pattern**:
```python
# Enhanced testing with SQLAlchemy
@pytest.fixture
async def database_url(request):
    """Provide database URL based on test marker."""
    db_type = request.node.get_closest_marker("database")
    if db_type and db_type.args[0] == "postgresql":
        return "postgresql+asyncpg://test:test@localhost/test_db"
    elif db_type and db_type.args[0] == "mysql":
        return "mysql+aiomysql://test:test@localhost/test_db"
    return "sqlite+aiosqlite:///:memory:"

@pytest.mark.database("postgresql")
async def test_postgresql_operations(database_url):
    """Test operations with PostgreSQL backend."""
    # Test implementation
```

### Documentation Needs
**MCP Server API Documentation**: Update existing API docs with SQLAlchemy integration details
**Database Configuration Guide**: Multi-database setup and migration procedures
**Performance Tuning Guide**: Database-specific optimization strategies
**Migration Guide**: Step-by-step migration from existing SQLite implementation

### Performance Considerations
**Concurrent Agent Access**:
- Connection pooling optimization for multi-agent workloads
- Database-specific performance tuning (SQLite PRAGMA, PostgreSQL shared_buffers)
- Query performance monitoring and slow query analysis
- Load testing with realistic 20+ concurrent agent scenarios

**Critical Performance Metrics**:
- <30ms message operations (existing requirement)
- 2-3ms fuzzy search performance (existing requirement)
- Connection pool efficiency under load
- Zero performance degradation vs current SQLite implementation

---

## Coordination Strategy

### Recommended Approach: Task-Coordinator with Phased Implementation
**Justification**: High complexity architectural change affecting core database operations across 19+ files with critical performance requirements necessitates orchestrated implementation.

**Coordination Requirements**:
- **Multi-phase coordination**: 4 distinct phases with validation checkpoints
- **Risk management**: Feature flag approach for gradual rollout
- **Performance validation**: Continuous benchmarking throughout implementation
- **Cross-module integration**: Updates to database, server, config, and testing modules

### Implementation Phases - Decomposed PRPs

This PRP has been decomposed into smaller, testable work chunks as follows:

#### Phase 1A: SQLAlchemy Core Foundation (PRP-007A)
**Scope**: SQLAlchemy dependencies and basic engine configuration
**Estimated Effort**: 2-3 days
**PRP Reference**: `PRPs/2-prps/007a_sqlalchemy-core-foundation.md`
**Key Deliverables**:
- SQLAlchemy 2.0+ dependencies with asyncio support
- Engine factory for SQLite, PostgreSQL, MySQL
- Basic connection manager with health checks
- Configuration integration with feature flags

#### Phase 1B: Database Manager Integration (PRP-007B)
**Scope**: Unified database manager with backend switching
**Estimated Effort**: 3-4 days
**PRP Reference**: `PRPs/2-prps/007b_database-manager-integration.md`
**Key Deliverables**:
- UnifiedDatabaseManager with legacy/SQLAlchemy modes
- Parameter translation between positional and named formats
- Feature flag control for gradual rollout
- Zero changes to server.py database operations

#### Phase 2A: Alembic Schema Definition (PRP-007C)
**Scope**: Schema migration framework setup
**Estimated Effort**: 2-3 days
**PRP Reference**: `PRPs/2-prps/007c_alembic-schema-definition.md`
**Key Deliverables**:
- Alembic configuration and environment setup
- SQLAlchemy Table definitions for all existing tables
- Initial migration script from current schema
- Cross-database schema compatibility

#### Phase 2B: Migration Testing and Validation (PRP-007D)
**Scope**: Migration safety and validation framework
**Estimated Effort**: 2-3 days
**PRP Reference**: `PRPs/2-prps/007d_migration-testing-validation.md`
**Key Deliverables**:
- MigrationValidator for data integrity checking
- DataMigrationService with backup and rollback
- PerformanceValidator for <30ms operations
- Comprehensive migration testing suite

#### Phase 3A: PostgreSQL Production Support (PRP-007E)
**Scope**: Production-ready PostgreSQL backend
**Estimated Effort**: 2-3 days
**PRP Reference**: `PRPs/2-prps/007e_postgresql-support.md`
**Key Deliverables**:
- PostgreSQLManager with connection pooling
- Database-specific optimizations and tuning
- Docker Compose production configuration
- PostgreSQL-specific monitoring and health checks

#### Phase 3B: Cross-Database Testing (PRP-007F)
**Scope**: Multi-database compatibility validation
**Estimated Effort**: 2-3 days
**PRP Reference**: `PRPs/2-prps/007f_cross-database-testing.md`
**Key Deliverables**:
- CrossDatabaseTester for functionality validation
- Docker-based test environment setup
- Performance parity testing across databases
- Comprehensive compatibility matrix

### Risk Mitigation
**Feature Flag Strategy**: Implement runtime switching between old/new database implementations
**Gradual Rollout**: Start with read-only operations, progress to full write operations
**Performance Monitoring**: Real-time metrics during migration phases
**Rollback Procedures**: Quick revert to existing SQLite implementation if critical issues arise

### Dependencies
**Infrastructure Prerequisites**:
- PostgreSQL 14+ server for production testing
- MySQL 8.0+ server for multi-database testing (optional)
- Performance testing environment with realistic load simulation

**Development Prerequisites**:
- SQLAlchemy 2.0+ with asyncio support
- Alembic for schema migrations
- pytest-asyncio for enhanced testing
- Database-specific async drivers (asyncpg, aiomysql)

---

## Success Criteria

### Functional Success
**Core MCP Operations**:
- All 183 SQL operations function correctly across SQLite, PostgreSQL, MySQL
- Session isolation and agent memory persistence maintained
- Schema migration system functional with forward/backward compatibility
- Database-specific optimizations preserved (SQLite PRAGMA, PostgreSQL settings)

**Integration Validation**:
- FastMCP server operations unchanged from external perspective
- Agent coordination patterns function identically
- UTC timestamp operations preserved for multi-agent coordination
- Error handling and recovery mechanisms maintained

### Integration Success
**Multi-Agent Coordination Verification**:
- 20+ concurrent agents supported with connection pooling
- Session isolation maintained under concurrent access
- Agent memory operations isolated per agent with proper TTL handling
- Search functionality (RapidFuzz) performance preserved

**Performance Validation**:
- <30ms message operations maintained across all database backends
- 2-3ms fuzzy search performance preserved
- Zero performance degradation vs current SQLite implementation
- Connection pool efficiency under multi-agent load

### Quality Gates
**FastMCP Testing Requirements**:
- 85%+ test coverage maintained across all database backends
- Cross-database test suite passing (SQLite, PostgreSQL, MySQL)
- Behavioral testing validates multi-agent scenarios
- Performance benchmarking confirms requirements met

**Production Readiness**:
- Migration procedures documented and tested
- Database configuration examples provided for all backends
- Troubleshooting guide covers common migration issues
- CI/CD pipeline updated for multi-database testing

**Validation Procedures**:
```bash
# Quality gate commands
uv run ruff check .                    # Code quality maintained
uv run mypy src/                       # Type checking passes
uv run pytest --cov=src --cov-report=html  # Test coverage ≥85%
uv run pytest -m "performance"        # Performance benchmarks pass
uv run pytest -m "database" --database postgresql  # Cross-database tests
```

---

## Long-term Vision

### Immediate Benefits (Phase Completion)
- Zero-downtime database migration capability
- Support for SQLite development, PostgreSQL production deployments
- Standardized schema migration procedures with Alembic
- Reduced vendor lock-in and improved deployment flexibility

### Medium-term Enhancements (Months 6-12)
- **Read/Write Splitting**: Master/replica configuration for high availability
- **Advanced Connection Pooling**: Database-specific optimization strategies
- **Multi-Region Support**: Database routing for global deployment scenarios
- **Performance Analytics**: Query analysis and automated optimization

### Long-term Capabilities (Year 2+)
- **Hybrid Database Architectures**: Specialized databases for different data types
- **Advanced Analytics Integration**: TimescaleDB for time-series agent interaction data
- **Global Scale Deployment**: Multi-master database configurations
- **Automated Operations**: Self-healing database management and optimization

---

**Document Metadata**:
- **Source Planning Document**: PRPs/1-planning/database-adapter-pattern/database-adapter-pattern.md
- **Research Context Preserved**: Expert technical review, comparative analysis, feasibility study
- **Architecture Integration**: FastMCP server patterns, multi-agent coordination, performance requirements
- **Implementation Ready**: All technical specifications and coordination strategy defined

**Next Step**: Execute with task-coordinator for orchestrated multi-phase implementation ensuring performance requirements and architectural integrity.
