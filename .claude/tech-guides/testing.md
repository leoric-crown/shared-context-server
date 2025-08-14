# Testing Guide

## Overview

This guide implements comprehensive testing patterns for the Shared Context MCP Server - a collaborative agent workspace. Focus on behavioral testing, agent handoff scenarios, and session-based collaboration workflows. The approach emphasizes testing collaborative agent behaviors rather than internal implementation.

## Core Testing Philosophy

### Behavioral Testing Focus
- **Test what, not how**: Focus on observable behaviors and outcomes
- **User-centric scenarios**: Test from the agent's perspective
- **Implementation agnostic**: Tests should survive refactoring
- **Complete workflows**: Test end-to-end user journeys
- **Real-world scenarios**: Multi-agent collaboration patterns

### Test Pyramid Strategy
```
         /\
        /  \  E2E Tests (Few)
       /    \  - Critical user journeys
      /      \  - Multi-agent scenarios
     /--------\
    /          \  Integration Tests (Some)
   /            \  - MCP tool interactions
  /              \  - Database operations
 /                \  - API endpoints
/------------------\
                     Unit Tests (Many)
                     - Business logic
                     - Validation rules
                     - Utility functions
```

## Modern Database Testing Infrastructure

### Overview: Real Database Testing

**🎯 Migration Complete**: We've migrated from fragile hardcoded mock databases to modern real database testing infrastructure. This approach provides better test fidelity, handles schema evolution gracefully, and tests actual database constraints and behaviors.

### Key Benefits
- **Schema Evolution Support**: Tests remain valid when database schemas change
- **Real Database Behavior**: Tests actual database constraints, triggers, and SQLite-specific behavior
- **Better Test Fidelity**: No more gaps between mock behavior and real database behavior
- **Easier Maintenance**: No need to update multiple hardcoded mocks when schemas change
- **Isolation**: Each test gets a clean database state with proper test data seeding

### Test Configuration

```python
# conftest.py - Simplified memory-based database testing fixtures
import inspect
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import pytest
from pydantic.fields import FieldInfo

from shared_context_server.database_testing import TestDatabaseManager, get_test_db_connection

@pytest.fixture(scope="function")
async def test_db_manager():
    """
    Create an isolated in-memory SQLite database manager for each test.

    This fixture provides a real database with the complete schema applied,
    ensuring tests work with actual database constraints and behaviors.
    Each test gets a clean database state with no file I/O complexity.

    Yields:
        TestDatabaseManager: Initialized database manager with applied schema
    """
    # Create in-memory database manager (no files, no cleanup needed)
    db_manager = TestDatabaseManager("sqlite:///:memory:")

    # Initialize database with schema
    await db_manager.initialize()

    # Verify schema is correctly applied
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        version = await cursor.fetchone()
        assert version and version[0] == 3, f"Expected schema version 3, got {version[0] if version else None}"

    yield db_manager
    # No cleanup needed - memory database automatically cleaned up

@pytest.fixture(scope="function")
async def test_db_connection(test_db_manager):
    """
    Provide a database connection for tests that need direct database access.

    Args:
        test_db_manager: The test database manager fixture

    Yields:
        aiosqlite.Connection: Database connection with optimized settings
    """
    async with test_db_manager.get_connection() as conn:
        yield conn
```

### FastMCP Integration with Real Database Testing

```python
# Testing-specific patterns for FastMCP tools (see Framework Integration Guide for implementation details)
async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """
    Call a FastMCP tool function with proper default handling.

    This helper automatically extracts Field defaults and merges them
    with provided kwargs to avoid FieldInfo object issues.
    """
    # Get the actual defaults
    defaults = extract_field_defaults(fastmcp_tool)

    # Merge defaults with provided kwargs (kwargs override defaults)
    call_args = {**defaults, **kwargs}

    # Call the function with context as first parameter
    return await fastmcp_tool.fn(ctx, **call_args)

def patch_database_connection(test_db_manager):
    """
    Create a patcher for the global get_db_connection function for testing.

    Note: See Framework Integration Guide for production database patterns.
    """
    from unittest.mock import patch

    @asynccontextmanager
    async def mock_get_db_connection():
        async with test_db_manager.get_connection() as conn:
            yield conn

    return patch("shared_context_server.server.get_db_connection", mock_get_db_connection)
```

## Testing Patterns

### 1. Modern FastMCP Tool Testing

**✅ Recommended Approach:**

```python
@pytest.mark.asyncio
async def test_message_creation_workflow(test_db_manager):
    """Test message creation using real database."""

    with patch("shared_context_server.server.get_db_connection") as mock_db_conn:
        # Use the real test database instead of hardcoded mocks
        @asynccontextmanager
        async def mock_get_db_connection():
            async with test_db_manager.get_connection() as conn:
                yield conn

        mock_db_conn.side_effect = mock_get_db_connection

        # Create test context
        ctx = MockContext("test_session", "test_agent")

        # Test session creation
        session_result = await call_fastmcp_tool(
            create_session,
            ctx,
            purpose="Test session",
            metadata={"test": True}
        )

        assert session_result["success"] is True
        session_id = session_result["session_id"]

        # Test message creation with proper schema support
        message_result = await call_fastmcp_tool(
            add_message,
            ctx,
            session_id=session_id,
            content="Test message",
            visibility="public",
            metadata={"agent": "test"}
        )

        assert message_result["success"] is True
```

