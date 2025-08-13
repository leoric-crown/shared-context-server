# Security & Authentication Guide

## Overview

This guide implements comprehensive security measures for the Shared Context MCP Server - a collaborative agent workspace. Addresses critical vulnerabilities and ensures secure agent handoffs, session isolation, and collaborative workflow protection.

## Core Security Principles

### Defense in Depth
- Multiple layers of security
- Assume breach and minimize impact
- Validate at every boundary
- Audit everything

### Zero Trust Architecture
- Never trust, always verify
- Authenticate every request
- Authorize every action
- Encrypt sensitive data

## Implementation Patterns

### Pattern 1: JWT Authentication with MCP Audience Validation

**Critical Finding**: MCP authentication has known vulnerabilities requiring audience validation to prevent token reuse attacks.

```python
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")  # Must be strong, random
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30
ISSUER = "shared-context-server"
AUDIENCE = "mcp-shared-context-server"

security = HTTPBearer()

class AuthManager:
    """Authentication manager using actual patterns from auth.py."""

    @staticmethod
    def create_agent_token(
        agent_id: str,
        agent_type: str = "unknown",
        permissions: list[str] = None
    ) -> str:
        """Generate JWT token for agent authentication."""

        if not SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY not configured")

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permissions": permissions or [],
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "iss": ISSUER,
            "aud": AUDIENCE,  # CRITICAL: Prevents token reuse
            "jti": str(uuid4()),  # Unique token ID for revocation
        }

        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """Verify JWT token with comprehensive validation."""

    token = credentials.credentials

    try:
        # Decode with audience validation (CRITICAL)
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,  # Prevents cross-service token use
            issuer=ISSUER,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True,
                "require": ["exp", "iat", "aud", "iss", "agent_id"]
            }
        )

        # Additional validation
        if datetime.fromtimestamp(payload["exp"], tz=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Token expired")

        # Check if token is blacklisted (for revocation)
        if await is_token_blacklisted(payload.get("jti")):
            raise HTTPException(status_code=401, detail="Token revoked")

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

### Pattern 2: Agent Identity and Permission Management

```python
from enum import Enum
from typing import Set

class Permission(str, Enum):
    """System permissions for RBAC."""
    CREATE_SESSION = "create_session"
    READ_SESSION = "read_session"
    WRITE_SESSION = "write_session"
    DELETE_SESSION = "delete_session"
    READ_PRIVATE = "read_private"
    WRITE_PRIVATE = "write_private"
    ADMIN = "admin"

