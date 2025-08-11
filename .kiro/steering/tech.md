# Technology Stack & Build System

## Core Framework: FastMCP

**Primary Framework**: FastMCP - Most Pythonic MCP implementation
- Native async/await support with 5-50x performance improvement over v1
- Built-in Pydantic v2 validation with automatic request/response validation
- In-memory testing capabilities (100x faster than subprocess testing)
- Minimal boilerplate code with production-ready features

## Database & Performance

### Database Stack
- **Primary**: SQLite with WAL (Write-Ahead Logging) mode
- **Connection Pooling**: aiosqlitepool (2-20 connections, significant performance gains)
- **Performance**: <10ms session creation, <20ms message ops, <30ms queries
- **Concurrency**: 20+ concurrent agents with no reader blocking

### Critical SQLite Configuration
```sql
PRAGMA journal_mode = WAL;           -- Enable concurrent reads/writes
PRAGMA synchronous = NORMAL;         -- Balance performance and safety
PRAGMA cache_size = -8000;           -- 8MB cache
PRAGMA temp_store = MEMORY;          -- Use memory for temp tables
PRAGMA mmap_size = 30000000000;      -- Memory-mapped I/O
PRAGMA busy_timeout = 5000;          -- 5 second timeout
PRAGMA optimize;                     -- Enable query optimizer
```

### Search Performance
- **RapidFuzz**: 5-10x faster than Python's difflib for fuzzy string matching
- **Performance**: 1000 messages in ~50ms, 10000 messages in ~500ms
- **API**: Drop-in replacement with better memory usage

## Key Dependencies

### Core Runtime
```toml
dependencies = [
    "fastmcp>=2.0.0",           # MCP server framework
    "aiosqlite>=0.19.0",        # Async SQLite
    "aiosqlitepool",            # Connection pooling
    "rapidfuzz>=3.0.0",         # Fast fuzzy search
    "pydantic>=2.0.0",          # Data validation
    "pydantic-settings>=2.0.0", # Configuration management
    "python-dotenv>=1.0.0",     # Environment variables
    "httpx>=0.25.0",            # HTTP client
    "fastapi>=0.100.0",         # Web framework
    "uvicorn[standard]>=0.23.0", # ASGI server
    "watchdog>=6.0.0",          # File watching for hot reload
    "PyJWT>=2.8.0",             # JWT authentication
]
```

### Development Tools
```toml
dev = [
    "pytest>=7.0.0",           # Testing framework
    "pytest-asyncio>=0.21.0",  # Async test support
    "pytest-cov>=4.0.0",       # Coverage reporting
    "ruff>=0.1.0",             # Linting and formatting
    "mypy>=1.0.0",             # Type checking
    "pre-commit>=3.0.0",       # Git hooks
]
```

## Build System: UV Package Manager

**Package Manager**: UV (modern Python package manager)
- **Installation**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Dependency Management**: `uv sync` (installs all dependencies)
- **Virtual Environment**: Automatic venv management
- **Performance**: Significantly faster than pip

### Common Commands

#### Development
```bash
# Install dependencies
uv sync

# Start development server with hot reload
MCP_TRANSPORT=http HTTP_PORT=23456 uv run python -m shared_context_server.scripts.dev

# Run with specific environment
MCP_TRANSPORT=http uv run python -m shared_context_server.scripts.dev
```

#### Code Quality
```bash
# Linting and formatting
uv run ruff check .         # Check for issues
uv run ruff format .        # Format code
uv run mypy src/            # Type checking

# Testing
uv run pytest tests/        # Run all tests
uv run pytest --cov=src    # With coverage
uv run pytest -m "not slow" # Skip slow tests

# Quality gates (run all)
uv run ruff check . && uv run mypy . && uv run pytest
```

#### Validation and Info
```bash
# Server validation
uv run python -m shared_context_server.scripts.dev --validate
uv run python -m shared_context_server.scripts.dev --info
```

## Architecture Patterns

### MCP Tool Implementation Pattern
```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(name="shared-context-server", version="1.0.0")

@mcp.tool()
async def create_session(
    purpose: str = Field(description="Purpose of the session"),
    metadata: Optional[Dict[str, Any]] = Field(default=None)
) -> Dict[str, Any]:
    """Create a new shared context session."""
    # Implementation with connection pooling
    async with db_pool.acquire() as conn:
        # Database operations
        pass
```

