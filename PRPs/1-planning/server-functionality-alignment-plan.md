# Server Functionality Alignment Plan

---
session_id: session_671bd2cd15b341f6
session_purpose: "Feature planning: Align functionality between shared-context-server and scs-dev"
created_date: 2025-08-23T14:24:00Z
stage: "1-planning"
planning_type: "bug_fix_alignment"
complexity: "medium"
estimated_effort: "60 minutes"
---

## Executive Summary

**Objective**: Fix critical data serialization bugs in the scs-dev server to achieve functional parity with the main shared-context-server.

**Strategic Context**: Following PRP-001 (Aggressive aiosqlite Removal), the dev server has SQLAlchemy wrapper implementation issues that prevent proper message retrieval and search functionality.

**Impact Scope**:
- **1 critical file**: `src/shared_context_server/database_manager.py`
- **2 critical methods**: `fetchone()` and `fetchall()` in SQLAlchemyCursorWrapper
- **Core functionality affected**: Message retrieval, search operations

## Current State Analysis

### Functional Comparison Results

**Main Server (shared-context-server) - ✅ FULLY FUNCTIONAL:**
- Authentication: PASS - JWT tokens generated correctly
- Session Management: PASS - Sessions created and retrieved successfully
- Message Operations: PASS - All message types stored and retrieved with proper visibility
- Memory Operations: PASS - Session and global memory working correctly
- Search Functionality: PASS - Messages found with proper similarity scores

**Dev Server (scs-dev) - ❌ CRITICAL ISSUES:**
- Authentication: PASS - Works after SQLAlchemy URL fix (completed in PRP-001)
- Session Management: PASS - Sessions created successfully
- **Message Operations: FAIL** - Messages stored but retrieved as empty objects `{}`
- **Search Functionality: FAIL** - Cannot find stored messages, returns empty results
- Memory Operations: Untested due to message retrieval failures

### Root Cause Analysis

**Primary Issue: Data Serialization Bug in SQLAlchemy Wrapper**

The `SQLAlchemyCursorWrapper` class in `database_manager.py` has inverted logic for row factory handling:

```python
# CURRENT BUG (lines 144-152)
async def fetchone(self) -> CompatibleRow | None:
    row = self._result.fetchone()
    if row is None:
        return None

    if self._row_factory:  # BUG: Logic is inverted
        return CompatibleRow(row)
    return row  # BUG: Returns unwrapped SQLAlchemy row
```

**Impact Chain:**
1. `get_db_connection()` sets `conn.row_factory = CompatibleRow` (line 422)
2. `fetchone()` incorrectly wraps rows only when factory is set
3. Messages retrieved as empty objects instead of proper data
4. Search functionality fails because it can't access message content

## Proposed Solution

### Technical Fix Strategy

**Approach**: Targeted bug fix with minimal code changes for maximum impact.

**Core Fix: Correct Row Wrapper Logic**

```python
# CORRECTED IMPLEMENTATION
async def fetchone(self) -> CompatibleRow | None:
    """Fetch one row with proper compatibility wrapping."""
    row = self._result.fetchone()
    if row is None:
        return None

    # Always ensure compatibility wrapper for consistent access
    if self._row_factory == CompatibleRow:
        return CompatibleRow(row)
    elif self._row_factory:
        return self._row_factory(row)
    else:
        # Default to CompatibleRow for backward compatibility
        return CompatibleRow(row)

async def fetchall(self) -> list[CompatibleRow]:
    """Fetch all rows with consistent wrapping."""
    rows = self._result.fetchall()
    if self._row_factory == CompatibleRow:
        return [CompatibleRow(row) for row in rows]
    elif self._row_factory:
        return [self._row_factory(row) for row in rows]
    else:
        # Default to CompatibleRow for backward compatibility
        return [CompatibleRow(row) for row in rows]
```

## Implementation Plan

### Phase 1: Critical Bug Fix (30 minutes)

**Step 1: Fix SQLAlchemyCursorWrapper Methods**
1. Update `fetchone()` method with correct row factory logic
2. Update `fetchall()` method for consistent row wrapping
3. Ensure backward compatibility with existing code

