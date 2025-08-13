# PRP-011: Web UI Implementation for Multi-Agent Session Management

**Status**: Implementation Ready
**Created**: 2025-08-13
**Research Context**: Tech guides validation, SQLAlchemy integration analysis, FastMCP-web integration research
**Complexity**: Moderate (6-8 files, 12-17 hours estimated)

## Research Context & Architectural Analysis

### Research Integration
Our comprehensive tech guides validation revealed:
- **FastMCP + Web UI Compatibility**: Research confirmed FastMCP is built on Starlette (ASGI framework) with full HTTP route support via `@mcp.custom_route()` decorator
- **Existing Proof of Concept**: The `/health` endpoint in `server.py` demonstrates working FastMCP + HTTP integration
- **Import Validation**: All tech guide import statements are correct - validation functions exist in `shared_context_server.models`
- **Performance Claims**: RapidFuzz "<100ms search" and "5-10x faster" claims are realistic but not yet validated

### Architectural Scope
**MCP Server Integration**: Zero-impact additive design extending existing FastMCP server
- Leverages existing `get_db_connection()` unified interface for dual backend support (aiosqlite + SQLAlchemy)
- Uses established database patterns with `messages` and `sessions` tables
- Maintains MCP tool isolation with separate web authentication system

**Multi-Agent Coordination Requirements**:
- Real-time WebSocket notifications for collaborative session viewing
- Session visibility controls aligned with agent authentication patterns
- WebSocket connection pooling for concurrent agent monitoring

### Existing Patterns to Leverage
- **Database Operations**: `get_db_connection()` context manager with automatic backend selection
- **FastMCP Tools**: Resource notification patterns via `ResourceNotificationManager`
- **Session Management**: Existing session isolation and UTC timestamp patterns
- **Error Handling**: LLM-optimized error responses with structured feedback

## Implementation Specification

### Core Requirements
**FastMCP Web Routes** (extends existing `server.py`):
```python
@mcp.custom_route("/ui/", methods=["GET"])
async def dashboard(request: Request) -> HTMLResponse

@mcp.custom_route("/ui/sessions/{session_id}", methods=["GET"])
async def session_view(request: Request, session_id: str) -> HTMLResponse

@mcp.websocket("/ui/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str)
```

**Template System**:
- Jinja2Templates for HTML rendering
- Static file serving for CSS/JS assets
- Mobile-responsive design with progressive enhancement

**WebSocket Integration**:
- Extend `ResourceNotificationManager` for real-time UI updates
- Connection pooling with cleanup for inactive connections
- Message broadcasting to connected session viewers

### Integration Points
**Database Layer**:
- Uses unified `get_db_connection()` - works with both aiosqlite and SQLAlchemy backends
- Leverages existing `messages` table with `sender`, `content`, `timestamp`, `visibility` fields
- No schema changes required - read-only access patterns

**Authentication System**:
- Separate web authentication independent of MCP JWT tokens
- Optional security model for trusted environments
- Session-based token management for web UI access

**Resource System**:
- Integrates with existing `session://` URI patterns
- WebSocket notifications parallel to MCP resource notifications
- Maintains MCP tool and web UI isolation

### API Requirements
**Web UI Endpoints**:
- `GET /ui/` - Main dashboard with session list
- `GET /ui/sessions/{id}` - Individual session message viewer
- `POST /ui/auth` - Web authentication (optional)
- `WebSocket /ui/ws/{id}` - Real-time session updates

**Data Patterns**:
- JSON responses for AJAX calls
- HTML templates for page rendering
- WebSocket JSON message protocol for real-time updates

## Quality Requirements

### Testing Strategy
**Multi-Backend Testing**:
- Parametrized tests across both aiosqlite and SQLAlchemy backends
- WebSocket connection and message delivery validation
- Template rendering and static file serving tests

**Integration Testing**:
- FastMCP + HTTP route integration tests
- Real-time WebSocket message broadcasting
- Concurrent agent access with web UI monitoring

**Frontend Testing**:
- JavaScript unit tests for WebSocket handling
- HTML template validation and XSS prevention
- Mobile responsiveness and accessibility compliance

### Documentation Needs
**Implementation Guide**:
- Step-by-step integration with existing `server.py`
- Template and static file organization
- WebSocket integration patterns

**API Documentation**:
- Web UI endpoint specifications
- WebSocket message protocol documentation
- Authentication flow (when enabled)

### Performance Considerations
**Concurrent Access**:
- WebSocket connection pooling (max 1000 connections)
- Database connection sharing with MCP operations
- Static file caching and optimization

**Resource Management**:
- Automatic WebSocket cleanup on disconnect
- Memory-efficient template rendering
- Progressive loading for large session histories

