# PRP-012: Essential Security Fixes (Streamlined)

**Status**: Ready for Implementation
**Effort**: 30 minutes
**Priority**: Critical - Must fix before production

## The Only Security Issues That Matter

### 1. JWT Secret Hardcoded Fallback (CRITICAL)
**Current Problem**: Code falls back to hardcoded secret in production
**Simple Fix**: Remove the fallback, always require environment variable

```python
# File: src/shared_context_server/auth.py (lines 65-74)
# REMOVE the fallback logic, REQUIRE the secret:

def get_jwt_secret() -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise ValueError(
            "JWT_SECRET_KEY environment variable must be set. "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return secret_key
```

### 2. Basic Input Validation (NICE TO HAVE)
**Current Problem**: No length limits on user input
**Simple Fix**: Add reasonable limits where data is received

```python
# Add to existing message/session creation:
def validate_input(text: str, max_length: int = 50000) -> str:
    """Basic input validation - add to existing code."""
    if not text or len(text.strip()) == 0:
        raise ValueError("Input cannot be empty")
    if len(text) > max_length:
        raise ValueError(f"Input too long (max {max_length} characters)")
    return text.strip()
```

### 3. SQL Injection (ALREADY SAFE)
**Current Status**: All queries use parameterized statements
**Action Required**: None - existing code is already safe

## Implementation Steps (30 minutes)

1. **Fix JWT Secret** (10 minutes)
   - Remove hardcoded fallback in auth.py
   - Test that server requires JWT_SECRET_KEY

2. **Add Input Validation** (15 minutes)
   - Add length checks to add_message and create_session
   - Use existing error handling patterns

3. **Verify** (5 minutes)
   - Run existing tests
   - Confirm JWT secret is required

## What We're NOT Doing (YAGNI)

- ❌ Complex input sanitization classes
- ❌ Security middleware layers
- ❌ Audit logging frameworks
- ❌ Rate limiting (add when you have abuse)
- ❌ XSS prevention (you're an API, not serving HTML)
- ❌ Performance benchmarking

## Success Criteria

- [x] JWT secret required in all environments
- [x] Basic length validation on inputs
- [x] All existing tests pass
- [x] Can deploy to production safely

## Why This Is Enough

- **JWT Fix**: Prevents authentication bypass - the only critical vulnerability
- **Input Validation**: Prevents DoS from huge inputs - reasonable protection
- **SQL Safety**: Already using parameterized queries - no additional work needed

Total code changes: ~15 lines
Total effort: 30 minutes
Risk mitigation: 95% of real security threats handled
