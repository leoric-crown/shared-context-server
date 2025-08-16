---
session_id: session_31ef217d52614289
session_purpose: "Feature planning: Memory UI scope toggle and session memory view"
created_date: 2025-08-16T07:15:00Z
stage: "1-planning"
planning_type: "ui_enhancement"
complexity: "moderate"
---

# Memory UI Scope Improvements - Planning Document

## Executive Summary

Enhance the shared context server web UI to provide complete visibility into the dual-scope memory system (global + session-scoped memories) through two targeted improvements:

1. **Memory View Enhancement**: Add scope filtering to `/ui/memory`
2. **Session View Integration**: Add session memory tab to `/ui/sessions/{session_id}`

**Goal**: Achieve full database visibility before migration to proper frontend framework.

## Discovery & Requirements

### Current State Analysis

**Memory View (`/ui/memory`)**:
- ✅ Shows global memories with search, pagination, modal views
- ❌ Hardcoded to global scope only (`WHERE session_id IS NULL`)
- ❌ No visibility into session-scoped memories

**Session View (`/ui/sessions/{session_id}`)**:
- ✅ Comprehensive message display with real-time updates
- ✅ WebSocket integration, metadata support
- ❌ No session memory section despite being primary use case

### User Requirements (Validated)

1. **Memory View**: Radio button scope filter
   - `● Global Only` (current behavior)
   - `○ Session-Scoped Only`
   - `○ All Memories`

2. **Session View**: Tabbed interface
   - `Messages` tab (current content)
   - `Memory` tab (new session memory table)

## Technical Implementation Plan

### Phase 1: Memory View Scope Filter

**Backend Changes**:
- Modify `memory_dashboard()` route at `server.py:442`
- Add `scope` query parameter: `?scope=global|session|all`
- Update SQL query conditionally:
  ```sql
  -- Global: WHERE session_id IS NULL
  -- Session: WHERE session_id IS NOT NULL
  -- All: No WHERE clause on session_id
  ```

**Frontend Changes**:
- Add radio button group to `memory.html` before search input
- JavaScript scope filtering with URL updates
- Update page title dynamically: "Global Memory" → "Memory Dashboard"
- Add scope-specific statistics display

**UX Considerations**:
- Default to "Global Only" (preserves current behavior)
- Show counts for each scope: "Global (2) | Session (3) | All (5)"
- Preserve search functionality across scope changes

### Phase 2: Session View Memory Tab

**Backend Changes**:
- Add session memory query to `session_view()` route
- Query session-scoped memories: `WHERE session_id = ?`
- Pass both messages and memories to template

**Frontend Changes**:
- Convert `session_view.html` to tabbed interface
- Move current content to "Messages" tab
- Create "Memory" tab with table similar to memory.html
- Preserve WebSocket updates for real-time memory changes

**UX Considerations**:
- Default to "Messages" tab (preserves current behavior)
- Show counts in tab labels: "Messages (5)" | "Memory (3)"
- Reuse existing modal and timestamp formatting code

## Integration Points

### Database Schema
- Existing `agent_memory` table supports dual scope via `session_id`
- No schema changes required

### Authentication
- Reuse existing agent context validation
- Memory visibility respects agent permissions

### WebSocket Integration
- Extend session WebSocket to include memory updates
- Real-time memory changes reflected in both views

### UI Component Reuse
- Modal system (`viewFullValue` function)
- Timestamp formatting (JavaScript utilities)
- Search functionality patterns
- Table styling and responsive design

## Implementation Complexity: Moderate

**Simple Elements**:
- SQL query modifications (conditional WHERE clauses)
- Radio button HTML/CSS (standard web pattern)
- Tab interface HTML structure

**Moderate Elements**:
- JavaScript state management for scope filtering
- WebSocket integration for memory updates
- Coordinating URL parameters with UI state

**Risk Mitigation**:
- Preserve existing behavior as defaults
- Incremental rollout (memory view first, then session view)
- Comprehensive testing of scope filtering edge cases

## Success Criteria

### Memory View Success
- ✅ Radio buttons filter correctly between scopes
- ✅ Search works within selected scope
- ✅ URL reflects current scope (`?scope=global`)
- ✅ Statistics update dynamically
- ✅ All 5 test memories visible in "All" mode

### Session View Success
- ✅ Tabs switch between Messages and Memory
- ✅ Session memory table shows session-scoped entries only
- ✅ Real-time updates work for both tabs
- ✅ Modal views work for memory values
- ✅ No regression in message functionality

### User Experience Success
- ✅ Intuitive UI - no training required
- ✅ Fast switching between scopes (<200ms)
- ✅ Mobile-responsive design maintained
- ✅ Consistent styling with existing UI
- ✅ Complete database visibility achieved

## Next Steps

1. **Implementation Phase**: Use `create-prp` command to convert this planning into detailed implementation specifications
2. **Development**: Implement memory view enhancements first, then session view integration
3. **Testing**: Validate with existing test memories across both scopes
4. **Documentation**: Update user guides for new memory visibility features

## Research Context

- **UI Patterns**: Radio buttons confirmed as best practice for single-select filtering
- **Tab Interfaces**: Widely supported, accessible, familiar to users
- **Industry Standards**: Scope filtering common in dashboard applications
- **Technical Foundation**: Existing codebase well-structured for enhancement

---

**Planning Session**: `session_31ef217d52614289`
**Implementation Ready**: ✅ All requirements validated and technical approach confirmed
**Agent Recommendation**: Use `cfw-developer` for implementation with browser testing validation
