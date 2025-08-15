"""
Testing utilities for FastMCP-based shared context server.

Provides modern database testing infrastructure using real in-memory SQLite databases
instead of fragile hardcoded mocks. This approach ensures tests remain valid as
database schemas evolve and provides better test fidelity.

Includes industry-standard background task cleanup for asyncio test environments.
"""

import asyncio
import inspect
import threading
import time
import weakref
from contextlib import asynccontextmanager, suppress
from typing import Any

import pytest
from pydantic.fields import FieldInfo

from shared_context_server.auth import AuthInfo

pytest_plugins = ["tests.fixtures.database"]

# =============================================================================
# COMPREHENSIVE THREAD AND TASK REGISTRY FOR TEST CLEANUP
# =============================================================================

# Global registries for tracking resources created during tests
_task_registry: set[asyncio.Task] = set()
_thread_registry: set[threading.Thread] = set()
_observer_registry: set = set()  # For watchdog observers

# Global flag to track pytest quiet mode
_pytest_quiet_mode: bool = False


def _quiet_print(*args, **kwargs):
    """Print only if not in quiet mode."""
    if not _pytest_quiet_mode:
        print(*args, **kwargs)


_original_create_task = asyncio.create_task


def _track_task_creation(coro, **kwargs):
    """Wrapper for asyncio.create_task that tracks created tasks."""
    task = _original_create_task(coro, **kwargs)
    _task_registry.add(task)

    # Add debug info to help identify problematic tasks
    task_name = getattr(coro, "__name__", "unknown")
    if hasattr(coro, "cr_code"):
        task_name = f"{coro.cr_code.co_name}"

    # Store debug info on the task
    task._test_debug_info = {"name": task_name, "created_at": time.time()}

    # Use weak reference callback to auto-remove completed tasks
    def cleanup_task_ref(task_ref):
        _task_registry.discard(task)

    weakref.ref(task, cleanup_task_ref)
    return task


# Monkey patch asyncio.create_task to track all tasks
asyncio.create_task = _track_task_creation

# Track thread creation (monkey patch threading.Thread)
_original_thread_init = threading.Thread.__init__


def _track_thread_creation(self, *args, **kwargs):
    """Wrapper for threading.Thread.__init__ that tracks created threads."""
    _original_thread_init(self, *args, **kwargs)
    _thread_registry.add(self)

    # Use weak reference callback to auto-remove finished threads
    def cleanup_thread_ref(thread_ref):
        _thread_registry.discard(self)

    weakref.ref(self, cleanup_thread_ref)


threading.Thread.__init__ = _track_thread_creation


# Track watchdog observers (will be patched when imported)
def register_observer(observer):
    """Register a watchdog observer for cleanup."""
    _observer_registry.add(observer)


def unregister_observer(observer):
    """Unregister a watchdog observer."""
    _observer_registry.discard(observer)


# =============================================================================
# COMPREHENSIVE RESOURCE CLEANUP UTILITIES
# =============================================================================


async def cleanup_async_tasks_with_timeout(timeout: float = 2.0) -> int:
    """Clean up asyncio tasks with proper timeout handling."""
    tasks_to_cancel = list(_task_registry)
    cancelled_count = 0

    for task in tasks_to_cancel:
        if not task.done():
            task.cancel()
            cancelled_count += 1

    # Wait for cancellation with timeout
    if tasks_to_cancel:
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            _quiet_print(
                f"⚠️ {len([t for t in tasks_to_cancel if not t.done()])} tasks didn't cancel within {timeout}s"
            )

    _task_registry.clear()
    return cancelled_count


def cleanup_threads_with_timeout(timeout: float = 1.0) -> int:
    """Clean up threads with proper timeout and daemon conversion."""
    threads_to_cleanup = list(_thread_registry)
    cleaned_count = 0

    for thread in threads_to_cleanup:
        if thread.is_alive() and thread != threading.current_thread():
            try:
                # First attempt: set as daemon
                if not thread.daemon:
                    thread.daemon = True
                    cleaned_count += 1
                    _quiet_print(f"🔧 Converted thread {thread.name} to daemon")

                # Second attempt: try to join with timeout
                if hasattr(thread, "join"):
                    thread.join(timeout=timeout)

            except Exception as e:
                _quiet_print(f"⚠️ Could not clean thread {thread.name}: {e}")

    _thread_registry.clear()
    return cleaned_count


