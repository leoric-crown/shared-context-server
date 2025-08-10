# Testing Guide

## Overview

This guide implements comprehensive testing patterns for the Shared Context MCP Server, focusing on behavioral testing, FastMCP in-memory testing, and multi-agent collaboration scenarios. The approach emphasizes testing what the system does rather than how it does it.

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
        /  \  E2E Tests (10%)
       /    \  - Critical user journeys
      /      \  - Multi-agent scenarios
     /--------\
    /          \  Integration Tests (30%)
   /            \  - MCP tool interactions
  /              \  - Database operations
 /                \  - API endpoints
/------------------\
                     Unit Tests (60%)
                     - Business logic
                     - Validation rules
                     - Utility functions
```

## Testing Infrastructure

### Test Configuration

```python
# conftest.py - Shared pytest fixtures
import pytest
import asyncio
from pathlib import Path
import tempfile
import json
from datetime import datetime, timezone
from fastmcp import FastMCP
from fastmcp.testing import TestClient
import aiosqlite
import aiosqlitepool

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_database():
    """Create temporary test database with schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Initialize schema
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                purpose TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                created_by TEXT NOT NULL,
                metadata JSON
            );
            
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                visibility TEXT DEFAULT 'public',
                message_type TEXT DEFAULT 'agent_response',
                metadata JSON,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parent_message_id INTEGER,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (parent_message_id) REFERENCES messages(id)
            );
            
            CREATE TABLE agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                session_id TEXT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(agent_id, session_id, key)
            );
            
            -- Performance indexes
            CREATE INDEX idx_messages_session_time ON messages(session_id, timestamp);
            CREATE INDEX idx_messages_sender ON messages(sender, timestamp);
            CREATE INDEX idx_agent_memory_lookup ON agent_memory(agent_id, session_id, key);
        """)
        await conn.commit()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)

@pytest.fixture
async def mcp_server(test_database):
    """Create MCP server with test database."""
    from shared_context_server import create_mcp_server
    
    # Create server with test database
    server = await create_mcp_server(database_path=test_database)
    
    yield server
    
    # Cleanup server resources
    await server.cleanup()

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

### Basic Tool Testing
```python
@pytest.mark.asyncio
async def test_create_session_tool(mcp_client, agent_identities):
    """Test session creation through MCP tool."""
    # Set agent context
    mcp_client.set_context(agent_identities["claude_main"])
    
    # Call create_session tool
    result = await mcp_client.call_tool(
        "create_session",
        {"purpose": "test session creation"}
    )
    
    # Verify response
    assert result["success"] is True
    assert "session_id" in result
    assert result["session_id"].startswith("session_")
    assert result["created_by"] == "claude-main"

@pytest.mark.asyncio
async def test_add_message_tool(mcp_client, agent_identities):
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
```yaml
# GitHub Actions example
test_strategy:
  unit_tests:
    command: pytest tests/unit/ -v --tb=short
    timeout: 5 minutes
    
  integration_tests:
    command: pytest tests/integration/ -v --tb=short
    timeout: 15 minutes
    
  behavioral_tests:
    command: pytest tests/behavioral/ -v --tb=short
    timeout: 20 minutes
    
  performance_tests:
    command: pytest tests/performance/ -v --tb=short -m benchmark
    timeout: 30 minutes
```

### Coverage Requirements
```python
# pytest.ini
[tool:pytest]
addopts = --cov=shared_context_server --cov-report=html --cov-report=term
testpaths = tests
markers =
    benchmark: performance and load testing
    integration: integration tests requiring database
    behavioral: multi-agent behavioral tests

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
fail_under = 85
```

## Success Criteria

### Test Quality Success
- Tests focus on behavior, not implementation details
- All critical user workflows have test coverage
- Multi-agent scenarios are thoroughly tested
- Edge cases and error conditions are covered
- Tests are fast, reliable, and maintainable

### Coverage Success
- High coverage of critical business logic (>85%)
- All MCP tools and resources have comprehensive tests
- Error handling paths are tested
- Performance requirements are validated
- Multi-agent collaboration patterns are verified

### Test Maintainability Success
- Tests survive refactoring without modification
- Test failures indicate actual problems, not false positives
- New tests follow established patterns and conventions
- Test code is clean and well-organized
- Tests provide clear failure messages

## References

- FastMCP Testing: https://github.com/jlowin/fastmcp/docs/testing
- Pytest Documentation: https://docs.pytest.org/
- Behavioral Testing: https://martinfowler.com/articles/practical-test-pyramid.html
- AsyncIO Testing: https://docs.python.org/3/library/asyncio-dev.html#testing

## Related Guides

- Core Architecture Guide - System design and components
- Framework Integration Guide - MCP server implementation
- Performance Optimization Guide - Performance patterns and monitoring