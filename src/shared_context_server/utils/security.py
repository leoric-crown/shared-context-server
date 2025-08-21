"""Security utilities for sanitizing sensitive data in logs and operations."""

import hashlib
import re


def sanitize_for_logging(value: str, keep_prefix: int = 4, keep_suffix: int = 4) -> str:
    """
    Sanitize sensitive strings for safe logging by showing only prefix/suffix.

    Args:
        value: The sensitive string to sanitize
        keep_prefix: Number of characters to keep from start
        keep_suffix: Number of characters to keep from end

    Returns:
        Sanitized string safe for logging
    """
    if not value or len(value) <= keep_prefix + keep_suffix:
        return "***" if value else ""

    return f"{value[:keep_prefix]}***{value[-keep_suffix:]}"


def sanitize_agent_id(agent_id: str) -> str:
    """Sanitize agent ID for logging."""
    return sanitize_for_logging(agent_id, keep_prefix=4, keep_suffix=2)


def sanitize_client_id(client_id: str) -> str:
    """Sanitize client ID for logging."""
    return sanitize_for_logging(client_id, keep_prefix=4, keep_suffix=2)


def sanitize_cache_key(cache_key: str) -> str:
    """
    Sanitize cache key for logging by removing sensitive session/agent data.

    This function combines multiple sanitization patterns to handle various
    cache key formats used throughout the application.

    Note: This function is designed to prevent sensitive data exposure in logs.
    """
    if not cache_key:
        return "[empty]"

    # Pattern for session IDs (session:uuid format)
    session_pattern = r"session:[^:]+"
    # Pattern for agent IDs (agent:id format)
    agent_pattern = r"agent:[^:]+"
    # Pattern for tokens or keys (long base64-like strings)
    token_pattern = r"[a-zA-Z0-9+/]{20,}={0,2}"
    # Pattern for UUIDs
    uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"

    # Apply multiple sanitization passes
    sanitized = cache_key
    sanitized = re.sub(
        session_pattern, "session:[redacted]", sanitized, flags=re.IGNORECASE
    )
    sanitized = re.sub(
        agent_pattern, "agent:[redacted]", sanitized, flags=re.IGNORECASE
    )
    sanitized = re.sub(uuid_pattern, "[uuid-redacted]", sanitized, flags=re.IGNORECASE)
    return re.sub(token_pattern, "[token-redacted]", sanitized)


def sanitize_token(token: str) -> str:
    """
    Sanitize token for safe logging by showing only prefix and length.

    This prevents token exposure in logs while maintaining debug utility.
    """
    if not token:
        return "[empty]"
    if len(token) <= 8:
        return "[redacted]"
    return f"{token[:8]}...({len(token)} chars)"


def sanitize_resource_uri(uri: str) -> str:
    """
    Sanitize resource URI for safe logging by removing sensitive identifiers.

    This prevents exposure of session IDs, agent IDs, and other sensitive data
    that may be embedded in resource URIs.
    """
    if not uri:
        return "[empty]"

    # Apply same patterns as cache key sanitization
    return sanitize_cache_key(uri)


def secure_hash_for_cache_keys(data: str) -> str:
    """
    Generate secure hash for cache key generation (NOT for passwords).

    Uses SHA-256 which is appropriate for cache key generation, content
    addressing, and data integrity - but NOT for password hashing.

    For password hashing, use bcrypt, scrypt, or Argon2 instead.

    Args:
        data: String data to hash (cache keys, content, etc.)

    Returns:
        SHA-256 hex digest
    """
    # SHA-256 is appropriate for cache keys and non-password uses
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def secure_hash_short_for_cache_keys(data: str, length: int = 8) -> str:
    """
    Generate short secure hash for cache keys and similar non-password uses.

    Uses SHA-256 which is appropriate for cache key generation - NOT for passwords.

    Args:
        data: String data to hash (cache keys, identifiers, etc.)
        length: Length of returned hash (default: 8)

    Returns:
        Truncated hex digest of SHA-256 hash
    """
    return secure_hash_for_cache_keys(data)[:length]
