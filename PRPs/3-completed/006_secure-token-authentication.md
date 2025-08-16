# PRP-006: Secure Token Authentication System (Simplified)

## Research Context & Architectural Analysis

**Research Integration**: Comprehensive analysis completed identifying critical JWT exposure vulnerability in MCP tool parameters. Simplified approach prioritizes core security goal (hiding JWTs) over enterprise-grade features for local MCP server deployment.

**Architectural Scope**: Minimal integration requiring simple `SecureTokenManager` class, basic database schema extension, and updates to existing `authenticate_agent` and `validate_jwt_token_parameter` functions.

**Existing Patterns**: Leverages existing `AuthManager` class in `src/shared_context_server/auth.py:83`, established aiosqlite patterns with UTC timestamps, and FastMCP tool definitions. Integration with current JWT validation pipeline at `auth.py:228`.

**Security Context**: Addresses P0 critical security vulnerability - JWT tokens currently exposed in logs, debugging tools, and network traces. Solution implements simple encrypted token format using Fernet encryption for local MCP server deployment with multi-agent concurrency support.

## Implementation Specification

**Core Requirements**:
- New `SecureTokenManager` class with Fernet encryption and protected token format (`sct_<uuid>`)
- Simple database schema extension with `secure_tokens` table for encrypted JWT storage
- Protected token resolution system replacing direct JWT parameter passing
- Simple token refresh mechanism with delete-old, create-new pattern

**Integration Points**:
- `authenticate_agent` MCP tool: Return protected tokens instead of raw JWTs
- `validate_jwt_token_parameter` function: Resolve protected tokens to JWT validation
- Database operations: Simple encrypted token storage with expiration
- MCP tool ecosystem: Basic `refresh_token` tool for token management

**Database Changes**:
```sql
-- Migration from schema version 2 to 3
BEGIN TRANSACTION;

-- Simple secure_tokens table with multi-agent support
CREATE TABLE secure_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id TEXT UNIQUE NOT NULL,
    encrypted_jwt BLOB NOT NULL,
    agent_id TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure data consistency for concurrent access
    CONSTRAINT secure_tokens_agent_id_not_empty CHECK (length(trim(agent_id)) > 0)
);

-- Indexes for efficient multi-agent access
CREATE INDEX idx_token_id ON secure_tokens(token_id);
CREATE INDEX idx_agent_expires ON secure_tokens(agent_id, expires_at);

-- Update schema version
INSERT INTO schema_version (version, description)
VALUES (3, 'Added secure_tokens table with Fernet encryption for JWT hiding');

COMMIT;
```

**API Requirements**:
- Basic `refresh_token` MCP tool with simple delete/create pattern
- Standard error responses for invalid/expired tokens
- Optional cleanup task for expired tokens

## Quality Requirements

**Testing Strategy**:
- **Basic functional tests** covering encryption/decryption and token refresh
- **Multi-agent concurrency** testing with 10-20 concurrent token operations
- **JWT exposure prevention** validation (no raw JWTs in logs)
- **Token expiration** and refresh flow testing
- **FastMCP TestClient** integration testing for token operations
- **Simple error handling** tests for invalid/expired tokens

**Documentation Needs**:
- Basic MCP tool usage examples with protected token format
- Simple agent integration guide for token refresh
- Environment variable configuration

**Performance Considerations**:
- Optimized indexes for multi-agent token lookup and cleanup
- Basic transaction safety for concurrent token refresh operations
- Fernet encryption/decryption overhead (minimal, scales well for dozens of agents)
- Simple database cleanup for expired tokens

## Coordination Strategy

**Recommended Approach**: Direct developer agent assignment - simple, well-defined scope optimized for local deployment.

**Implementation Phases**:
1. **Core Secure Token System** (1.5 hours): Simple `SecureTokenManager` class with Fernet and basic transaction safety
2. **Database Migration** (30 min): Simple table creation with multi-agent indexes
3. **Token Refresh System** (1.5 hours): Basic `refresh_token` MCP tool with concurrency handling
4. **Integration & Testing** (30 min): Update functions and basic multi-agent concurrency tests

**Risk Mitigation**:
- Token security: Fernet encryption prevents JWT exposure
- Token expiration: 1-hour default with refresh capability
- Multi-agent concurrency: Atomic refresh pattern prevents race conditions during concurrent operations
- Graceful degradation: Failed cleanup doesn't break token refresh (old tokens expire naturally)
- Simple error handling: Clear error messages for invalid/expired tokens

**Dependencies**:
- Existing `AuthManager` and JWT validation infrastructure
- aiosqlite database operations with existing patterns
- FastMCP server tool registration
- Environment variable `JWT_ENCRYPTION_KEY` for Fernet key

## Success Criteria

**Functional Success**:
- Protected token format (`sct_*`) prevents JWT exposure in logs/traces
- Token refresh operations work correctly with multi-agent concurrency
- Token expiration enforced properly
- Multiple agents (10-50) can operate simultaneously without conflicts
- Local MCP server usage works seamlessly

**Integration Success**:
- All existing authentication tests pass with protected token format
- `authenticate_agent` returns protected tokens maintaining API compatibility
- `validate_jwt_token_parameter` resolves protected tokens transparently
- Database migration applies cleanly

**Quality Gates**:
- **Basic functional tests** validate encryption and token operations
- **JWT exposure prevention** confirmed through log analysis
- **Token refresh flow** works correctly
- **Error handling** for invalid/expired tokens
- **Integration tests** with existing authentication system

