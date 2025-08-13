# Secure Token Authentication Implementation Plan

## Executive Summary

**Critical Security Issue**: JWT tokens passed as MCP tool parameters are exposed in logs, debugging tools, and network traces, creating a fundamental security vulnerability. This plan implements a secure token reference system (`sct_*` format) that protects JWT tokens while maintaining the dynamic authorization model required for multi-agent coordination.

**Solution Approach**: OAuth 2.0 compliant token refresh system with hybrid safeguards (manual refresh + auto-renewal safety net) following industry best practices and expert developer recommendations.

---

## Problem Statement

### Current Security Vulnerability
- **JWT Exposure**: JWT tokens visible in Claude Code logs, MCP server debug output, network traffic
- **Sensitive Data**: Tokens contain agent_id, permissions, and authentication claims
- **Attack Surface**: 24-hour token expiry extends exposure window for compromised tokens
- **Compliance Risk**: Violates OWASP, OAuth 2.0, and JWT security best practices

### Technical Constraints
- **MCP Protocol Limitation**: Cannot use Authorization headers for dynamic per-request authentication
- **Dynamic Authorization Required**: Static MCP headers insufficient for agent permission delegation
- **Long-Running Workflows**: Autonomous agents need 20-30 minute token validity

---

## Discovery Results

### Authentication Model Clarification
- **MCP Headers**: Static API keys for client connection authentication
- **JWT Parameters**: Dynamic per-request agent authorization (required for orchestrator → sub-agent workflows)
- **Token Lifecycle**: 30-minute tokens supporting autonomous agent operations

### Developer Agent Analysis
**Recommendation**: Approach A (New Token on Refresh) with hybrid safeguards

