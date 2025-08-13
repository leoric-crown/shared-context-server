# PRP-012: WebSocket Real-time Message Broadcasting Bridge

**Status**: Implementation Complete ✅
**Priority**: High
**Complexity**: Low
**Estimated Effort**: 2-4 hours
**Generated**: 2025-01-13
**Planning Source**: PRPs/1-planning/1.0.2-dashboard/websocket-realtime-broadcast-bridge.md
**Implementation Retrospective**: PRPs/1-planning/1.0.2-dashboard/retrospective.md

## Research Context & Architectural Analysis

**Research Integration**: Comprehensive planning phase completed with expert validation from @agent-developer (9.5/10) and @agent-tester (8/10). Technical approach validated using FastAPI WebSocket Broadcasting patterns from established community implementations.

**Architectural Scope**: Simple HTTP bridge implementation between existing dual-server architecture:
- **MCP Server** (port 23456): Main FastMCP server with database operations and message storage
- **WebSocket Server** (port 8081): Separate FastAPI server using mcpsock for real-time connections
- **Integration Point**: websocket_manager already imported from server.py to websocket_server.py

**Existing Patterns**: Leverages established FastAPI async patterns, existing httpx>=0.25.0 dependency, and proven WebSocket connection management already working in websocket_server.py.

**Root Cause Analysis**: Dual-server architecture isolates memory - MCP server's websocket_manager.broadcast_to_session() broadcasts to empty connection manager while actual WebSocket connections exist on separate server process.

## Implementation Specification

### Core Requirements

**HTTP Bridge Implementation**:
1. **WebSocket Server Enhancement** (`src/shared_context_server/websocket_server.py`):
   - Add `POST /broadcast/{session_id}` endpoint to receive broadcast requests
   - Use existing websocket_manager import from server.py for connection management
   - Return success/failure status for debugging and monitoring

2. **MCP Server Integration** (`src/shared_context_server/server.py`):
   - Add async HTTP client call using existing httpx dependency
   - Integrate with existing `add_message` function after message storage
   - Implement graceful error handling for optional WebSocket functionality

### Integration Points

**FastMCP Server Integration**:
- Modify existing `add_message` MCP tool in server.py (line ~1036)
- Add HTTP notification after successful message storage in database
- Maintain existing FastMCP patterns and async/await operations

**Database Integration**:
- No schema changes required - feature uses existing message storage
- UTC timestamp coordination maintained for message synchronization
- Existing aiosqlite patterns preserved

**WebSocket Connection Management**:
- Leverage existing websocket_manager from server.py
- Use established connection pooling and session isolation
- Maintain existing WebSocket authentication and session management

### API Requirements

**New HTTP Endpoint**:
```python
POST /broadcast/{session_id}
Content-Type: application/json

{
  "type": "new_message",
  "data": {
    "id": int,
    "sender": str,
    "sender_type": str,
    "content": str,
    "visibility": str,
    "timestamp": str,
    "metadata": dict
  }
}
```

**Response Format**:
```python
{"success": true, "session_id": "session-uuid"}
# OR
{"success": false, "error": "error description"}
```

**MCP Tool Integration**:
- Existing add_message tool enhanced with HTTP bridge notification
- No new MCP tools required - leverages existing session and message tools
- Maintains existing agent authentication and authorization patterns

## Quality Requirements

### Testing Strategy

**FastMCP TestClient Behavioral Testing**:
```python
# tests/behavioral/test_websocket_bridge.py
@pytest.mark.asyncio
async def test_websocket_bridge_end_to_end():
    """Behavioral test: MCP message triggers WebSocket broadcast."""
    client = TestClient(websocket_app)
    with client.websocket_connect("/ws/test-session") as websocket:
        await add_message("test-session", "test-agent", "test-message")
        data = websocket.receive_json()
        assert data["type"] == "new_message"
        assert data["data"]["content"] == "test-message"
```

**Multi-Agent Testing Coverage**:
- Test concurrent message addition from multiple agents
- Verify session isolation in WebSocket broadcasts
- Test graceful degradation when WebSocket server unavailable
- Integration tests using existing FastMCP TestClient patterns

### Documentation Needs

**MCP Server API Documentation**:
- FastAPI automatic documentation updates for new HTTP endpoint
- No new MCP tool documentation required - existing tools enhanced
- WebSocket integration examples for multi-agent coordination

### Performance Considerations

**Concurrent Agent Access**:
- HTTP bridge calls complete in <100ms target
- Non-blocking async operations maintain FastMCP performance
- Existing database connection pooling handles concurrent access
- 2-second timeout prevents hanging operations

**Resource Management**:
- httpx.AsyncClient context management for connection cleanup
- WebSocket connection pooling maintained by existing websocket_manager
- Minimal memory overhead - single HTTP POST per message

## Coordination Strategy

### Recommended Approach

**Direct Agent Assignment** - Low complexity feature suitable for developer agent:
- **File Count**: Only 2 files require modification (server.py, websocket_server.py)
- **Integration Complexity**: Simple HTTP bridge pattern using existing dependencies
- **Risk Level**: LOW - proven FastAPI patterns with graceful error handling
- **No Task Coordination Required**: Straightforward implementation with clear specifications

### Implementation Phases

**Phase 1: HTTP Endpoint Addition** (30 minutes):
- Add broadcast endpoint to websocket_server.py
- Test endpoint independently using FastAPI TestClient

**Phase 2: MCP Server Integration** (30 minutes):
- Add HTTP client call to server.py add_message function
- Implement graceful error handling for WebSocket server availability

**Phase 3: Integration Testing** (30 minutes):
- Create behavioral tests for end-to-end message broadcasting
- Test graceful degradation scenarios

### Risk Mitigation

