# PRP-007A: SQLAlchemy Core Foundation Setup

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-12
**Parent PRP**: PRP-007 SQLAlchemy Core Database Migration
**Status**: Implementation Ready
**Priority**: High - Foundation Component
**Estimated Effort**: 2-3 days
**Complexity Level**: Medium - Foundation Setup

---

## Executive Summary

Establish SQLAlchemy Core foundation infrastructure including dependencies, basic engine configuration, and core abstractions while maintaining backward compatibility with existing database operations.

**Scope**: Dependencies, basic SQLAlchemy setup, and foundation classes
**Goal**: Zero-risk foundation that can coexist with existing database implementation

---

## Implementation Specification

### Core Requirements

**Dependencies Setup**:
```toml
# pyproject.toml additions
[project.dependencies]
sqlalchemy = {extras = ["asyncio"], version = ">=2.0.23"}

[project.optional-dependencies]
postgresql = [
    "asyncpg>=0.29.0",
]
mysql = [
    "aiomysql>=0.2.0",
]
database-testing = [
    "pytest-asyncio>=0.23.0",
    "sqlalchemy[testing]>=2.0.23",
]
```

**Basic SQLAlchemy Core Engine Factory**:
```python
# src/shared_context_server/database/sqlalchemy_core.py
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SQLAlchemyEngineFactory:
    """Factory for creating SQLAlchemy async engines with database-specific configuration."""

    @staticmethod
    def create_engine(database_url: str, **kwargs) -> Any:
        """Create async engine with database-specific optimizations."""
        engine_config = SQLAlchemyEngineFactory._get_engine_config(database_url)
        engine_config.update(kwargs)

        return create_async_engine(database_url, **engine_config)

    @staticmethod
    def _get_engine_config(database_url: str) -> Dict[str, Any]:
        """Get database-specific engine configuration."""
        if database_url.startswith('sqlite'):
            return {
                'poolclass': StaticPool,
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 30.0,
                },
                'echo': False,
                'pool_pre_ping': True,
            }
        elif database_url.startswith('postgresql'):
            return {
                'pool_size': 20,
                'max_overflow': 10,
                'pool_timeout': 30.0,
                'pool_pre_ping': True,
                'echo': False,
            }
        elif database_url.startswith('mysql'):
            return {
                'pool_size': 20,
                'max_overflow': 10,
                'pool_timeout': 30.0,
                'pool_pre_ping': True,
                'echo': False,
                'pool_recycle': 3600,
            }
        return {}

class SQLAlchemyConnectionManager:
    """Basic connection manager for SQLAlchemy Core operations."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = SQLAlchemyEngineFactory.create_engine(database_url)
        self.metadata = MetaData()

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> list[dict]:
        """Execute SELECT query and return results as list of dicts."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]

    async def execute_update(self, query: str, params: Optional[Dict] = None) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected row count."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return result.rowcount

    async def health_check(self) -> bool:
        """Basic health check - execute simple query."""
        try:
            result = await self.execute_query("SELECT 1 as test")
            return len(result) == 1 and result[0]['test'] == 1
        except Exception as e:
            logger.error(f"SQLAlchemy health check failed: {e}")
            return False

    async def close(self):
        """Close engine and cleanup connections."""
        await self.engine.dispose()
```

**Configuration Integration**:
```python
# src/shared_context_server/config.py (additions)
from pydantic import Field

class DatabaseConfig(BaseModel):
    # Existing configuration preserved
    database_path: str = Field(
        default="./chat_history.db",
        description="Database file path (SQLite)"
    )

    # New SQLAlchemy configuration
    sqlalchemy_database_url: Optional[str] = Field(
        default=None,
        description="SQLAlchemy database URL (overrides database_path when set)"
    )
    enable_sqlalchemy: bool = Field(
        default=False,
        description="Enable SQLAlchemy Core engine (feature flag)"
    )
    pool_size: int = Field(default=20, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    enable_query_logging: bool = Field(default=False, description="Enable SQL query logging")

    @property
    def effective_database_url(self) -> str:
        """Get effective database URL for SQLAlchemy."""
        if self.sqlalchemy_database_url:
            return self.sqlalchemy_database_url
        # Convert file path to SQLite URL
        return f"sqlite+aiosqlite:///{self.database_path}"
```

### Integration Points

**Coexistence Strategy**:
- New SQLAlchemy infrastructure in `src/shared_context_server/database/` subdirectory
- Existing database operations unchanged in `src/shared_context_server/database.py`
- Feature flag controls which implementation is used
- Zero changes to external APIs

**File Structure**:
```
src/shared_context_server/
├── database.py                    # Existing implementation (unchanged)
├── database/                      # New SQLAlchemy infrastructure
│   ├── __init__.py               # Module initialization
│   ├── sqlalchemy_core.py        # Core engine and connection management
│   └── utils.py                  # Utility functions
├── config.py                      # Enhanced with SQLAlchemy config
└── ...
```

### Testing Strategy

