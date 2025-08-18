"""
Thread-safe JWT authentication context management using ContextVar.

This module provides a ContextVar-based approach to managing JWTAuthenticationManager
instances, replacing the LazyAuthManager singleton anti-pattern with proper thread-safe
context management.

Key Benefits:
- Zero global state pollution between tests
- Perfect thread safety without locks
- Automatic isolation for concurrent requests
- Eliminates manual reset() calls in test suites
"""

from contextvars import ContextVar
from typing import Optional

from .auth_core import JWTAuthenticationManager

# Thread-safe context variable for JWT auth manager instances
# Each asyncio task/thread gets its own isolated instance
_jwt_auth_manager_context: ContextVar[Optional[JWTAuthenticationManager]] = ContextVar(
    "jwt_auth_manager", default=None
)


def get_jwt_auth_manager() -> JWTAuthenticationManager:
    """
    Get JWT auth manager from thread-local context.

    Creates a new instance if none exists in the current context,
    providing automatic isolation between different execution contexts
    (threads, asyncio tasks, etc.).

    Returns:
        JWTAuthenticationManager: Thread-local auth manager instance

    Thread Safety:
        Perfect - each context gets its own instance automatically
    """
    manager = _jwt_auth_manager_context.get()
    if manager is None:
        manager = JWTAuthenticationManager()
        _jwt_auth_manager_context.set(manager)
    return manager


def set_jwt_auth_manager_for_testing(
    manager: Optional[JWTAuthenticationManager],
) -> None:
    """
    Set JWT auth manager in context - for test injection only.

    This function is intended for testing scenarios where you need to
    inject a specific auth manager instance (e.g., mock or configured instance).

    Args:
        manager: Auth manager instance to set in context, or None to clear

    Note:
        This is primarily for testing - production code should use
        get_jwt_auth_manager() which handles instance creation automatically.
    """
    _jwt_auth_manager_context.set(manager)


def reset_jwt_auth_context() -> None:
    """
    Reset context - automatic isolation for tests.

    Clears the current context, forcing the next call to get_jwt_auth_manager()
    to create a fresh instance. This is useful for test isolation, though in most
    cases the automatic context isolation should be sufficient.

    Note:
        With ContextVar, this is rarely needed as each test naturally gets
        its own context. This is provided for explicit cleanup scenarios.
    """
    _jwt_auth_manager_context.set(None)


def get_current_jwt_auth_manager() -> Optional[JWTAuthenticationManager]:
    """
    Get current JWT auth manager from context without creating one.

    Returns:
        JWTAuthenticationManager or None: Current manager if one exists in context

    Use Case:
        Checking if an auth manager exists without triggering creation.
        Useful for debugging or conditional logic.
    """
    return _jwt_auth_manager_context.get()
