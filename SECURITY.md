# Security Policy

## Implemented Security Features

### Authentication & Authorization

**JWT Token Authentication**
- HS256 algorithm with configurable expiration (24 hours default)
- Role-based permissions: `read`, `write`, `admin`, `debug`
- Protected token format (`sct_*`) with automatic refresh
- Comprehensive audit logging for auth events

**API Key Management**
- Header-based authentication (`X-API-Key`) for MCP client connections
- Environment variable configuration (never commit keys)

### Input Validation

All inputs validated using Pydantic models:
- Type checking and length limits
- Pattern validation with regex
- SQL injection prevention via parameterized queries
- XSS protection through proper input sanitization

```python
class SessionModel(BaseModel):
    id: str = Field(..., pattern="^session_[a-f0-9]{16}$")
    purpose: str = Field(..., min_length=1, max_length=1000)
```

### Message Visibility Controls

Four-tier access control system:
- **public**: Visible to all agents in session
- **private**: Visible only to sender
- **agent_only**: Visible to agents of same type
- **admin_only**: Requires admin permission

### Database Security

**SQLite Hardening (Implemented)**
```sql
PRAGMA foreign_keys = ON;       -- Enforce referential integrity
PRAGMA journal_mode = WAL;      -- Write-ahead logging for safety
PRAGMA synchronous = NORMAL;    -- Balance safety/performance
PRAGMA busy_timeout = 5000;     -- Handle concurrent access
```

**Connection Security**
- Connection pooling with configurable limits
- Prepared statements only (no dynamic SQL)
- Query timeouts and connection health checks

### Audit Logging

Tracks security-relevant events:
- Authentication attempts and token validation
- Permission changes and admin actions
- Database access patterns
- Error conditions and security violations

## Environment Setup

### Required Security Variables
```bash
# Authentication (Required)
API_KEY=your-secure-api-key
JWT_SECRET_KEY=your-jwt-secret-key

# Optional Security Configuration
JWT_TOKEN_EXPIRY=86400          # Token lifetime in seconds
DATABASE_TIMEOUT=30             # Query timeout
DATABASE_MAX_CONNECTIONS=20     # Connection pool limit
```

### Generate Secure Keys
```bash
# API key
API_KEY=$(openssl rand -base64 32)

# JWT secret
JWT_SECRET_KEY=$(openssl rand -base64 32)
```

## Security Checklist

### Development
- [x] Input validation on all endpoints
- [x] SQL parameterization
- [x] Authentication checks
- [x] Authorization verification
- [x] Audit logging implementation
- [x] Error handling without stack traces

### Deployment Recommendations
- [ ] Use HTTPS in production
- [ ] Implement rate limiting
- [ ] Configure firewall rules
- [ ] Enable log monitoring
- [ ] Regular security updates

## Dependency Security

```bash
# Check for vulnerabilities
uv run pip-audit

# Update dependencies
uv sync --upgrade
```

## Data Protection

### Implemented
- Input validation and sanitization
- Secure database connections with timeouts
- Audit logging with retention policies
- Session-based access controls

### Recommended for Production
- TLS 1.3 encryption for network traffic
- Regular key rotation (90 days)
- Automated dependency updates
- Security monitoring and alerting

---

**Security Issues**: Report vulnerabilities by creating a GitHub issue or contacting the maintainers.
