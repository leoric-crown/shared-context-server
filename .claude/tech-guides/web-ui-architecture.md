# Web UI Architecture Guide

## Overview

This guide provides technical implementation details for the Shared Context Server web UI. The design follows a zero-impact, additive approach that extends existing functionality without disrupting the core MCP server architecture.

> **Architecture Reference**: See [Core Architecture Guide](core-architecture.md) for system foundation and [Framework Integration Guide](framework-integration.md) for MCP server patterns.

## Design Principles

### 1. Zero-Impact Additive Design
- **Non-disruptive**: Web UI adds functionality without modifying core server
- **Separate concerns**: Web authentication independent of MCP JWT system
- **Optional feature**: Server functions fully without web UI enabled
- **Resource efficient**: Minimal memory and CPU overhead when inactive

### 2. Minimal Dependencies
- **Vanilla HTML/CSS/JS**: Zero external frameworks or build processes
- **Standard libraries**: Uses only Python standard library and existing dependencies
- **No compilation**: Direct file serving without preprocessors
- **Browser compatibility**: Modern browsers with WebSocket support

### 3. Progressive Enhancement
- **Core functionality first**: Basic message viewing works without JavaScript
- **Real-time updates**: WebSocket integration for live message updates
- **Graceful degradation**: Fallback to manual refresh if WebSocket unavailable

## Technical Architecture

### System Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    Shared Context Server                   │
├─────────────────────────────────────────────────────────────┤
│         FastMCP Server (Existing)                          │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐│
│  │    MCP Tools Layer      │  │     Web UI Layer (New)     ││
│  │  - create_session       │  │  - GET /ui/                 ││
│  │  - add_message          │  │  - GET /ui/sessions/{id}    ││
│  │  - search_context       │  │  - POST /ui/auth            ││
│  │  - set_memory           │  │  - WebSocket /ui/ws/{id}    ││
│  └─────────────────────────┘  └─────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                 Business Logic Layer (Shared)              │
├─────────────────────────────────────────────────────────────┤
│          ResourceNotificationManager (Extended)            │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐│
│  │  MCP Resource Updates   │  │   WebSocket Notifications   ││
│  │  - session:// URIs      │  │   - Real-time message push  ││
│  │  - Subscription mgmt    │  │   - Connection management   ││
│  └─────────────────────────┘  └─────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                SQLite Database (Unchanged)                 │
└─────────────────────────────────────────────────────────────┘
```

### Web Routes Architecture

```python
# Five minimal web routes using /ui prefix
from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# 1. Static file serving
app.mount("/ui/static", StaticFiles(directory="static"), name="static")

# 2. Main dashboard
@app.get("/ui/")
async def dashboard(request: Request):
    """Session list and creation interface"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# 3. Session viewer
@app.get("/ui/sessions/{session_id}")
async def session_view(request: Request, session_id: str):
    """Individual session message history"""
    session = await get_session(session_id)
    return templates.TemplateResponse("session.html", {
        "request": request,
        "session": session,
        "session_id": session_id
    })

# 4. Authentication
@app.post("/ui/auth")
async def authenticate(credentials: WebAuthRequest):
    """Web-specific authentication (separate from MCP JWT)"""
    if validate_web_credentials(credentials):
        return {"token": create_web_session_token(credentials.user)}
    raise HTTPException(401, "Invalid credentials")

# 5. WebSocket connection
@app.websocket("/ui/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Real-time message updates for session"""
    await websocket.accept()
    await handle_websocket_session(websocket, session_id)
```

## WebSocket Integration Pattern

### Extending ResourceNotificationManager

```python
# Extend existing notification system for WebSocket support
class WebUINotificationManager(ResourceNotificationManager):
    def __init__(self):
        super().__init__()
        self.websocket_connections: Dict[str, Set[WebSocket]] = {}

    async def register_websocket(self, session_id: str, websocket: WebSocket):
        """Register WebSocket for session updates"""
        if session_id not in self.websocket_connections:
            self.websocket_connections[session_id] = set()
        self.websocket_connections[session_id].add(websocket)

    async def unregister_websocket(self, session_id: str, websocket: WebSocket):
        """Remove WebSocket connection"""
        if session_id in self.websocket_connections:
            self.websocket_connections[session_id].discard(websocket)
            if not self.websocket_connections[session_id]:
                del self.websocket_connections[session_id]

    async def notify_session_update(self, session_id: str, message: dict):
        """Send real-time updates to connected WebSockets"""
        # Standard MCP resource notification
        await super().notify_resource_update(f"session://{session_id}")

        # WebSocket notification for real-time UI
        if session_id in self.websocket_connections:
            disconnected = set()
            for websocket in self.websocket_connections[session_id]:
                try:
                    await websocket.send_json({
                        "type": "message_added",
                        "session_id": session_id,
                        "message": message
                    })
                except ConnectionClosedOK:
                    disconnected.add(websocket)

            # Clean up disconnected sockets
            for websocket in disconnected:
                await self.unregister_websocket(session_id, websocket)
