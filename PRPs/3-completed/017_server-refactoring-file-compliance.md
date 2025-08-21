# PRP-001: Server Refactoring for File Size Compliance

---
session_id: session_593bb84a27204f59
session_purpose: "PRP creation: Hardening and Multi-Database Support from planning 1.1.0"
created_date: 2025-08-16T23:04:35.414102+00:00
stage: "2-prps"
planning_source: "PRPs/1-planning/1.1.0-hardening-and-multidb/"
planning_session_id: session_4f261d2db4ae43fe
team_evaluation_complete: true
effort_estimate: "14-18 hours"
complexity: "HIGH"
risk_level: "HIGH"
---

## Research Context & Architectural Analysis

**Research Integration**: Comprehensive team evaluation completed with 4 specialized agents providing detailed technical analysis. FastMCP architectural patterns researched to ensure proper modularization approaches align with framework best practices.

**Architectural Scope**: Critical refactoring of server.py (3,712 lines → 8 modules) while preserving all 23 MCP tools, dual database backend support, WebSocket integration, and JWT authentication systems. Zero-regression requirement for production system.

**Existing Patterns**:
- FastMCP decorator-based tool registration system
- Dual backend architecture (aiosqlite/SQLAlchemy)
- JWT authentication with role-based access control
- Comprehensive validation framework with 1,044+ tests
- Performance targets: <30ms operations, 2-3ms search (RapidFuzz)

**Team Evaluation Findings**:
- **Scale Reality Check**: server.py actually 3,712 lines (47% larger than planned)
- **Implementation Status**: Multi-DB support already complete (contrary to planning assumptions)
- **Critical Gaps**: 13 files violating size limits, JWT development fallback present
- **Effort Correction**: 14-18 hours realistic vs original 4-5 hour estimates

## Implementation Specification

### Core Requirements

**Primary Objective**: Refactor server.py into 8 compliant modules (<500 lines each) while maintaining 100% functional compatibility and zero regressions.

**File Size Compliance Targets**:
- server.py: 3,712 lines → 8 modules averaging 460 lines
- 12 additional files requiring compliance (detailed in Phase 3)
- Security hardening: Remove JWT development fallback

**Critical Constraints**:
- All 1,044+ tests must continue passing
- All 23 MCP tools maintain exact interface compatibility
- Performance targets preserved (<30ms operations, 2-3ms search)
- Dual database backend support unchanged
- WebSocket and Web UI functionality preserved

### Integration Points

**Module Architecture** (8-module breakdown):
1. `core_server.py` (~150 lines): FastMCP foundation and initialization
2. `websocket_handlers.py` (~100 lines): Real-time communication infrastructure
3. `web_endpoints.py` (~350 lines): Dashboard UI and web interface
4. `auth_tools.py` (~400 lines): Authentication MCP tools and JWT handling
5. `session_tools.py` (~550 lines): Session management tools (create_session, get_session, etc.)
6. `search_tools.py` (~650 lines): Search and discovery tools (search_context, fuzzy search)
7. `memory_tools.py` (~500 lines): Agent memory management tools with TTL
8. `admin_tools.py` (~550 lines): Administration, monitoring, and performance tools

**Interface Preservation Strategy**:
- Facade pattern for backward compatibility: `from .server import tool_name`
- MCP tool registration system maintained
- Import structure unchanged for existing consumers
- Environment variable configuration preserved

**Data Model Changes**: None required - refactoring preserves all data structures and database schemas.

### Quality Requirements

**Testing Strategy**:
- Zero-Regression Guarantee: Comprehensive validation framework already established
- Incremental validation: Full test suite after each module extraction
- Performance benchmarking: Baseline comparison after each change
- Rollback procedures: Git checkpoints with <30 second recovery time

**Validation Framework** (Pre-implemented):
- `tests/security/test_jwt_hardening_validation.py`: 7 JWT security tests
- `tests/integration/test_api_stability_validation.py`: 23+ MCP tool interface validation
- `tests/integration/test_rollback_strategy_validation.py`: Safe rollback procedures
- Dual backend testing: `USE_SQLALCHEMY=true/false make test`

**Critical Regression Tracking Commands**:
```bash
# Execute these specific test suites for regression validation:
uv run pytest tests/integration/test_api_stability_validation.py tests/security/test_jwt_hardening_validation.py
```

**Documentation Needs**:
- Update module import documentation
- Architecture diagram showing 8-module structure
- Migration guide for developers extending the system

**Performance Considerations**:
- Maintain <30ms message operations
- Preserve 2-3ms fuzzy search performance (RapidFuzz)
- No degradation >5% in critical paths
- Support 20+ concurrent agents per session

## Coordination Strategy

