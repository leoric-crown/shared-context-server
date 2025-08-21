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
    """
    # Pattern for session IDs (session:uuid format)
    session_pattern = r"session:[^:]+"
    # Pattern for agent IDs (agent:id format)
    agent_pattern = r"agent:[^:]+"
    # Pattern for tokens or keys (long base64-like strings)
    token_pattern = r"[a-zA-Z0-9+/]{20,}={0,2}"
    # Pattern for UUIDs
    uuid_pattern = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"

    return re.sub(
        token_pattern,
        "[token-redacted]",
        re.sub(
            uuid_pattern,
            "[uuid-redacted]",
            re.sub(
                agent_pattern,
                "agent:[redacted]",
                re.sub(
                    session_pattern,
                    "session:[redacted]",
                    cache_key,
                    flags=re.IGNORECASE,
                ),
                flags=re.IGNORECASE,
            ),
            flags=re.IGNORECASE,
        ),
    )


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


def secure_hash(data: str, algorithm: str = "sha256") -> str:
    """
    Generate secure hash using SHA-256 or other secure algorithms.

    Args:
        data: String data to hash
        algorithm: Hash algorithm to use (default: sha256)

    Returns:
        Hex digest of the hash
    """
    if algorithm == "sha256":
        return hashlib.sha256(data.encode()).hexdigest()
    if algorithm == "sha1":
        return hashlib.sha1(data.encode()).hexdigest()
    raise ValueError(f"Unsupported hash algorithm: {algorithm}")


def secure_hash_short(data: str, length: int = 8) -> str:
    """
    Generate short secure hash for cache keys and similar uses.

    Args:
        data: String data to hash
        length: Length of returned hash (default: 8)

    Returns:
        Truncated hex digest of SHA-256 hash
    """
    return secure_hash(data)[:length]