```

### WebSocket Message Protocol

```javascript
// Client-side WebSocket handling
class SessionWebSocket {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.ws = new WebSocket(`ws://localhost:8000/ui/ws/${sessionId}`);
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            // Retry connection after delay
            setTimeout(() => this.reconnect(), 5000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showConnectionError();
        };
    }

    handleMessage(data) {
        switch(data.type) {
            case 'message_added':
                this.addMessageToUI(data.message);
                break;
            case 'session_updated':
                this.refreshSessionInfo(data.session);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    addMessageToUI(message) {
        const messageElement = this.createMessageElement(message);
        document.getElementById('messages').appendChild(messageElement);
        messageElement.scrollIntoView({ behavior: 'smooth' });
    }

    reconnect() {
        this.ws = new WebSocket(`ws://localhost:8000/ui/ws/${this.sessionId}`);
        this.setupEventHandlers();
    }
}
```

## Frontend Architecture

### HTML Structure

```html
<!-- dashboard.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shared Context Dashboard</title>
    <link rel="stylesheet" href="/ui/static/style.css">
</head>
<body>
    <header class="header">
        <h1>Shared Context Server</h1>
        <nav class="nav">
            <a href="/ui/">Dashboard</a>
            <a href="/ui/docs">API Docs</a>
        </nav>
    </header>

    <main class="main">
        <section class="session-list">
            <h2>Active Sessions</h2>
            <div id="sessions-container">
                <!-- Sessions loaded dynamically -->
            </div>
            <button id="create-session" class="btn-primary">Create New Session</button>
        </section>
    </main>

    <script src="/ui/static/dashboard.js"></script>
</body>
</html>
```

```html
<!-- session.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session {{ session_id }}</title>
    <link rel="stylesheet" href="/ui/static/style.css">
</head>
<body>
    <header class="header">
        <h1>Session: {{ session_id }}</h1>
        <nav class="nav">
            <a href="/ui/">← Dashboard</a>
            <div class="session-info">
                <span class="message-count">{{ session.message_count }} messages</span>
                <span class="status" id="connection-status">Connected</span>
            </div>
        </nav>
    </header>

    <main class="main">
        <div class="messages-container">
            <div id="messages" class="messages">
                {% for message in session.messages %}
                <div class="message" data-sender="{{ message.sender }}">
                    <div class="message-header">
                        <span class="sender">{{ message.sender }}</span>
                        <span class="timestamp">{{ message.timestamp }}</span>
                    </div>
                    <div class="message-content">{{ message.content }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
    </main>

    <script>
        const sessionId = "{{ session_id }}";
    </script>
    <script src="/ui/static/session.js"></script>
</body>
</html>
```

### CSS Styling

```css
/* static/style.css */
:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --success-color: #16a34a;
    --error-color: #dc2626;
    --warning-color: #d97706;
    --background-color: #f8fafc;
    --surface-color: #ffffff;
    --text-color: #1e293b;
    --border-color: #e2e8f0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: var(--background-color);
    color: var(--text-color);
    line-height: 1.6;
}

.header {
    background-color: var(--surface-color);
    border-bottom: 1px solid var(--border-color);
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.nav {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.nav a {
    color: var(--primary-color);
    text-decoration: none;
    font-weight: 500;
}

.messages-container {
    max-width: 800px;
    margin: 2rem auto;
    background-color: var(--surface-color);
    border-radius: 8px;
    border: 1px solid var(--border-color);
    height: calc(100vh - 120px);
    overflow-y: auto;
}

.message {
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
}

.message:last-child {
    border-bottom: none;
}

.message-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: var(--secondary-color);
}

.sender {
    font-weight: 600;
    color: var(--primary-color);
}

.message-content {
    white-space: pre-wrap;
    word-wrap: break-word;
}

.status {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.status.connected {
    background-color: var(--success-color);
    color: white;
}

.status.disconnected {
    background-color: var(--error-color);
    color: white;
}

.btn-primary {
    background-color: var(--primary-color);
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 6px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
}

.btn-primary:hover {
    background-color: #1d4ed8;
}
```

### JavaScript Functionality

```javascript
// static/dashboard.js
class Dashboard {
    constructor() {
        this.sessions = [];
        this.init();
    }

    async init() {
        await this.loadSessions();
        this.setupEventListeners();
        this.startPolling();
    }

    async loadSessions() {
        try {
            const response = await fetch('/mcp/sessions');
            this.sessions = await response.json();
            this.renderSessions();
        } catch (error) {
            console.error('Failed to load sessions:', error);
            this.showError('Failed to load sessions');
        }
    }

    renderSessions() {
        const container = document.getElementById('sessions-container');
        container.innerHTML = '';

        if (this.sessions.length === 0) {
            container.innerHTML = '<p class="no-sessions">No active sessions</p>';
            return;
        }

        this.sessions.forEach(session => {
            const sessionElement = this.createSessionElement(session);
            container.appendChild(sessionElement);
        });
    }

    createSessionElement(session) {
        const element = document.createElement('div');
        element.className = 'session-card';
        element.innerHTML = `
            <div class="session-header">
                <h3>${session.id}</h3>
                <span class="message-count">${session.message_count} messages</span>
            </div>
            <div class="session-meta">
                <span class="created">Created: ${new Date(session.created).toLocaleDateString()}</span>
                <span class="updated">Updated: ${new Date(session.updated).toLocaleDateString()}</span>
            </div>
            <div class="session-actions">
                <a href="/ui/sessions/${session.id}" class="btn-secondary">View</a>
            </div>
        `;
        return element;
    }

    setupEventListeners() {
        document.getElementById('create-session').addEventListener('click',
            () => this.createSession());
    }

    async createSession() {
        try {
            const response = await fetch('/mcp/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ purpose: 'Web UI Session' })
            });
            const newSession = await response.json();
            window.location.href = `/ui/sessions/${newSession.session_id}`;
        } catch (error) {
            console.error('Failed to create session:', error);
            this.showError('Failed to create session');
        }
    }

    startPolling() {
        // Refresh session list every 30 seconds
        setInterval(() => this.loadSessions(), 30000);
    }

    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
```

```javascript
// static/session.js
class SessionViewer {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.scrollToBottom();
    }

    connectWebSocket() {
        try {
            this.websocket = new WebSocket(`ws://localhost:8000/ui/ws/${this.sessionId}`);
            this.websocket.onopen = () => this.handleConnectionOpen();
            this.websocket.onmessage = (event) => this.handleMessage(event);
            this.websocket.onclose = () => this.handleConnectionClose();
            this.websocket.onerror = (error) => this.handleConnectionError(error);
        } catch (error) {
            console.error('WebSocket connection failed:', error);
            this.updateConnectionStatus('disconnected');
        }
    }

    handleConnectionOpen() {
        console.log('WebSocket connected');
        this.updateConnectionStatus('connected');
        this.reconnectAttempts = 0;
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.processMessage(data);
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    processMessage(data) {
        switch (data.type) {
            case 'message_added':
                this.addMessage(data.message);
                break;
            case 'session_updated':
                this.updateSessionInfo(data.session);
                break;
            case 'ping':
                this.websocket.send(JSON.stringify({ type: 'pong' }));
                break;
            default:
                console.warn('Unknown WebSocket message type:', data.type);
        }
    }

    addMessage(message) {
        const messagesContainer = document.getElementById('messages');
        const messageElement = this.createMessageElement(message);
        messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
        this.updateMessageCount();
    }

    createMessageElement(message) {
        const element = document.createElement('div');
        element.className = 'message';
        element.setAttribute('data-sender', message.sender);

        const timestamp = new Date(message.timestamp).toLocaleString();
        element.innerHTML = `
            <div class="message-header">
                <span class="sender">${this.escapeHtml(message.sender)}</span>
                <span class="timestamp">${timestamp}</span>
            </div>
            <div class="message-content">${this.escapeHtml(message.content)}</div>
        `;

        return element;
    }

    handleConnectionClose() {
        console.log('WebSocket connection closed');
        this.updateConnectionStatus('disconnected');
        this.attemptReconnect();
    }

    handleConnectionError(error) {
        console.error('WebSocket error:', error);
        this.updateConnectionStatus('error');
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

            console.log(`Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
            setTimeout(() => this.connectWebSocket(), delay);
        } else {
            console.error('Max reconnection attempts reached');
            this.updateConnectionStatus('failed');
        }
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        statusElement.className = `status ${status}`;
    }

    scrollToBottom() {
        const messagesContainer = document.querySelector('.messages-container');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    updateMessageCount() {
        const messages = document.querySelectorAll('.message');
        const countElement = document.querySelector('.message-count');
        if (countElement) {
            countElement.textContent = `${messages.length} messages`;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    setupEventListeners() {
        // Add any additional event listeners for UI interactions
        window.addEventListener('beforeunload', () => {
            if (this.websocket) {
                this.websocket.close();
            }
        });
    }
}

// Initialize session viewer when page loads
document.addEventListener('DOMContentLoaded', () => {
    new SessionViewer(sessionId);
});
```

## Security Considerations

### Web Authentication (Separate from MCP)

```python
# Web-specific authentication system
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

class WebAuthSystem:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.web_users = {}  # In production: use database

    def create_web_user(self, username: str, password: str):
        """Create web UI user (separate from MCP agent system)"""
        hashed_password = self.pwd_context.hash(password)
        self.web_users[username] = {
            "username": username,
            "hashed_password": hashed_password,
            "created": datetime.utcnow(),
            "permissions": ["read_sessions", "create_sessions"]
        }

    def authenticate_web_user(self, username: str, password: str) -> Optional[str]:
        """Authenticate web user and return session token"""
        user = self.web_users.get(username)
        if user and self.pwd_context.verify(password, user["hashed_password"]):
            # Create web session token (different from MCP JWT)
            payload = {
                "username": username,
                "permissions": user["permissions"],
                "exp": datetime.utcnow() + timedelta(hours=24),
                "iat": datetime.utcnow(),
                "type": "web_session"  # Distinguish from MCP tokens
            }
            return jwt.encode(payload, self.secret_key, algorithm="HS256")
        return None

    def validate_web_token(self, token: str) -> Optional[dict]:
        """Validate web session token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            if payload.get("type") != "web_session":
                return None
            return payload
        except jwt.InvalidTokenError:
            return None
```

### Input Sanitization

```python
import html
from urllib.parse import quote

def sanitize_session_id(session_id: str) -> str:
    """Sanitize session ID for safe URL usage"""
    if not session_id or not isinstance(session_id, str):
        raise ValueError("Invalid session ID")

    # Validate format (UUID-like)
    if not re.match(r'^[a-f0-9\-]{36}$', session_id):
        raise ValueError("Session ID must be valid UUID format")

    return session_id

def sanitize_message_content(content: str) -> str:
    """Sanitize message content for HTML display"""
    if not content:
        return ""

    # HTML escape to prevent XSS
    escaped = html.escape(content)

    # Limit length to prevent DoS
    if len(escaped) > 50000:
        escaped = escaped[:50000] + "... [content truncated]"

    return escaped
```

## Testing the Web UI

### Integration Tests

```python
# tests/test_web_ui.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

@pytest.fixture
def web_client(test_app):
    return TestClient(test_app)

async def test_dashboard_loads(web_client):
    """Test dashboard page loads correctly"""
    response = web_client.get("/ui/")
    assert response.status_code == 200
    assert "Shared Context Dashboard" in response.text

async def test_session_view_loads(web_client, sample_session):
    """Test session view page loads with messages"""
    session_id = sample_session["session_id"]
    response = web_client.get(f"/ui/sessions/{session_id}")
    assert response.status_code == 200
    assert session_id in response.text

async def test_websocket_connection(web_client, sample_session):
    """Test WebSocket connection and message delivery"""
    session_id = sample_session["session_id"]

    with web_client.websocket_connect(f"/ui/ws/{session_id}") as websocket:
        # Simulate message addition
        test_message = {
            "sender": "test_agent",
            "content": "Test WebSocket message",
            "timestamp": datetime.utcnow().isoformat()
        }

        # This would normally be triggered by MCP tool
        await notify_session_update(session_id, test_message)

        # Receive WebSocket notification
        data = websocket.receive_json()
        assert data["type"] == "message_added"
        assert data["message"]["content"] == "Test WebSocket message"

async def test_web_authentication(web_client):
    """Test web UI authentication system"""
    # Test login
    response = web_client.post("/ui/auth", json={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 200
    token = response.json()["token"]
    assert token

    # Test protected route access
    headers = {"Authorization": f"Bearer {token}"}
    response = web_client.get("/ui/sessions/protected", headers=headers)
    assert response.status_code == 200
```

### Frontend Testing

```javascript
// static/test/test_session.js (for browser testing)
describe('SessionViewer', () => {
    let sessionViewer;
    let mockWebSocket;

    beforeEach(() => {
        // Mock WebSocket
        mockWebSocket = {
            send: jest.fn(),
            close: jest.fn()
        };
        global.WebSocket = jest.fn(() => mockWebSocket);

        // Setup DOM
        document.body.innerHTML = `
            <div id="messages"></div>
            <span id="connection-status"></span>
            <span class="message-count"></span>
        `;

        sessionViewer = new SessionViewer('test-session-id');
    });

    test('adds message to UI', () => {
        const message = {
            sender: 'test_agent',
            content: 'Test message',
            timestamp: new Date().toISOString()
        };

        sessionViewer.addMessage(message);

        const messages = document.querySelectorAll('.message');
        expect(messages.length).toBe(1);
        expect(messages[0].textContent).toContain('Test message');
    });

    test('handles WebSocket reconnection', () => {
        sessionViewer.handleConnectionClose();

        expect(sessionViewer.reconnectAttempts).toBe(0);
        // Would trigger reconnection logic
    });

    test('sanitizes HTML in messages', () => {
        const maliciousMessage = {
            sender: '<script>alert("xss")</script>',
            content: '<script>alert("xss")</script>',
            timestamp: new Date().toISOString()
        };

        sessionViewer.addMessage(maliciousMessage);

        const messageElement = document.querySelector('.message');
        expect(messageElement.innerHTML).not.toContain('<script>');
        expect(messageElement.textContent).toContain('alert("xss")');
    });
});
```

## Deployment Considerations

### Production Configuration

```python
# Configuration for production deployment
WEB_UI_CONFIG = {
    "enabled": True,
    "static_files_path": "/opt/shared-context-server/static",
    "templates_path": "/opt/shared-context-server/templates",
    "websocket_heartbeat_interval": 30,
    "max_websocket_connections": 1000,
    "session_timeout": 3600,  # 1 hour
    "rate_limiting": {
        "requests_per_minute": 60,
        "websocket_connections_per_ip": 10
    }
}
```

### Performance Optimization

```python
# WebSocket connection pooling
class WebSocketConnectionPool:
    def __init__(self, max_connections=1000):
        self.connections = {}
        self.max_connections = max_connections

    async def add_connection(self, session_id: str, websocket: WebSocket):
        if len(self.connections) >= self.max_connections:
            # Remove oldest inactive connection
            await self.cleanup_inactive_connections()

        if session_id not in self.connections:
            self.connections[session_id] = set()
        self.connections[session_id].add(websocket)

    async def cleanup_inactive_connections(self):
        """Remove closed WebSocket connections"""
        for session_id in list(self.connections.keys()):
            active_connections = set()
            for ws in self.connections[session_id]:
                if ws.client_state == WebSocketState.CONNECTED:
                    active_connections.add(ws)
                else:
                    try:
                        await ws.close()
                    except:
                        pass

            if active_connections:
                self.connections[session_id] = active_connections
            else:
                del self.connections[session_id]
```

## Integration Points

### MCP Resource Integration
- **Session Resources**: `session://{id}` URIs accessible via web UI
- **Resource Notifications**: Real-time updates through existing notification system
- **Tool Integration**: Web UI displays results from MCP tool operations

### Database Integration
- **Read-Only Access**: Web UI primarily reads from existing database schema
- **No Schema Changes**: Uses existing `chat_history` table structure
- **Concurrent Access**: SQLite WAL mode supports concurrent web and MCP access

### Authentication Integration
- **Separate Systems**: Web auth independent of MCP JWT tokens
- **No Conflicts**: Web UI doesn't interfere with MCP agent authentication
- **Optional Security**: Web UI can run without authentication for trusted environments

This web UI architecture provides a practical, zero-impact interface for viewing and monitoring shared context sessions while maintaining the integrity and performance of the core MCP server system.
