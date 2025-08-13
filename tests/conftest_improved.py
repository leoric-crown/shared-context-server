"""
Improved testing utilities for FastMCP-based shared context server.

This module provides simplified, modern database testing infrastructure that:
1. Uses real in-memory SQLite databases instead of fragile mocks
2. Provides proper test isolation with minimal overhead
3. Supports both aiosqlite and SQLAlchemy backends seamlessly
4. Implements streamlined cleanup without excessive complexity

Key improvements over the original conftest.py:
- Reduced complexity in background task management
- Simplified fixture design focused on database isolation
- Better separation of concerns between database and other resources
- More maintainable and predictable test behavior
"""

import asyncio
import threading
import weakref
from typing import Any

import pytest
from pydantic.fields import FieldInfo

from shared_context_server.auth import AuthInfo

# =============================================================================
# SIMPLIFIED TASK TRACKING
# =============================================================================

# Simplified task registry - only track what's necessary
_test_tasks: set[asyncio.Task] = set()
_test_threads: set[threading.Thread] = set()


def track_test_task(task: asyncio.Task) -> None:
    """Track a task for cleanup."""
    _test_tasks.add(task)

    # Auto-remove when done
    def cleanup_ref(task_ref):
        _test_tasks.discard(task)

    weakref.ref(task, cleanup_ref)


def track_test_thread(thread: threading.Thread) -> None:
    """Track a thread for cleanup."""
    _test_threads.add(thread)

    # Auto-remove when done
    def cleanup_ref(thread_ref):
        _test_threads.discard(thread)

    weakref.ref(thread, cleanup_ref)


async def cleanup_test_tasks(timeout: float = 1.0) -> int:
    """Clean up test tasks with timeout."""
    tasks_to_cancel = [t for t in _test_tasks if not t.done()]

    for task in tasks_to_cancel:
        task.cancel()

    if tasks_to_cancel:
        import contextlib

        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(
                asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                timeout=timeout,
            )

    _test_tasks.clear()
    return len(tasks_to_cancel)


def cleanup_test_threads(timeout: float = 0.5) -> int:
    """Clean up test threads with timeout."""
    threads_to_cleanup = [t for t in _test_threads if t.is_alive()]

    for thread in threads_to_cleanup:
        if thread != threading.current_thread():
            try:
                thread.daemon = True
                thread.join(timeout=timeout)
            except Exception:
                pass

    _test_threads.clear()
    return len(threads_to_cleanup)


# =============================================================================
# FASTMCP TESTING UTILITIES
# =============================================================================


def extract_field_defaults(fastmcp_tool) -> dict[str, Any]:
    """Extract actual default values from a FastMCP tool function."""
    import inspect

    defaults = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for name, param in sig.parameters.items():
        if name == "ctx":  # Skip context parameter
            continue

        if isinstance(param.default, FieldInfo):
            defaults[name] = param.default.default
        elif param.default is not inspect.Parameter.empty:
            defaults[name] = param.default

    return defaults


async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """Call a FastMCP tool function with proper default handling."""
    defaults = extract_field_defaults(fastmcp_tool)
    call_args = {**defaults, **kwargs}
    return await fastmcp_tool.fn(ctx, **call_args)


class MockContext:
    """Standard mock context for FastMCP testing."""

    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        self._auth_info = AuthInfo(
            jwt_validated=False,
            agent_id=agent_id,
            agent_type="test",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="api_key",
            token_id=None,
        )

    @property
    def agent_id(self) -> str:
        return self._auth_info.agent_id

    @agent_id.setter
    def agent_id(self, value: str) -> None:
        self._auth_info.agent_id = value

    @property
    def agent_type(self) -> str:
        return self._auth_info.agent_type


# =============================================================================
# SIMPLIFIED CLEANUP FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Simplified cleanup that focuses on the essentials."""
    yield  # Let the test run

    # Clean up tasks and threads
    cancelled_tasks = await cleanup_test_tasks()
    cleaned_threads = cleanup_test_threads()

    # Only log if there was actual cleanup needed
    if cancelled_tasks > 0 or cleaned_threads > 0:
        print(f"Test cleanup: {cancelled_tasks} tasks, {cleaned_threads} threads")


@pytest.fixture(autouse=True)
async def reset_global_state():
    """Reset global state between tests."""
    yield  # Let the test run

    # Reset database managers
    try:
        import shared_context_server.database as db_module

        db_module._db_manager = None
        db_module._sqlalchemy_manager = None
    except ImportError:
        pass


# =============================================================================
# PYTEST HOOKS
# =============================================================================


def pytest_configure(config):
    """Configure pytest for improved testing."""
    # Set asyncio mode
    import os

    os.environ["PYTEST_ASYNCIO_MODE"] = "auto"


def pytest_sessionfinish(session, exitstatus):
    """Final cleanup when test session ends."""
    # Convert any remaining threads to daemon
    remaining_threads = [
        t
        for t in threading.enumerate()
        if t != threading.main_thread() and t.is_alive()
    ]

    # Convert remaining threads to daemon threads outside the loop
    # to avoid performance overhead of try-except in loop
    import contextlib

    for thread in remaining_threads:
        with contextlib.suppress(Exception):
            if not thread.daemon:
                thread.daemon = True


# =============================================================================
# EXAMPLE USAGE DOCUMENTATION
# =============================================================================

"""
USAGE EXAMPLES:

# 1. Basic database testing with isolation
@pytest.mark.asyncio
async def test_example(isolated_db: DatabaseTestManager):
    async with isolated_db.get_connection() as conn:
        # Each test gets a fresh database
        await conn.execute("INSERT INTO sessions ...")

# 2. Testing global functions with patching
@pytest.mark.asyncio
async def test_global_functions(patched_db_connection):
    result = await execute_query("SELECT ...")
    # Functions use isolated test database

# 3. Testing with pre-populated data
@pytest.mark.asyncio
async def test_with_data(seeded_db: DatabaseTestManager):
    # Database already has test sessions, messages, etc.
    async with seeded_db.get_connection() as conn:
        await assert_table_count(conn, "sessions", 2)

# 4. FastMCP tool testing
@pytest.mark.asyncio
async def test_mcp_tool():
    ctx = MockContext(session_id="test", agent_id="test_agent")
    result = await call_fastmcp_tool(create_session_tool, ctx, purpose="Test")

MIGRATION FROM OLD PATTERNS:

OLD (overmocked):
    with patch('database.get_connection') as mock_conn:
        mock_conn.return_value = mock_result
        # Fragile test that breaks when implementation changes

NEW (integration):
    async def test_with_real_db(isolated_db: DatabaseTestManager):
        # Test with real database behavior and constraints
        async with isolated_db.get_connection() as conn:
            # Real foreign keys, JSON validation, etc.
"""