**❌ Old Approach (Don't Use):**

```python
# DEPRECATED: Hardcoded mock database (fragile and unmaintainable)
@pytest.fixture
def mock_database():
    """DEPRECATED: Don't use hardcoded mocks."""
    messages = {}

    async def mock_execute(query, params=()):
        if "INSERT INTO messages" in query:
            # ❌ This breaks when schema changes!
            session_id, sender, content, visibility, metadata, parent_id = params  # Only 6 params!
            # Real schema now has 7 parameters including sender_type
            # This causes "Error binding parameter 7: type 'FieldInfo' is not supported"

    # ... hardcoded mock implementation
```

### 2. Migration Guide

If you encounter failing tests with messages like:
- `"Error binding parameter 7: type 'FieldInfo' is not supported"`
- Parameter count mismatches in mock databases

**Follow these steps:**

1. **Replace hardcoded mock fixtures** with `test_db_manager`
2. **Use `call_fastmcp_tool()` instead of `.fn()`** to handle FieldInfo defaults
3. **Patch database connections** properly using the new pattern
4. **Remove hardcoded parameter parsing** that expects specific counts

**Example Migration:**

```python
# Before (broken with schema changes)
@pytest.mark.asyncio
async def test_example(mock_database):
    with patch("server.get_db_connection") as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_database
        result = await add_message.fn(ctx, session_id, content, visibility)  # ❌ FieldInfo error

# After (schema evolution safe)
@pytest.mark.asyncio
async def test_example(test_db_manager):
    with patch("server.get_db_connection") as mock_db:
        @asynccontextmanager
        async def mock_get_db_connection():
            async with test_db_manager.get_connection() as conn:
                yield conn
        mock_db.side_effect = mock_get_db_connection

        result = await call_fastmcp_tool(add_message, ctx, session_id=session_id, content=content)  # ✅ Works
```

@pytest.fixture
async def test_database():
    """Create temporary test database with schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    # Initialize schema (see Core Architecture Guide for complete schema)
    async with aiosqlite.connect(db_path) as conn:
        from shared_context_server.database import DatabaseManager

        # Use DatabaseManager to apply schema
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        await db_manager.initialize()

        await conn.commit()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)

@pytest.fixture
async def mcp_server(test_database):
    """Create MCP server with test database."""
    from shared_context_server.server import mcp  # Use actual FastMCP server instance

    # Use the actual FastMCP server instance from server.py
    # Database is handled through the global DatabaseManager

    yield mcp

    # Cleanup handled by test fixtures

@pytest.fixture
async def mcp_client(mcp_server):
    """Create FastMCP test client for in-memory testing."""
    async with TestClient(mcp_server) as client:
        yield client

@pytest.fixture
def agent_identities():
    """Test agent identities for multi-agent testing."""
    return {
        "claude_main": {
            "agent_id": "claude-main",
            "agent_type": "orchestrator",
            "permissions": ["create", "read", "write", "delete"]
        },
        "developer": {
            "agent_id": "developer-agent",
            "agent_type": "developer",
            "permissions": ["read", "write"]
        },
        "tester": {
            "agent_id": "tester-agent",
            "agent_type": "tester",
            "permissions": ["read", "write"]
        },
        "docs": {
            "agent_id": "docs-agent",
            "agent_type": "docs",
            "permissions": ["read"]
        }
    }
```

## Unit Testing Patterns

### Pure Function Testing
```python
def test_session_id_generation():
    """Test session ID generation behavior."""
    from shared_context_server.utils import generate_session_id

    # Test format
    session_id = generate_session_id()
    assert session_id.startswith("session_")
    assert len(session_id) == 24  # session_ + 16 hex chars

    # Test uniqueness
    ids = set(generate_session_id() for _ in range(100))
    assert len(ids) == 100  # All unique

def test_message_sanitization():
    """Test input sanitization behavior."""
    from shared_context_server.utils import sanitize_message_content

    # Test HTML escaping
    dirty_input = '<script>alert("xss")</script>Hello'
    clean_output = sanitize_message_content(dirty_input)
    assert '<script>' not in clean_output
    assert 'Hello' in clean_output

    # Test whitespace normalization
    messy_input = '  Multiple   spaces\n\nand\tlines  '
    clean_output = sanitize_message_content(messy_input)
    assert clean_output == 'Multiple spaces and lines'

def test_fuzzy_search_scoring():
    """Test fuzzy search scoring behavior."""
    from shared_context_server.search import calculate_fuzzy_score

    # Perfect match
    assert calculate_fuzzy_score("hello", "hello") == 100.0

    # No match
    assert calculate_fuzzy_score("hello", "xyz") == 0.0

    # Partial match
    score = calculate_fuzzy_score("hello world", "hello")
    assert 50.0 < score < 100.0
```

### Data Validation Testing
```python
@pytest.mark.asyncio
async def test_message_model_validation():
    """Test Pydantic message model validation."""
    from shared_context_server.models import MessageModel

    # Valid data should pass
    valid_data = {
        "session_id": "session_abc123",
        "sender": "test-agent",
        "content": "Test message",
        "visibility": "public"
    }
    model = MessageModel(**valid_data)
    assert model.session_id == "session_abc123"
    assert model.visibility == "public"

@pytest.mark.asyncio
async def test_message_model_validation_errors():
    """Test validation error behavior."""
    from shared_context_server.models import MessageModel
    from pydantic import ValidationError

    # Missing required field
    with pytest.raises(ValidationError, match="session_id.*required"):
        MessageModel(sender="test", content="hello")

    # Invalid visibility
    with pytest.raises(ValidationError, match="visibility.*invalid"):
        MessageModel(
            session_id="session_123",
            sender="test",
            content="hello",
            visibility="invalid"
        )
```

## FastMCP Integration Testing

⚠️ **CRITICAL: FastMCP Field Default Issue**

FastMCP tools decorated with `@mcp.tool()` have a critical issue when accessed via `.fn` attribute for testing. The Field default values become `FieldInfo` objects instead of actual default values, causing arithmetic and comparison errors.

### **✅ WORKING SOLUTION: Inline Helper Functions**

The cleanest approach is to inline the helper functions directly in test files to avoid import complexity:

```python
# FastMCP testing helpers (inlined for simplicity)
import inspect
from pydantic.fields import FieldInfo

def extract_field_defaults(fastmcp_tool):
    """Extract actual default values from FastMCP tool function."""
    defaults = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for param_name, param in sig.parameters.items():
        if param_name == 'ctx':  # Skip context parameter
            continue
        if isinstance(param.default, FieldInfo):
            defaults[param_name] = param.default.default
        elif param.default != inspect.Parameter.empty:
            defaults[param_name] = param.default
    return defaults

async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """Call FastMCP tool with proper default handling."""
    defaults = extract_field_defaults(fastmcp_tool)
    call_args = {**defaults, **kwargs}
    return await fastmcp_tool.fn(ctx, **call_args)

class MockContext:
    """Mock context for FastMCP testing."""
    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        self.agent_id = agent_id
```

### **🎯 Key Testing Patterns Discovered**

1. **Agent ID Generation**: System uses consistent `getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")` pattern
   - MockContext("alice_session", "test_agent") → sender becomes "test_agent" (uses explicit agent_id)
   - MockContext("alice_session") → sender becomes "agent_alice_se" (fallback pattern)
   - Tests must use MockContext with explicit agent_id for predictable behavior

2. **Agent Memory Isolation Fix** ⚠️ **CRITICAL FIX APPLIED**
   - **Previous bug**: Memory system used session-based agent ID preventing isolation in shared sessions
   - **Root cause**: `agent_id = f"agent_{ctx.session_id[:8]}"` made agents in same session share memory
   - **Fix applied**: ALL server functions now use `getattr(ctx, 'agent_id', f"agent_{ctx.session_id[:8]}")`
   - **Functions updated**: `create_session`, `add_message`, `get_messages`, `get_session`, `search_context`
   - **Result**: Agents can share sessions while maintaining isolated memory
   - **Testing pattern**: Use same session_id but different agent_id values for isolation tests
   ```python
   # Correct pattern for testing agent isolation
   agent1_ctx = MockContext("shared_session", "agent_1")
   agent2_ctx = MockContext("shared_session", "agent_2")
   ```

3. **Database Row Factory Fix** ⚠️ **CRITICAL FIX APPLIED**
   - **Previous bug**: Database queries failed with "dictionary update sequence element #0 has length 24; 2 is required"
   - **Root cause**: Missing `conn.row_factory = aiosqlite.Row` in server functions
   - **Fix applied**: All server functions now set row factory for proper dict conversion
   - **Functions updated**: `get_session`, `get_messages`, `search_context`
   ```python
   async with get_db_connection() as conn:
       # Set row factory for dict-like access
       conn.row_factory = aiosqlite.Row
       # ... rest of database operations
   ```

4. **Visibility Filtering Logic** ⚠️ **MAJOR LOGIC OVERHAUL**
   - **Previous bug**: Visibility filters were additive instead of restrictive
   - **Root cause**: Adding visibility_filter as OR condition instead of replacing base rules
   - **Fix applied**: Complete rewrite of visibility filtering in `get_messages`
   - **New logic**:
     - With filter: Apply specific filter (`public`, `private`, `agent_only`) with agent access rules
     - Without filter: Default rules (public + own private/agent_only)
   ```python
   # New visibility filtering logic
   if visibility_filter:
       if visibility_filter == "public":
           where_conditions.append("visibility = 'public'")
       elif visibility_filter == "private":
           where_conditions.append("visibility = 'private' AND sender = ?")
           params.append(agent_id)
   else:
       # Default: public + own private/agent_only
       visibility_conditions = [
           "visibility = 'public'",
           "(visibility = 'private' AND sender = ?)",
           "(visibility = 'agent_only' AND sender = ?)",
       ]
       params.extend([agent_id, agent_id])
   ```

5. **Mock Database Parameter Updates** ⚠️ **PARAMETER FORMAT CHANGES**
   - **Issue**: Mock databases in behavioral tests expected old parameter formats
   - **Root cause**: Visibility filtering changes altered parameter structures
   - **Fix applied**: Updated mock database parameter parsing logic
   - **New parameter formats**:
     - Public filter: `(session_id, limit, offset)`
     - Private/agent_only: `(session_id, agent_id, limit, offset)`
     - No filter: `(session_id, agent_id, agent_id, limit, offset)`

6. **Database Mocking**: Use AsyncMock with proper return structure
   ```python
   mock_conn = AsyncMock()
   mock_conn.execute = AsyncMock(return_value=AsyncMock(lastrowid=None))
   mock_conn.commit = AsyncMock()
   ```

7. **Context Objects**: Must be objects with attributes, not dictionaries
   ```python
   # ✅ Correct - object with attributes
   ctx = MockContext("session_123", "agent_456")

   # ❌ Wrong - dictionary
   ctx = {"session_id": "session_123", "agent_id": "agent_456"}
   ```

### Working FastMCP Testing Patterns

#### Method 1: Manual Parameter Passing (Explicit Approach)

```python
from tests.test_utils import MockContext

@pytest.mark.asyncio
async def test_create_session_tool_manual():
    """Test session creation using manual parameter passing."""
    from shared_context_server.server import create_session
    from unittest.mock import AsyncMock, patch

    # Create mock context (NOT a dict, but an object with attributes)
    ctx = MockContext("test_session_123", "test_agent")

    # Mock database operations
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=AsyncMock(lastrowid=None))
    mock_conn.commit = AsyncMock()

    with patch("shared_context_server.server.get_db_connection") as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        # CRITICAL: Call .fn with context as first parameter
        # and explicit defaults to avoid FieldInfo objects
        result = await create_session.fn(
            ctx,  # Context as first parameter
            purpose="test session creation",
            metadata=None,  # Explicit default to avoid FieldInfo
        )

        # Verify response
        assert result["success"] is True
        assert "session_id" in result
        assert result["session_id"].startswith("session_")
        assert result["created_by"] == "agent_test_ses"  # Based on context.session_id

@pytest.mark.asyncio
async def test_set_memory_with_explicit_defaults():
    """Test memory setting with all explicit defaults."""
    from shared_context_server.server import set_memory
    from unittest.mock import AsyncMock, patch

    ctx = MockContext("test_session", "test_agent")

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=AsyncMock())
    mock_conn.commit = AsyncMock()

    with patch("shared_context_server.server.get_db_connection") as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        # CRITICAL: Pass ALL parameters to avoid FieldInfo defaults
        result = await set_memory.fn(
            ctx,  # Context first
            key="test_key",
            value={"test": "data"},
            session_id="session_123",
            expires_in=None,      # Explicit default
            metadata=None,        # Explicit default
            overwrite=True,       # Explicit default
        )

        assert result["success"] is True
```

#### Method 2: Helper Function (Recommended Approach)

Create `tests/test_utils.py` with helper functions:

```python
"""Testing utilities for FastMCP-based shared context server."""

import inspect
from typing import Any, Dict
from pydantic.fields import FieldInfo

def extract_field_defaults(fastmcp_tool) -> Dict[str, Any]:
    """Extract actual default values from a FastMCP tool function."""
    defaults = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for name, param in sig.parameters.items():
        if name == 'ctx':  # Skip context parameter
            continue

        if isinstance(param.default, FieldInfo):
            # Extract the actual default from FieldInfo
            defaults[name] = param.default.default
        elif param.default is not inspect.Parameter.empty:
            defaults[name] = param.default

    return defaults

async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """Call a FastMCP tool function with proper default handling."""
    # Get the actual defaults
    defaults = extract_field_defaults(fastmcp_tool)

    # Merge defaults with provided kwargs (kwargs override defaults)
    call_args = {**defaults, **kwargs}

    # Call the function with context as first parameter
    return await fastmcp_tool.fn(ctx, **call_args)

class MockContext:
    """Standard mock context for FastMCP testing."""

    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        self.agent_id = agent_id
```

Using the helper function:

```python
@pytest.mark.asyncio
async def test_create_session_with_helper():
    """Test session creation using helper function."""
    from shared_context_server.server import create_session
    from tests.test_utils import call_fastmcp_tool, MockContext
    from unittest.mock import AsyncMock, patch

    ctx = MockContext("helper_session", "helper_agent")

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=AsyncMock(lastrowid=None))
    mock_conn.commit = AsyncMock()

    with patch("shared_context_server.server.get_db_connection") as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        # Use helper - automatically handles defaults
        result = await call_fastmcp_tool(
            create_session,
            ctx,
            purpose="test session with helper"
            # metadata will use default (None) automatically
        )

        assert result["success"] is True
        assert result["session_id"].startswith("session_")

@pytest.mark.asyncio
async def test_search_context_with_helper():
    """Test context search using helper function."""
    from shared_context_server.server import search_context
    from tests.test_utils import call_fastmcp_tool, MockContext
    from unittest.mock import AsyncMock, patch

    ctx = MockContext("search_session", "search_agent")

    # Mock empty database
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=AsyncMock(fetchall=AsyncMock(return_value=[])))

    with patch("shared_context_server.server.get_db_connection") as mock_db:
        mock_db.return_value.__aenter__.return_value = mock_conn

        # Helper automatically applies defaults: fuzzy_threshold=60.0, limit=10, etc.
        result = await call_fastmcp_tool(
            search_context,
            ctx,
            session_id="session_123",
            query="test search query"
        )

        assert result["success"] is True
        assert "results" in result
        assert "search_time_ms" in result
```

#### Method 3: Debugging Field Defaults

To understand what defaults a FastMCP tool needs:

```python
from tests.test_utils import extract_field_defaults
from shared_context_server.server import set_memory, search_context

# See what defaults are needed
print("set_memory defaults:", extract_field_defaults(set_memory))
print("search_context defaults:", extract_field_defaults(search_context))

# Output shows:
# set_memory defaults: {'expires_in': None, 'metadata': None, 'overwrite': True, ...}
# search_context defaults: {'fuzzy_threshold': 60.0, 'limit': 10, 'search_metadata': True, ...}
```

### Real FastMCP Test Example

```python
@pytest.mark.asyncio
async def test_add_message_tool(ctx, mock_database):
    """Test message addition through MCP tool."""
    mcp_client.set_context(agent_identities["developer"])

    # Create session first
    session_result = await mcp_client.call_tool(
        "create_session",
        {"purpose": "message testing"}
    )
    session_id = session_result["session_id"]

    # Add message
    message_result = await mcp_client.call_tool(
        "add_message",
        {
            "session_id": session_id,
            "content": "Hello from developer agent",
            "visibility": "public",
            "metadata": {"type": "greeting"}
        }
    )

    # Verify message creation
    assert message_result["success"] is True
    assert "message_id" in message_result
    assert "timestamp" in message_result

@pytest.mark.asyncio
async def test_search_context_tool(mcp_client, agent_identities):
    """Test context search through MCP tool."""
    mcp_client.set_context(agent_identities["tester"])

    # Setup: Create session and add messages
    session_result = await mcp_client.call_tool("create_session", {"purpose": "search testing"})
    session_id = session_result["session_id"]

    messages = [
        "Implementing authentication middleware",
        "Writing unit tests for auth",
        "Documenting API endpoints",
        "Refactoring database queries"
    ]

    for msg in messages:
        await mcp_client.call_tool("add_message", {
            "session_id": session_id,
            "content": msg,
            "visibility": "public"
        })

    # Test fuzzy search
    search_result = await mcp_client.call_tool("search_context", {
        "session_id": session_id,
        "query": "authentication",
        "fuzzy_threshold": 60.0,
        "limit": 5
    })

    # Verify search results
    assert search_result["success"] is True
    assert len(search_result["results"]) > 0

    # Check that authentication-related message ranks highest
    top_result = search_result["results"][0]
    assert "authentication" in top_result["message"]["content"].lower()
    assert top_result["score"] > 60.0
```

### Resource Testing
```python
@pytest.mark.asyncio
async def test_session_resource_access(mcp_client, agent_identities):
    """Test session resource access."""
    mcp_client.set_context(agent_identities["claude_main"])

    # Create session with messages
    session_result = await mcp_client.call_tool("create_session", {"purpose": "resource test"})
    session_id = session_result["session_id"]

    await mcp_client.call_tool("add_message", {
        "session_id": session_id,
        "content": "First message",
        "visibility": "public"
    })

    # Read session resource
    resource = await mcp_client.read_resource(f"session://{session_id}")

    # Verify resource content
    assert resource.uri == f"session://{session_id}"
    assert resource.mimeType == "application/json"

    content = json.loads(resource.text)
    assert "session" in content
    assert "messages" in content
    assert len(content["messages"]) == 1
    assert content["messages"][0]["content"] == "First message"

@pytest.mark.asyncio
async def test_resource_subscription(mcp_client, agent_identities):
    """Test resource subscription for real-time updates."""
    mcp_client.set_context(agent_identities["developer"])

    # Create session
    session_result = await mcp_client.call_tool("create_session", {"purpose": "subscription test"})
    session_id = session_result["session_id"]

    # Subscribe to resource updates
    subscription = await mcp_client.subscribe_to_resource(f"session://{session_id}")
    assert subscription is not None

    # Add message (should trigger notification)
    await mcp_client.call_tool("add_message", {
        "session_id": session_id,
        "content": "New message should trigger update",
        "visibility": "public"
    })

    # Wait for notification
    notification = await mcp_client.wait_for_notification(timeout=5.0)
    assert notification is not None
    assert notification["uri"] == f"session://{session_id}"
```

## Multi-Agent Behavioral Testing

### Agent Collaboration Scenarios
```python
@pytest.mark.asyncio
async def test_multi_agent_collaboration(mcp_server, agent_identities):
    """Test multiple agents collaborating on shared context."""

    # Create separate clients for each agent
    async with TestClient(mcp_server) as claude_client, \
               TestClient(mcp_server) as dev_client, \
               TestClient(mcp_server) as test_client:

        # Set agent contexts
        claude_client.set_context(agent_identities["claude_main"])
        dev_client.set_context(agent_identities["developer"])
        test_client.set_context(agent_identities["tester"])

        # Claude creates session
        session_result = await claude_client.call_tool("create_session", {
            "purpose": "Multi-agent feature development"
        })
        session_id = session_result["session_id"]

        # Subscribe all agents to updates
        await dev_client.subscribe_to_resource(f"session://{session_id}")
        await test_client.subscribe_to_resource(f"session://{session_id}")

        # Claude adds initial requirements
        await claude_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Implement user authentication with JWT tokens",
            "metadata": {"type": "requirement", "priority": "high"}
        })

        # Developer responds with implementation plan
        await dev_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Plan: 1) Create JWT middleware 2) Add login endpoint 3) Secure existing routes",
            "metadata": {"type": "plan", "estimated_hours": 8}
        })

        # Tester adds testing considerations
        await test_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Testing approach: Unit tests for JWT validation, integration tests for auth flow",
            "metadata": {"type": "test_plan", "coverage_target": 0.9}
        })

        # Verify all messages are visible to all agents
        for client in [claude_client, dev_client, test_client]:
            resource = await client.read_resource(f"session://{session_id}")
            content = json.loads(resource.text)
            assert len(content["messages"]) == 3

            # Verify message types are preserved
            message_types = [msg["metadata"].get("type") for msg in content["messages"]]
            assert "requirement" in message_types
            assert "plan" in message_types
            assert "test_plan" in message_types

@pytest.mark.asyncio
async def test_private_agent_memory(mcp_server, agent_identities):
    """Test that agent memory is private and isolated."""

    async with TestClient(mcp_server) as dev_client, \
               TestClient(mcp_server) as test_client:

        dev_client.set_context(agent_identities["developer"])
        test_client.set_context(agent_identities["tester"])

        # Create shared session
        session_result = await dev_client.call_tool("create_session", {"purpose": "memory test"})
        session_id = session_result["session_id"]

        # Each agent stores private memory
        await dev_client.call_tool("set_memory", {
            "key": "current_task",
            "value": json.dumps({"task": "implement auth", "progress": 0.3}),
            "session_id": session_id
        })

        await test_client.call_tool("set_memory", {
            "key": "current_task",
            "value": json.dumps({"task": "write tests", "progress": 0.1}),
            "session_id": session_id
        })

        # Verify each agent can only access their own memory
        dev_memory = await dev_client.call_tool("get_memory", {
            "key": "current_task",
            "session_id": session_id
        })
        assert dev_memory["success"] is True
        task_data = json.loads(dev_memory["value"])
        assert task_data["task"] == "implement auth"

        test_memory = await test_client.call_tool("get_memory", {
            "key": "current_task",
            "session_id": session_id
        })
        assert test_memory["success"] is True
        task_data = json.loads(test_memory["value"])
        assert task_data["task"] == "write tests"

@pytest.mark.asyncio
async def test_message_visibility_controls(mcp_server, agent_identities):
    """Test message visibility controls work correctly."""

    async with TestClient(mcp_server) as dev_client, \
               TestClient(mcp_server) as test_client:

        dev_client.set_context(agent_identities["developer"])
        test_client.set_context(agent_identities["tester"])

        # Create session
        session_result = await dev_client.call_tool("create_session", {"purpose": "visibility test"})
        session_id = session_result["session_id"]

        # Developer adds public message
        await dev_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Public implementation notes",
            "visibility": "public"
        })

        # Developer adds private message
        await dev_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Private debugging thoughts",
            "visibility": "private"
        })

        # Tester adds public message
        await test_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Test results look good",
            "visibility": "public"
        })

        # Developer should see all their own messages (public + private)
        dev_resource = await dev_client.read_resource(f"session://{session_id}")
        dev_content = json.loads(dev_resource.text)
        dev_messages = [msg["content"] for msg in dev_content["messages"]]

        # Should see public messages from both agents, plus their own private
        assert "Public implementation notes" in dev_messages
        assert "Private debugging thoughts" in dev_messages  # Own private message
        assert "Test results look good" in dev_messages

        # Tester should only see public messages
        test_resource = await test_client.read_resource(f"session://{session_id}")
        test_content = json.loads(test_resource.text)
        test_messages = [msg["content"] for msg in test_content["messages"]]

        # Should see public messages from both agents, but not developer's private
        assert "Public implementation notes" in test_messages
        assert "Private debugging thoughts" not in test_messages  # Not visible
        assert "Test results look good" in test_messages
```

## Security Testing Patterns

### Agent Memory Isolation Testing
```python
@pytest.mark.asyncio
async def test_agent_memory_isolation_in_shared_sessions():
    """Test that agents maintain isolated memory even in shared sessions."""
    from tests.security.test_agent_memory_isolation import (
        test_agent_memory_isolation_in_shared_sessions
    )

    # Create shared session with multiple agents
    session_id = "shared_session_123"
    agent1_ctx = MockContext(session_id, "agent_alpha")
    agent2_ctx = MockContext(session_id, "agent_beta")

    # Each agent stores private memory
    await agent1_set_memory("current_task", {"task": "implement_auth"})
    await agent2_set_memory("current_task", {"task": "write_tests"})

    # Verify memory isolation
    agent1_memory = await agent1_get_memory("current_task")
    agent2_memory = await agent2_get_memory("current_task")

    assert agent1_memory["task"] == "implement_auth"
    assert agent2_memory["task"] == "write_tests"
    assert agent1_memory != agent2_memory
```

### Authentication Security Testing
```python
@pytest.mark.asyncio
async def test_jwt_token_validation_security():
    """Test JWT token validation with various attack scenarios."""
    # Test invalid signatures
    invalid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature"

    with pytest.raises(AuthenticationError):
        await validate_jwt_token(invalid_token)

    # Test expired tokens
    expired_token = create_expired_token()
    with pytest.raises(TokenExpiredError):
        await validate_jwt_token(expired_token)

    # Test malformed tokens
    malformed_token = "not.a.jwt.token"
    with pytest.raises(ValidationError):
        await validate_jwt_token(malformed_token)
```

### Message Visibility Security Testing
```python
@pytest.mark.asyncio
async def test_message_visibility_security_boundaries():
    """Test that message visibility controls prevent unauthorized access."""
    session_id = "security_test_session"
    agent1_ctx = MockContext(session_id, "agent_secure")
    agent2_ctx = MockContext(session_id, "agent_unauthorized")

    # Agent 1 creates private message
    await add_message(
        agent1_ctx,
        session_id=session_id,
        content="Sensitive security information",
        visibility="private"
    )

    # Agent 2 should not see private message
    agent2_messages = await get_messages(agent2_ctx, session_id=session_id)
    private_content = [msg for msg in agent2_messages["messages"]
                      if "Sensitive security information" in msg["content"]]

    assert len(private_content) == 0, "Private message leaked to unauthorized agent"
```

### MCP Authentication Validation Testing
```python
@pytest.mark.asyncio
async def test_mcp_tool_requires_valid_authentication():
    """Test that MCP tools require proper authentication."""
    # Test without authentication
    unauthenticated_ctx = MockContext("test_session", None)  # No agent_id

    with pytest.raises(AuthenticationRequired):
        await create_session(unauthenticated_ctx, purpose="unauthorized access")

    # Test with invalid authentication
    invalid_ctx = MockContext("test_session", "invalid_agent_id")

    with patch('shared_context_server.auth.validate_agent_permissions') as mock_validate:
        mock_validate.return_value = False

        with pytest.raises(PermissionDenied):
            await create_session(invalid_ctx, purpose="permission test")
```

## End-to-End Testing

### Complete Workflow Testing
```python
@pytest.mark.asyncio
async def test_complete_feature_development_workflow(mcp_server, agent_identities):
    """Test complete multi-agent feature development workflow."""

    async with TestClient(mcp_server) as claude_client, \
               TestClient(mcp_server) as dev_client, \
               TestClient(mcp_server) as test_client, \
               TestClient(mcp_server) as docs_client:

        # Set contexts
        claude_client.set_context(agent_identities["claude_main"])
        dev_client.set_context(agent_identities["developer"])
        test_client.set_context(agent_identities["tester"])
        docs_client.set_context(agent_identities["docs"])

        # 1. Claude creates session and defines requirements
        session_result = await claude_client.call_tool("create_session", {
            "purpose": "Implement password reset functionality",
            "metadata": {"epic": "user-auth", "sprint": "2024-Q1"}
        })
        session_id = session_result["session_id"]

        await claude_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Requirements: Password reset via email with secure token expiration",
            "metadata": {"type": "requirement"}
        })

        # 2. Developer breaks down into tasks
        await dev_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Implementation tasks: 1) Email service integration 2) Token generation/validation 3) Reset endpoint 4) Frontend form",
            "metadata": {"type": "breakdown"}
        })

        # 3. Tester defines acceptance criteria
        await test_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Test scenarios: Valid email sends token, invalid email fails gracefully, expired tokens rejected, successful reset updates password",
            "metadata": {"type": "acceptance_criteria"}
        })

        # 4. Developer implements (simulated with memory)
        await dev_client.call_tool("set_memory", {
            "key": "implementation_status",
            "value": json.dumps({
                "email_service": "completed",
                "token_generation": "completed",
                "reset_endpoint": "in_progress",
                "frontend_form": "pending"
            }),
            "session_id": session_id
        })

        await dev_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Progress update: Email service and tokens implemented, working on reset endpoint",
            "metadata": {"type": "progress", "completion": 0.5}
        })

        # 5. Tester runs initial tests
        await test_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Unit tests passing for email service and token generation. Integration tests pending endpoint completion.",
            "metadata": {"type": "test_results", "status": "partial_pass"}
        })

        # 6. Developer completes implementation
        await dev_client.call_tool("set_memory", {
            "key": "implementation_status",
            "value": json.dumps({
                "email_service": "completed",
                "token_generation": "completed",
                "reset_endpoint": "completed",
                "frontend_form": "completed"
            }),
            "session_id": session_id
        })

        await dev_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Feature complete: All password reset functionality implemented and tested locally",
            "metadata": {"type": "completion", "files_modified": ["auth.py", "email.py", "reset.html"]}
        })

        # 7. Tester runs full test suite
        await test_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "All tests passing: 15 unit tests, 8 integration tests, 4 E2E scenarios. Feature ready for deployment.",
            "metadata": {"type": "test_complete", "coverage": 0.95}
        })

        # 8. Docs agent adds documentation
        await docs_client.call_tool("add_message", {
            "session_id": session_id,
            "content": "Documentation updated: API endpoints documented, user guide updated with password reset flow",
            "metadata": {"type": "documentation", "pages_updated": ["api-auth.md", "user-guide.md"]}
        })

        # 9. Claude searches context for final summary
        search_result = await claude_client.call_tool("search_context", {
            "session_id": session_id,
            "query": "completion status tests documentation",
            "fuzzy_threshold": 50.0,
            "limit": 10
        })

        # Verify complete workflow captured
        resource = await claude_client.read_resource(f"session://{session_id}")
        content = json.loads(resource.text)

        # Should have messages from all agent types
        message_types = set()
        for msg in content["messages"]:
            if "type" in msg.get("metadata", {}):
                message_types.add(msg["metadata"]["type"])

        expected_types = {"requirement", "breakdown", "acceptance_criteria", "progress", "completion", "test_complete", "documentation"}
        assert expected_types.issubset(message_types)

        # Search should find relevant completion messages
        assert search_result["success"] is True
        assert len(search_result["results"]) > 0
```

## Performance Testing

### Load Testing
```python
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_concurrent_agent_performance(mcp_server, agent_identities):
    """Test system performance with multiple concurrent agents."""
    import time

    async def agent_workload(agent_id: str, session_id: str):
        """Simulate typical agent workload."""
        async with TestClient(mcp_server) as client:
            client.set_context({"agent_id": agent_id})

            # Each agent adds 10 messages
            for i in range(10):
                await client.call_tool("add_message", {
                    "session_id": session_id,
                    "content": f"Message {i} from {agent_id}",
                    "metadata": {"iteration": i}
                })

            # Each agent performs 5 searches
            for i in range(5):
                await client.call_tool("search_context", {
                    "session_id": session_id,
                    "query": f"message from {agent_id}",
                    "limit": 5
                })

            return f"{agent_id}_completed"

    # Create session
    async with TestClient(mcp_server) as setup_client:
        setup_client.set_context(agent_identities["claude_main"])
        session_result = await setup_client.call_tool("create_session", {
            "purpose": "Performance test session"
        })
        session_id = session_result["session_id"]

    # Run 20 agents concurrently
    agents = [f"agent_{i}" for i in range(20)]

    start_time = time.perf_counter()

    tasks = [agent_workload(agent_id, session_id) for agent_id in agents]
    results = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000

    # Verify all agents completed successfully
    assert len(results) == 20
    assert all("completed" in result for result in results)

    # Performance targets
    assert elapsed_ms < 10000, f"20 concurrent agents took {elapsed_ms:.2f}ms (should be < 10s)"

    # Verify final state
    async with TestClient(mcp_server) as verify_client:
        resource = await verify_client.read_resource(f"session://{session_id}")
        content = json.loads(resource.text)

        # Should have 200 total messages (20 agents × 10 messages each)
        assert len(content["messages"]) == 200

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_search_performance_large_dataset(mcp_server, agent_identities):
    """Test search performance with large message dataset."""
    import time

    async with TestClient(mcp_server) as client:
        client.set_context(agent_identities["claude_main"])

        # Create session
        session_result = await client.call_tool("create_session", {
            "purpose": "Large dataset search test"
        })
        session_id = session_result["session_id"]

        # Add 1000 messages with varied content
        messages = [
            f"Implementation of feature {i} with authentication middleware and database integration"
            for i in range(1000)
        ]

        # Add messages in batches for efficiency
        batch_size = 50
        for i in range(0, len(messages), batch_size):
            batch_tasks = []
            for j in range(i, min(i + batch_size, len(messages))):
                task = client.call_tool("add_message", {
                    "session_id": session_id,
                    "content": messages[j],
                    "metadata": {"index": j}
                })
                batch_tasks.append(task)
            await asyncio.gather(*batch_tasks)

        # Test search performance
        queries = [
            "authentication middleware implementation",
            "database integration feature",
            "implementation of feature 500",
            "middleware and database"
        ]

        search_times = []
        for query in queries:
            start_time = time.perf_counter()

            result = await client.call_tool("search_context", {
                "session_id": session_id,
                "query": query,
                "fuzzy_threshold": 60.0,
                "limit": 10
            })

            end_time = time.perf_counter()
            search_time_ms = (end_time - start_time) * 1000
            search_times.append(search_time_ms)

            # Verify search returns relevant results
            assert result["success"] is True
            assert len(result["results"]) > 0

            # Verify results are ranked by relevance
            scores = [r["score"] for r in result["results"]]
            assert scores == sorted(scores, reverse=True)

        # Performance target: search should complete in under 100ms
        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)

        assert avg_search_time < 100, f"Average search time {avg_search_time:.2f}ms exceeds 100ms target"
        assert max_search_time < 200, f"Max search time {max_search_time:.2f}ms exceeds 200ms threshold"
```

## Test Organization

### File Structure
```
tests/
├── unit/
│   ├── test_models.py              # Pydantic model validation
│   ├── test_utils.py               # Utility functions
│   ├── test_search.py              # Search algorithms
│   └── test_sanitization.py       # Input sanitization
├── integration/
│   ├── test_mcp_tools.py           # MCP tool functionality
│   ├── test_resources.py          # MCP resource access
│   ├── test_database.py           # Database operations
│   └── test_authentication.py     # Auth and permissions
├── behavioral/
│   ├── test_multi_agent.py        # Multi-agent collaboration
│   ├── test_workflows.py          # Complete workflows
│   ├── test_privacy.py            # Privacy and visibility
│   └── test_real_time.py          # Subscriptions and updates
├── security/
│   ├── test_agent_memory_isolation.py    # Agent memory isolation
│   ├── test_authentication_security.py  # Auth security patterns
│   ├── test_mcp_auth_validation.py       # MCP auth validation
│   ├── test_message_visibility.py       # Message visibility controls
│   └── test_uat_reproduction.py         # Security regression tests
├── performance/
│   ├── test_load.py                # Concurrent usage
│   ├── test_search_speed.py       # Search performance
│   └── test_memory_usage.py       # Memory efficiency
└── conftest.py                     # Shared fixtures
```

## Best Practices

### Test Naming Conventions
```python
# Good test names describe the behavior being tested
def test_agent_can_create_session_with_valid_purpose():
    """Test that agents can create sessions when providing valid purpose."""
    pass

def test_private_message_only_visible_to_sender():
    """Test that private messages are only visible to the sending agent."""
    pass

def test_fuzzy_search_returns_ranked_results():
    """Test that fuzzy search returns results ranked by relevance score."""
    pass
```

### Test Documentation
```python
@pytest.mark.asyncio
async def test_multi_agent_subscription_workflow():
    """
    Test complete multi-agent subscription workflow.

    Scenario: Three agents collaborate on shared context with real-time updates
    1. Agent A creates session and subscribes to updates
    2. Agent B joins session and adds message
    3. Agent A receives notification of new message
    4. Agent C adds private message (should not notify others)
    5. Agents A and B should see public messages, not private

    Verifies:
    - Real-time subscription notifications work
    - Privacy controls are respected in notifications
    - Multiple concurrent subscriptions are supported
    """
    pass
```

### Fixture Management
```python
# Use appropriate fixture scopes
@pytest.fixture(scope="session")  # Expensive setup, reuse across all tests
def event_loop():
    pass

@pytest.fixture(scope="function")  # Fresh database for each test
async def test_database():
    pass

# Parametrized fixtures for testing multiple scenarios
@pytest.fixture(params=["public", "private", "agent_only"])
def message_visibility(request):
    return request.param
```

## Continuous Integration

### Test Running Strategy

**Mandatory Quality Commands** - **MUST PASS**:
```bash
# Quality gates for all development
uv run ruff check .                                          # MANDATORY: Zero lint errors
uv run mypy .                                               # MANDATORY: Zero type errors
uv run pytest tests/ --cov=src --cov-fail-under=80         # MANDATORY: High coverage
uv run pytest tests/performance/ -v --benchmark-only        # MANDATORY: Performance targets met
```

```yaml
# GitHub Actions example
test_strategy:
  quality_gates:
    command: |
      uv run ruff check . &&
      uv run mypy . &&
      uv run pytest tests/ --cov=src --cov-fail-under=80
    timeout: 10 minutes

  unit_tests:
    command: pytest tests/unit/ -v --tb=short
    timeout: 5 minutes

  integration_tests:
    command: pytest tests/integration/ -v --tb=short
    timeout: 15 minutes

  behavioral_tests:
    command: pytest tests/behavioral/ -v --tb=short
    timeout: 20 minutes

  security_tests:
    command: pytest tests/security/ -v --tb=short
    timeout: 15 minutes

  performance_tests:
    command: pytest tests/performance/ -v --tb=short -m benchmark
    timeout: 30 minutes
```

### Coverage Requirements

**Coverage Quality Standards**:
- **Core modules**: Achieve high coverage of critical business logic
- **Database operations**: Comprehensive coverage of all database patterns
- **Security functions**: Complete coverage of authentication and authorization
- **New modules**: Achieve excellent coverage during development

**Quality Gate Commands**:
```bash
# Coverage validation with quality reporting
uv run pytest tests/ --cov=src --cov-report=html --cov-fail-under=80

# Performance testing
uv run pytest tests/performance/ -v --benchmark-only

# Security testing
uv run pytest tests/security/ -v
```

```python
# pytest.ini
[tool:pytest]
addopts = --cov=shared_context_server --cov-report=html --cov-report=term
testpaths = tests
markers =
    benchmark: performance and load testing
    integration: integration tests requiring database
    behavioral: multi-agent behavioral tests
    security: security and authentication tests

# Coverage configuration
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/venv/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
# Quality coverage target
fail_under = 80  # High quality coverage standard
```

## Success Criteria

### Test Quality Success
- **Tests focus on behavior, not implementation details**
- **All critical user workflows have test coverage**
- **Multi-agent scenarios are thoroughly tested**
- **Edge cases and error conditions are covered**
- **Tests are fast, reliable, and maintainable**
- **Security patterns are comprehensively tested**

### Coverage Success
- **High coverage of critical business logic**
- **All MCP tools and resources have comprehensive tests**
- **Error handling paths are tested**
- **Performance requirements are validated**
- **Multi-agent collaboration patterns are verified**
- **Security boundaries and authentication are tested**
- **Quality gate enforcement**: All tests must pass before deployment

### Test Maintainability Success
- Tests survive refactoring without modification
- Test failures indicate actual problems, not false positives
- New tests follow established patterns and conventions
- Test code is clean and well-organized
- Tests provide clear failure messages

## Testing Standardization Findings

**COMPREHENSIVE TEST STANDARDIZATION**

During the comprehensive test standardization effort, critical implementation fixes were discovered and applied across the entire codebase. This resulted in achieving excellent test coverage and reliability across all test categories.

### Critical Implementation Fixes Applied

#### 1. Agent ID Consistency Fix ⚠️ **SYSTEM-WIDE CRITICAL FIX**
- **Issue**: Agent ID generation was inconsistent across server functions
- **Root Cause**: Some functions used old `agent_id = f"agent_{ctx.session_id[:8]}"` while others used new `getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")` pattern
- **Impact**: Tests expecting specific agent ID formats failed unpredictably
- **Fix Applied**: Updated ALL server functions to use consistent pattern:
  ```python
  agent_id = getattr(ctx, "agent_id", f"agent_{ctx.session_id[:8]}")
  ```
- **Functions Updated**: `create_session`, `add_message`, `get_messages`, `get_session`, `search_context`
- **Result**: Predictable agent ID generation, proper agent memory isolation in shared sessions

#### 2. Database Row Factory Fix ⚠️ **DATABASE OPERATION CRITICAL FIX**
- **Issue**: Database queries failed with "dictionary update sequence element #0 has length 24; 2 is required"
- **Root Cause**: Missing `conn.row_factory = aiosqlite.Row` in server functions
- **Impact**: Database operations returned tuples instead of dict-like rows
- **Fix Applied**: Added row factory to ALL database operations:
  ```python
  async with get_db_connection() as conn:
      conn.row_factory = aiosqlite.Row  # Enable dict-like access
      # ... rest of database operations
  ```
- **Functions Updated**: `get_session`, `get_messages`, `search_context`
- **Result**: Proper dict-like database row access throughout system

#### 3. Visibility Filtering Logic Overhaul ⚠️ **MAJOR SECURITY LOGIC FIX**
- **Issue**: Visibility filters were additive instead of restrictive, breaking security boundaries
- **Root Cause**: Adding visibility_filter as OR condition instead of replacing base visibility rules
- **Impact**: Agents could potentially access messages they shouldn't see
- **Fix Applied**: Complete rewrite of visibility filtering in `get_messages`:
  ```python
  # New restrictive visibility logic
  if visibility_filter:
      if visibility_filter == "public":
          where_conditions.append("visibility = 'public'")
      elif visibility_filter == "private":
          where_conditions.append("visibility = 'private' AND sender = ?")
          params.append(agent_id)
      elif visibility_filter == "agent_only":
          where_conditions.append("visibility = 'agent_only' AND sender = ?")
          params.append(agent_id)
  else:
      # Default visibility rules: public + own private/agent_only
      visibility_conditions = [
          "visibility = 'public'",
          "(visibility = 'private' AND sender = ?)",
          "(visibility = 'agent_only' AND sender = ?)",
      ]
      params.extend([agent_id, agent_id])
      where_conditions.append(f"({' OR '.join(visibility_conditions)})")
  ```
- **Result**: Proper security boundaries enforced, visibility filters work as expected

#### 4. Mock Database Parameter Format Updates ⚠️ **TEST INFRASTRUCTURE FIX**
- **Issue**: Mock databases in behavioral tests expected old parameter formats
- **Root Cause**: Visibility filtering changes altered SQL parameter structures
- **Impact**: Behavioral tests failed with parameter format mismatches
- **Fix Applied**: Updated mock database parameter parsing logic for new formats:
  - Public filter: `(session_id, limit, offset)`
  - Private/agent_only: `(session_id, agent_id, limit, offset)`
  - No filter: `(session_id, agent_id, agent_id, limit, offset)`
- **Files Updated**: `tests/behavioral/test_visibility.py`, `tests/integration/test_agent_workflow.py`
- **Result**: Mock databases properly handle new parameter formats

#### 5. Database Test Infrastructure Fixes ⚠️ **DATABASE TESTING CRITICAL FIXES**
- **Multiple Issues**:
  - Index name mismatch: `idx_messages_session_timestamp` → `idx_messages_session_time`
  - Session ID format validation issues
  - Global function database consistency problems
  - Trigger timing issues requiring longer sleep periods
- **Fix Applied**: Comprehensive database test infrastructure improvements:
  ```python
  # Fixed global function consistency
  with patch.dict(os.environ, {"DATABASE_PATH": str(test_db_manager.database_path)}):
      import src.shared_context_server.database as db_module
      db_module._db_manager = test_db_manager
      stats = await cleanup_expired_data()
  ```
- **Result**: All database tests passing with comprehensive coverage

#### 6. Test Pattern Standardization ⚠️ **TESTING INFRASTRUCTURE STANDARDIZATION**
- **Issue**: Inconsistent test patterns across unit, integration, and behavioral tests
- **Root Cause**: Mix of obsolete `mcp.context` patches and modern direct context passing
- **Fix Applied**: Standardized ALL test files to use consistent `call_fastmcp_tool` pattern:
  ```python
  # Standardized test pattern
  result = await call_fastmcp_tool(
      fastmcp_tool_function,
      mock_context,
      **test_parameters
  )
  ```
- **Files Standardized**: All unit, integration, behavioral, and end-to-end test files
- **Result**: Consistent, maintainable test patterns across entire codebase

### Test Success Rate Achievement

**Test Results**: Excellent test reliability and coverage achieved

#### By Test Category:
- **Database Tests**: All passing - comprehensive database operation coverage
- **Behavioral Tests**: All passing - multi-agent scenarios working reliably
- **Integration Tests**: All passing - component integration verified
- **Unit Tests**: All passing - individual component validation complete
- **Security Tests**: All passing - authentication and isolation verified
- **End-to-End Tests**: All passing - complete workflow validation

#### Key Test Categories Fixed:
1. **Agent Memory Isolation**: Tests now properly validate agent memory isolation in shared sessions
2. **Visibility Controls**: All visibility filtering tests pass with proper security boundaries
3. **Database Operations**: Schema, triggers, constraints, and performance tests all pass
4. **FastMCP Integration**: All tools work consistently with standardized test patterns
5. **Multi-Agent Workflows**: Complex agent interaction scenarios work reliably

### FastMCP Testing Patterns - Standardized Approach

**Final Recommended Pattern**: Use helper functions with consistent MockContext objects:

```python
# Standard test pattern (now used across all test files)
from conftest import call_fastmcp_tool, MockContext

@pytest.mark.asyncio
async def test_example_functionality():
    """Test description."""
    ctx = MockContext("test_session_id", "test_agent_id")

    with patch("shared_context_server.server.get_db_connection") as mock_db:
        # Setup mocks...

        result = await call_fastmcp_tool(
            fastmcp_tool_function,
            ctx,
            parameter1="value1",
            parameter2="value2"
        )

        assert result["success"] is True
```

### Implementation Quality Standards Achieved

1. **Zero Regression Tolerance**: All existing functionality preserved while fixing critical bugs
2. **Security-First Approach**: Visibility filtering logic completely rewritten to ensure proper security boundaries
3. **Consistency Standards**: Agent ID generation, database operations, and test patterns now consistent system-wide
4. **Performance Maintained**: All fixes applied with no performance degradation
5. **Test Coverage**: Excellent test success rate maintained throughout all fixes

## References

- FastMCP Testing: https://github.com/jlowin/fastmcp/docs/testing
- Pytest Documentation: https://docs.pytest.org/
- Behavioral Testing: https://martinfowler.com/articles/practical-test-pyramid.html
- AsyncIO Testing: https://docs.python.org/3/library/asyncio-dev.html#testing

## Related Guides

- Core Architecture Guide - System design and components
- Framework Integration Guide - MCP server implementation
- Performance Optimization Guide - Performance patterns and monitoring
