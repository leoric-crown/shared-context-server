# Security Policy

## Security Best Practices

### Authentication & Authorization

#### JWT Token Security
- **Secret Key Management**:
  ```bash
  # Generate secure JWT secret
  openssl rand -base64 64 > jwt_secret.key
  chmod 600 jwt_secret.key
  ```
- Rotate JWT secrets every 90 days
- Use RS256 algorithm for production
- Set appropriate token expiration (24 hours default)

#### API Key Management
- Never commit API keys to version control
- Use environment variables for all secrets
- Implement rate limiting per API key
- Log all authentication attempts

### Input Validation

All user inputs are validated using Pydantic models with:
- Type checking
- Length limits
- Pattern validation (regex)
- SQL injection prevention
- XSS protection

Example validation:
```python
class SessionModel(BaseModel):
    id: str = Field(..., regex="^session_[a-f0-9]{16}$")
    purpose: str = Field(..., min_length=1, max_length=1000)
```

### Message Visibility Controls

The system implements four visibility levels:
- **public**: Visible to all agents in session
- **private**: Visible only to sender
- **agent_only**: Visible to agents of same type
- **admin_only**: Requires admin permission

### Audit Logging

Comprehensive audit logging tracks:
- Authentication attempts
- Permission changes
- Data access patterns
- Administrative actions
- Security-relevant events

### Database Security

#### SQLite Hardening
```sql
PRAGMA journal_mode = WAL;      -- Prevent corruption
PRAGMA synchronous  = NORMAL;   -- Balance safety/performance
PRAGMA foreign_keys = ON;       -- Enforce referential integrity
```

#### Connection Security
- Use connection pooling with limits
- Implement query timeouts
- Prepared statements only
- No dynamic SQL construction

### Network Security

#### HTTPS Only (Production)
```python
# Enforce HTTPS in production
if ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

#### CORS Configuration
```python
# Restrict CORS origins in production
CORS_ORIGINS = [
    "https://trusted-domain.com",
    "https://app.trusted-domain.com"
]
```

#### Rate Limiting
```python
# Implement rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/endpoint")
@limiter.limit("100/minute")
async def endpoint():
    pass
```

## Security Headers

Production deployments should include:
```python
security_headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
}
```

## Dependency Security

### Regular Updates
```bash
# Check for security vulnerabilities
pip-audit

# Update dependencies
uv sync --upgrade
```

### Supply Chain Security
- Pin dependency versions
- Use hash verification
- Regular security audits
- Monitor CVE databases

## Data Protection

### Encryption at Rest
- Sensitive data encrypted using AES-256
- Key management via environment variables
- Automatic key rotation

### Encryption in Transit
- TLS 1.3 minimum
- Strong cipher suites only
- Certificate pinning for clients

### Data Retention
- Audit logs: 90 days
- Session data: 30 days
- Automatic purging of expired data

## Access Control

### Role-Based Permissions
```python
PERMISSION_LEVELS = {
    "read": ["view_sessions", "view_messages"],
    "write": ["create_sessions", "add_messages"],
    "admin": ["all_permissions", "view_audit_logs", "modify_visibility"]
}
```

### Principle of Least Privilege
- Default to minimal permissions
- Explicit permission grants
- Regular permission audits
- Time-bound elevated access

## Incident Response

### Incident Classification
- **P0 (Critical)**: Data breach, authentication bypass
- **P1 (High)**: Permission escalation, DoS vulnerability
- **P2 (Medium)**: Information disclosure, session issues
- **P3 (Low)**: Minor security improvements

### Response Process
1. **Detect**: Monitoring, alerts, reports
2. **Assess**: Severity, impact, scope
3. **Contain**: Isolate affected systems
4. **Eradicate**: Remove vulnerability
5. **Recover**: Restore normal operations
6. **Review**: Post-incident analysis

## Security Checklist

### Development
- [ ] Input validation on all endpoints
- [ ] Output encoding for XSS prevention
- [ ] SQL parameterization
- [ ] Authentication checks
- [ ] Authorization verification
- [ ] Audit logging implementation
- [ ] Error handling (no stack traces)
- [ ] Secure defaults

### Deployment
- [ ] HTTPS configuration
- [ ] Security headers
- [ ] Rate limiting
- [ ] Firewall rules
- [ ] Backup encryption
- [ ] Log monitoring
- [ ] Intrusion detection
- [ ] Vulnerability scanning

### Operations
- [ ] Regular security audits
- [ ] Dependency updates
- [ ] Key rotation schedule
- [ ] Access reviews
- [ ] Incident drills
- [ ] Security training
- [ ] Compliance checks
- [ ] Penetration testing

## Security Tools

### Recommended Security Tools
```bash
# Static analysis
bandit -r src/

# Dependency scanning
safety check
pip-audit

# OWASP dependency check
dependency-check --scan .

# Secret scanning
trufflehog filesystem .
```

### Monitoring & Alerting
- Failed authentication attempts
- Privilege escalation attempts
- Unusual data access patterns
- System resource anomalies
- Error rate spikes
