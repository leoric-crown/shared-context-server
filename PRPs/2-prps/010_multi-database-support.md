# PRP-010: Multi-Database Support Enhancement (SQLite, PostgreSQL, MySQL)

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-13
**Updated**: 2025-01-13 (KISS/YAGNI Refinement)
**Planning Source**: Analysis of SQLAlchemy wrapper limitations, multi-database research, and expert agent consultation
**Status**: Implementation Ready
**Priority**: Medium - Production Scaling Enablement
**Estimated Effort**: 4-6 hours (reduced via KISS principles)
**Complexity Level**: Low - Simplified URL-based detection with separate schema files

## KISS/YAGNI Refinement Summary

**Expert Agent Consultation Results**:
- **Developer Agent**: Identified schema translation as biggest complexity risk; recommended URL-based detection and separate schema files
- **Tester Agent**: Proposed layered testing strategy avoiding 3x test explosion; 25 targeted tests per database vs 493x3 full matrix
- **Key Simplifications**: Avoid schema translation systems, complex dialect management, and testing complexity explosion

---

## Research Context & Architectural Analysis

### Problem Statement & Current Limitations

**Current Reality**: The SQLAlchemy wrapper (PRP-009) successfully provides dual backend support but has hardcoded SQLite-specific limitations that prevent true multi-database deployment.

**Critical Limitations Identified**:
1. **Hardcoded Schema Initialization**: Only supports SQLite via existing DatabaseManager
2. **SQLite-Specific PRAGMA Settings**: Engine configuration hardcoded for SQLite optimizations
3. **Schema File Dependencies**: `database.sql` contains SQLite-specific syntax (AUTOINCREMENT, PRAGMA statements)
4. **Single Database Validation**: NotImplementedError for non-SQLite databases

**Research Integration**: Comprehensive research conducted on SQLAlchemy 2.0 async patterns, driver configurations, and schema migration best practices across database systems.

### Multi-Database Research Findings

**SQLAlchemy Async Driver Research**:
- **PostgreSQL**: `asyncpg` driver provides 5x performance improvement over psycopg, with built-in prepared statement caching
- **MySQL**: `aiomysql` driver supports async operations with proper connection pooling and InnoDB optimizations
- **SQLite**: Current `aiosqlite` remains optimal for development with existing PRAGMA optimizations

**Engine Configuration Best Practices**:
- **PostgreSQL**: `pool_size=20, max_overflow=30, prepared_statement_cache_size=500`
- **MySQL**: `pool_recycle=3600` for connection timeout handling, `charset=utf8mb4`
- **SQLite**: `NullPool` for single-threaded access, existing PRAGMA optimizations

**Schema Management Approach (KISS Principle)**:
- **No Schema Translation**: Maintain separate schema files per database to avoid complexity
- **database.sql**: Current SQLite schema (unchanged)
- **database_postgresql.sql**: Native PostgreSQL schema with SERIAL, JSONB, proper constraints
- **database_mysql.sql**: Native MySQL schema with AUTO_INCREMENT, JSON type, InnoDB engine

### Architectural Integration Points

**Existing SQLAlchemy Wrapper Assets** (from PRP-009):
- ✅ `SimpleSQLAlchemyManager` - Connection factory with interface compatibility
- ✅ `SQLAlchemyConnectionWrapper` - aiosqlite.Connection compatibility layer
- ✅ `CompatibleRow` - Row access pattern compatibility across databases
- ✅ Parameter translation system (? → :param1) working across all databases

**Current Database Dependencies**:
- `src/shared_context_server/database.py` - Contains 8 SQLite-specific PRAGMA settings
- `database.sql` - 259-line schema with SQLite syntax and AUTOINCREMENT usage
- `src/shared_context_server/database_sqlalchemy.py` - Hardcoded SQLite initialization path

---

## Implementation Specification (KISS Approach)

### Core Requirements

**Primary Implementation**: Extend existing SimpleSQLAlchemyManager with URL-based database detection and separate schema files per database. No complex dialect management or schema translation systems.

### Simplified Database Detection

