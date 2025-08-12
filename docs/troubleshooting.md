# Shared Context MCP Server - Troubleshooting Guide

Comprehensive troubleshooting guide for common issues, performance problems, and integration challenges with the Shared Context MCP Server.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues & Solutions](#common-issues--solutions)
- [Performance Troubleshooting](#performance-troubleshooting)
- [Integration Problems](#integration-problems)
- [Security & Authentication Issues](#security--authentication-issues)
- [Database Issues](#database-issues)
- [Monitoring & Debugging](#monitoring--debugging)

---

## Quick Diagnostics

### Health Check Commands

Run these commands to quickly diagnose server health:

```bash
# Check server health
curl -f http://localhost:23456/health

# Check MCP connection
claude mcp list | grep shared-context-server

# Test basic tool access
curl -X POST http://localhost:23456/mcp/tool/authenticate_agent \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "test", "agent_type": "test", "api_key": "your-api-key"}'

# Check server logs
tail -f shared_context_server.log

# Validate environment
uv run python -m shared_context_server.scripts.dev --validate
```

### Server Status Indicators

| Status | Health Check Response | Action Required |
|--------|----------------------|-----------------|
| ✅ Healthy | `{"status": "ok", "database": "connected"}` | None |
| ⚠️ Warning | `{"status": "warning", "issues": [...]}` | Check issues list |
| ❌ Error | `{"status": "error", "error": "..."}` | Immediate attention |
| 🚫 Unavailable | Connection refused/timeout | Start server |

---

## Common Issues & Solutions

### 1. Server Won't Start

**Symptoms:**
- `ConnectionRefusedError` when connecting
- Port already in use errors
- Import/dependency errors

**Solutions:**

```bash
# Check if port is in use
lsof -i :23456
# Kill existing process if needed
kill -9 <PID>

# Verify dependencies
uv sync --all-extras

# Check Python version
python --version  # Should be 3.11+

# Start with debug logging
LOG_LEVEL=DEBUG uv run python -m shared_context_server.scripts.dev

# Check for conflicting installations
pip list | grep shared-context-server
```

**Fix for common dependency conflicts:**
```bash
# Clean install
rm -rf .venv
uv venv
uv sync --all-extras

# Update dependencies
uv sync --upgrade
```

### 2. Authentication Failures

**Symptoms:**
- `INVALID_API_KEY` errors
- `401 Unauthorized` responses
- JWT token validation failures

**Solutions:**

```bash
# Verify API key is set
echo $API_KEY

# Check JWT secret configuration
echo $JWT_SECRET_KEY

# Test authentication manually
curl -X POST http://localhost:23456/mcp/tool/authenticate_agent \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test-agent",
    "agent_type": "claude",
    "api_key": "your-correct-api-key"
  }'
```

**Fix for JWT issues:**
```bash
# Generate new JWT secret (32+ characters)
export JWT_SECRET_KEY="$(openssl rand -hex 32)"

# Restart server with new secret
MCP_TRANSPORT=http uv run python -m shared_context_server.scripts.dev
```

**Fix for API key issues:**
```bash
# Set API key in environment
export API_KEY="your-secure-api-key-here"

# Or create .env file
echo "API_KEY=your-secure-api-key-here" > .env

# Verify in code
python -c "import os; print('API_KEY set:', bool(os.getenv('API_KEY')))"
```

### 3. Claude Code Connection Issues

**Symptoms:**
- Claude Code shows "❌ Failed to connect"
- `mcp-proxy` not found errors
- Transport configuration problems

**Solutions:**

```bash
# Install mcp-proxy
uv tool install mcp-proxy

# Verify mcp-proxy installation
which mcp-proxy

# Remove and re-add connection
claude mcp remove shared-context-server
claude mcp add-json shared-context-server '{
  "command": "mcp-proxy",
  "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]
}'

# Check connection status
claude mcp list

# Test with direct stdio connection (alternative)
claude mcp add shared-context-server "uv run python -m shared_context_server.scripts.cli"
```

**Fix for transport issues:**
```bash
# Ensure server is running on correct port
netstat -tlnp | grep 23456

# Try alternative port
uv run python -m shared_context_server.scripts.dev

# Update Claude Code connection
claude mcp add-json shared-context-server '{
  "command": "mcp-proxy",
  "args": ["--transport=streamablehttp", "http://localhost:23456/mcp/"]
}'
```

### 4. Database Connection Problems

**Symptoms:**
- `database locked` errors
- `no such table` errors
- Connection timeout errors

**Solutions:**

```bash
# Check database file permissions
ls -la chat_history.db

# Fix permissions
chmod 664 chat_history.db

# Reset database schema
rm chat_history.db
uv run python -c "
from shared_context_server.database import initialize_database
import asyncio
asyncio.run(initialize_database())
"

# Check database integrity
sqlite3 chat_history.db "PRAGMA integrity_check;"
```

**Fix for locked database:**
```bash
# Find and kill processes using database
lsof chat_history.db

# Enable WAL mode for better concurrency
sqlite3 chat_history.db "PRAGMA journal_mode=WAL;"

# Check WAL file
ls -la chat_history.db*
```

### 5. Memory and Performance Issues

**Symptoms:**
- High memory usage
- Slow response times
- Connection pool exhaustion
- Cache performance issues

**Solutions:**

```bash
# Monitor server performance
curl -X POST http://localhost:23456/mcp/tool/get_performance_metrics \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Check memory usage
ps aux | grep python | grep shared_context_server

# Monitor database performance
sqlite3 chat_history.db ".timer on" "SELECT COUNT(*) FROM messages;"
```

**Fix for performance issues:**
```bash
# Optimize database
sqlite3 chat_history.db "VACUUM; ANALYZE;"

# Clear old data
sqlite3 chat_history.db "
DELETE FROM messages WHERE timestamp < datetime('now', '-30 days');
DELETE FROM sessions WHERE created_at < datetime('now', '-30 days');
"

# Restart with optimized settings
DATABASE_POOL_SIZE=20 \
CACHE_SIZE=1000 \
uv run python -m shared_context_server.scripts.dev
```

---

## Performance Troubleshooting

### Identifying Performance Issues

**Use built-in performance monitoring:**

```python
import httpx

# Get comprehensive metrics (requires admin token)
async def check_performance():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:23456/mcp/tool/get_performance_metrics",
            headers={"Authorization": "Bearer YOUR_ADMIN_TOKEN"}
        )
        metrics = response.json()

        # Check key performance indicators
        db_perf = metrics["database_performance"]
        print(f"Average query time: {db_perf['connection_stats']['avg_query_time']}ms")
        print(f"Pool utilization: {db_perf['pool_stats']['pool_utilization']*100:.1f}%")
        print(f"Cache hit ratio: {db_perf['cache_stats']['cache_hit_ratio']*100:.1f}%")

        # Performance targets (all should be met)
        targets = metrics["performance_targets"]
        print(f"Performance targets: {targets}")
```

### Performance Optimization Steps

1. **Database Optimization**
```sql
-- Run these in sqlite3 chat_history.db
PRAGMA optimize;
VACUUM;
ANALYZE;

-- Check index usage
.expert
SELECT * FROM messages WHERE session_id = 'test';
```

2. **Connection Pool Tuning**
```bash
# Increase pool size for high concurrency
export DATABASE_POOL_MIN_SIZE=10
export DATABASE_POOL_MAX_SIZE=100
export CONNECTION_TIMEOUT=60

# Monitor pool stats
curl -s http://localhost:23456/mcp/tool/get_performance_metrics | \
  jq '.database_performance.pool_stats'
```

3. **Cache Optimization**
```bash
# Increase cache sizes
export CACHE_L1_SIZE=2000
export CACHE_L2_SIZE=10000
export CACHE_DEFAULT_TTL=900

# Check cache performance
curl -s http://localhost:23456/mcp/tool/get_performance_metrics | \
  jq '.database_performance.cache_stats'
```

### Performance Benchmarking

**Run performance tests:**

```python
import asyncio
import httpx
import time
from statistics import mean, median

async def benchmark_tools():
    """Benchmark MCP tool performance."""

    # Authenticate first
    async with httpx.AsyncClient() as client:
        auth_response = await client.post(
            "http://localhost:23456/mcp/tool/authenticate_agent",
            json={
                "agent_id": "benchmark",
                "agent_type": "test",
                "api_key": "your-api-key"
            }
        )
        token = auth_response.json()["token"]

        # Create test session
        session_response = await client.post(
            "http://localhost:23456/mcp/tool/create_session",
            headers={"Authorization": f"Bearer {token}"},
            json={"purpose": "Performance benchmark"}
        )
        session_id = session_response.json()["session_id"]

        # Benchmark message operations
        times = []
        for i in range(100):
            start = time.time()
            await client.post(
                "http://localhost:23456/mcp/tool/add_message",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "session_id": session_id,
                    "content": f"Benchmark message {i}",
                    "visibility": "public"
                }
            )
            times.append((time.time() - start) * 1000)

        print(f"Message insertion benchmark:")
        print(f"  Average: {mean(times):.2f}ms")
        print(f"  Median: {median(times):.2f}ms")
        print(f"  95th percentile: {sorted(times)[94]:.2f}ms")
        print(f"  Target: < 20ms")

# Run benchmark
asyncio.run(benchmark_tools())
```

---

## Integration Problems

### AutoGen Integration Issues

**Common Problem: Agent Authentication Loop**
```python
# ❌ Wrong - creates authentication loop
class SharedContextAgent(ConversableAgent):
    async def send(self, message, recipient):
        await self.authenticate()  # Don't authenticate on every send
        return await super().send(message, recipient)

# ✅ Correct - authenticate once during setup
class SharedContextAgent(ConversableAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.authenticated = False

    async def setup_once(self):
        if not self.authenticated:
            await self.authenticate()
            self.authenticated = True
```

**Fix for AutoGen Group Chat Issues:**
```python
# Ensure all agents share the same session
async def setup_autogen_group():
    # Create session with primary agent
    primary_agent = SharedContextAgent("Primary", ...)
    await primary_agent.setup_shared_context("Group chat session")
    session_id = primary_agent.shared_context.current_session_id

    # Other agents join the same session
    for agent in other_agents:
        agent.shared_context.token = primary_agent.shared_context.token
        agent.shared_context.current_session_id = session_id
        await agent.shared_context.add_message(f"{agent.name} joined session")
```

### CrewAI Integration Issues

**Common Problem: Tool Execution in Synchronous Context**
```python
# ❌ Wrong - asyncio.run() in synchronous context causes issues
@tool("Add to shared context")
def add_message_wrong(content: str) -> str:
    result = asyncio.run(async_operation(content))  # Can cause event loop issues
    return result

# ✅ Correct - handle async properly
@tool("Add to shared context")
def add_message_correct(content: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Use thread pool for nested event loops
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_operation(content))
                result = future.result(timeout=30)
        else:
            result = asyncio.run(async_operation(content))
        return result
    except Exception as e:
        return f"Error: {e}"
```

**Fix for CrewAI Task Dependencies:**
```python
# Ensure tasks have proper dependencies
requirements_task = Task(
    description="Define requirements",
    agent=product_manager,
    expected_output="Requirements document"
)

architecture_task = Task(
    description="Design architecture using requirements from shared context",
    agent=tech_lead,
    expected_output="Architecture design",
    context=[requirements_task]  # Explicit dependency
)
```

### LangChain Integration Issues

**Common Problem: Memory Management**
```python
# ❌ Wrong - LangChain memory conflicts with shared context
memory = ConversationBufferMemory()
agent = initialize_agent(
    tools=shared_context_tools,
    memory=memory,  # This can conflict with shared context
    llm=llm
)

# ✅ Correct - Use shared context as primary memory
class SharedContextMemoryWrapper:
    def __init__(self, shared_context):
        self.shared_context = shared_context

    def save_context(self, inputs, outputs):
        # Save to shared context instead of local memory
        asyncio.create_task(self.shared_context.add_message(
            f"Input: {inputs}\nOutput: {outputs}"
        ))

    def load_memory_variables(self, inputs):
        # Load from shared context
        messages = asyncio.run(self.shared_context.get_messages(limit=10))
        return {"history": messages}
```

**Fix for LangChain Tool Integration:**
```python
# Handle async tools properly in LangChain
def create_sync_wrapper(async_func):
    """Create synchronous wrapper for async functions."""
    def wrapper(*args, **kwargs):
        try:
            # Check if we're in an event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Use thread executor for nested loops
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                    return future.result(timeout=30)
            else:
                return asyncio.run(async_func(*args, **kwargs))
        except Exception as e:
            return f"Error executing tool: {e}"

    return wrapper

# Apply to tools
sync_add_message = create_sync_wrapper(shared_context.add_message)
```

---

## Security & Authentication Issues

### JWT Token Problems

**Token Expiration Issues:**
```python
# Check token expiration
import jwt
import datetime

def check_token_expiry(token):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp = decoded.get('exp')
        if exp:
            exp_time = datetime.datetime.fromtimestamp(exp)
            now = datetime.datetime.now()
            remaining = exp_time - now
            print(f"Token expires: {exp_time}")
            print(f"Time remaining: {remaining}")
            return remaining.total_seconds() > 0
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        return False

# Auto-refresh token before expiry
class TokenManager:
    def __init__(self, api_key, agent_id):
        self.api_key = api_key
        self.agent_id = agent_id
        self.token = None
        self.expires_at = None

    async def get_valid_token(self):
        if not self.token or self._needs_refresh():
            await self._refresh_token()
        return self.token

    def _needs_refresh(self):
        if not self.expires_at:
            return True
        # Refresh 5 minutes before expiry
        return datetime.datetime.now() > (self.expires_at - datetime.timedelta(minutes=5))

    async def _refresh_token(self):
        # Implement token refresh logic
        pass
```

### Permission Problems

**Fix for Permission Denied Errors:**
```python
# Check current permissions
def check_permissions(token):
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        permissions = payload.get('permissions', [])
        print(f"Current permissions: {permissions}")
        return permissions
    except jwt.InvalidTokenError:
        print("Invalid token")
        return []

# Request elevated permissions if needed
async def ensure_permissions(client, required_permissions):
    """Ensure agent has required permissions."""
    current_token = client.token
    current_perms = check_permissions(current_token)

    missing_perms = set(required_permissions) - set(current_perms)
    if missing_perms:
        print(f"Missing permissions: {missing_perms}")
        print("Re-authenticating with elevated permissions...")

        # Re-authenticate with required permissions
        auth_response = await client.authenticate(
            requested_permissions=list(set(current_perms) | set(required_permissions))
        )

        if not auth_response.get("success"):
            raise Exception("Failed to obtain required permissions")
```

### API Key Security

**Fix for API Key Exposure:**
```python
# ❌ Wrong - API key in code
client = SharedContextClient(api_key="sk-1234567890abcdef")

# ✅ Correct - API key from environment
import os
api_key = os.getenv("SHARED_CONTEXT_API_KEY")
if not api_key:
    raise ValueError("SHARED_CONTEXT_API_KEY environment variable not set")
client = SharedContextClient(api_key=api_key)

# For production, use secret management
# AWS Secrets Manager, Azure Key Vault, etc.
```

---

## Database Issues

### Database Corruption

**Symptoms:**
- `database disk image is malformed`
- Inconsistent query results
- Unexpected crashes

**Recovery Steps:**
```bash
# 1. Stop the server
pkill -f shared_context_server

# 2. Backup corrupted database
cp chat_history.db chat_history.db.corrupted.$(date +%Y%m%d_%H%M%S)

# 3. Check integrity
sqlite3 chat_history.db "PRAGMA integrity_check;"

# 4. Try to repair
sqlite3 chat_history.db ".recover" | sqlite3 chat_history_recovered.db

# 5. If recovery fails, restore from backup
# (Ensure you have regular backups!)
cp chat_history.db.backup.latest chat_history.db

# 6. Restart server
uv run python -m shared_context_server.scripts.dev
```

### Database Locking Issues

**Fix for "database is locked" errors:**
```bash
# Check for zombie processes
lsof chat_history.db

# Kill processes holding locks
kill -9 <PID>

# Enable WAL mode for better concurrency
sqlite3 chat_history.db "
PRAGMA journal_mode=WAL;
PRAGMA wal_autocheckpoint=1000;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
"

# Verify WAL mode is active
sqlite3 chat_history.db "PRAGMA journal_mode;"
```

### Database Performance Issues

**Optimize database performance:**
```sql
-- Run in sqlite3 chat_history.db

-- Analyze query plans
.expert
SELECT * FROM messages WHERE session_id = 'test' ORDER BY timestamp DESC LIMIT 50;

-- Update statistics
ANALYZE;

-- Optimize database
PRAGMA optimize;

-- Check index usage
.indices messages
.indices sessions

-- Create additional indexes if needed
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);
```

---

## Monitoring & Debugging

### Enable Debug Logging

```bash
# Set debug logging
export LOG_LEVEL=DEBUG

# Start server with verbose logging
DEBUG=1 uv run python -m shared_context_server.scripts.dev

# Log to file
uv run python -m shared_context_server.scripts.dev 2>&1 | tee server.log

# Monitor logs in real-time
tail -f server.log | grep -E "(ERROR|WARNING|DEBUG)"
```

### Performance Monitoring Setup

**Real-time monitoring script:**
```python
import asyncio
import httpx
import time
import json
from datetime import datetime

async def monitor_server():
    """Continuous server monitoring."""

    admin_token = "your-admin-token"  # Get from authentication

    while True:
        try:
            async with httpx.AsyncClient() as client:
                # Get performance metrics
                response = await client.post(
                    "http://localhost:23456/mcp/tool/get_performance_metrics",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    metrics = response.json()

                    # Extract key metrics
                    db_stats = metrics["database_performance"]["connection_stats"]
                    pool_stats = metrics["database_performance"]["pool_stats"]

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Queries: {db_stats['total_queries']}, "
                          f"Avg: {db_stats['avg_query_time']:.1f}ms, "
                          f"Pool: {pool_stats['pool_utilization']*100:.1f}%")

                    # Alert on performance issues
                    if db_stats['avg_query_time'] > 100:
                        print("⚠️  WARNING: High query latency detected!")

                    if pool_stats['pool_utilization'] > 0.8:
                        print("⚠️  WARNING: High pool utilization!")

                else:
                    print(f"❌ Health check failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Monitoring error: {e}")

        await asyncio.sleep(30)  # Check every 30 seconds

# Run monitoring
if __name__ == "__main__":
    asyncio.run(monitor_server())
```

### Debug Client Connections

**Test client connectivity:**
```python
import asyncio
import httpx
import json

async def debug_client_connection():
    """Debug client connection issues."""

    base_url = "http://localhost:23456"

    # Test 1: Basic connectivity
    print("Testing basic connectivity...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            print(f"✅ Health check: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connectivity failed: {e}")
        return

    # Test 2: Authentication
    print("\nTesting authentication...")
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.post(
                f"{base_url}/mcp/tool/authenticate_agent",
                json={
                    "agent_id": "debug-client",
                    "agent_type": "debug",
                    "api_key": "your-api-key"
                }
            )
            auth_data = auth_response.json()

            if auth_data.get("success"):
                print("✅ Authentication successful")
                token = auth_data["token"]
                print(f"   Token received: {token[:20]}...")
            else:
                print(f"❌ Authentication failed: {auth_data}")
                return

    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return

    # Test 3: Session operations
    print("\nTesting session operations...")
    try:
        async with httpx.AsyncClient() as client:
            # Create session
            session_response = await client.post(
                f"{base_url}/mcp/tool/create_session",
                headers={"Authorization": f"Bearer {token}"},
                json={"purpose": "Debug session"}
            )

            session_data = session_response.json()
            if session_data.get("success"):
                session_id = session_data["session_id"]
                print(f"✅ Session created: {session_id}")

                # Add message
                msg_response = await client.post(
                    f"{base_url}/mcp/tool/add_message",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "session_id": session_id,
                        "content": "Debug message",
                        "visibility": "public"
                    }
                )

                msg_data = msg_response.json()
                if msg_data.get("success"):
                    print(f"✅ Message added: ID {msg_data['message_id']}")
                else:
                    print(f"❌ Message failed: {msg_data}")

            else:
                print(f"❌ Session creation failed: {session_data}")

    except Exception as e:
        print(f"❌ Session operation error: {e}")

# Run debug
asyncio.run(debug_client_connection())
```

### Database Debug Queries

**Useful debug queries:**
```sql
-- Check table sizes
SELECT
    'sessions' as table_name,
    COUNT(*) as row_count,
    MAX(created_at) as latest_entry
FROM sessions
UNION ALL
SELECT
    'messages' as table_name,
    COUNT(*) as row_count,
    MAX(timestamp) as latest_entry
FROM messages
UNION ALL
SELECT
    'agent_memory' as table_name,
    COUNT(*) as row_count,
    MAX(created_at) as latest_entry
FROM agent_memory;

-- Check for orphaned messages (messages without sessions)
SELECT COUNT(*) as orphaned_messages
FROM messages m
LEFT JOIN sessions s ON m.session_id = s.id
WHERE s.id IS NULL;

-- Top sessions by message count
SELECT
    s.id,
    s.purpose,
    COUNT(m.id) as message_count,
    s.created_at
FROM sessions s
LEFT JOIN messages m ON s.id = m.session_id
GROUP BY s.id
ORDER BY message_count DESC
LIMIT 10;

-- Recent activity
SELECT
    m.session_id,
    m.sender,
    m.content,
    m.timestamp
FROM messages m
ORDER BY m.timestamp DESC
LIMIT 20;
```

---

## Emergency Recovery Procedures

### Server Crash Recovery

**If server crashes unexpectedly:**

1. **Identify the Issue:**
```bash
# Check logs
tail -100 server.log | grep -i error

# Check process status
ps aux | grep shared_context_server

# Check system resources
df -h  # Disk space
free -h  # Memory
```

2. **Safe Restart:**
```bash
# Kill any zombie processes
pkill -f shared_context_server

# Check database integrity
sqlite3 chat_history.db "PRAGMA integrity_check;"

# Restart with debug logging
LOG_LEVEL=DEBUG uv run python -m shared_context_server.scripts.dev
```

3. **Data Recovery:**
```bash
# If database is corrupted
sqlite3 chat_history.db ".backup backup_$(date +%Y%m%d_%H%M%S).db"
sqlite3 chat_history.db ".recover" | sqlite3 recovered.db
mv recovered.db chat_history.db
```

### Complete System Reset

**If all else fails, reset to clean state:**

```bash
# 1. Backup important data
mkdir -p backup/$(date +%Y%m%d_%H%M%S)
cp chat_history.db backup/$(date +%Y%m%d_%H%M%S)/
cp .env backup/$(date +%Y%m%d_%H%M%S)/

# 2. Clean installation
rm -rf .venv
rm chat_history.db*
uv venv
uv sync --all-extras

# 3. Reset database
uv run python -c "
from shared_context_server.database import initialize_database
import asyncio
asyncio.run(initialize_database())
print('Database initialized')
"

# 4. Test basic functionality
uv run python -m shared_context_server.scripts.dev --validate

# 5. Restart server
MCP_TRANSPORT=http uv run python -m shared_context_server.scripts.dev
```

---

## Getting Help

### Support Channels

1. **GitHub Issues**: Report bugs and feature requests
2. **Documentation**: Check latest docs at `/docs/`
3. **Community**: Join discussions and get help

### Information to Provide

When seeking help, include:

```bash
# System information
uv --version
python --version
cat /etc/os-release

# Server status
curl -f http://localhost:23456/health

# Recent logs (last 50 lines)
tail -50 server.log

# Configuration (sanitized - remove API keys!)
env | grep -E "(DATABASE|LOG|API)" | sed 's/=.*/=REDACTED/'

# Error details with full stack trace
# Include exact error messages and reproduction steps
```

### Self-Diagnosis Checklist

Before seeking help, verify:

- [ ] Server is running and accessible
- [ ] Environment variables are set correctly
- [ ] Database file has proper permissions
- [ ] API keys are valid and not expired
- [ ] Network connectivity is working
- [ ] Dependencies are installed and up-to-date
- [ ] No conflicting processes on the port
- [ ] Sufficient disk space and memory available

---

For additional resources:
- [API Reference](./api-reference.md) - Complete tool documentation
- [Integration Guide](./integration-guide.md) - Framework-specific examples
- [Performance Guide](./performance-guide.md) - Optimization tips
