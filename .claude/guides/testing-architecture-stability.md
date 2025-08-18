# Testing Architecture & Stability

Technical patterns for reliable test suites and dependency management.

## Architecture Patterns

### Preferred: Dependency Injection
**Use for all new code.**

Benefits:
- Zero global state
- Perfect test isolation
- Thread safety by design
- Easy mocking
- Explicit contracts

### Implementation Pattern

```python
from dataclasses import dataclass
from typing import Protocol
from contextvars import ContextVar

class TokenManager(Protocol):
    def create_token(self, agent_id: str, agent_type: str) -> str: ...
    def validate_token(self, token: str) -> dict: ...

@dataclass
class AuthenticationService:
    token_manager: TokenManager

    def authenticate_agent(self, agent_id: str, agent_type: str) -> dict:
        token = self.token_manager.create_token(agent_id, agent_type)
        return {"token": token, "agent_id": agent_id}

# Context-based injection for web frameworks
_auth_service_context: ContextVar[AuthenticationService | None] = ContextVar(
    'auth_service', default=None
)

def get_auth_service() -> AuthenticationService:
    service = _auth_service_context.get()
    if service is None:
        token_manager = SecureTokenManager()
        service = AuthenticationService(token_manager)
        _auth_service_context.set(service)
    return service

def set_auth_service(service: AuthenticationService) -> None:
    _auth_service_context.set(service)
```

### Test Pattern

```python
class TestAuthenticationService:

    def test_authenticate_agent_success(self):
        mock_token_manager = Mock(spec=TokenManager)
        mock_token_manager.create_token.return_value = "test_token_123"

        auth_service = AuthenticationService(mock_token_manager)
        result = auth_service.authenticate_agent("agent_1", "claude")

        assert result["token"] == "test_token_123"
        assert result["agent_id"] == "agent_1"
        mock_token_manager.create_token.assert_called_once_with("agent_1", "claude")

    def test_authenticate_agent_integration(self):
        test_service = AuthenticationService(TestTokenManager())
        set_auth_service(test_service)

        result = test_authentication_endpoint()
        assert result.success
```

## Legacy Pattern (Existing Code Only)

### Enhanced Singleton Pattern

```python
class SecureTokenManager:
    _instance: Optional['SecureTokenManager'] = None
    _lock = Lock()
    _test_mode: bool = False

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._instance = None

    @classmethod
    def enable_test_mode(cls):
        cls._test_mode = True
        cls.reset()

def test_legacy_authentication(self):
    from shared_context_server.auth_secure import reset_secure_token_manager

    reset_secure_token_manager()

    with patch.dict(os.environ, {
        "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
        "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
    }, clear=False):
        reset_secure_token_manager()

        result = authenticate_agent("test_agent", "claude")
        assert result.success
```

## Migration Strategy

- **New code**: Use dependency injection
- **Existing code**: Enhanced Singleton until migration
- **Goal**: Remove global state entirely

## Development Standards

### New Code
```python
# ✅ DO: Use dependency injection
class FeatureService:
    def __init__(self, database: Database, cache: Cache):
        self.database = database
        self.cache = cache

# ❌ DON'T: Create global singletons
feature_service = None  # FORBIDDEN

def get_feature_service():  # ANTI-PATTERN
    global feature_service
    if feature_service is None:
        feature_service = FeatureService()
    return feature_service
```

### Existing Code
```python
# ✅ DO: Reset singletons in tests
def test_existing_feature(self):
    reset_feature_singleton()
    # test logic

# ❌ DON'T: Skip singleton reset
def test_existing_feature_bad(self):
    result = existing_singleton_feature()  # Will cause random failures
```

## Test Organization

### Pytest Markers
```python
# Architecture
@pytest.mark.singleton
@pytest.mark.auth
@pytest.mark.security
@pytest.mark.isolation

# Features
@pytest.mark.core
@pytest.mark.tools
@pytest.mark.websocket
@pytest.mark.search

# Quality
@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.edge_case
@pytest.mark.integration
@pytest.mark.behavioral
@pytest.mark.performance
@pytest.mark.slow
```

### Execution
```bash
pytest -m "singleton and not slow" -v
pytest -m "auth and integration" -v
pytest -m "core and not edge_case" -v
pytest -m "smoke" -v
```

### Directory Structure
```
tests/
├── unit/                    # Pure unit tests
├── integration/            # Component integration
├── behavioral/             # End-to-end scenarios
├── fixtures/               # Shared test utilities
└── legacy/                 # Legacy singleton tests
```

## Anti-Patterns

### Forbidden: New Global Singletons
```python
# NEVER DO THIS
global_service = None

def get_global_service():
    global global_service
    if global_service is None:
        global_service = SomeService()
    return global_service
```

### Forbidden: Missing Singleton Resets
```python
# NEVER DO THIS
def test_without_reset(self):
    result = existing_singleton_method()  # Will cause random failures
    assert result.success
```

### Forbidden: Environment Pollution
```python
# NEVER DO THIS
def test_bad_environment(self):
    os.environ["SECRET_KEY"] = "test"
    # No cleanup - affects other tests
```

## Automated Validation

### Pre-Commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: singleton-patterns
        name: Validate singleton testing patterns
        entry: python3 scripts/validate_singleton_patterns.py
        files: '^tests/.*\.py$'

      - id: dependency-injection-check
        name: Prevent new global singletons
        entry: python3 scripts/check_dependency_injection.py
        files: '^src/.*\.py$'
```

### Validation Script
```python
# scripts/check_dependency_injection.py
import ast
import sys

def check_for_global_singletons(file_path):
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('get_'):
            for child in ast.walk(node):
                if isinstance(child, ast.Global):
                    violations.append(f"Line {node.lineno}: Singleton pattern in {node.name}")
    return violations

if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        violations = check_for_global_singletons(file_path)
        if violations:
            print(f"❌ {file_path}:")
            for violation in violations:
                print(f"  {violation}")
            sys.exit(1)
    print("✅ No singleton anti-patterns detected")
```

## Success Metrics

- Test reliability: >95% pass rate
- Development velocity: 80% feature work, 20% test maintenance
- Zero state pollution between tests
- Thread-safe concurrent execution
- New code: 100% dependency injection usage