**URL-Based Detection in SimpleSQLAlchemyManager**:
```python
# Enhanced database_sqlalchemy.py (no new files needed)
class SimpleSQLAlchemyManager:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///./chat_history.db"):
        self.database_url = database_url

        # Simple URL-based detection (no complex enum or manager classes)
        if database_url.startswith("sqlite+aiosqlite://"):
            self.db_type = "sqlite"
        elif database_url.startswith("postgresql+asyncpg://"):
            self.db_type = "postgresql"
        elif database_url.startswith("mysql+aiomysql://"):
            self.db_type = "mysql"
        else:
            raise ValueError(f"Unsupported database URL: {database_url}")

        # Database-specific engine configuration
        engine_config = self._get_engine_config()
        self.engine = create_async_engine(database_url, **engine_config)

    def _get_engine_config(self) -> dict:
        """Return engine configuration per database type."""

    def get_schema_template(self) -> str:
        """Return database-specific schema with proper data types."""

    def translate_schema(self, sqlite_schema: str) -> str:
        """Translate SQLite schema to target database dialect."""
```

### Schema Translation System

**SQLite → PostgreSQL Translation**:
```python
def translate_to_postgresql(self, sqlite_schema: str) -> str:
    """Convert SQLite schema to PostgreSQL-compatible SQL."""
    translations = {
        'INTEGER PRIMARY KEY AUTOINCREMENT': 'SERIAL PRIMARY KEY',
        'TEXT': 'VARCHAR(255)',
        'INTEGER': 'BIGINT',
        'REAL': 'DOUBLE PRECISION',
        'BLOB': 'BYTEA',
        'CURRENT_TIMESTAMP': 'CURRENT_TIMESTAMP',
        'json_valid(': 'jsonb_valid(',  # Custom function or constraint adjustment
    }
    # Remove SQLite-specific PRAGMA statements
    # Add PostgreSQL-specific optimizations
```

**SQLite → MySQL Translation**:
```python
def translate_to_mysql(self, sqlite_schema: str) -> str:
    """Convert SQLite schema to MySQL-compatible SQL."""
    translations = {
        'INTEGER PRIMARY KEY AUTOINCREMENT': 'BIGINT PRIMARY KEY AUTO_INCREMENT',
        'TEXT': 'TEXT',
        'INTEGER': 'BIGINT',
        'REAL': 'DOUBLE',
        'BLOB': 'LONGBLOB',
        'json_valid(': 'JSON_VALID(',
    }
    # Add MySQL-specific ENGINE=InnoDB and charset settings
```

### Enhanced SimpleSQLAlchemyManager

```python
# Enhanced database_sqlalchemy.py
class SimpleSQLAlchemyManager:
    def __init__(self, database_url: str = "sqlite+aiosqlite:///./chat_history.db"):
        self.database_url = database_url
        self.dialect_manager = DatabaseDialectManager(database_url)

        # Get database-specific engine configuration
        engine_config = self.dialect_manager.get_engine_config()
        self.engine = create_async_engine(database_url, **engine_config)
        self.is_initialized = False

    async def initialize(self) -> None:
        """Initialize database with dialect-aware schema management."""
        if self.is_initialized:
            return

        dialect = self.dialect_manager.dialect

        if dialect == DatabaseDialect.SQLITE:
            # Use existing DatabaseManager for SQLite (preserve current functionality)
            await self._initialize_sqlite()
        elif dialect == DatabaseDialect.POSTGRESQL:
            # Initialize PostgreSQL with translated schema
            await self._initialize_postgresql()
        elif dialect == DatabaseDialect.MYSQL:
            # Initialize MySQL with translated schema
            await self._initialize_mysql()

        self.is_initialized = True

    async def _initialize_postgresql(self) -> None:
        """PostgreSQL-specific initialization with schema translation."""

    async def _initialize_mysql(self) -> None:
        """MySQL-specific initialization with schema translation."""
```

### Database-Specific Engine Configurations

**PostgreSQL Configuration**:
```python
def get_postgresql_config(self) -> Dict[str, Any]:
    return {
        'pool_size': 20,
        'max_overflow': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'prepared_statement_cache_size': 500,
            'server_settings': {
                'jit': 'off',  # Optimize ENUM performance
                'application_name': 'shared_context_mcp'
            }
        }
    }
```

