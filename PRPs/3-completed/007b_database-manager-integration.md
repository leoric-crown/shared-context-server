# PRP-007B: Database Manager Integration

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-12
**Parent PRP**: PRP-007 SQLAlchemy Core Database Migration
**Prerequisite**: PRP-007A SQLAlchemy Core Foundation Setup
**Status**: Implementation Ready
**Priority**: High - Core Integration
**Estimated Effort**: 3-4 days
**Complexity Level**: High - Core System Integration

---

## Executive Summary

Integrate SQLAlchemy Core with existing database operations by creating a unified database manager that can operate in both legacy mode (direct aiosqlite) and SQLAlchemy mode, with feature flag control for gradual migration.

**Scope**: Database manager integration, feature flag implementation, API compatibility
**Goal**: Seamless operation with both database backends while maintaining performance requirements

---

## Implementation Specification

### Core Requirements

**Unified Database Manager**:
```python
# src/shared_context_server/database/manager.py
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
from ..database import DatabaseManager as LegacyDatabaseManager
from .sqlalchemy_core import SQLAlchemyConnectionManager
from ..config import get_database_config

class UnifiedDatabaseManager:
    """Unified database manager supporting both legacy and SQLAlchemy backends."""

    def __init__(self, use_sqlalchemy: Optional[bool] = None):
        config = get_database_config()

        # Determine which backend to use
        if use_sqlalchemy is None:
            use_sqlalchemy = config.enable_sqlalchemy

        self.use_sqlalchemy = use_sqlalchemy

        if use_sqlalchemy:
            self.backend = SQLAlchemyConnectionManager(config.effective_database_url)
            self.backend_type = "sqlalchemy"
        else:
            self.backend = LegacyDatabaseManager(config.database_path)
            self.backend_type = "legacy"

    async def initialize(self) -> None:
        """Initialize the database backend."""
        if hasattr(self.backend, 'initialize'):
            await self.backend.initialize()

    async def execute_query(
        self,
        query: str,
        params: Union[tuple, dict, None] = None
    ) -> List[Dict[str, Any]]:
        """Execute SELECT query with backend-specific parameter handling."""
        if self.use_sqlalchemy:
            # SQLAlchemy uses dict parameters
            if isinstance(params, tuple):
                # Convert positional parameters to named parameters
                params_dict = {f"param_{i}": val for i, val in enumerate(params)}
                # Replace ? with :param_N in query
                query_parts = query.split('?')
                if len(query_parts) > 1:
                    query = query_parts[0]
                    for i in range(1, len(query_parts)):
                        query += f":param_{i-1}" + query_parts[i]
                params = params_dict
            elif params is None:
                params = {}

            return await self.backend.execute_query(query, params)
        else:
            # Legacy uses tuple parameters
            if isinstance(params, dict):
                # This shouldn't happen in migration, but handle gracefully
                raise ValueError("Legacy backend requires tuple parameters")
            return await self.backend.execute_query(query, params or ())

    async def execute_update(
        self,
        query: str,
        params: Union[tuple, dict, None] = None
    ) -> int:
        """Execute INSERT/UPDATE/DELETE with backend-specific parameter handling."""
        if self.use_sqlalchemy:
            # SQLAlchemy uses dict parameters
            if isinstance(params, tuple):
                # Convert positional parameters to named parameters
                params_dict = {f"param_{i}": val for i, val in enumerate(params)}
                # Replace ? with :param_N in query
                query_parts = query.split('?')
                if len(query_parts) > 1:
                    query = query_parts[0]
                    for i in range(1, len(query_parts)):
                        query += f":param_{i-1}" + query_parts[i]
                params = params_dict
            elif params is None:
                params = {}

            return await self.backend.execute_update(query, params)
        else:
            # Legacy uses tuple parameters
            if isinstance(params, dict):
                raise ValueError("Legacy backend requires tuple parameters")
            return await self.backend.execute_update(query, params or ())

    async def execute_insert(
        self,
        query: str,
        params: Union[tuple, dict, None] = None
    ) -> int:
        """Execute INSERT and return last row ID."""
        if self.use_sqlalchemy:
            # SQLAlchemy doesn't have separate insert method - use execute_update
            result = await self.execute_update(query, params)
            # For SQLAlchemy, we need to implement lastrowid differently
            # This is a simplified implementation - may need enhancement
            return result
        else:
            # Legacy has dedicated execute_insert method
            if isinstance(params, dict):
                raise ValueError("Legacy backend requires tuple parameters")
            return await self.backend.execute_insert(query, params or ())

    @asynccontextmanager
    async def get_connection(self):
        """Get database connection using backend-specific patterns."""
        if self.use_sqlalchemy:
            # SQLAlchemy connection management
            async with self.backend.engine.begin() as conn:
                yield conn
        else:
            # Legacy connection management
            async with self.backend.get_connection() as conn:
                yield conn

    async def health_check(self) -> Dict[str, Any]:
        """Perform backend-specific health check."""
        if self.use_sqlalchemy:
            healthy = await self.backend.health_check()
            return {
                "status": "healthy" if healthy else "unhealthy",
                "backend": "sqlalchemy",
                "database_url": self.backend.database_url,
            }
        else:
            # Use existing health_check from legacy backend
            return await self.backend.health_check()

    def get_stats(self) -> Dict[str, Any]:
        """Get backend-specific statistics."""
        base_stats = {
            "backend_type": self.backend_type,
            "use_sqlalchemy": self.use_sqlalchemy,
        }

        if hasattr(self.backend, 'get_stats'):
            base_stats.update(self.backend.get_stats())

        return base_stats
```