**Multi-Agent Coordination Risks**:
- **Minimal Risk**: Feature is additive and doesn't modify existing MCP tool signatures
- **Backward Compatibility**: System works without WebSocket server running
- **Error Isolation**: HTTP bridge failures don't affect MCP server operations
- **Testing Coverage**: Behavioral tests ensure multi-agent functionality

### Dependencies

**Prerequisites**:
- Existing httpx>=0.25.0 dependency (already available)
- FastAPI and mcpsock packages (already configured)
- Existing websocket_manager implementation (already working)

**Integration Requirements**:
- No database schema changes required
- No new MCP tools or resources needed
- Compatible with existing authentication and session management

## Success Criteria

### Functional Success

**MCP Operations**:
- Messages added via MCP API appear in real-time in browser WebSocket clients
- Existing add_message MCP tool functionality preserved exactly
- Multi-agent message addition triggers appropriate WebSocket broadcasts
- Session isolation maintained - messages broadcast only to correct session clients

### Integration Success

**Multi-Agent Coordination Verification**:
- Multiple agents can add messages concurrently with real-time updates
- WebSocket clients receive broadcasts with proper agent attribution
- System maintains performance under concurrent agent access
- Graceful degradation when WebSocket server unavailable

### Quality Gates

**FastMCP Testing Requirements**:
- All existing MCP tool tests continue to pass
- New behavioral tests verify WebSocket bridge functionality
- Integration tests confirm multi-agent real-time messaging
- Performance tests validate <100ms HTTP bridge latency

**Code Quality Standards**:
- `ruff check` and `mypy` pass for modified files
- Maximum 500 lines per file maintained (both files well under limit)
- UTC timestamp consistency maintained across servers
- FastMCP async/await patterns preserved

## Architecture Impact

**Before Implementation**:
```
MCP Server (23456) ❌ WebSocket Server (8081)
├── Messages stored     ├── WebSocket connections active
├── websocket_manager   ├── No real-time updates
└── Empty connections   └── Page refresh required
```

**After Implementation**:
```
MCP Server (23456) ➜ HTTP Bridge ➜ WebSocket Server (8081) ✅
├── Messages stored     ├── POST /broadcast/{id}     ├── Real-time updates
├── HTTP client call    ├── websocket_manager        ├── WebSocket broadcasts
└── add_message tool    └── Success/failure status   └── Multi-agent support
```

**Integration Benefits**:
- Maintains necessary dual-server architecture (FastMCP limitation)
- Enables real-time communication with minimal code complexity
- Preserves existing FastMCP patterns and MCP tool functionality
- Supports concurrent multi-agent message broadcasting

## Implementation Details

### Code Specifications

**WebSocket Server Enhancement** (`websocket_server.py`):
```python
@websocket_app.post("/broadcast/{session_id}")
async def trigger_broadcast(session_id: str, request: dict):
    """HTTP endpoint to trigger WebSocket broadcast from MCP server."""
    try:
        from .server import websocket_manager
        await websocket_manager.broadcast_to_session(session_id, request)
        return {"success": True, "session_id": session_id}
    except Exception as e:
        logger.warning(f"Failed to broadcast to session {session_id}: {e}")
        return {"success": False, "error": str(e)}
```

**MCP Server Integration** (`server.py`):
```python
import httpx

async def _notify_websocket_server(session_id: str, message_data: dict) -> None:
    """Notify WebSocket server of new message via HTTP bridge."""
    try:
        config = get_config()
        ws_host = config.mcp_server.websocket_host
        ws_port = config.mcp_server.websocket_port

        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.post(
                f"http://{ws_host}:{ws_port}/broadcast/{session_id}",
                json=message_data
            )
            response.raise_for_status()
            logger.debug(f"WebSocket broadcast triggered for session {session_id}")
    except Exception as e:
        logger.debug(f"WebSocket broadcast failed (non-critical): {e}")

# Integration point in add_message function (after line 1036):
await _notify_websocket_server(session_id, {
    "type": "new_message",
    "data": {
        "id": message_id,
        "sender": agent_id,
        "sender_type": agent_type,
        "content": content,
        "visibility": visibility,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    },
})
```

### YAGNI Implementation Notes

**What We're Building** (KISS Principles):
- ✅ Simple HTTP POST bridge between servers
- ✅ Graceful error handling with 2-second timeout
- ✅ Minimal behavioral testing using FastAPI TestClient
- ✅ Integration with existing websocket_manager

**What We're NOT Building** (YAGNI):
- ❌ Redis/message queue (unnecessary for single-process architecture)
- ❌ Complex retry logic (2-second timeout sufficient)
- ❌ WebSocket server clustering (not needed for MVP)
- ❌ Message persistence in WebSocket server (MCP server handles storage)
- ❌ Authentication for internal HTTP calls (localhost-only communication)
- ❌ Performance benchmarks (simple solution, no optimization needed)

---

**Research Sources**:
- [FastAPI WebSocket Broadcasting Discussion](https://github.com/fastapi/fastapi/discussions/8312) - Standard HTTP-to-WebSocket trigger pattern
- [FastAPI WebSocket Broadcasting Guide](https://www.codingeasypeasy.com/blog/fastapi-websocket-broadcasting-messages-to-all-connected-clients) - Proven implementation patterns
- Existing codebase analysis - Confirmed dual-server architecture and dependencies
- Expert validation from specialized agents - Technical approach and testing strategy approved

---

**Implementation Completed**: All success criteria achieved with excellent reliability and performance. See [PRPs/1-planning/1.0.2-dashboard/retrospective.md](../1-planning/1.0.2-dashboard/retrospective.md) for comprehensive implementation retrospective, E2E testing results, and security assessment.