class AgentRole(str, Enum):
    """Pre-defined agent roles with permission sets."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    TESTER = "tester"
    DOCS = "docs"
    VIEWER = "viewer"

# Role-based permission mapping
ROLE_PERMISSIONS = {
    AgentRole.ADMIN: {Permission.ADMIN},  # All permissions
    AgentRole.DEVELOPER: {
        Permission.CREATE_SESSION,
        Permission.READ_SESSION,
        Permission.WRITE_SESSION,
        Permission.READ_PRIVATE,
        Permission.WRITE_PRIVATE,
    },
    AgentRole.TESTER: {
        Permission.READ_SESSION,
        Permission.WRITE_SESSION,
    },
    AgentRole.DOCS: {
        Permission.READ_SESSION,
    },
    AgentRole.VIEWER: {
        Permission.READ_SESSION,
    },
}

class AgentIdentity:
    """Secure agent identity with permission checking."""

    def __init__(self, payload: Dict[str, Any]):
        self.id = payload["agent_id"]
        self.type = payload.get("agent_type", "unknown")
        self.permissions = set(payload.get("permissions", []))
        self.session_scope = payload.get("session_scope")

        # Add role-based permissions
        role = payload.get("role")
        if role and role in ROLE_PERMISSIONS:
            self.permissions.update(ROLE_PERMISSIONS[role])

    def has_permission(self, permission: Permission) -> bool:
        """Check if agent has specific permission."""
        return permission in self.permissions or Permission.ADMIN in self.permissions

    def can_access_session(self, session_id: str) -> bool:
        """Check if agent can access specific session."""
        if self.session_scope and self.session_scope != session_id:
            return False
        return self.has_permission(Permission.READ_SESSION)

async def get_current_agent(
    token_payload: Dict = Depends(verify_token)
) -> AgentIdentity:
    """Extract and validate agent identity from token."""
    return AgentIdentity(token_payload)

# Usage in endpoints
@app.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    message: MessageModel,
    agent: AgentIdentity = Depends(get_current_agent)
):
    # Check permissions
    if not agent.has_permission(Permission.WRITE_SESSION):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not agent.can_access_session(session_id):
        raise HTTPException(status_code=403, detail="Cannot access this session")

    # Proceed with operation
    return await db.add_message(session_id, message, agent.id)
```

### Pattern 3: Input Sanitization and Validation

```python
import re
import html
from typing import Any, Dict
import bleach
from ..utils.llm_errors import (
    ErrorSeverity,
    create_llm_error_response,
    create_validation_error
)

class InputSanitizer:
    """Comprehensive input sanitization to prevent injection attacks."""

    # Allowed HTML tags (if any)
    ALLOWED_TAGS = []
    ALLOWED_ATTRIBUTES = {}

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|CREATE|ALTER)\b)",
        r"(--|\||;|\/\*|\*\/)",
        r"(\bOR\b\s*\d+\s*=\s*\d+)",
        r"(\bAND\b\s*\d+\s*=\s*\d+)",
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitize text input to prevent XSS and injection."""
        if not text:
            return text

        # HTML escape
        text = html.escape(text)

        # Remove any remaining HTML tags
        text = bleach.clean(
            text,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )

        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

        # Normalize whitespace
        text = ' '.join(text.split())

        return text.strip()

    @classmethod
    def sanitize_json(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize JSON data."""
        if isinstance(data, dict):
            return {k: cls.sanitize_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize_json(item) for item in data]
        elif isinstance(data, str):
            return cls.sanitize_text(data)
        else:
            return data

    @classmethod
    def detect_sql_injection(cls, text: str) -> bool:
        """Detect potential SQL injection attempts."""
        text_upper = text.upper()
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        return False

    @classmethod
    def validate_session_id(cls, session_id: str) -> str:
        """Validate and sanitize session ID."""
        # Only allow alphanumeric, dash, underscore
        if not re.match(r'^[a-zA-Z0-9-_]{8,64}$', session_id):
            raise create_validation_error(
                f"Invalid session ID format: {session_id}",
                field="session_id",
                received_value=session_id
            )
        return session_id

    @classmethod
    def validate_agent_id(cls, agent_id: str) -> str:
        """Validate and sanitize agent ID."""
        if not re.match(r'^[a-zA-Z0-9-_.]+$', agent_id):
            raise create_validation_error(
                f"Invalid agent ID format: {agent_id}",
                field="agent_id",
                received_value=agent_id
            )
        return agent_id

# Middleware for automatic sanitization
from fastapi import Request
from ..models import create_error_response

@app.middleware("http")
async def sanitize_inputs(request: Request, call_next):
    """Middleware to sanitize all incoming data."""

    # Sanitize path parameters
    if request.path_params:
        for key, value in request.path_params.items():
            if isinstance(value, str):
                if InputSanitizer.detect_sql_injection(value):
                    return create_error_response(
                        "Potential injection detected",
                        status_code=400,
                        error_type="security_violation"
                    )

    response = await call_next(request)
    return response
```

### Pattern 4: Rate Limiting

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

# Initialize rate limiter
async def init_rate_limiter():
    redis_client = redis.from_url(
        "redis://localhost:6379",
        encoding="utf-8",
        decode_responses=True
    )
    await FastAPILimiter.init(redis_client)

# Rate limiting configurations
RATE_LIMITS = {
    "default": {"times": 100, "seconds": 60},  # 100 requests per minute
    "auth": {"times": 5, "seconds": 60},  # 5 auth attempts per minute
    "create": {"times": 10, "seconds": 60},  # 10 creates per minute
    "search": {"times": 30, "seconds": 60},  # 30 searches per minute
}

# Apply rate limiting to endpoints
@app.post(
    "/auth/token",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))]
)
async def authenticate(credentials: AuthCredentials):
    """Rate-limited authentication endpoint."""
    return await generate_token(credentials)

@app.post(
    "/sessions",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
async def create_session(
    session: SessionModel,
    agent: AgentIdentity = Depends(get_current_agent)
):
    """Rate-limited session creation."""
    return await db.create_session(session, agent.id)

# Per-agent rate limiting
class AgentRateLimiter:
    """Rate limiter that tracks per-agent usage."""

    def __init__(self, times: int = 100, seconds: int = 60):
        self.times = times
        self.seconds = seconds
        self.cache = {}  # In production, use Redis

    async def __call__(
        self,
        agent: AgentIdentity = Depends(get_current_agent)
    ):
        key = f"rate_limit:{agent.id}"
        # Check and update rate limit
        # Implementation details...
        pass
```

### Pattern 5: Audit Logging

```python
import logging
from datetime import datetime, timezone
from typing import Optional
import json

class AuditLogger:
    """Comprehensive audit logging for security events."""

    def __init__(self):
        self.logger = logging.getLogger("audit")
        handler = logging.FileHandler("audit.log")
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_event(
        self,
        event_type: str,
        agent_id: str,
        session_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        metadata: Optional[Dict] = None
    ):
        """Log security-relevant event."""

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "session_id": session_id,
            "resource": resource,
            "action": action,
            "result": result,
            "metadata": metadata or {}
        }

        self.logger.info(json.dumps(event))

    def log_authentication(
        self,
        agent_id: str,
        success: bool,
        reason: Optional[str] = None
    ):
        """Log authentication attempts."""
        self.log_event(
            event_type="authentication",
            agent_id=agent_id,
            result="success" if success else "failure",
            metadata={"reason": reason} if reason else None
        )

    def log_authorization(
        self,
        agent_id: str,
        resource: str,
        action: str,
        granted: bool
    ):
        """Log authorization decisions."""
        self.log_event(
            event_type="authorization",
            agent_id=agent_id,
            resource=resource,
            action=action,
            result="granted" if granted else "denied"
        )

    def log_data_access(
        self,
        agent_id: str,
        session_id: str,
        operation: str,
        message_count: int = 0
    ):
        """Log data access patterns."""
        self.log_event(
            event_type="data_access",
            agent_id=agent_id,
            session_id=session_id,
            action=operation,
            metadata={"message_count": message_count}
        )

# Global audit logger
audit = AuditLogger()

# Usage in endpoints
@app.post("/sessions/{session_id}/messages")
async def add_message(
    session_id: str,
    message: MessageModel,
    agent: AgentIdentity = Depends(get_current_agent)
):
    # Log the attempt
    audit.log_data_access(
        agent_id=agent.id,
        session_id=session_id,
        operation="add_message"
    )

    try:
        result = await db.add_message(session_id, message, agent.id)
        audit.log_event(
            event_type="message_added",
            agent_id=agent.id,
            session_id=session_id,
            result="success"
        )
        return result
    except Exception as e:
        audit.log_event(
            event_type="message_add_failed",
            agent_id=agent.id,
            session_id=session_id,
            result="failure",
            metadata={"error": str(e)}
        )
        raise
```

### Pattern 6: Secure Database Operations

```python
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from shared_context_server.database import get_db_connection
from shared_context_server.utils.llm_errors import create_database_error, create_validation_error

class SecureDatabase:
    """Database operations with security best practices using DatabaseManager."""

    def __init__(self):
        # Database connection handled by get_db_connection()

    async def execute_query(
        self,
        query: str,
        parameters: tuple = ()
    ) -> List[Dict[str, Any]]:
        """Execute query with parameterized inputs (prevents SQL injection)."""

        # NEVER use string formatting for queries
        # ALWAYS use parameterized queries

        try:
            async with get_db_connection() as connection:
                cursor = await connection.execute(query, parameters)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            raise create_database_error(
                f"Query execution failed: {str(e)}",
                operation="execute_query",
                query=query[:100]  # First 100 chars for debugging
            )

    async def get_session_messages(
        self,
        session_id: str,
        agent_id: str,
        include_private: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve messages with visibility controls."""

        # Validate inputs
        session_id = InputSanitizer.validate_session_id(session_id)
        agent_id = InputSanitizer.validate_agent_id(agent_id)

        if include_private:
            # Include private messages only for the requesting agent
            query = """
                SELECT * FROM messages
                WHERE session_id = ?
                AND (visibility = 'public' OR
                     (visibility = 'private' AND sender = ?))
                ORDER BY timestamp ASC
            """
            params = (session_id, agent_id)
        else:
            # Only public messages
            query = """
                SELECT * FROM messages
                WHERE session_id = ? AND visibility = 'public'
                ORDER BY timestamp ASC
            """
            params = (session_id,)

        return await self.execute_query(query, params)

    async def add_message(
        self,
        session_id: str,
        sender: str,
        content: str,
        visibility: str = 'public',
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Add message with sanitization."""

        # Sanitize all inputs
        session_id = InputSanitizer.validate_session_id(session_id)
        sender = InputSanitizer.validate_agent_id(sender)
        content = InputSanitizer.sanitize_text(content)

        if metadata:
            metadata = InputSanitizer.sanitize_json(metadata)

        query = """
            INSERT INTO messages
            (session_id, sender, content, visibility, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        params = (
            session_id,
            sender,
            content,
            visibility,
            json.dumps(metadata) if metadata else '{}',
            datetime.now(timezone.utc).isoformat()
        )

        try:
            async with get_db_connection() as connection:
                cursor = await connection.execute(query, params)
                await connection.commit()
                return cursor.lastrowid
        except Exception as e:
            raise create_database_error(
                f"Failed to add message: {str(e)}",
                operation="add_message",
                session_id=session_id
            )
```

## Best Practices

### 1. Environment Variables for Secrets

```python
import os
from dotenv import load_dotenv

load_dotenv()

# NEVER hardcode secrets
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
DATABASE_ENCRYPTION_KEY = os.environ.get("DATABASE_ENCRYPTION_KEY")
API_KEYS = os.environ.get("API_KEYS", "").split(",")

if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY must be set")
```

### 2. Secure Headers

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Trusted host validation
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["shared-context-server.com", "*.shared-context-server.com"]
)
```

### 3. Token Refresh Strategy

```python
class TokenRefresher:
    """Secure token refresh mechanism."""

    @staticmethod
    async def refresh_token(
        refresh_token: str
    ) -> Dict[str, str]:
        """Generate new access token from refresh token."""

        try:
            # Verify refresh token (longer expiry)
            payload = jwt.decode(
                refresh_token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                audience=f"{AUDIENCE}:refresh"
            )

            # Check if refresh token is blacklisted
            if await is_token_blacklisted(payload.get("jti")):
                raise ValueError("Refresh token revoked")

            # Generate new access token
            # Use actual auth manager patterns
            new_access_token = auth_manager.validate_token(
                agent_id=payload["agent_id"],
                agent_type=payload.get("agent_type"),
                permissions=payload.get("permissions")
            )

            return {
                "access_token": new_access_token,
                "token_type": "bearer"
            }

        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
```

## Common Pitfalls

### 1. ❌ Not Validating Audience Claims

```python
# BAD - No audience validation
payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# GOOD - Validate audience
payload = jwt.decode(
    token,
    SECRET_KEY,
    algorithms=[ALGORITHM],
    audience=AUDIENCE  # Prevents token reuse
)
```

### 2. ❌ String Concatenation in SQL

```python
# BAD - SQL injection vulnerability
query = f"SELECT * FROM messages WHERE session_id = '{session_id}'"

# GOOD - Parameterized query
query = "SELECT * FROM messages WHERE session_id = ?"
params = (session_id,)
```

### 3. ❌ Storing Secrets in Code

```python
# BAD - Hardcoded secret
SECRET_KEY = "my-secret-key-123"

# GOOD - Environment variable
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
```

### 4. ❌ Missing Rate Limiting

```python
# BAD - No rate limiting
@app.post("/auth/token")
async def authenticate(credentials):
    pass

# GOOD - Rate limited
@app.post(
    "/auth/token",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))]
)
async def authenticate(credentials):
    pass
```

## Performance Considerations

- JWT validation adds minimal overhead with proper caching
- Rate limiting should use async patterns to avoid blocking
- Audit logging should be async to avoid blocking
- DatabaseManager (via get_db_connection()) provides connection pooling for optimal performance
- Use UTC timestamps consistently to avoid timezone conversion overhead

## Security Implications

### Critical Security Requirements
1. **Always validate JWT audience** - Prevents cross-service attacks
2. **Use parameterized queries** - Prevents SQL injection
3. **Sanitize all inputs** - Prevents XSS and injection
4. **Rate limit all endpoints** - Prevents abuse
5. **Audit all operations** - Enables forensics

## Testing Strategies

```python
import pytest
from unittest.mock import patch
from ..utils.llm_errors import ValidationError, DatabaseError

async def test_jwt_audience_validation():
    """Test that invalid audience is rejected."""
    # Create token with wrong audience
    token = jwt.encode(
        {"agent_id": "test", "aud": "wrong-audience"},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    with pytest.raises(HTTPException) as exc:
        await verify_token(token)
    assert exc.value.status_code == 401
    assert "Invalid audience" in str(exc.value.detail)

async def test_sql_injection_prevention():
    """Test that SQL injection attempts are blocked."""
    malicious_input = "'; DROP TABLE messages; --"

    with pytest.raises(ValidationError) as exc:
        InputSanitizer.validate_session_id(malicious_input)
    assert "Invalid session ID" in str(exc.value)
    assert exc.value.field == "session_id"

async def test_database_error_handling():
    """Test that database errors are properly handled."""
    secure_db = SecureDatabase()

    with patch('shared_context_server.database.get_db_connection') as mock_conn:
        mock_conn.side_effect = Exception("Database connection failed")

        with pytest.raises(DatabaseError) as exc:
            await secure_db.execute_query("SELECT * FROM messages")

        assert "Query execution failed" in str(exc.value)
        assert exc.value.operation == "execute_query"

async def test_rate_limiting():
    """Test that rate limiting blocks excessive requests."""
    # Make requests exceeding limit
    for i in range(6):
        response = await client.post("/auth/token", json={})

    # 6th request should be rate limited
    assert response.status_code == 429
```

## References

- JWT Best Practices: [RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- OWASP Security Guidelines
- Data Validation Guide: `.claude/tech-guides/data-validation.md`
- Error Handling Guide: `.claude/tech-guides/error-handling.md`
- Core Architecture Guide: `.claude/tech-guides/core-architecture.md`
- CI Environment Guide: `.claude/tech-guides/ci.md`

## Related Guides

- Data Validation Guide - Pydantic models and validation patterns
- Error Handling Guide - Security error responses
- Testing Guide - Security testing patterns