**Parameter Translation Utilities**:
```python
# src/shared_context_server/database/query_translator.py
import re
from typing import Dict, Tuple, Any

class QueryParameterTranslator:
    """Translate between positional (?) and named (:name) query parameters."""

    @staticmethod
    def positional_to_named(query: str, params: Tuple[Any, ...]) -> Tuple[str, Dict[str, Any]]:
        """Convert ? parameters to :param_N format."""
        if not params:
            return query, {}

        # Replace ? with :param_N
        param_dict = {}
        query_parts = query.split('?')

        if len(query_parts) != len(params) + 1:
            raise ValueError(f"Parameter count mismatch: {len(params)} params, {len(query_parts)-1} placeholders")

        new_query = query_parts[0]
        for i, param in enumerate(params):
            param_name = f"param_{i}"
            param_dict[param_name] = param
            new_query += f":{param_name}" + (query_parts[i + 1] if i + 1 < len(query_parts) else "")

        return new_query, param_dict

    @staticmethod
    def named_to_positional(query: str, params: Dict[str, Any]) -> Tuple[str, Tuple[Any, ...]]:
        """Convert :name parameters to ? format."""
        if not params:
            return query, ()

        # Find all :param_name patterns
        param_pattern = re.compile(r':(\w+)')
        matches = param_pattern.findall(query)

        # Replace named parameters with ?
        new_query = param_pattern.sub('?', query)

        # Build parameter tuple in order of appearance
        param_tuple = tuple(params[param_name] for param_name in matches)

        return new_query, param_tuple
```

**Global Database Manager Factory**:
```python
# src/shared_context_server/database/__init__.py
from typing import Optional
from .manager import UnifiedDatabaseManager

# Global instance
_db_manager: Optional[UnifiedDatabaseManager] = None

def get_database_manager(use_sqlalchemy: Optional[bool] = None) -> UnifiedDatabaseManager:
    """Get global database manager instance."""
    global _db_manager

    if _db_manager is None:
        _db_manager = UnifiedDatabaseManager(use_sqlalchemy=use_sqlalchemy)

    return _db_manager

async def initialize_database(use_sqlalchemy: Optional[bool] = None) -> None:
    """Initialize global database manager."""
    manager = get_database_manager(use_sqlalchemy=use_sqlalchemy)
    await manager.initialize()

# Compatibility functions for existing code
async def get_db_connection():
    """Get database connection using global manager."""
    manager = get_database_manager()
    async with manager.get_connection() as conn:
        yield conn

async def execute_query(query: str, params: tuple = ()) -> list[dict]:
    """Execute query using global manager."""
    manager = get_database_manager()
    return await manager.execute_query(query, params)

async def execute_update(query: str, params: tuple = ()) -> int:
    """Execute update using global manager."""
    manager = get_database_manager()
    return await manager.execute_update(query, params)

async def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute insert using global manager."""
    manager = get_database_manager()
    return await manager.execute_insert(query, params)
```

### Integration Points

**Server Module Integration** (Minimal Changes):
```python
# src/shared_context_server/server.py
# Change imports only:
from .database import (
    get_database_manager,
    initialize_database,
    get_db_connection,  # Existing function signature preserved
    execute_query,      # Existing function signature preserved
    execute_update,     # Existing function signature preserved
)

# All existing code remains unchanged - functions work identically
```

**Configuration Enhancement**:
```python
# Environment variable support
# .env or environment
ENABLE_SQLALCHEMY=true
SQLALCHEMY_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
```

### Testing Strategy

