# PRP-008: SQLAlchemy Core Migration Stabilization (KISS Edition)

**Document Type**: Product Requirement Prompt
**Created**: 2025-01-13
**Status**: Implementation Ready
**Priority**: Critical - 22 Failing Tests
**Estimated Effort**: 1-2 days
**Complexity Level**: Medium - Bug Fixes

---

## Problem Statement

**Reality Check**: 22 tests are failing due to over-engineered SQLAlchemy migration that's 85% complete but broken.

**Current Issues**:
- Working `database_legacy.py` was replaced by complex SQLAlchemy infrastructure
- Multiple database managers, migration validators, cross-database testers - all failing
- Over-engineered solution for a simple SQLite MCP server
- Technical debt created by premature optimization

**Goal**: Get tests passing with minimal viable SQLAlchemy integration.

---

## KISS Solution

### Phase 1: Stabilize Core (1 day)

**Fix Import Issues**:
1. Fix all import errors in new SQLAlchemy modules
2. Ensure database connection works with existing server.py
3. Get basic CRUD operations working

**Essential Files Only**:
- `src/shared_context_server/database/manager.py` - Single unified manager
- Fix imports in `src/shared_context_server/server.py`
- Remove failing test infrastructure until basics work

### Phase 2: Test Stabilization (1 day)

**Fix 22 Failing Tests**:
1. Focus on core functionality tests first
2. Comment out complex cross-database tests until basics work
3. Fix health checks and schema operations
4. Get session/message operations passing

**Remove YAGNI Violations**:
- Remove PostgreSQL support (not needed for MVP)
- Remove cross-database testing (not needed for MVP)
- Remove migration validators (over-engineered)
- Remove performance validators (premature optimization)

---

## Minimal Implementation

### Single Database Manager
```python
# src/shared_context_server/database/manager.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import aiosqlite

class SimpleSQLAlchemyManager:
    """Dead simple SQLAlchemy wrapper - KISS principle."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./chat_history.db"):
        self.database_url = database_url
        self.engine = create_async_engine(database_url)

    async def execute_query(self, query: str, params: dict = None):
        """Execute query - that's it."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]

    async def execute_update(self, query: str, params: dict = None):
        """Execute update - that's it."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text(query), params or {})
            return result.rowcount
```

### Simplified Integration
```python
# Update config.py to use simple manager
from .database.manager import SimpleSQLAlchemyManager

# Update server.py imports - minimal changes
# Remove complex features until basics work
```

---

## Success Criteria (Minimal)

### Critical Path Only
- [ ] All import errors fixed
- [ ] Server starts without errors
- [ ] Basic session create/get operations work
- [ ] Message add/retrieve operations work
- [ ] Health check passes
- [ ] **22 failing tests become passing**

### Explicit YAGNI Eliminations
- ❌ PostgreSQL support (not needed for MVP)
- ❌ MySQL support (not needed for MVP)
- ❌ Cross-database testing (not needed for MVP)
- ❌ Migration validators (over-engineered)
- ❌ Performance validators (premature optimization)
- ❌ Complex connection pooling (SQLite handles this)
- ❌ Database-specific optimizations (premature optimization)
- ❌ Multi-phase migration (over-engineered)

### What We Keep
- ✅ SQLAlchemy Core (already implemented)
- ✅ Basic async operations
- ✅ Existing schema
- ✅ UTC timestamps
- ✅ Basic error handling

---

## Implementation Strategy

### Day 1: Fix Imports & Core
1. **Fix all import errors** - get system starting
2. **Simplify database manager** - remove complex features
3. **Get server.py working** - minimal changes to existing code
4. **Basic functionality test** - create session, add message

### Day 2: Test Fixes
1. **Fix core database tests** - health, schema, basic ops
2. **Fix server integration tests** - session and message ops
3. **Comment out complex tests** - cross-database, performance, migration
4. **Validate 22 tests pass** - or at least core functionality works

### Rollback Plan
If SQLAlchemy still doesn't work after 2 days:
1. Revert to `database_legacy.py`
2. Remove all SQLAlchemy infrastructure
3. Get system working with simple SQLite again
4. Consider SQLAlchemy later when MVP is stable

---

## Anti-Patterns Eliminated

❌ **Over-Engineering**: Removed complex migration framework
❌ **Future-Proofing**: Removed multi-database support
❌ **Premature Optimization**: Removed performance validators
❌ **Gold-Plating**: Removed advanced features not needed for MVP
❌ **Analysis Paralysis**: Simple fix-the-tests approach

---

**Next Step**: Fix imports, get tests passing, ship working code.