**Key Findings**:
- ✅ **OAuth 2.0 Compliant**: Follows industry standard token rotation practices
- ✅ **Security Best Practice**: Immediate old token invalidation reduces attack surface
- ✅ **JWT Principles**: Respects token immutability (JWTs shouldn't be modified)
- ✅ **Industry Alignment**: Matches patterns from Google, GitHub, AWS, Microsoft
- ❌ **Token Extension Rejected**: Violates JWT immutability and industry standards

---

## Research Context

### Industry Standards Analysis
- **OAuth 2.0 RFC 6749**: Requires token rotation on refresh
- **JWT RFC 7519**: Tokens should be immutable, new tokens issued for refresh
- **OWASP Guidelines**: Minimize token lifetime, implement rotation best practices
- **Major Cloud Providers**: All use new token issuance pattern for refresh

### Security Framework Alignment
- **Zero Trust Architecture**: Server-side token validation and encryption
- **Defense in Depth**: Multiple security layers (encryption, salting, rotation)
- **Audit Compliance**: Complete token lifecycle tracking for SOC 2/security audits

### Performance Considerations
- **Current Latency**: ~1-2ms per request (direct JWT validation)
- **Proposed Latency**: ~3-5ms per request (DB lookup + decryption + validation)
- **Trade-off Assessment**: 2-3ms increase acceptable for critical security improvement

---

## Technical Specifications

### Protected Token Format
```
Format: sct_<base64_hash>_<timestamp>
Example: sct_YWJjZGVmZ2hpams_1703123456

Components:
- sct: "secure context token" prefix
- hash: Salted SHA-256 of internal reference
- timestamp: Creation time for client-side expiry validation
```

### Database Schema
```sql
CREATE TABLE secure_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT UNIQUE NOT NULL,
    jwt_encrypted BLOB NOT NULL,
    salt TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    predecessor_token_id INTEGER REFERENCES secure_tokens(id),
    refresh_count INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT 1,
    INDEX idx_token_hash (token_hash),
    INDEX idx_expires_at (expires_at),
    INDEX idx_agent_id (agent_id)
);
```

### Security Properties
- **AES-GCM Encryption**: AEAD encryption for stored JWT tokens
- **Unique Salting**: Different cryptographic salt per token generation
- **Non-Reversible**: Cannot derive JWT content from protected token
- **Short-Lived**: 30-minute base expiry with controlled refresh
- **Immediate Invalidation**: Old tokens become invalid on refresh

---

## Implementation Plan

### Phase 1: Core Secure Token System (3 hours)
**Deliverables:**
- `SecureTokenManager` class with encryption and token mapping
- Database migration for `secure_tokens` table
- Protected token generation with `sct_*` format
- Update `authenticate_agent` to return protected tokens
- Update `validate_jwt_token_parameter` to resolve protected tokens

**Key Components:**
```python
class SecureTokenManager:
    async def create_protected_token(self, jwt_token: str, agent_id: str) -> str
    async def resolve_protected_token(self, protected_token: str) -> dict | None
    async def invalidate_token(self, protected_token: str) -> bool
    async def cleanup_expired_tokens(self) -> int
```

### Phase 2: Token Refresh System (2 hours)
**Deliverables:**
- `refresh_token` MCP tool implementation
- Atomic refresh operations (validate → create new → invalidate old)
- Predecessor token tracking for audit trails
- Refresh count limits and validation

**Tool Signature:**
```python
@mcp.tool()
async def refresh_token(ctx: Context, current_token: str) -> dict[str, Any]:
    """Generate new protected token, invalidate current token."""
    # Atomic operation with database transaction
    # Returns new sct_* token with same permissions
```

### Phase 3: Safety Net Auto-Renewal (1 hour)
**Deliverables:**
- Auto-renewal logic in token validation
- 5-minute expiry window detection
- 10-minute safety extension for expiring tokens
- Transparent auto-renewal logging

**Integration Point:**
```python
async def validate_jwt_token_parameter(auth_token: str) -> dict[str, Any]:
    # Primary validation
    # Safety net: extend by 10 minutes if expires within 5 minutes
    # Log auto-renewals for audit trail
```

### Phase 4: System Integration (2 hours)
**Deliverables:**
- Update all authentication tests for `sct_*` format
- Background cleanup task for expired/invalidated tokens
- Enhanced error messages for token expiry scenarios
- Documentation updates with refresh examples
- Performance monitoring and logging

---

## Security Considerations

### Encryption Standards
- **Algorithm**: AES-256-GCM with AEAD properties
- **Key Management**: Server-side encryption keys from environment variables
- **Salt Generation**: Cryptographically secure random salts per token
- **Key Rotation**: Support for periodic encryption key rotation

### Attack Vector Mitigation
- **Token Exposure**: Protected tokens reveal no sensitive information
- **Replay Attacks**: One-time use tokens with immediate invalidation
- **Brute Force**: Cryptographically strong hashing prevents enumeration
- **Timing Attacks**: Constant-time comparison for token validation

### Audit Requirements
- **Token Generation**: Log all protected token creation with agent context
- **Token Refresh**: Track refresh operations with predecessor relationships
- **Token Expiry**: Log natural expiration and cleanup operations
- **Auto-Renewal**: Log safety net extensions with justification

---

## Implementation Workflow

### Agent Experience
```python
# 1. Agent authenticates and receives protected token
auth_result = await authenticate_agent(agent_id="claude_main", agent_type="admin")
my_token = auth_result["token"]  # sct_abc123_1703123456

# 2. Agent uses token for operations
result = await add_message(session_id="...", content="...", auth_token=my_token)

# 3. Before long operation, refresh if needed
if token_expires_soon(my_token):
    refresh_result = await refresh_token(my_token)
    my_token = refresh_result["token"]  # New sct_xyz789_1703126456

# 4. Continue with new token
result = await some_long_operation(auth_token=my_token)
```

### Database Operations
```python
# Atomic refresh transaction
async def refresh_token_atomic(current_token: str, agent_id: str) -> dict:
    async with database_transaction() as tx:
        # 1. Validate current token
        current = await tx.fetchone(
            "SELECT * FROM secure_tokens WHERE token_hash = ? AND active = 1",
            (hash_token(current_token),)
        )

        # 2. Generate new protected token
        new_token_ref = generate_protected_token()
        new_jwt_encrypted = encrypt_jwt(current.decrypted_jwt)

        # 3. Atomic swap
        await tx.execute("UPDATE secure_tokens SET active = 0 WHERE id = ?", (current.id,))
        await tx.execute("""
            INSERT INTO secure_tokens
            (token_hash, jwt_encrypted, salt, agent_id, expires_at, predecessor_token_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (hash_token(new_token_ref), new_jwt_encrypted, generate_salt(),
              agent_id, datetime.now() + timedelta(minutes=30), current.id))

        await tx.commit()
        return {"token": new_token_ref, "expires_at": "..."}
```

---

## Risk Assessment & Mitigation

### Implementation Risks
| Risk | Impact | Probability | Mitigation Strategy |
|------|---------|-------------|-------------------|
| Database performance degradation | Medium | Low | Proper indexing, connection pooling |
| Race conditions in refresh | High | Medium | Atomic transactions, unique constraints |
| Agent token management complexity | Medium | Medium | Clear documentation, error handling |
| Encryption key compromise | High | Low | Key rotation procedures, environment isolation |

### Operational Risks
- **Token Cleanup**: Background task failure → disk space growth
- **Auto-Renewal**: Safety net failure → agent workflow interruption
- **Audit Compliance**: Incomplete logging → compliance violations
- **Performance**: Database bottleneck → system slowdown

### Mitigation Strategies
- **Database Monitoring**: Connection pool metrics, query performance
- **Error Handling**: Graceful degradation for token operations
- **Backup Procedures**: Token recovery and validation mechanisms
- **Performance Testing**: Load testing with realistic token refresh patterns

---

## Success Criteria

### Security Objectives
- ✅ **Zero JWT Exposure**: No raw JWT tokens in logs or network traces
- ✅ **Compliance Adherence**: Meets OAuth 2.0, OWASP, SOC 2 requirements
- ✅ **Attack Surface Reduction**: Immediate invalidation limits exposure window
- ✅ **Audit Trail Completeness**: Full token lifecycle tracking

### Functional Objectives
- ✅ **Agent Workflow Continuity**: 30-minute tokens support autonomous operations
- ✅ **Reliable Refresh**: Manual token refresh with <5ms average latency
- ✅ **Safety Net Coverage**: Auto-renewal prevents workflow interruption
- ✅ **Error Handling**: Clear error messages for token expiry scenarios

### Performance Objectives
- ✅ **Latency Impact**: <3ms additional latency for token resolution
- ✅ **Database Performance**: <100ms response time for refresh operations
- ✅ **Memory Efficiency**: Automatic cleanup prevents unbounded growth
- ✅ **Scalability**: Support for 1000+ concurrent tokens

---

## Next Steps

### Immediate Actions
1. **Environment Setup**: Configure encryption keys and database schema
2. **Core Implementation**: Begin Phase 1 development with `SecureTokenManager`
3. **Testing Strategy**: Develop security-focused test suite
4. **Documentation**: Update API documentation with new token format

### Implementation Timeline
- **Week 1**: Phase 1 (Core system) + Phase 2 (Refresh mechanism)
- **Week 2**: Phase 3 (Safety net) + Phase 4 (Integration)
- **Week 3**: Security testing, performance optimization, documentation
- **Week 4**: Production deployment, monitoring setup

### Validation Checkpoints
- **Security Review**: Independent security assessment of implementation
- **Performance Testing**: Load testing with realistic multi-agent scenarios
- **Compliance Audit**: Verification of audit trail completeness
- **Agent Integration**: Testing with actual Claude Code workflows

---

## Appendices

### A. Reference Implementation Examples
- OAuth 2.0 token refresh patterns from major providers
- JWT security best practices from OWASP guidelines
- MCP authentication examples from industry implementations

### B. Database Migration Scripts
- Schema creation with proper indexing
- Data migration procedures for existing tokens
- Rollback procedures for deployment safety

### C. Testing Scenarios
- Security penetration testing protocols
- Performance benchmarking procedures
- Multi-agent coordination test cases
- Error handling and recovery testing

---

**Document Version**: 1.0
**Created**: 2025-01-12
**Status**: Ready for Implementation
**Estimated Effort**: 8 hours
**Priority**: P0 - Critical Security Issue
