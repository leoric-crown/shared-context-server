# Test Organization & Categorization

This document describes the test organization strategy for the shared context server, including directory structure, test markers, and execution patterns.

## Directory Structure

```
tests/
├── unit/                    # Pure unit tests - isolated component testing
│   ├── test_auth_*.py      # Authentication & authorization tests
│   ├── test_database_*.py  # Database layer tests
│   ├── test_server_*.py    # Server functionality tests
│   ├── test_models_*.py    # Data model validation tests
│   └── test_singleton_*.py # Singleton lifecycle tests
├── integration/             # Multi-component integration tests
│   ├── test_agent_*.py     # Agent workflow integration
│   └── test_api_*.py       # API contract validation
├── behavioral/              # End-to-end user scenarios
│   ├── test_database_*.py  # Database behavior validation
│   ├── test_websocket_*.py # WebSocket integration scenarios
│   └── test_phase*.py      # Phase validation tests
├── performance/             # Performance benchmarks & regression tests
│   ├── test_performance_*.py    # Performance target validation
│   └── test_rapidfuzz_*.py      # Search optimization tests
├── security/                # Security validation & penetration tests
│   ├── test_auth_*.py      # Authentication security
│   ├── test_jwt_*.py       # JWT hardening validation
│   └── test_message_*.py   # Message visibility controls
└── fixtures/                # Shared test infrastructure
    └── database.py         # Database test utilities
```

## Test Markers

Use pytest markers to categorize tests for selective execution:

### Test Types
- `@pytest.mark.unit` - Pure isolation tests, no external dependencies
- `@pytest.mark.integration` - Multi-component interaction tests
- `@pytest.mark.behavioral` - End-to-end user scenarios
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.security` - Security validation tests

### Architecture & Lifecycle
- `@pytest.mark.singleton` - Singleton pattern validation
- `@pytest.mark.auth` - Authentication & authorization
- `@pytest.mark.isolation` - Test isolation patterns
- `@pytest.mark.database` - Database access required

### Feature Areas
- `@pytest.mark.core` - Core server functionality
- `@pytest.mark.tools` - MCP tools implementation
- `@pytest.mark.websocket` - WebSocket functionality
- `@pytest.mark.search` - Search & context functionality
- `@pytest.mark.memory` - Memory operations

### Quality Assurance
- `@pytest.mark.smoke` - Basic smoke tests
- `@pytest.mark.regression` - Regression prevention
- `@pytest.mark.edge_case` - Edge cases & error conditions
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.flaky` - Potentially unstable tests

### Backend Specific
- `@pytest.mark.sqlalchemy` - SQLAlchemy backend (now the only backend)
- `@pytest.mark.database` - Database functionality tests

## Test Execution Patterns

### Quick Development Feedback
```bash
# Smoke tests only - fastest feedback
pytest -m smoke -v

# Unit tests only - fast isolation validation
pytest -m unit -v

# Authentication tests - specific feature area
pytest -m auth -v

# Non-slow tests - reasonable development cycle
pytest -m "not slow" -v
```

### Feature Development
```bash
# Test specific feature area during development
pytest -m "core and not slow" -v           # Core functionality
pytest -m "tools and unit" -v              # MCP tools unit tests
pytest -m "websocket and integration" -v   # WebSocket integration

# Test database functionality
pytest -m "database and unit" -v --tb=short
```

### Quality Assurance
```bash
# Full test suite - CI/CD validation
pytest tests/ -v

# Security validation
pytest -m security -v

# Performance regression check
pytest -m performance -v

# Singleton lifecycle validation
pytest -m singleton -v
```

### Debugging & Investigation
```bash
# Test isolation issues
pytest -m "isolation or singleton" -v

# Authentication problems
pytest -m "auth and not slow" -v --tb=long

# Edge case investigation
pytest -m edge_case -v -s
```

## Adding Markers to Tests

### File-Level Markers (Recommended)
```python
# tests/unit/test_example.py
import pytest

# Apply to all tests in the file
pytestmark = [
    pytest.mark.unit,
    pytest.mark.auth,
    pytest.mark.core,
]

class TestExample:
    def test_functionality(self):
        pass
```

### Individual Test Markers
```python
# For tests that need specific markers
@pytest.mark.slow
@pytest.mark.edge_case
def test_complex_scenario(self):
    pass
```

### Class-Level Markers
```python
@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    def test_workflow_a(self):
        pass
    def test_workflow_b(self):
        pass
```

## Test Architecture Best Practices

### 1. Singleton Test Isolation
Always include singleton reset for authentication tests:
```python
async def test_auth_functionality(self):
    # ... test logic
```

### 2. Database Testing
Use SQLAlchemy backend for all database operations:
```python
@pytest.mark.database
async def test_database_operation(self, test_db_manager):
    # All tests use SQLAlchemy backend (aiosqlite backend removed)
    with patch_database_connection(test_db_manager):
        # ... test logic
```

### 3. Environment Isolation
Isolate environment variables:
```python
@pytest.mark.auth
async def test_with_clean_environment(self):
    with patch.dict(os.environ, {
        "JWT_SECRET_KEY": "test-key",
        "JWT_ENCRYPTION_KEY": "test-encryption-key",
    }, clear=False):
        # ... test logic
```

## Continuous Integration

### Test Matrix
The CI system runs tests with different configurations:
- **Database Backend**: SQLAlchemy (single backend)
- **Python Versions**: 3.11, 3.12
- **Parallel Execution**: Auto-detected CPU cores
- **Coverage Target**: 84%+

### Quality Gates
1. **Smoke Tests** (30 seconds) - Basic functionality
2. **Unit Tests** (2 minutes) - Component isolation
3. **Integration Tests** (5 minutes) - Multi-component workflows
4. **Full Test Suite** (10 minutes) - Complete validation

### Failure Investigation
1. Check test markers - identify specific test category
2. Run individual test for isolation - `pytest path/to/test.py::test_name -v`
3. Check singleton state - authentication tests often have isolation issues
4. Validate environment variables - missing JWT keys cause auth failures

## Performance Targets

- **Individual Tests**: <30ms average execution
- **Unit Test Suite**: <2 minutes total
- **Full Test Suite**: <10 minutes total
- **Singleton Reset Overhead**: <1ms per test
- **Parallel Efficiency**: 80%+ CPU utilization

## Migration Guidance

When adding new tests:
1. **Choose appropriate directory** based on test scope
2. **Add relevant markers** for categorization
3. **Follow singleton patterns** for authentication tests
4. **Use SQLAlchemy backend** for all database-related tests
5. **Document edge cases** with descriptive test names

This categorization system enables precise test execution, faster development cycles, and reliable CI/CD validation.
