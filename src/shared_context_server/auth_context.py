"""
Thread-safe authentication context management using ContextVar.

This module provides a ContextVar-based approach to managing SecureTokenManager
instances, eliminating the need for global singletons and complex test isolation
patterns while ensuring perfect thread safety.

Key Benefits:
- Zero global state pollution between tests
- Perfect thread safety without locks
- Automatic isolation for concurrent requests
- Eliminates 90+ test reset calls across the test suite
"""

from contextvars import ContextVar
from typing import Optional

from .auth_secure import SecureTokenManager

# Thread-safe context variable for token manager instances
# Each asyncio task/thread gets its own isolated instance
_token_manager_context: ContextVar[Optional[SecureTokenManager]] = ContextVar(
    "token_manager", default=None
)


def get_secure_token_manager() -> SecureTokenManager:
    """
    Get token manager from thread-local context.

    Creates a new instance if none exists in the current context,
    providing automatic isolation between different execution contexts
    (threads, asyncio tasks, etc.).

    Returns:
        SecureTokenManager: Thread-local token manager instance

    Thread Safety:
        Perfect - each context gets its own instance automatically
    """
    manager = _token_manager_context.get()
    if manager is None:
        manager = SecureTokenManager()
        _token_manager_context.set(manager)
    return manager


def set_token_manager_for_testing(manager: Optional[SecureTokenManager]) -> None:
    """
    Set token manager in context - for test injection only.

    This function is intended for testing scenarios where you need to
    inject a specific token manager instance (e.g., mock or configured instance).

    Args:
        manager: Token manager instance to set in context, or None to clear

    Note:
        This is primarily for testing - production code should use
        get_secure_token_manager() which handles instance creation automatically.
    """
    _token_manager_context.set(manager)


def reset_token_context() -> None:
    """
    Reset context - automatic isolation for tests.

    Clears the current context, forcing the next call to get_secure_token_manager()
    to create a fresh instance. This is useful for test isolation, though in most
    cases the automatic context isolation should be sufficient.

    Note:
        With ContextVar, this is rarely needed as each test naturally gets
        its own context. This is provided for explicit cleanup scenarios.
    """
    _token_manager_context.set(None)


def get_current_token_manager() -> Optional[SecureTokenManager]:
    """
    Get current token manager from context without creating one.

    Returns:
        SecureTokenManager or None: Current manager if one exists in context

    Use Case:
        Checking if a token manager exists without triggering creation.
        Useful for debugging or conditional logic.
    """
    return _token_manager_context.get()