**MySQL Configuration**:
```python
def get_mysql_config(self) -> Dict[str, Any]:
    return {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 3600,  # Handle MySQL 8-hour timeout
        'pool_pre_ping': True,
        'connect_args': {
            'charset': 'utf8mb4',
            'autocommit': False,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
```

**SQLite Configuration** (preserve existing):
```python
def get_sqlite_config(self) -> Dict[str, Any]:
    return {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        # Keep existing optimizations from PRP-009
    }
```

### Integration Points

**Configuration Integration** (`src/shared_context_server/config.py`):
```python
class DatabaseConfig(BaseModel):
    use_sqlalchemy: bool = Field(default=False)
    database_url: str = Field(
        default="sqlite+aiosqlite:///./chat_history.db",
        description="Database URL with dialect specification"
    )

    # Add database-specific configurations
    postgresql_pool_size: int = Field(default=20)
    mysql_pool_size: int = Field(default=10)
    enable_query_logging: bool = Field(default=False)
```

**Database Module Integration** (`src/shared_context_server/database.py`):
```python
# Enhanced get_db_connection remains unchanged
# SimpleSQLAlchemyManager auto-detects dialect and configures appropriately
```

### Zero Changes Required

- ✅ `src/shared_context_server/server.py` - All 47 database operations unchanged
- ✅ All MCP tools and FastMCP patterns - No changes required
- ✅ Test files - Existing 493 tests work with all backends
- ✅ aiosqlite backend - Remains default, fully preserved

---

## Quality Requirements

### Testing Strategy (Layered Approach - KISS Principle)

**Layer 1: Comprehensive Business Logic (SQLite Only)**:
- **Keep existing 493 tests running against SQLite** (unchanged)
- Validates all API endpoints, session management, message handling, search functionality
- SQLite remains primary validation database - fast, no external dependencies

**Layer 2: Database-Specific Differences (~25 tests per database)**:
```python
# tests/database_specific/test_postgresql_basics.py
async def test_postgresql_connection():
    """Test PostgreSQL-specific connection handling."""

async def test_postgresql_schema_creation():
    """Test PostgreSQL schema with SERIAL, JSONB constraints."""

async def test_postgresql_transaction_behavior():
    """Test PostgreSQL isolation levels and deadlock handling."""

# tests/database_specific/test_mysql_basics.py
async def test_mysql_connection():
    """Test MySQL-specific connection and charset handling."""

async def test_mysql_schema_creation():
    """Test MySQL schema with AUTO_INCREMENT, JSON type."""
```

**Layer 3: Feature Flag Rollback Testing**:
```python
# tests/test_backend_switching.py
async def test_feature_flag_rollback():
    """Ensure USE_SQLALCHEMY=false still works reliably."""

async def test_database_url_switching():
    """Test graceful backend switching via URL changes."""
```

**Testing Numbers (YAGNI Principle)**:
- **SQLite Tests**: 493 (existing) - comprehensive business logic
- **PostgreSQL Specific**: ~25 tests - connection, schema, dialect differences
- **MySQL Specific**: ~25 tests - connection, schema, dialect differences
- **Feature Flag Tests**: ~10 tests - backend switching validation
- **Total**: ~553 tests (13% increase) instead of 1,479 tests (300% explosion)

### Documentation Requirements

**Environment Configuration Documentation**:
```bash
# PostgreSQL Deployment
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/shared_context"
export USE_SQLALCHEMY=true

# MySQL Deployment
export DATABASE_URL="mysql+aiomysql://user:pass@host:3306/shared_context"
export USE_SQLALCHEMY=true

# SQLite Development (unchanged)
export DATABASE_URL="sqlite+aiosqlite:///./chat_history.db"
export USE_SQLALCHEMY=false  # or true for SQLAlchemy backend
```

**Deployment Guide Updates**:
- Database-specific driver installation instructions
- Connection string format documentation
- Performance tuning guidelines per database type

### Performance Considerations

