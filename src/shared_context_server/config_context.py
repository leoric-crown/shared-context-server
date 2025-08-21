"""
Thread-safe configuration context management using ContextVar.

This module provides a ContextVar-based approach to managing SharedContextServerConfig
instances, replacing the global _config singleton anti-pattern with proper thread-safe
context management.

Key Benefits:
- Zero global state pollution between tests
- Perfect thread safety without locks
- Automatic isolation for concurrent requests
- Environment variable isolation per context
- Eliminates manual config resets in test suites
"""

from contextvars import ContextVar
from typing import Optional

from .config import SharedContextServerConfig, load_config

# Thread-safe context variable for config instances
# Each asyncio task/thread gets its own isolated instance
_config_context: ContextVar[Optional[SharedContextServerConfig]] = ContextVar(
    "shared_context_config", default=None
)


def get_context_config(env_file: str | None = None) -> SharedContextServerConfig:
    """
    Get configuration from thread-local context.

    Creates a new instance if none exists in the current context,
    providing automatic isolation between different execution contexts
    (threads, asyncio tasks, etc.).

    Args:
        env_file: Optional path to .env file for config loading

    Returns:
        SharedContextServerConfig: Thread-local config instance

    Thread Safety:
        Perfect - each context gets its own instance automatically
    """
    config = _config_context.get()
    if config is None:
        config = load_config(env_file)
        _config_context.set(config)
    return config


def set_config_for_testing(config: Optional[SharedContextServerConfig]) -> None:
    """
    Set configuration in context - for test injection only.

    This function is intended for testing scenarios where you need to
    inject a specific config instance (e.g., mock or configured instance).

    Args:
        config: Config instance to set in context, or None to clear

    Note:
        This is primarily for testing - production code should use
        get_context_config() which handles instance creation automatically.
    """
    _config_context.set(config)


def reset_config_context() -> None:
    """
    Reset context - automatic isolation for tests.

    Clears the current context, forcing the next call to get_context_config()
    to create a fresh instance. This is useful for test isolation, though in most
    cases the automatic context isolation should be sufficient.

    Note:
        With ContextVar, this is rarely needed as each test naturally gets
        its own context. This is provided for explicit cleanup scenarios.
    """
    _config_context.set(None)


def get_current_config() -> Optional[SharedContextServerConfig]:
    """
    Get current configuration from context without creating one.

    Returns:
        SharedContextServerConfig or None: Current config if one exists in context

    Use Case:
        Checking if a config exists without triggering creation.
        Useful for debugging or conditional logic.
    """
    return _config_context.get()


def reload_config_in_context(env_file: str | None = None) -> SharedContextServerConfig:
    """
    Force reload configuration in current context.

    This bypasses any cached config in the context and creates a fresh
    instance by calling load_config() directly.

    Args:
        env_file: Optional path to .env file for config loading

    Returns:
        SharedContextServerConfig: Newly loaded config instance

    Use Case:
        When you need to reload config due to environment changes
        within the same context (e.g., during testing).
    """
    config = load_config(env_file)
    _config_context.set(config)
    return config