**Foundation Testing**:
```python
# tests/unit/test_sqlalchemy_foundation.py
import pytest
from shared_context_server.database.sqlalchemy_core import (
    SQLAlchemyEngineFactory,
    SQLAlchemyConnectionManager
)

class TestSQLAlchemyEngineFactory:
    def test_sqlite_engine_config(self):
        """Test SQLite engine configuration."""
        config = SQLAlchemyEngineFactory._get_engine_config("sqlite+aiosqlite:///test.db")
        assert config['poolclass'].__name__ == 'StaticPool'
        assert config['connect_args']['check_same_thread'] is False
        assert config['pool_pre_ping'] is True

    def test_postgresql_engine_config(self):
        """Test PostgreSQL engine configuration."""
        config = SQLAlchemyEngineFactory._get_engine_config("postgresql+asyncpg://user@host/db")
        assert config['pool_size'] == 20
        assert config['max_overflow'] == 10
        assert config['pool_pre_ping'] is True

@pytest.mark.asyncio
class TestSQLAlchemyConnectionManager:
    async def test_basic_operations(self):
        """Test basic SQLAlchemy operations with in-memory SQLite."""
        manager = SQLAlchemyConnectionManager("sqlite+aiosqlite:///:memory:")

        # Test health check
        assert await manager.health_check() is True

        # Test query execution
        result = await manager.execute_query("SELECT 1 as test, 'hello' as message")
        assert len(result) == 1
        assert result[0]['test'] == 1
        assert result[0]['message'] == 'hello'

        await manager.close()

    async def test_error_handling(self):
        """Test error handling in connection manager."""
        manager = SQLAlchemyConnectionManager("sqlite+aiosqlite:///:memory:")

        # Test invalid query
        with pytest.raises(Exception):
            await manager.execute_query("INVALID SQL QUERY")

        await manager.close()
```

**Configuration Testing**:
```python
# tests/unit/test_config_sqlalchemy.py
import pytest
from shared_context_server.config import DatabaseConfig

class TestDatabaseConfigSQLAlchemy:
    def test_default_configuration(self):
        """Test default SQLAlchemy configuration."""
        config = DatabaseConfig()
        assert config.enable_sqlalchemy is False
        assert config.sqlalchemy_database_url is None
        assert config.effective_database_url.startswith("sqlite+aiosqlite:///")

    def test_sqlalchemy_url_override(self):
        """Test SQLAlchemy URL override."""
        config = DatabaseConfig(
            sqlalchemy_database_url="postgresql+asyncpg://user:pass@host/db"
        )
        assert config.effective_database_url == "postgresql+asyncpg://user:pass@host/db"

    def test_feature_flag_control(self):
        """Test feature flag functionality."""
        config = DatabaseConfig(enable_sqlalchemy=True)
        assert config.enable_sqlalchemy is True
```

---

## Success Criteria

### Functional Success
- ✅ SQLAlchemy dependencies installed and importable
- ✅ Engine factory creates valid async engines for SQLite, PostgreSQL, MySQL
- ✅ Connection manager executes basic queries successfully
- ✅ Health check functionality works across database types
- ✅ Configuration integration preserves existing functionality

### Integration Success
- ✅ Zero changes to existing database operations
- ✅ Feature flag controls SQLAlchemy usage
- ✅ Coexistence with existing `database.py` module
- ✅ Configuration backward compatibility maintained

### Quality Gates
- ✅ All tests pass with 100% coverage for new code
- ✅ No regressions in existing functionality
- ✅ Type checking passes (mypy)
- ✅ Code quality checks pass (ruff)

### Validation Commands
```bash
# Dependency verification
uv sync --all-extras
uv run python -c "import sqlalchemy; print(sqlalchemy.__version__)"

# Core functionality testing
uv run pytest tests/unit/test_sqlalchemy_foundation.py -v
uv run pytest tests/unit/test_config_sqlalchemy.py -v

# Quality gates
uv run ruff check src/shared_context_server/database/
uv run mypy src/shared_context_server/database/
uv run pytest --cov=src/shared_context_server/database --cov-report=term-missing
```

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Dependency conflicts | Medium | Low | Pin specific versions, test in clean environment |
| Engine configuration issues | Medium | Medium | Comprehensive testing across database types |
| Memory leaks in connections | High | Low | Proper connection cleanup, automated testing |

### Mitigation Strategy
- **Isolated Implementation**: New code in separate module, zero impact on existing functionality
- **Feature Flag Control**: Can be disabled instantly if issues arise
- **Comprehensive Testing**: Test coverage for all engine configurations and error scenarios

---

## Next Steps

**Upon Completion**: This PRP establishes the foundation for PRP-007B (Database Manager Integration)
**Dependencies**: None - can be implemented immediately
**Follow-up PRPs**:
- PRP-007B: Database Manager Integration
- PRP-007C: Alembic Setup and Schema Definition

---

**Implementation Notes**:
- Start with SQLite engine configuration and testing
- Add PostgreSQL and MySQL configurations incrementally
- Ensure all tests pass before proceeding to integration phase
- Maintain strict backward compatibility throughout implementation