**Step 2: Validate Data Access**
1. Test basic message storage and retrieval
2. Verify row objects contain expected data
3. Confirm CompatibleRow wrapper functionality

### Phase 2: Functional Validation (20 minutes)

**Step 3: E2E Regression Testing**
1. Run E2E test suite against fixed dev server
2. Compare results with main server functionality
3. Validate all message operations return proper data

**Step 4: Search Functionality Validation**
1. Test search operations with proper data access
2. Verify fuzzy search finds stored messages
3. Confirm search results include similarity scores

### Phase 3: Quality Assurance (10 minutes)

**Step 5: Test Suite Validation**
1. Run unit tests to ensure no regressions
2. Verify test coverage maintained
3. Check for any additional issues

**Step 6: Performance Validation**
1. Confirm <30ms message operations maintained
2. Validate search performance (2-3ms target)
3. Check memory usage patterns

## Risk Assessment & Mitigation

### Low Risk Factors

**1. Localized Change Impact**
- **Risk**: Fix affects only data access layer
- **Mitigation**: Minimal scope reduces regression risk
- **Validation**: Comprehensive testing covers edge cases

**2. Backward Compatibility**
- **Risk**: Changes might affect existing API contracts
- **Mitigation**: Preserve all existing function signatures
- **Testing**: API compatibility validation

### Mitigation Strategies

**1. Incremental Testing**
- Test each method change independently
- Validate data access before proceeding
- Run regression tests after each fix

**2. Fallback Plan**
- Keep original implementation for quick rollback
- Document exact changes for easy reversal
- Maintain test coverage for both paths

## Success Criteria

### Technical Success
- ✅ **Data Retrieval Fixed**: Messages retrieved as proper objects (not empty `{}`)
- ✅ **Search Functionality Restored**: Search operations find stored messages correctly
- ✅ **Row Wrapper Consistency**: CompatibleRow provides uniform data access
- ✅ **API Compatibility Maintained**: All existing interfaces work identically

### Functional Success
- ✅ **E2E Test Parity**: Dev server matches main server test results
- ✅ **Message Operations**: All CRUD operations work with proper data access
- ✅ **Search Performance**: 2-3ms fuzzy search performance maintained
- ✅ **Memory Operations**: Session and global memory work reliably

### Quality Success
- ✅ **No Regressions**: Test suite pass rate maintained or improved
- ✅ **Performance Maintained**: <30ms message operations preserved
- ✅ **Code Quality**: Fix follows established patterns and standards

## Files Impacted

### Files to Modify (1 file)
- `src/shared_context_server/database_manager.py` - Fix SQLAlchemyCursorWrapper methods

### Specific Changes
- **Lines 144-152**: Update `fetchone()` method logic
- **Lines 154-158**: Update `fetchall()` method logic
- **Estimated Impact**: ~15 lines of code changes

## Validation Plan

### Test Sequence
1. **Unit Tests**: Verify wrapper methods work correctly
2. **Integration Tests**: Test database operations with fixed wrapper
3. **E2E Tests**: Run full regression suite against dev server
4. **Performance Tests**: Validate operation timing targets
5. **Comparison Tests**: Verify dev server matches main server results

### Success Validation Commands
```bash
# Test message operations
uv run python -c "
from shared_context_server.session_tools import create_session, add_message, get_messages
# Test basic functionality
"

# Run E2E regression tests
pytest tests/e2e-llm-regression-test.py -v

# Performance validation
pytest tests/performance/ -v --timeout=30
```

## Next Steps

### Immediate Actions
1. **Begin Implementation**: Start with fetchone() method fix
2. **Incremental Testing**: Test each change before proceeding
3. **Validation**: Run E2E tests to confirm functionality
4. **Documentation**: Update any relevant technical docs

### Post-Implementation
1. **Performance Monitoring**: Track operation timing
2. **User Validation**: Confirm dev server functionality
3. **Cleanup**: Remove any temporary debugging code
4. **Knowledge Transfer**: Document solution for future reference

---

**Planning Status**: ✅ **COMPLETE - Ready for Implementation**
**Next Phase**: Begin targeted bug fix implementation
**Estimated Completion**: 60 minutes for complete alignment
