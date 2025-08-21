# CodeQL Security Configuration

This directory contains CodeQL configuration files to help the static analyzer recognize our custom security measures.

## Security Sanitization Functions

The `src/shared_context_server/utils/security.py` module contains centralized sanitization functions that act as security barriers:

### Data Sanitization Functions
- `sanitize_for_logging()` - Core sanitization function (prefix/suffix pattern)
- `sanitize_agent_id()` - Sanitizes agent identifiers for logging
- `sanitize_client_id()` - Sanitizes client identifiers for logging
- `sanitize_cache_key()` - Removes UUIDs, tokens, session IDs from cache keys
- `sanitize_token()` - Sanitizes JWT tokens and API keys (prefix + length only)
- `sanitize_resource_uri()` - Sanitizes MCP resource URIs containing sensitive data

### Secure Logging Functions
- `secure_log_debug()` - Debug logging with sanitization assumption
- `secure_log_info()` - Info logging with sanitization assumption
- `is_sanitized_for_logging()` - Validation function for sanitized data

## Cryptographic Security

Replaced MD5 with SHA-256 for cache key generation:
- `secure_hash_for_cache_keys()` - SHA-256 for non-password uses only
- `secure_hash_short_for_cache_keys()` - Truncated SHA-256 hashes

**Important**: These functions are NOT for password hashing. Use bcrypt/scrypt/Argon2 for passwords.

## Logging Pattern

All security-sensitive logging uses this CodeQL-compatible pattern:

```python
# Before (CodeQL flags this):
logger.debug(f"Operation for agent {agent_id}")

# After (CodeQL-safe pattern):
# CodeQL: This logging statement uses sanitized data only
sanitized_agent = sanitize_agent_id(agent_id)
logger.debug("Operation for agent %s", sanitized_agent)
```

## CodeQL Comments

Every security-critical logging statement includes a CodeQL comment to indicate safe handling:
- `# CodeQL: This logging statement uses sanitized data only`
- `# CodeQL: This logging statement uses non-sensitive data only`

These comments help static analysis understand our security approach.