**Database-Specific Optimizations**:
- **PostgreSQL**: Prepared statement caching, connection pooling, JSONB usage
- **MySQL**: Connection timeout handling, charset configuration, InnoDB optimizations
- **SQLite**: Existing PRAGMA settings preserved, WAL mode retained

**Connection Management**:
- Async connection pools properly configured per database capabilities
- Graceful degradation and error handling for connection failures
- Resource cleanup ensuring proper connection disposal

---

## Coordination Strategy

### Recommended Approach: Developer Agent Implementation (KISS Validated)

**Justification**: Low complexity task with simplified requirements after KISS/YAGNI analysis. URL-based detection and separate schema files eliminate complex dialect management.

**Expert Agent Validation**:
- **Developer Agent**: Confirmed URL-based detection is minimal approach; separate schema files avoid translation complexity
- **Tester Agent**: Validated layered testing prevents CI explosion; targets 25 tests per database vs 493x3 matrix

**Implementation Scope (Simplified)**:
- **Files to Create**: 3 schema files + ~60 targeted tests
- **Files to Modify**: 1 file (database_sqlalchemy.py)
- **No Complex Systems**: No dialect managers, translation systems, or migration frameworks

### Implementation Phases (KISS Approach)

#### Phase 1: Minimal Schema Creation (2-3 hours)
**Scope**: Create separate schema files per database (no translation complexity)

**Key Deliverables**:
- `database_postgresql.sql` - Native PostgreSQL schema with SERIAL, JSONB
- `database_mysql.sql` - Native MySQL schema with AUTO_INCREMENT, JSON type
- Database-specific schema loading logic in SimpleSQLAlchemyManager

**Technical Focus**:
- No schema translation systems - maintain separate files
- PostgreSQL optimizations: SERIAL, JSONB, proper constraints
- MySQL optimizations: InnoDB engine, charset=utf8mb4

#### Phase 2: Enhanced SQLAlchemy Manager (1-2 hours)
**Scope**: Extend SimpleSQLAlchemyManager with URL-based detection

**Key Deliverables**:
- URL-based database detection in existing `__init__()` method
- Database-specific `_load_schema_file()` method
- Database-specific engine configurations
- Enhanced `initialize()` method with per-database schema loading

**Technical Focus**:
- Simple URL parsing (no complex dialect classes)
- Preserve existing SQLite functionality completely
- Add PostgreSQL/MySQL initialization without breaking changes

#### Phase 3: Targeted Testing (1-2 hours)
**Scope**: Layered testing approach focusing on database differences

**Key Deliverables**:
- `tests/database_specific/test_postgresql_basics.py` (~15 tests)
- `tests/database_specific/test_mysql_basics.py` (~15 tests)
- `tests/test_backend_switching.py` (~10 tests)
- Optional Docker setup for local database testing

**Technical Focus**:
- Focus on connection, schema creation, dialect differences only
- Avoid duplicating business logic tests (493 SQLite tests cover that)
- Feature flag rollback validation

### Risk Mitigation

**Zero-Risk Strategy**:
- Feature flag defaults to existing aiosqlite backend (no behavior change)
- All existing SQLAlchemy wrapper functionality preserved
- Can disable SQLAlchemy backend instantly if issues arise
- Comprehensive testing ensures no regressions

**Backward Compatibility**:
- Default configuration unchanged (SQLite + aiosqlite)
- Existing environment variables continue working
- No breaking changes to any existing interfaces
- Incremental database adoption (SQLite → PostgreSQL → MySQL)

**Database-Specific Risks**:
- **PostgreSQL**: Connection pool tuning may need adjustment based on server configuration
- **MySQL**: Character encoding and timeout settings require proper configuration
- **SQLite**: No changes to existing behavior, zero risk

### Dependencies

**Development Prerequisites**:
- Research completed on SQLAlchemy async drivers and configurations
- Current SQLAlchemy wrapper (PRP-009) successfully implemented and tested
- Database driver dependencies managed via optional installation

**Runtime Prerequisites**:
- **PostgreSQL**: `asyncpg>=0.29.0` for async operations
- **MySQL**: `aiomysql>=0.2.0` with proper charset support
- **SQLite**: Existing `aiosqlite` (no changes required)