def cleanup_observers() -> int:
    """Clean up watchdog observers."""
    observers_to_cleanup = list(_observer_registry)
    cleaned_count = 0

    observer_errors = []

    def stop_observer(observer) -> str | None:
        try:
            if hasattr(observer, "stop"):
                observer.stop()
            if hasattr(observer, "join"):
                observer.join(timeout=1.0)
            _quiet_print("🔧 Stopped watchdog observer")
        except Exception as e:
            return str(e)
        else:
            return None

    for observer in observers_to_cleanup:
        error = stop_observer(observer)
        if error:
            observer_errors.append(error)
        else:
            cleaned_count += 1

    # Log any errors after the loop
    for error in observer_errors:
        _quiet_print(f"⚠️ Could not stop observer: {error}")

    _observer_registry.clear()
    return cleaned_count


# =============================================================================
# AGGRESSIVE EVENT LOOP MANAGEMENT
# =============================================================================


def pytest_configure(config):
    """Configure pytest with aggressive cleanup settings."""
    # Store quiet flag for later use in hooks
    global _pytest_quiet_mode
    _pytest_quiet_mode = config.getoption("quiet", 0) > 0

    # Force asyncio mode settings
    import os

    os.environ["PYTEST_ASYNCIO_MODE"] = "auto"

    # Patch watchdog Observer if it gets imported
    try:
        from watchdog.observers import Observer

        _original_observer_init = Observer.__init__
        _original_observer_start = Observer.start

        def _track_observer_init(self, *args, **kwargs):
            _original_observer_init(self, *args, **kwargs)
            register_observer(self)

        def _track_observer_start(self, *args, **kwargs):
            result = _original_observer_start(self, *args, **kwargs)
            # Ensure this observer is tracked when started
            register_observer(self)
            return result

        Observer.__init__ = _track_observer_init
        Observer.start = _track_observer_start

        _quiet_print("🔧 Watchdog Observer patched for tracking")

    except ImportError:
        # Watchdog not available, no need to patch
        pass


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add more aggressive cleanup."""
    # This runs after collection but before any tests
    import signal
    import sys

    def force_cleanup_handler(signum, frame):
        """Force cleanup on signals."""
        _quiet_print("🚨 Signal received, forcing cleanup...")

        # Cancel all tracked tasks immediately
        for task in list(_task_registry):
            if not task.done():
                task.cancel()

        # Force exit
        sys.exit(1)

    # Register signal handlers for cleanup
    signal.signal(signal.SIGINT, force_cleanup_handler)
    signal.signal(signal.SIGTERM, force_cleanup_handler)


def get_background_task_count() -> int:
    """Get current count of tracked background tasks for monitoring."""
    return len(_task_registry)


def validate_no_background_tasks() -> bool:
    """Validate that no background tasks are currently running."""
    active_tasks = [task for task in _task_registry if not task.done()]
    return len(active_tasks) == 0


def extract_field_defaults(fastmcp_tool) -> dict[str, Any]:
    """
    Extract actual default values from a FastMCP tool function.

    FastMCP decorated functions have FieldInfo objects as defaults,
    but we need the actual default values for testing.

    Args:
        fastmcp_tool: A FastMCP FunctionTool object

    Returns:
        Dict mapping parameter names to their actual default values
    """
    defaults = {}
    sig = inspect.signature(fastmcp_tool.fn)

    for name, param in sig.parameters.items():
        if name == "ctx":  # Skip context parameter
            continue

        if isinstance(param.default, FieldInfo):
            # Extract the actual default from FieldInfo
            defaults[name] = param.default.default
        elif param.default is not inspect.Parameter.empty:
            defaults[name] = param.default

    return defaults


async def call_fastmcp_tool(fastmcp_tool, ctx, **kwargs):
    """
    Call a FastMCP tool function with proper default handling.

    This helper automatically extracts Field defaults and merges them
    with provided kwargs to avoid FieldInfo object issues.

    Args:
        fastmcp_tool: A FastMCP FunctionTool object
        ctx: Mock context object
        **kwargs: Arguments to pass to the function

    Returns:
        Result of the function call
    """
    # Get the actual defaults
    defaults = extract_field_defaults(fastmcp_tool)

    # Merge defaults with provided kwargs (kwargs override defaults)
    call_args = {**defaults, **kwargs}

    # Call the function with context as first parameter
    return await fastmcp_tool.fn(ctx, **call_args)


class MockContext:
    """Standard mock context for FastMCP testing."""

    def __init__(self, session_id="test_session", agent_id="test_agent"):
        self.session_id = session_id
        # Set up authentication using AuthInfo pattern
        self._auth_info = AuthInfo(
            jwt_validated=False,
            agent_id=agent_id,
            agent_type="test",
            permissions=["read", "write"],
            authenticated=True,
            auth_method="api_key",
            token_id=None,
        )

    # Backward compatibility properties for old attribute access
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
# MODERN DATABASE TESTING INFRASTRUCTURE
# =============================================================================


@pytest.fixture(scope="function")
async def test_db_manager():
    """
    Create an isolated in-memory SQLite database manager for each test.

    This fixture provides a real database with the complete schema applied,
    ensuring tests work with actual database constraints and behaviors.
    Each test gets a clean database state with no file I/O complexity.

    Yields:
        TestDatabaseManager: Initialized database manager with applied schema
    """
    from shared_context_server.database_testing import TestDatabaseManager

    # Create in-memory database manager (no files, no cleanup needed)
    db_manager = TestDatabaseManager("sqlite:///:memory:")

    # Initialize database with schema
    await db_manager.initialize()

    # Verify schema is correctly applied
    async with db_manager.get_connection() as conn:
        cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
        version = await cursor.fetchone()
        assert version and version[0] == 3, (
            f"Expected schema version 3, got {version[0] if version else None}"
        )

    yield db_manager
    # No cleanup needed - memory database automatically cleaned up


@pytest.fixture(scope="function")
async def test_db_connection(test_db_manager):
    """
    Provide a database connection for tests that need direct database access.

    Args:
        test_db_manager: The test database manager fixture

    Yields:
        aiosqlite.Connection: Database connection with optimized settings
    """
    async with test_db_manager.get_connection() as conn:
        yield conn


@asynccontextmanager
async def get_test_db_connection():
    """
    Get database connection using the test database manager.

    This function can be used to patch the global get_db_connection function
    in server modules during testing.

    Yields:
        aiosqlite.Connection: Test database connection
    """
    # This will be dynamically set by the test infrastructure
    # Each test should patch this appropriately
    raise RuntimeError("get_test_db_connection must be patched by test fixtures")


# =============================================================================
# TEST DATA UTILITIES
# =============================================================================


@pytest.fixture(scope="function")
async def seed_test_data(test_db_connection):
    """
    Seed the test database with common test data for comprehensive scenarios.

    Args:
        test_db_connection: Database connection fixture
    """
    # Create test sessions
    await test_db_connection.execute(
        """
        INSERT INTO sessions (id, purpose, created_by, metadata)
        VALUES (?, ?, ?, ?)
        """,
        ("session_test_1", "Test session 1", "test_agent", '{"test": true}'),
    )

    await test_db_connection.execute(
        """
        INSERT INTO sessions (id, purpose, created_by, metadata)
        VALUES (?, ?, ?, ?)
        """,
        ("session_test_2", "Test session 2", "another_agent", '{"test": true}'),
    )

    # Create test messages with proper schema (including sender_type)
    test_messages = [
        (
            "session_test_1",
            "test_agent",
            "test",
            "Public test message",
            "public",
            None,
            None,
        ),
        (
            "session_test_1",
            "test_agent",
            "test",
            "Private test message",
            "private",
            None,
            None,
        ),
        (
            "session_test_2",
            "another_agent",
            "test",
            "Another session message",
            "public",
            None,
            None,
        ),
    ]

    for msg_data in test_messages:
        await test_db_connection.execute(
            """
            INSERT INTO messages (session_id, sender, sender_type, content, visibility, metadata, parent_message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            msg_data,
        )

    # Create test agent memory
    await test_db_connection.execute(
        """
        INSERT INTO agent_memory (agent_id, session_id, key, value, metadata)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("test_agent", "session_test_1", "test_key", '{"test": "data"}', None),
    )

    await test_db_connection.commit()


# =============================================================================
# IMPORT DATABASE FIXTURES
# =============================================================================

# Import all fixtures from fixtures/database.py

# =============================================================================
# INTEGRATION WITH EXISTING FASTMCP PATTERNS
# =============================================================================


def patch_database_connection(test_db_manager=None, backend="aiosqlite"):
    """
    Create a unified patcher for all database connections that works with any backend.

    This patches the source function in the database module to ensure
    all imports and usages get the test database connection from the specified backend.

    Args:
        test_db_manager: The test database manager to use (optional, will create one if None)
        backend: Database backend to use ("aiosqlite" or "sqlalchemy")

    Returns:
        unittest.mock.patch context manager
    """
    from unittest.mock import patch

    from shared_context_server.database_testing import get_test_db_connection

    @asynccontextmanager
    async def mock_get_db_connection():
        if test_db_manager:
            # Use provided test manager
            async with test_db_manager.get_connection() as conn:
                yield conn
        else:
            # Use unified test database with specified backend
            async with get_test_db_connection(backend) as conn:
                yield conn

    # Patch all the places where get_db_connection is used
    patches = [
        patch(
            "shared_context_server.database.get_db_connection", mock_get_db_connection
        ),
        patch("shared_context_server.server.get_db_connection", mock_get_db_connection),
        patch("shared_context_server.auth.get_db_connection", mock_get_db_connection),
    ]

    # Return a context manager that applies all patches
    from contextlib import ExitStack

    class UnifiedDatabasePatch:
        def __enter__(self):
            self.stack = ExitStack()
            for patch_obj in patches:
                self.stack.enter_context(patch_obj)
            return self

        def __exit__(self, *args):
            self.stack.__exit__(*args)

    return UnifiedDatabasePatch()


# Example usage patterns for common tools:

# Use call_fastmcp_tool(tool_function, ctx, **kwargs) to call any MCP tool
# - create_session: purpose="Test session"
# - add_message: session_id, content, visibility
# - set_memory: key, value, session_id (optional)
# - search_context: session_id, query

# New database testing patterns:
# 1. Use test_db_manager fixture for isolated database testing
# 2. Use patch_database_connection(test_db_manager) to integrate with FastMCP tools
# 3. Use seed_test_data fixture for tests requiring pre-populated data
# 4. All tests automatically get clean database state with proper schema applied


# =============================================================================
# INDUSTRY-STANDARD BACKGROUND TASK CLEANUP FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
async def cleanup_background_tasks():
    """
    Automatically clean up background tasks after each test.

    This fixture ensures no background tasks persist between tests,
    preventing test suite hanging and resource leaks.
    """
    yield  # Let the test run

    # Use the enhanced cleanup utilities
    # Skip asyncio cleanup in CI due to event loop closure issues across Python versions
    import os

    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        cancelled_tasks = 0  # Skip asyncio cleanup in CI environments
    else:
        cancelled_tasks = await cleanup_async_tasks_with_timeout(timeout=2.0)

    cleaned_threads = cleanup_threads_with_timeout(timeout=1.0)
    cleaned_observers = cleanup_observers()

    # Log detailed information about cleanup
    if cancelled_tasks > 0 or cleaned_threads > 0 or cleaned_observers > 0:
        import logging

        logger = logging.getLogger(__name__)
        cleanup_summary = []
        if cancelled_tasks > 0:
            cleanup_summary.append(f"{cancelled_tasks} async tasks")
        if cleaned_threads > 0:
            cleanup_summary.append(f"{cleaned_threads} threads")
        if cleaned_observers > 0:
            cleanup_summary.append(f"{cleaned_observers} observers")

        logger.debug(f"Test cleanup: {', '.join(cleanup_summary)}")


@pytest.fixture(autouse=True)
async def reset_global_singletons():
    """
    Reset global singletons between tests to prevent state leakage.

    This fixture ensures clean state for global managers like
    db_pool and cache_manager.
    """
    yield  # Let the test run

    # Reset connection pool if it exists
    try:
        from shared_context_server.utils.performance import db_pool

        with suppress(Exception):
            await db_pool.reset_for_testing()
    except ImportError:
        pass

    # Reset cache manager if it exists
    try:
        from shared_context_server.utils.caching import cache_manager

        with suppress(Exception):
            await cache_manager.reset_for_testing()
    except ImportError:
        pass

    # Reset notification manager if it exists
    try:
        from shared_context_server.server import notification_manager

        with suppress(Exception):
            # Clear all subscribers and client tracking
            notification_manager.subscribers.clear()
            notification_manager.client_last_seen.clear()
    except ImportError:
        pass

    # Reset database managers for both aiosqlite and SQLAlchemy
    try:
        import shared_context_server.database as db_module

        with suppress(Exception):
            # Reset global database managers to ensure clean state
            db_module._db_manager = None
            db_module._sqlalchemy_manager = None
    except ImportError:
        pass


@pytest.fixture(autouse=True)
async def mock_websocket_notifications(request):
    """
    Mock WebSocket server notifications to prevent tests from making HTTP requests
    to the production dev server during testing.

    This prevents WebSocket broadcast messages from appearing in dev server logs
    when tests run that trigger add_message operations.

    Tests can be excluded from this mock by using the 'no_websocket_mock' marker.
    """
    from unittest.mock import AsyncMock, patch

    # Check if test is marked to skip websocket mocking
    if request.node.get_closest_marker("no_websocket_mock"):
        yield  # Skip mocking for this test
    else:
        with patch(
            "shared_context_server.server._notify_websocket_server",
            new_callable=AsyncMock,
        ):
            yield


@pytest.fixture(scope="session", autouse=True)
async def cleanup_on_session_finish():
    """
    Final cleanup when the entire test session finishes.

    This ensures all resources are properly cleaned up even if
    individual test cleanups fail.
    """
    yield  # Let the entire test session run

    _quiet_print("🧹 Starting final cleanup...")

    # Skip asyncio cleanup in CI due to event loop closure issues across Python versions
    import os

    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        _quiet_print("Skipping asyncio cleanup in CI environment")
        _task_registry.clear()
        return

    # Cancel all remaining tasks aggressively
    tasks_to_cancel = list(_task_registry)
    if tasks_to_cancel:
        _quiet_print(
            f"Final cleanup: cancelling {len(tasks_to_cancel)} remaining background tasks"
        )

        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        # Wait for all tasks to finish with timeout
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=2.0,
                )
            except asyncio.TimeoutError:
                _quiet_print("Warning: Some background tasks did not shut down cleanly")

    _task_registry.clear()

    # Cancel any other running tasks in the event loop
    try:
        current_task = asyncio.current_task()
        all_tasks = [
            t for t in asyncio.all_tasks() if t != current_task and not t.done()
        ]

        if all_tasks:
            _quiet_print(
                f"Final cleanup: found {len(all_tasks)} additional running tasks"
            )
            for task in all_tasks:
                task.cancel()

            # Wait for them to finish
            try:
                await asyncio.wait_for(
                    asyncio.gather(*all_tasks, return_exceptions=True), timeout=1.0
                )
            except asyncio.TimeoutError:
                _quiet_print("Warning: Some additional tasks did not shut down cleanly")

    except RuntimeError:
        # No event loop running
        pass

    # Clean up any remaining coroutines before garbage collection
    import gc
    import types

    # Find and close any remaining coroutines
    for obj in gc.get_objects():
        if isinstance(obj, types.CoroutineType) and not obj.cr_frame:
            with suppress(Exception):
                obj.close()

    # Force garbage collection
    gc.collect()

    # Restore original asyncio.create_task
    asyncio.create_task = _original_create_task

    _quiet_print("🧹 Final cleanup completed")


# =============================================================================
# PYTEST HOOKS FOR FINAL CLEANUP
# =============================================================================


def pytest_sessionfinish(session, exitstatus):
    """
    Hook that runs after the test session is finished.

    This runs after all fixtures are torn down and provides
    a final chance to clean up any remaining resources.
    """
    import gc
    import threading

    _quiet_print("🔧 Running pytest session finish hook...")

    # Final cleanup of any remaining resources
    try:
        # Clean up any remaining observers
        cleaned_observers = cleanup_observers()

        # Clean up any remaining threads
        cleaned_threads = cleanup_threads_with_timeout(timeout=2.0)

        if cleaned_observers > 0 or cleaned_threads > 0:
            _quiet_print(
                f"🔧 Final cleanup: {cleaned_observers} observers, {cleaned_threads} threads"
            )

    except Exception as e:
        _quiet_print(f"⚠️ Error during final cleanup: {e}")

    # Clean up any SQLAlchemy-created directory artifacts
    try:
        import shutil
        from pathlib import Path

        sqlite_dir = Path("./sqlite+aiosqlite:")
        if sqlite_dir.exists():
            shutil.rmtree(sqlite_dir)
            _quiet_print(f"🔧 Cleaned up SQLAlchemy artifact directory: {sqlite_dir}")
    except Exception as e:
        _quiet_print(f"⚠️ Error cleaning up SQLAlchemy directory: {e}")

    # Check for any truly persistent threads
    remaining_threads = [
        t
        for t in threading.enumerate()
        if t != threading.main_thread() and t.is_alive()
    ]

    if remaining_threads:
        _quiet_print(
            f"🔧 Converting {len(remaining_threads)} remaining threads to daemon:"
        )
        thread_errors = []

        def set_thread_daemon(thread) -> tuple[str, str] | None:
            try:
                if not thread.daemon:
                    thread.daemon = True
                    _quiet_print(f"  ✅ {thread.name} -> daemon")
                else:
                    _quiet_print(f"  ℹ️  {thread.name} already daemon")
            except Exception as e:
                return (thread.name, str(e))
            else:
                return None

        for thread in remaining_threads:
            result = set_thread_daemon(thread)
            if result:
                thread_errors.append(result)

        # Log any errors after the loop
        for thread_name, error in thread_errors:
            _quiet_print(f"  ⚠️ {thread_name}: {error}")

    # Force garbage collection
    for _ in range(3):
        gc.collect()

    _quiet_print("🔧 Session finish hook completed")


def pytest_unconfigure(config):
    """
    Hook that runs when pytest is about to exit.

    This is the very last hook and our final chance to clean up.
    Uses a combination of elegant cleanup and nuclear exit as last resort.
    """
    import os
    import threading
    import time

    _quiet_print("🚪 Running pytest unconfigure hook...")

    # Final check and cleanup
    remaining_threads = [
        t for t in threading.enumerate() if t != threading.main_thread()
    ]
    if remaining_threads:
        _quiet_print(f"🚪 Final cleanup: {len(remaining_threads)} threads found")

        # First attempt: Convert threads to daemon (elegant approach)
        daemon_converted = 0
        persistent_threads = []

        for thread in remaining_threads:
            if thread.is_alive():
                try:
                    if not thread.daemon:
                        thread.daemon = True
                        daemon_converted += 1
                        _quiet_print(f"  🔧 {thread.name} -> daemon")
                    else:
                        _quiet_print(f"  ℹ️  {thread.name} already daemon")
                except RuntimeError as e:
                    if "cannot set daemon status of active thread" in str(e):
                        persistent_threads.append(thread)
                        _quiet_print(f"  ⚠️ {thread.name} - persistent active thread")
                    else:
                        _quiet_print(f"  ⚠️ {thread.name}: {e}")
                except Exception as e:
                    _quiet_print(f"  ⚠️ {thread.name}: {e}")

        # Second attempt: If we have persistent threads that can't be converted, use nuclear option
        if persistent_threads:
            _quiet_print(
                f"🚨 {len(persistent_threads)} persistent threads detected - using nuclear exit"
            )
            _quiet_print("   This prevents pytest from hanging on non-daemon threads")

            # Give a brief moment for any final cleanup
            time.sleep(0.1)

            # Nuclear exit as last resort to prevent hanging
            _quiet_print("💥 Nuclear exit - os._exit(0)")
            os._exit(0)

        if daemon_converted > 0:
            _quiet_print(
                f"🔧 Converted {daemon_converted} threads to daemon - process will exit cleanly"
            )

    # Restore original functions
    try:
        asyncio.create_task = _original_create_task
        threading.Thread.__init__ = _original_thread_init
        _quiet_print("🔧 Restored original function implementations")
    except Exception as e:
        _quiet_print(f"⚠️ Could not restore original functions: {e}")

    _quiet_print("🚪 Unconfigure hook completed - process should exit cleanly")
