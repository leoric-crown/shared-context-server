# WebSocket Real-time Message Broadcasting Bridge

**COMPLETED**: Simple behavioral testing strategy defined following KISS/YAGNI principles - basic integration tests sufficient for MVP implementation.

**Status**: Ready for Implementation
**Priority**: High
**Complexity**: Low
**Estimated Effort**: 2-4 hours (implementation) + additional for comprehensive testing

## Problem Statement

Real-time WebSocket message broadcasting is not working in the dual-server architecture. When messages are added via the MCP API server (port 23456), they don't appear in real-time for WebSocket clients connected to the WebSocket server (port 8081) without page refresh.

**Root Cause**: The MCP HTTP server and WebSocket server run as separate processes with isolated memory. The MCP server's `websocket_manager.broadcast_to_session()` broadcasts to an empty connection manager while actual WebSocket connections exist on the separate server.

## Minimal Solution

Implement an **HTTP bridge** between the two servers using the proven FastAPI pattern from the community:

1. **WebSocket Server**: Add HTTP endpoint `POST /broadcast/{session_id}` to receive broadcast requests
2. **MCP Server**: Add HTTP client call to trigger broadcasts after message storage
3. **Error Handling**: Graceful fallback if WebSocket server is unavailable

## Existing Tools We Can Leverage

- ✅ `httpx>=0.25.0` already available as dependency
- ✅ WebSocket connection management already working in WebSocket server
- ✅ Message broadcast logic already working in MCP server
- ✅ Both servers run in same process (development script manages both)

## Quality Considerations

- **Security**: Internal HTTP call between localhost servers only
- **Performance**: Single HTTP POST per message (minimal overhead)
- **Reliability**: Graceful degradation if WebSocket server unavailable
- **Maintainability**: Follows established FastAPI async patterns
- **Testing**: Can be tested independently and with integration tests

## Implementation Steps

### Step 1: Add Broadcast HTTP Endpoint to WebSocket Server (30 min)

**File**: `src/shared_context_server/websocket_server.py`

```python
@websocket_app.post("/broadcast/{session_id}")
async def trigger_broadcast(session_id: str, request: dict):
    """HTTP endpoint to trigger WebSocket broadcast from MCP server."""
    try:
        # Use existing websocket_manager from server.py
        from .server import websocket_manager
        await websocket_manager.broadcast_to_session(session_id, request)
        return {"success": True, "session_id": session_id}
    except Exception as e:
        logger.warning(f"Failed to broadcast to session {session_id}: {e}")
        return {"success": False, "error": str(e)}
```

### Step 2: Add HTTP Client Call to MCP Server (30 min)

**File**: `src/shared_context_server/server.py`

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
        # Non-critical: WebSocket is optional feature
        logger.debug(f"WebSocket broadcast failed (non-critical): {e}")
```

Update `add_message` function (after line 1036):

```python
# Send real-time message update via WebSocket bridge
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

### Step 3: Simple Behavioral Testing (30 min)

**Basic Integration Tests** (following FastAPI TestClient pattern):
```python
# tests/behavioral/test_websocket_bridge.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_websocket_bridge_end_to_end():
    """Behavioral test: MCP message triggers WebSocket broadcast."""
    # 1. Start both servers (test fixtures)
    # 2. Connect WebSocket client via TestClient
    # 3. Add message via MCP API
    # 4. Assert WebSocket client receives broadcast

    client = TestClient(websocket_app)
    with client.websocket_connect("/ws/test-session") as websocket:
        # Trigger MCP message addition (mocked)
        await add_message("test-session", "test-agent", "test-message")

        # Assert WebSocket receives broadcast
        data = websocket.receive_json()
        assert data["type"] == "new_message"
        assert data["data"]["content"] == "test-message"

@pytest.mark.asyncio
async def test_graceful_degradation():
    """Test MCP operations continue when WebSocket server unavailable."""
    with patch('httpx.AsyncClient.post', side_effect=Exception("Connection refused")):
        # Should not raise exception
        result = await add_message("test-session", "test-agent", "test-message")
        assert result["success"] is True  # MCP operation succeeds
```

**Manual Verification**:
- Real-time updates visible in browser after implementation
- System continues working if WebSocket server down

## YAGNI Notes (What We're NOT Building)

- ❌ Redis/message queue (unnecessary for single-process architecture)
- ❌ Complex retry logic (2-second timeout sufficient)
- ❌ WebSocket server clustering (not needed for MVP)
- ❌ Message persistence in WebSocket server (MCP server handles storage)
- ❌ Authentication for internal HTTP calls (localhost-only communication)
- ❌ Performance benchmarks (simple solution, no optimization needed)
- ❌ Load testing (KISS - basic functionality first)
- ❌ Complex error scenarios (graceful degradation sufficient)

## Success Criteria

1. **Functional**: Messages added via MCP API appear in real-time in browser WebSocket clients
2. **Performance**: HTTP bridge call completes in <100ms
3. **Reliability**: System works gracefully when WebSocket server unavailable
4. **Quality**: All existing tests pass + new integration tests for real-time updates

## Architecture Impact

**Before**: MCP Server (23456) ❌ WebSocket Server (8081)
**After**: MCP Server (23456) ➜ HTTP Bridge ➜ WebSocket Server (8081) ✅

This maintains the necessary dual-server architecture (FastMCP limitation) while enabling real-time communication with minimal code and maximum simplicity.

## Next Steps

1. Implement HTTP endpoint in WebSocket server
2. Add HTTP client call in MCP server
3. Test real-time broadcasting functionality
4. Add integration tests for the bridge
5. Update documentation with real-time features

## Expert Validation Summary

**@agent-developer**: ✅ **HIGHLY RECOMMENDED** (9.5/10)
- Technical approach perfectly aligned with existing FastMCP architecture
- Implementation is straightforward using established patterns (httpx, FastAPI)
- All required dependencies already available
- Risk level: LOW - proven patterns with graceful error handling

**@agent-tester**: ✅ **APPROVED** (8/10)
- Technical approach is sound and testable
- Simple behavioral tests using FastAPI TestClient pattern are appropriate for MVP
- Testing strategy follows KISS/YAGNI principles - basic integration tests sufficient
- Quality gates can be added iteratively as needed

**Consensus**: Both agents agree the technical solution is excellent. Simple behavioral testing approach finalized following KISS/YAGNI principles - ready for implementation.

---

**Research Sources**:
- [FastAPI WebSocket Broadcasting Discussion](https://github.com/fastapi/fastapi/discussions/8312) - Standard HTTP-to-WebSocket trigger pattern
- [FastAPI WebSocket Broadcasting Guide](https://www.codingeasypeasy.com/blog/fastapi-websocket-broadcasting-messages-to-all-connected-clients) - Proven implementation patterns
- Existing codebase analysis - Confirmed dual-server architecture and dependencies