## Coordination Strategy

### Recommended Approach
**task-coordinator** coordination recommended due to:
- **Multi-file Integration**: Updates to `server.py`, new template files, static assets, test files
- **Frontend + Backend Coordination**: HTML/CSS/JS frontend with FastMCP backend integration
- **Quality Gates**: Multiple testing phases (backend, frontend, integration)
- **Documentation Requirements**: Implementation guide and API documentation

### Implementation Phases
**Phase 1: Core Web Routes (4-6 hours)**
- Add FastMCP web routes to `server.py`
- Create basic HTML templates (dashboard, session viewer)
- Implement static file serving
- Basic database integration with `get_db_connection()`

**Phase 2: WebSocket Integration (3-4 hours)**
- Extend `ResourceNotificationManager` for WebSocket support
- Implement real-time message broadcasting
- WebSocket connection management and cleanup
- Frontend JavaScript for real-time updates

**Phase 3: Authentication & Polish (2-3 hours)**
- Optional web authentication system
- CSS styling and mobile responsiveness
- Error handling and user feedback
- Performance optimization

**Phase 4: Testing & Documentation (3-4 hours)**
- Comprehensive test suite (backend + frontend)
- Integration testing with both database backends
- Implementation documentation
- API reference documentation

### Risk Mitigation
**Architecture Integration Risks**:
- **Mitigation**: Use existing `@mcp.custom_route()` pattern proven by `/health` endpoint
- **Validation**: Incremental testing at each phase

**Database Backend Compatibility**:
- **Mitigation**: Unified `get_db_connection()` interface abstracts backend differences
- **Validation**: Parametrized testing across both aiosqlite and SQLAlchemy

**Performance Impact**:
- **Mitigation**: Optional feature flag for web UI enablement
- **Validation**: Performance benchmarking with concurrent MCP operations

### Dependencies
**Infrastructure Ready**:
- ✅ FastMCP server with HTTP route support
- ✅ Dual database backend system (aiosqlite + SQLAlchemy)
- ✅ Unified database connection interface
- ✅ Resource notification system foundation

**Missing Dependencies** (to be added):
- HTML templates and static assets
- WebSocket integration code
- Web authentication system (optional)
- Frontend JavaScript for real-time updates

## Success Criteria

### Functional Success
**Core Web UI Operations**:
- Dashboard loads and displays active sessions
- Session viewer shows message history with real-time updates
- WebSocket connections maintain stability with automatic reconnection
- Works identically with both aiosqlite and SQLAlchemy backends

**Multi-Agent Collaboration**:
- Multiple agents can view session progress simultaneously
- Real-time message updates visible to all connected viewers
- Session isolation maintained across different collaborative contexts

### Integration Success
**MCP Server Integration**:
- Web UI operates without disrupting MCP tool functionality
- Database operations maintain concurrency with agent operations
- Resource notifications work for both MCP tools and web UI

**Performance Validation**:
- WebSocket connections handle 100+ concurrent viewers
- Page load times under 2 seconds for 1000+ message sessions
- No performance degradation to existing MCP operations

### Quality Gates
**Testing Requirements**:
- 85%+ code coverage including WebSocket and template code
- Multi-backend parametrized testing validates identical behavior
- Frontend testing covers WebSocket handling and XSS prevention

**Documentation Standards**:
- Complete implementation guide with code examples
- API documentation for all web endpoints
- WebSocket protocol specification with message examples

**Production Readiness**:
- Environment configuration for production deployment
- Security validation for web authentication (when enabled)
- Performance benchmarking under concurrent load

## Implementation Notes

### SQLAlchemy Backend Compatibility
The web UI automatically adapts to database backend selection:
```python
# Works with both backends via unified interface
async with get_db_connection() as conn:
    if hasattr(conn, 'row_factory'):
        import aiosqlite
        conn.row_factory = aiosqlite.Row

    cursor = await conn.execute("SELECT * FROM messages WHERE session_id = ?", (session_id,))
    messages = [dict(row) for row in await cursor.fetchall()]
```

### Zero-Impact Design
- Web UI routes use `/ui/*` prefix to avoid MCP tool conflicts
- Separate authentication system prevents MCP JWT interference
- Optional feature - server functions fully without web UI enabled
- Feature flag rollback capability for production safety

### Future Extensibility
- Foundation for advanced features (search, filtering, export)
- WebSocket infrastructure supports additional real-time features
- Template system enables customization and branding
- SQLAlchemy backend positions for PostgreSQL scaling when needed

---

**Generated**: 2025-08-13
**Context**: Tech guides validation, FastMCP integration research, dual database backend analysis
**Next Step**: Use `execute-prp` with task-coordinator for multi-phase implementation