### Database Connection Pattern
```python
# Global connection pool
db_pool = await aiosqlitepool.create_pool(
    database_path,
    min_size=2,
    max_size=20,
    check_same_thread=False
)

# Usage pattern
async with db_pool.acquire() as conn:
    conn.row_factory = aiosqlite.Row  # Enable dict-like access
    cursor = await conn.execute(query, params)
    results = await cursor.fetchall()
```

### Error Handling Pattern
```python
from enum import Enum

class ErrorCode(str, Enum):
    AUTHENTICATION_FAILED = "AUTH_001"
    SESSION_NOT_FOUND = "RESOURCE_001"
    INVALID_INPUT = "VALIDATION_001"

class SharedContextError(Exception):
    def __init__(self, message: str, code: ErrorCode, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
```

## Configuration Management

### Environment Configuration
- **Primary**: `.env` file with python-dotenv
- **Validation**: Pydantic BaseSettings with type checking
- **Structure**: Hierarchical config sections (database, security, operational)

### Key Environment Variables
```bash
# Database
DATABASE_PATH=./chat_history.db
DATABASE_MAX_CONNECTIONS=20

# Server
MCP_TRANSPORT=http
HTTP_PORT=23456

# Security (REQUIRED)
API_KEY=your-secure-api-key-replace-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key

# Performance
LOG_LEVEL=INFO
ENABLE_PERFORMANCE_MONITORING=true
```

## Testing Infrastructure

### Testing Stack
- **Framework**: pytest with asyncio support
- **Database**: Real SQLite databases (not mocks) for better fidelity
- **MCP Testing**: FastMCP TestClient for in-memory testing (100x faster)
- **Coverage**: pytest-cov with 85%+ target coverage

### Testing Patterns
```python
# Modern database testing (recommended)
@pytest.fixture
async def test_db_manager():
    """Create isolated test database with real schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        temp_db_path = temp_db.name

    db_manager = DatabaseManager(f"sqlite:///{temp_db_path}")
    await db_manager.initialize()
    yield db_manager

    Path(temp_db_path).unlink(missing_ok=True)

# FastMCP tool testing
async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """Helper to call FastMCP tools with proper default handling."""
    defaults = extract_field_defaults(fastmcp_tool)
    call_args = {**defaults, **kwargs}
    return await fastmcp_tool.fn(ctx, **call_args)
```

## Performance Optimizations

### Critical Performance Features
1. **Connection Pooling**: 5-10x improvement for concurrent access
2. **RapidFuzz Search**: 5-10x faster than difflib
3. **Multi-level Caching**: 10-100x faster for hot data
4. **SQLite WAL Mode**: Enables concurrent reads/writes
5. **Async/Await**: Non-blocking operations throughout

### Monitoring
```python
# Performance monitoring decorator
@monitor.track_time("operation_name")
async def operation():
    pass

# Cache performance
cache_stats = cache.get_stats()  # Hit rate, size, etc.
```

## Security Implementation

### Authentication
- **JWT Tokens**: With MCP audience validation to prevent token reuse
- **API Keys**: Environment-based with validation
- **Rate Limiting**: Per-endpoint and per-agent limits

### Input Validation
- **Pydantic Models**: Automatic validation with custom sanitizers
- **SQL Injection Prevention**: Parameterized queries only
- **XSS Protection**: HTML escaping and content sanitization

## Deployment

### Development
```bash
# Hot reload server
MCP_TRANSPORT=http HTTP_PORT=8000 uv run python -m shared_context_server.scripts.dev

# Claude Code integration
claude mcp add-json shared-context-server '{"command": "mcp-proxy", "args": ["--transport=streamablehttp", "http://localhost:8000/mcp/"]}'
```

### Production
- **Transport**: HTTP for remote access
- **Database**: SQLite with WAL mode and connection pooling
- **Monitoring**: Performance metrics, health checks, audit logging
- **Security**: JWT authentication, rate limiting, security headers

## Code Quality Standards

### Linting: Ruff Configuration
```toml
[tool.ruff]
line-length = 88
target-version = "py39"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM", "TCH", "PTH", "ERA", "RET", "TRY", "PERF"]
```

### Type Checking: MyPy
```toml
[tool.mypy]
python_version = "3.10"
disallow_untyped_defs = true
warn_return_any = true
strict_equality = true
```

### Testing: Pytest Configuration
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = ["-ra", "--strict-markers", "-v", "--tb=short"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "performance: marks tests as performance tests"
]
```