**Backend Compatibility Testing**:
```python
# tests/unit/test_database_manager_integration.py
import pytest
from shared_context_server.database import UnifiedDatabaseManager
from shared_context_server.database.query_translator import QueryParameterTranslator

@pytest.mark.asyncio
class TestUnifiedDatabaseManager:
    async def test_legacy_backend_operations(self):
        """Test operations with legacy backend."""
        manager = UnifiedDatabaseManager(use_sqlalchemy=False)
        await manager.initialize()

        # Test basic query with tuple parameters
        result = await manager.execute_query("SELECT 1 as test", ())
        assert len(result) == 1
        assert result[0]['test'] == 1

    async def test_sqlalchemy_backend_operations(self):
        """Test operations with SQLAlchemy backend."""
        manager = UnifiedDatabaseManager(use_sqlalchemy=True)
        await manager.initialize()

        # Test basic query with dict parameters
        result = await manager.execute_query("SELECT 1 as test", {})
        assert len(result) == 1
        assert result[0]['test'] == 1

    async def test_parameter_translation(self):
        """Test parameter translation between backends."""
        manager = UnifiedDatabaseManager(use_sqlalchemy=True)
        await manager.initialize()

        # Test tuple parameters get translated to dict
        result = await manager.execute_query("SELECT ? as value", (42,))
        assert result[0]['value'] == 42

class TestQueryParameterTranslator:
    def test_positional_to_named_conversion(self):
        """Test converting ? to :param_N."""
        query = "SELECT * FROM table WHERE id = ? AND name = ?"
        params = (1, "test")

        new_query, new_params = QueryParameterTranslator.positional_to_named(query, params)

        assert new_query == "SELECT * FROM table WHERE id = :param_0 AND name = :param_1"
        assert new_params == {"param_0": 1, "param_1": "test"}

    def test_named_to_positional_conversion(self):
        """Test converting :name to ?."""
        query = "SELECT * FROM table WHERE id = :id AND name = :name"
        params = {"id": 1, "name": "test"}

        new_query, new_params = QueryParameterTranslator.named_to_positional(query, params)

        assert new_query == "SELECT * FROM table WHERE id = ? AND name = ?"
        assert new_params == (1, "test")
```

**Performance Comparison Testing**:
```python
# tests/performance/test_backend_performance.py
import pytest
import time
from shared_context_server.database import UnifiedDatabaseManager

@pytest.mark.performance
@pytest.mark.asyncio
class TestBackendPerformance:
    async def test_query_performance_comparison(self):
        """Compare query performance between backends."""
        legacy_manager = UnifiedDatabaseManager(use_sqlalchemy=False)
        sqlalchemy_manager = UnifiedDatabaseManager(use_sqlalchemy=True)

        await legacy_manager.initialize()
        await sqlalchemy_manager.initialize()

        # Test simple query performance
        query = "SELECT 1 as test"
        iterations = 100

        # Legacy performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            await legacy_manager.execute_query(query, ())
        legacy_time = time.perf_counter() - start_time

        # SQLAlchemy performance
        start_time = time.perf_counter()
        for _ in range(iterations):
            await sqlalchemy_manager.execute_query(query, {})
        sqlalchemy_time = time.perf_counter() - start_time

        # Performance should be comparable (within 50% difference)
        performance_ratio = sqlalchemy_time / legacy_time
        assert performance_ratio < 1.5, f"SQLAlchemy is {performance_ratio:.2f}x slower than legacy"

        print(f"Legacy: {legacy_time:.4f}s, SQLAlchemy: {sqlalchemy_time:.4f}s, Ratio: {performance_ratio:.2f}x")
```

---

## Success Criteria

### Functional Success
- ✅ Unified database manager works with both legacy and SQLAlchemy backends
- ✅ Parameter translation handles positional ↔ named conversion correctly
- ✅ All existing database operations work identically regardless of backend
- ✅ Feature flag controls backend selection at runtime
- ✅ Health checks and statistics work for both backends

### Integration Success
- ✅ Zero changes required to server.py database calls
- ✅ Existing test suite passes with both backends
- ✅ Performance within 50% of legacy implementation
- ✅ Memory usage comparable between backends

### Quality Gates
- ✅ 100% test coverage for new integration code
- ✅ Performance tests validate <50% degradation
- ✅ All existing tests pass with both backends
- ✅ Type checking and code quality maintained

### Validation Commands
```bash
# Backend functionality testing
uv run pytest tests/unit/test_database_manager_integration.py -v

# Performance validation
uv run pytest tests/performance/test_backend_performance.py -v

# Existing test suite with both backends
ENABLE_SQLALCHEMY=false uv run pytest tests/ -x
ENABLE_SQLALCHEMY=true uv run pytest tests/ -x

# Quality gates
uv run ruff check src/shared_context_server/database/
uv run mypy src/shared_context_server/database/
```

---

## Risk Assessment

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Parameter translation bugs | High | Medium | Comprehensive test coverage, gradual rollout |
| Performance degradation | High | Medium | Performance benchmarking, optimization tuning |
| Connection management issues | High | Low | Thorough testing, proper cleanup patterns |
| Feature flag state corruption | Medium | Low | Clear configuration management, validation |

### Migration Strategy
- **Gradual Rollout**: Start with read-only operations, progress to writes
- **Feature Flag Control**: Instant rollback capability
- **A/B Testing**: Run both backends in parallel during testing phase
- **Performance Monitoring**: Continuous metrics collection during migration

---

## Next Steps

**Upon Completion**: Enables toggling between database backends for safe migration testing
**Dependencies**: Requires PRP-007A (SQLAlchemy Core Foundation)
**Follow-up PRPs**:
- PRP-007C: Alembic Setup and Schema Definition
- PRP-007D: Migration Testing and Validation

---

**Implementation Notes**:
- Implement parameter translation carefully with comprehensive testing
- Ensure connection management patterns are properly abstracted
- Validate performance meets requirements before proceeding
- Test feature flag switching extensively to ensure reliability
