# Real-Time WebSocket Implementation

## Overview

This document describes the comprehensive real-time WebSocket implementation for the Shared Context Server, which provides live updates for the Web UI without requiring page refreshes.

## Architecture

### Components

1. **Main FastMCP Server** (`server.py`) - Runs on port 45678
   - Handles MCP protocol and HTTP endpoints
   - Serves the Web UI static files and templates
   - Manages database operations

2. **WebSocket Server** (`websocket_server.py`) - Runs on port 8080
   - Dedicated WebSocket server using `mcpsock` package
   - Provides real-time updates for session messages
   - Integrates with main server's database

3. **Client-Side JavaScript** (`static/js/app.js`)
   - Automatic WebSocket connection for session pages
   - Real-time message updates with smooth animations
   - Connection status monitoring and automatic reconnection
   - Graceful degradation when WebSocket is unavailable

## Implementation Details

### WebSocket Server Features

- **mcpsock Integration**: Uses the specialized `mcpsock` package designed for FastMCP
- **Tool-Based API**: Exposes WebSocket functions as MCP tools:
  - `subscribe`: Subscribe to session updates
  - `get_messages`: Retrieve messages since a specific ID
  - `get_session_info`: Get session metadata
- **Health Monitoring**: Dedicated health endpoint for monitoring
- **Fallback Support**: Gracefully handles missing `mcpsock` dependency

### Client-Side Features

- **Automatic Connection**: WebSocket connects automatically on session pages
- **Smart Reconnection**: Exponential backoff reconnection with max attempts
- **Real-Time Updates**: Live message additions with fade-in animations
- **Connection Status**: Visual indicator of WebSocket connection state
- **Keep-Alive**: Periodic ping/pong to maintain connection

### Database Integration

- **Shared Database**: Both servers use the same SQLite database
- **Message Retrieval**: Efficient queries for new messages since last ID
- **Session Management**: Real-time session status and metadata updates

## Usage

### Starting Servers

#### Method 1: Separate Servers (Recommended for Development)
```bash
# Terminal 1: Main server
uv run python -m shared_context_server.scripts.dev

# Terminal 2: WebSocket server
uv run python -m shared_context_server.websocket_server
```

#### Method 2: Integrated Server (Experimental)
```bash
uv run python -m shared_context_server.scripts.dev_with_websocket
```

### Accessing the Web UI

1. Open http://localhost:45678/ui/ for the dashboard
2. Navigate to any session page
3. The WebSocket connection will establish automatically
4. Look for "Real-time updates active" status indicator

### Testing WebSocket Functionality

1. Open a session page in your browser
2. Use Claude Code to add messages to that session via MCP tools
3. Messages should appear instantly without page refresh
4. Connection status shows in the top-right corner

## Configuration

### Environment Variables

```bash
# Main server (default: 127.0.0.1:45678)
SHARED_CONTEXT_HOST=127.0.0.1
SHARED_CONTEXT_PORT=45678

# WebSocket server (hardcoded: 127.0.0.1:8080)
# Will be configurable in future versions
```

### Client Configuration

WebSocket connection details are auto-detected:
- Protocol: `ws://` for HTTP, `wss://` for HTTPS
- Host: Same as main server
- Port: 8080 (hardcoded)
- Path: `/ws/{session_id}`

## Error Handling

### Server-Side Errors
- Database connection failures: Logged and returned as error responses
- WebSocket connection drops: Handled by client reconnection logic
- mcpsock import failures: Graceful fallback to basic WebSocket

### Client-Side Errors
- Connection failures: Automatic reconnection with exponential backoff
- Message parsing errors: Logged to console, connection maintained
- Network timeouts: Status indicator shows connection issues

## Performance Considerations

### Database Queries
- Efficient queries with `LIMIT` clauses
- Row factory for dict conversion
- Indexed session_id and timestamp columns

### WebSocket Connections
- Keep-alive pings every 30 seconds
- Automatic cleanup on disconnect
- Connection pooling handled by FastAPI/Uvicorn

### Client-Side Optimization
- Event debouncing for performance
- DOM updates with requestAnimationFrame
- Smooth scroll and fade animations

## Security

### Authentication
- WebSocket server uses same database as main server
- Session-based access control (future enhancement)
- Message visibility filtering (public/private/agent_only)

### Input Sanitization
- HTML escaping for all user content
- JSON validation for WebSocket messages
- SQL parameterized queries to prevent injection

## Dependencies

### Required Packages
- `mcpsock>=0.1.5` - WebSocket support for FastMCP
- `fastapi>=0.100.0` - WebSocket server framework
- `uvicorn>=0.35.0` - ASGI server
- `websockets>=12.0` - WebSocket protocol implementation

### Optional Dependencies
- Falls back to basic WebSocket if mcpsock unavailable
- Graceful degradation if WebSocket connection fails

## Testing

### Automated Tests
```bash
# Test WebSocket server health
uv run pytest tests/test_webui_live.py::test_websocket_server_health -v

# Test all WebUI functionality
uv run pytest tests/test_webui_integration.py -v
```

### Manual Testing
1. Start both servers
2. Open session page in browser
3. Check developer console for WebSocket logs
4. Add messages via MCP tools
5. Verify real-time updates appear

## Troubleshooting

### Common Issues

#### "WebSocket server not running"
- Start the WebSocket server: `uv run python -m shared_context_server.websocket_server`
- Check port 8080 is available
- Verify mcpsock installation: `uv list | grep mcpsock`

#### "Connection failed" in browser
- Check browser developer console for errors
- Verify both servers are running
- Check firewall/network settings for port 8080

#### "Real-time updates unavailable"
- WebSocket connection failed but page still works
- Messages will update on page refresh
- Check server logs for connection errors

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
uv run python -m shared_context_server.websocket_server
```

## Future Enhancements

### Planned Features
1. **Authentication Integration**: JWT token validation for WebSocket connections
2. **Message Broadcasting**: Real-time updates across multiple browser tabs
3. **Typing Indicators**: Show when agents are composing messages
4. **Connection Pooling**: Optimize WebSocket connections for multiple sessions
5. **Server-Sent Events**: Alternative transport for one-way updates
6. **Mobile Support**: WebSocket optimization for mobile browsers

### Configuration Improvements
1. **Configurable Ports**: Environment variables for all server ports
2. **Load Balancing**: Multiple WebSocket server instances
3. **SSL/TLS Support**: HTTPS/WSS in production environments
4. **Docker Integration**: Container-based deployment

## API Reference

### WebSocket Tools

#### `subscribe`
Subscribe to real-time updates for a session.
```json
{
  "tool": "subscribe",
  "arguments": {
    "session_id": "session_abc123"
  }
}
```

#### `get_messages`
Retrieve messages since a specific message ID.
```json
{
  "tool": "get_messages",
  "arguments": {
    "session_id": "session_abc123",
    "since_id": 42
  }
}
```

#### `get_session_info`
Get session metadata and status.
```json
{
  "tool": "get_session_info",
  "arguments": {
    "session_id": "session_abc123"
  }
}
```

### WebSocket Events

#### Connection Events
- `connected`: Initial connection established
- `subscribed`: Successfully subscribed to session updates
- `disconnected`: Connection lost, attempting reconnection
- `error`/`failed`: Connection failed or max reconnection attempts reached

#### Message Events
- `new_message`: New message added to session
- `session_update`: Session metadata changed
- `ping`/`pong`: Keep-alive messages

This implementation provides a robust, scalable foundation for real-time updates in the Shared Context Server Web UI.