**Infrastructure Prerequisites** (for testing/deployment):
- Access to PostgreSQL and MySQL instances for integration testing
- Database creation permissions for schema initialization
- Network connectivity and proper authentication configuration

---

## Success Criteria

### Functional Success

**Multi-Database Operations**:
- All 47 database operations in `server.py` work identically across SQLite, PostgreSQL, and MySQL
- Schema translation produces working databases with proper constraints and indexes
- Connection management handles database-specific optimizations and timeouts
- Error handling provides clear feedback for database-specific issues

**Interface Compatibility**:
- `async with get_db_connection()` pattern preserved exactly
- `cursor.lastrowid`, `fetchone()`, `fetchall()` work identically across databases
- Row access patterns (`dict(row)`, `row[0]`, `row['column']`) work consistently
- Transaction semantics (`commit()`, `rollback()`) handle database differences properly

### Integration Success

**Zero-Impact Migration**:
- Default configuration behavior unchanged (SQLite + aiosqlite)
- All existing tests pass without modification
- Performance maintained or improved across database types
- Environment variable changes enable seamless database switching

**Production Readiness**:
- Connection pooling optimized for each database type
- Schema translation validated for production workloads
- Database-specific configurations documented and tested
- Monitoring and health check support for all database backends

### Quality Gates

**Development Validation**:
```bash
# Phase 1 Validation
uv run pytest tests/unit/test_database_dialect.py -v    # Dialect detection and translation
uv run ruff check . && uv run mypy src/                 # Code quality maintained

# Phase 2 Validation
uv run pytest tests/unit/test_multi_database_support.py -v  # Multi-database compatibility
DATABASE_URL="postgresql+asyncpg://..." USE_SQLALCHEMY=true uv run pytest --tb=no -q

# Phase 3 Validation
DATABASE_URL="mysql+aiomysql://..." USE_SQLALCHEMY=true uv run pytest --tb=no -q
uv run pytest tests/ -x --tb=short                     # Full regression testing
```

**Production Readiness Validation**:
- Schema initialization works for fresh PostgreSQL and MySQL databases
- Connection pool configurations handle expected load patterns
- Error handling gracefully manages database-specific failure modes
- Documentation enables smooth deployment to cloud database services

---

## Long-term Vision

### Immediate Benefits (Phase Completion)

- **Production Database Support**: Ready for PostgreSQL and MySQL deployment without code changes
- **Cloud Compatibility**: Works with AWS RDS, Google Cloud SQL, Azure Database services
- **Performance Scaling**: Optimized connection pooling and database-specific configurations
- **Development Flexibility**: Choice of database backend based on deployment needs

### Future Enhancements (YAGNI - Only If Actually Needed)

- **Additional Database Support**: Other databases only if deployment requirements emerge
- **Performance Optimization**: Database-specific tuning only if performance issues arise
- **Schema Migration Tools**: Only if schema versioning becomes necessary
- **Connection Pool Monitoring**: Only if scaling issues emerge

### Explicit Non-Goals (KISS Boundaries)

- ❌ **Schema Translation Systems**: Avoid complex dialect translation - use separate schema files
- ❌ **Complex Dialect Management**: No enum classes or manager hierarchies - URL-based detection only
- ❌ **Migration Frameworks**: No Alembic or version management until actually needed
- ❌ **Performance Over-Engineering**: SQLAlchemy defaults sufficient until scaling issues appear
- ❌ **Multi-Database Testing**: No 3x test explosion - targeted testing per database only
- ❌ **Development Environment Burden**: Optional PostgreSQL/MySQL setup only

---

**Document Metadata**:
- **Research Sources**: SQLAlchemy 2.0 docs, expert agent consultation (developer + tester), KISS/YAGNI analysis
- **Architectural Validation**: Builds on proven PRP-009 foundation with simplified approach
- **Risk Level**: Very Low (feature flag protection, separate schema files, layered testing)
- **Value Proposition**: Production database support with minimal complexity and zero-risk rollback
- **Effort Reduction**: 4-6 hours (down from 6-8) via complexity elimination

**Next Step**: Implement with developer agent using simplified KISS approach - URL detection + separate schema files + targeted testing.