**Recommended Approach**: Single specialist agent (cfw-refactor) due to:
- **Complexity Assessment**: HIGH (3,712 lines, 23 MCP tools, dual backends)
- **Risk Level**: HIGH (production system, 1,044+ tests must pass)
- **Maintainability Focus**: Primary goal is code organization and maintainability
- **Refactoring Expertise**: Complex module extraction with interface preservation

**Implementation Phases**:

### Phase 1: Critical Compliance (6-8 hours)
**Priority**: server.py modularization with zero regression
- Incremental extraction: 8 logical modules with git checkpoints
- Facade pattern implementation for 100% backward compatibility
- Full test validation after each module extraction
- Performance monitoring throughout refactoring

### Phase 2: Security Hardening (30 minutes)
**Priority**: Remove JWT development fallback
- File: `src/shared_context_server/auth.py` (lines 68-77)
- Force JWT_SECRET_KEY requirement in all environments
- Low risk (production already protected)

### Phase 3: Complete File Compliance (8-10 hours)
**Priority**: Remaining 12 files achieving size compliance
- Source code files: database.py, models.py, auth.py, config.py, etc.
- Test files: Large comprehensive test suites modularization
- Systematic approach with same validation framework

**Risk Mitigation**:
- Incremental approach: One module extraction per session
- Git checkpoint after each successful change
- Automated rollback triggers: test failures, >10% performance degradation
- Recovery time: <5 minutes per rollback

**Dependencies**:
- Baseline metrics documentation (already complete)
- Comprehensive validation framework (already implemented)
- Team evaluation specifications (available in session_4f261d2db4ae43fe)

## Success Criteria

**Functional Success**:
- All 13 files achieve size compliance (<500 lines source, <1000 lines tests)
- 100% test pass rate maintained (1,044+ tests)
- All 23 MCP tools fully operational with identical interfaces
- JWT security hardening complete (no development fallbacks)

**Integration Success**:
- Dual database backend support preserved (aiosqlite/SQLAlchemy)
- WebSocket and Web UI functionality unchanged
- Import compatibility: `from .server import tool_name` works unchanged
- Configuration environment variables function identically

**Quality Gates**:
- Performance baselines maintained or improved
- Zero breaking changes in API contracts
- Complete rollback capability validated
- Security boundaries preserved throughout refactoring

**Validation Approach**:
- Pre-refactoring: Baseline establishment with current metrics
- During refactoring: Module-by-module validation with rollback triggers
- Post-refactoring: Comprehensive integration testing and final validation
- Production readiness: Complete security audit and performance verification

## Implementation Context

**FastMCP Framework Integration**:
- Leverage FastMCP decorator patterns for clean tool registration
- Maintain server initialization and lifecycle management
- Preserve tool discovery and metadata systems
- Follow FastMCP modularization best practices

**Database Backend Coordination**:
- USE_SQLALCHEMY environment variable switching preserved
- Schema migration compatibility maintained
- Query performance parity across backends
- Connection pooling behavior consistency

**Existing Validation Infrastructure**:
- Comprehensive test coverage (1,044+ tests with 99.84% pass rate)
- Performance benchmarking tools established
- Security validation framework operational
- Rollback and recovery procedures tested

**Team Coordination Reference**:
- Original evaluation session: session_4f261d2db4ae43fe
- Detailed technical specifications available from 4 specialist agents
- 17 technical analysis messages with complete implementation strategy
- Cross-reference capability for specific technical details

## Next Steps

1. **Environment Preparation**: Work in `/Users/Ricardo_Leon1/TestIO/scs/1.1.0-refactor/` worktree, establish baseline metrics
2. **Module Extraction Sequence**: Begin with session management module (lowest risk) in refactor branch
3. **Validation Protocol**: Execute comprehensive test suite after each extraction
4. **Quality Assurance**: Continuous performance monitoring and rollback readiness within worktree
5. **Security Hardening**: JWT development fallback removal after core refactoring
6. **Complete Compliance**: Systematic approach to remaining 12 files

**Recommended Agent**: `cfw-refactor` - Complex refactoring specialist with maintainability focus
**Coordination Level**: Single agent with comprehensive validation framework
**Session Context**: Continue using session_593bb84a27204f59 for coordination and progress tracking
**Working Directory**: Execute all refactoring in `/Users/Ricardo_Leon1/TestIO/scs/1.1.0-refactor/` worktree
**Quality Assurance**: Zero-regression guarantee with established testing infrastructure

---

**PRP Status**: Ready for execution with comprehensive planning and validation framework
**Research Complete**: Team evaluation findings integrated with FastMCP architectural patterns
**Risk Assessment**: High complexity with comprehensive mitigation strategies in place
**Execution Timeline**: 14-18 hours across 3 phases with incremental validation
