# PRP-013: Simple Server.py Refactoring (Streamlined)

**Status**: Ready for Implementation
**Effort**: 2-3 hours
**Priority**: High - Code maintainability

## The Real Problem

- `server.py` is 2546 lines (5x over the 500-line limit)
- Hard to navigate and maintain
- Everything mixed together

## The Simple Solution: 6 Logical Files

### File Structure (Follow Existing Patterns)

```python
src/shared_context_server/
├── server.py           (~200 lines) # Core server + initialization
├── auth_tools.py       (~200 lines) # Authentication tools (already exists, just add tools)
├── session_tools.py    (~400 lines) # Session + message operations
├── search_tools.py     (~400 lines) # All search functionality
├── memory_tools.py     (~350 lines) # Memory management
├── web_routes.py       (~400 lines) # Web UI + WebSocket endpoints
└── utils/              (existing)   # Already organized properly
```

## Implementation Steps (2-3 hours)

### Step 1: Extract Search Tools (30 minutes)
Move lines 1166-1530 to `search_tools.py`:
- search_context (RapidFuzz)
- search_by_sender
- search_by_timerange

### Step 2: Extract Memory Tools (30 minutes)
Move lines 1538-1971 to `memory_tools.py`:
- set_memory
- get_memory
- list_memory

### Step 3: Extract Session Tools (45 minutes)
Move lines 753-1158 to `session_tools.py`:
- create_session
- get_session
- add_message
- get_messages

### Step 4: Extract Web Routes (30 minutes)
Move lines 222-425 + WebSocket code to `web_routes.py`:
- Dashboard endpoint
- Session view endpoint
- WebSocket endpoint
- WebSocketManager class

### Step 5: Move Auth Tools (15 minutes)
Move lines 468-745 to existing `auth_tools.py`:
- authenticate_agent
- refresh_token

### Step 6: Clean Up Server.py (30 minutes)
Keep only:
- FastMCP initialization
- Basic imports
- Tool registration (simple imports, no factory pattern)

```python
# server.py becomes simple:
from .auth_tools import authenticate_agent, refresh_token
from .session_tools import create_session, get_session, add_message, get_messages
from .search_tools import search_context, search_by_sender, search_by_timerange
from .memory_tools import set_memory, get_memory, list_memory
from .web_routes import setup_web_routes

mcp = FastMCP("shared-context-server")

# Register tools (they're already decorated with @mcp.tool())
# Just importing them registers them

# Setup web routes
setup_web_routes(mcp.app)
```

## What We're NOT Doing (YAGNI)

- ❌ Factory patterns
- ❌ Registration functions
- ❌ Dependency injection
- ❌ 14 micro-modules
- ❌ Complex import management

## Testing Strategy

After each file extraction:
```bash
# Quick validation
uv run pytest tests/ -x  # Stop on first failure

# Verify MCP tools still work
claude mcp list
```

## Success Criteria

- [x] All files under 500 lines
- [x] All tests pass unchanged
- [x] All MCP tools work
- [x] Web UI works
- [x] No new abstractions added

## Why This Works

- **Simple Imports**: Python's import system handles registration
- **Existing Patterns**: Follow what auth.py already does
- **Clear Boundaries**: Each file has obvious responsibility
- **Easy Navigation**: Find code by function, not by hunting through 2500 lines

Total changes: File moves + imports
Total new code: ~10 lines (imports)
Complexity added: Zero