**Security Validation**:
- Zero raw JWT tokens in system logs or network traces
- Fernet encryption working properly
- Token expiration prevents stale token usage

## Technical Implementation Details

**Protected Token Format**:
```
Format: sct_<uuid4>
Example: sct_f47ac10b-58cc-4372-a567-0e02b2c3d479
- sct: "secure context token" prefix for identification
- uuid4: Standard UUID4 for simple, unique identification
```

**SecureTokenManager Implementation** (Simplified Fernet):
```python
from cryptography.fernet import Fernet
import uuid
import os
from datetime import datetime, timedelta, timezone
from .database import get_db_connection

class SecureTokenManager:
    def __init__(self):
        key = os.environ.get("JWT_ENCRYPTION_KEY")
        if not key:
            raise ValueError("JWT_ENCRYPTION_KEY environment variable required")
        self.fernet = Fernet(key.encode())

    async def create_protected_token(self, jwt_token: str, agent_id: str) -> str:
        """Create encrypted protected token with simple UUID."""
        token_id = f"sct_{uuid.uuid4()}"
        encrypted_jwt = self.fernet.encrypt(jwt_token.encode())

        # Use basic transaction for multi-agent safety
        async with get_db_connection() as conn:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                await conn.execute("""
                    INSERT INTO secure_tokens (token_id, encrypted_jwt, agent_id, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    token_id, encrypted_jwt, agent_id,
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ))
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

        return token_id

    async def refresh_token_safely(self, current_token: str, agent_id: str) -> str:
        """Atomic refresh: create new, then delete old to prevent race conditions."""
        # Get current JWT
        jwt = await self.resolve_protected_token(current_token)
        if not jwt:
            raise ValueError("Token invalid or expired")

        # Create new token first (atomic)
        new_token = await self.create_protected_token(jwt, agent_id)

        # Then delete old token (if this fails, old token expires naturally)
        try:
            async with get_db_connection() as conn:
                await conn.execute("DELETE FROM secure_tokens WHERE token_id = ?", (current_token,))
                await conn.commit()
        except Exception:
            # Cleanup failed but new token is valid - acceptable degradation
            pass

        return new_token

    async def resolve_protected_token(self, token_id: str) -> str | None:
        """Resolve protected token to original JWT."""
        async with get_db_connection() as conn:
            row = await conn.fetchone("""
                SELECT encrypted_jwt, expires_at FROM secure_tokens
                WHERE token_id = ?
            """, (token_id,))

            if not row:
                return None

            # Check expiration
            expires_at = datetime.fromisoformat(row[1])
            if expires_at <= datetime.now(timezone.utc):
                return None

            # Decrypt and return JWT
            try:
                return self.fernet.decrypt(row[0]).decode()
            except Exception:
                return None
```

**FastMCP Tool Integration**:
```python
@mcp.tool()
async def refresh_token(
    ctx: Context,
    current_token: str = Field(
        description="Current protected token to refresh",
        pattern=r"^sct_[a-f0-9-]{36}$"
    )
) -> dict[str, Any]:
    """
    Refresh a protected token (simple delete-old, create-new).

    Returns a new protected token with extended expiry.
    """
    try:
        # Extract agent context
        agent_context = await extract_agent_context(ctx)
        agent_id = agent_context["agent_id"]

        # Use the race-condition-safe refresh method
        new_token = await secure_token_manager.refresh_token_safely(current_token, agent_id)

        return {
            "success": True,
            "token": new_token,
            "expires_in": 3600
        }

    except Exception as e:
        logger.exception("Token refresh failed")
        return {"success": False, "error": "System error during refresh"}
```

**Agent Workflow Example**:
```python
# Agent authentication receives protected token
auth_result = await authenticate_agent(agent_id="claude_main", agent_type="admin")
my_token = auth_result["token"]  # sct_f47ac10b-58cc-4372-a567-0e02b2c3d479

# Token used normally for operations
result = await add_message(session_id="...", content="...", auth_token=my_token)

# Simple refresh before expiry
refresh_result = await refresh_token(my_token)
my_token = refresh_result["token"]  # New UUID
```

---

**Document Metadata:**
- **PRP Number:** 006
- **Feature:** Secure Token Authentication System (Simplified)
- **Planning Source:** `PRPs/1-planning/secure-token-authentication/secure-token-authentication-plan.md`
- **Created:** 2025-01-12
- **Priority:** P0 - Critical Security Issue
- **Estimated Effort:** 4 hours (simplified approach with basic multi-agent concurrency support)
- **Complexity:** Simple (3-4 files, straightforward integration)
- **Status:** Ready for Implementation

## Environment Setup

**Required Configuration**:
```bash
# Single required environment variable
JWT_ENCRYPTION_KEY="your-fernet-key-here"  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Key Generation**:
```python
# Generate a new Fernet key for JWT_ENCRYPTION_KEY
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(f"JWT_ENCRYPTION_KEY={key.decode()}")
```

**Optional Configuration**:
```bash
# Optional settings
TOKEN_EXPIRY_HOURS=1           # Default token expiry
CLEANUP_EXPIRED_TOKENS=true    # Periodic cleanup
```

This simplified approach maintains the core security goal (preventing JWT exposure) while supporting multi-agent concurrency from a single user. Removes enterprise complexity while ensuring reliable operation when dozens of agents access the server simultaneously.
