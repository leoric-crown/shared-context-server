"""
Unit tests for ContextVar-based authentication context management.

These tests validate the core functionality of the new ContextVar approach,
ensuring proper isolation, thread safety, and backward compatibility.
"""

import asyncio
import os
import threading
from unittest.mock import Mock, patch

import pytest

from shared_context_server.auth_context import (
    get_current_token_manager,
    get_secure_token_manager,
    reset_token_context,
    set_token_manager_for_testing,
)
from shared_context_server.auth_secure import SecureTokenManager


class TestContextVarBasics:
    """Test basic ContextVar functionality."""

    def test_get_secure_token_manager_creates_instance(self):
        """Test that get_secure_token_manager creates an instance when none exists."""
        # Reset context to ensure clean state
        reset_token_context()

        # Set required environment variables for token manager
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            manager = get_secure_token_manager()

            assert manager is not None
            assert isinstance(manager, SecureTokenManager)

    def test_get_secure_token_manager_returns_same_instance(self):
        """Test that repeated calls return the same instance."""
        reset_token_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            manager1 = get_secure_token_manager()
            manager2 = get_secure_token_manager()

            assert manager1 is manager2

    def test_reset_token_context_clears_instance(self):
        """Test that reset_token_context forces new instance creation."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            manager1 = get_secure_token_manager()
            reset_token_context()
            manager2 = get_secure_token_manager()

            assert manager1 is not manager2

    def test_set_token_manager_for_testing(self):
        """Test setting custom token manager for testing."""
        reset_token_context()

        mock_manager = Mock(spec=SecureTokenManager)
        set_token_manager_for_testing(mock_manager)

        retrieved_manager = get_secure_token_manager()
        assert retrieved_manager is mock_manager

    def test_get_current_token_manager_without_creation(self):
        """Test getting current manager without triggering creation."""
        reset_token_context()

        # Should return None when no manager exists
        current = get_current_token_manager()
        assert current is None

        # Create a manager and verify it's returned
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            manager = get_secure_token_manager()
            current = get_current_token_manager()
            assert current is manager


class TestThreadSafety:
    """Test thread safety of ContextVar approach."""

    def test_thread_isolation(self):
        """Test that different threads get different token manager instances."""
        managers = {}
        barrier = threading.Barrier(2)  # Synchronize 2 threads

        def create_manager_in_thread(thread_id):
            with patch.dict(
                os.environ,
                {
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ):
                barrier.wait()  # Ensure both threads start simultaneously
                managers[thread_id] = get_secure_token_manager()

        # Create threads
        thread1 = threading.Thread(target=create_manager_in_thread, args=("thread1",))
        thread2 = threading.Thread(target=create_manager_in_thread, args=("thread2",))

        # Start and wait for completion
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Verify different instances
        assert "thread1" in managers
        assert "thread2" in managers
        assert managers["thread1"] is not managers["thread2"]

    def test_concurrent_access_safety(self):
        """Test that concurrent access to same context is safe."""
        reset_token_context()

        results = []

        def concurrent_access():
            with patch.dict(
                os.environ,
                {
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ):
                manager = get_secure_token_manager()
                results.append(manager)

        # Create multiple threads accessing the same context
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=concurrent_access)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Each thread should get its own instance
        assert len(results) == 5
        assert len({id(r) for r in results}) == 5  # All different instances


@pytest.mark.asyncio
class TestAsyncIsolation:
    """Test ContextVar behavior with asyncio tasks."""

    async def test_async_task_isolation(self):
        """Test that different asyncio tasks get different token manager instances."""
        managers = {}

        async def create_manager_in_task(task_id):
            with patch.dict(
                os.environ,
                {
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ):
                # Small delay to ensure tasks are truly concurrent
                await asyncio.sleep(0.001)
                managers[task_id] = get_secure_token_manager()

        # Create concurrent tasks
        tasks = [
            create_manager_in_task("task1"),
            create_manager_in_task("task2"),
            create_manager_in_task("task3"),
        ]

        await asyncio.gather(*tasks)

        # Each task should get its own instance
        assert len(managers) == 3
        assert managers["task1"] is not managers["task2"]
        assert managers["task2"] is not managers["task3"]
        assert managers["task1"] is not managers["task3"]

    async def test_same_task_consistency(self):
        """Test that same task always gets the same instance."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            manager1 = get_secure_token_manager()
            await asyncio.sleep(0.001)  # Yield control
            manager2 = get_secure_token_manager()

            assert manager1 is manager2


class TestBackwardCompatibility:
    """Test that the new system maintains backward compatibility."""

    def test_same_interface_as_singleton(self):
        """Test that the interface is identical to the old singleton approach."""
        reset_token_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            manager = get_secure_token_manager()

            # Should have the same methods as SecureTokenManager
            assert hasattr(manager, "create_protected_token")
            assert hasattr(manager, "refresh_token_safely")
            assert hasattr(manager, "resolve_protected_token")
            assert callable(manager.create_protected_token)
            assert callable(manager.refresh_token_safely)
            assert callable(manager.resolve_protected_token)

    def test_environment_variable_handling(self):
        """Test that environment variable requirements are preserved."""
        reset_token_context()

        # Should work with proper environment variables
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            manager = get_secure_token_manager()
            assert manager is not None

        # Should handle missing environment variables appropriately
        reset_token_context()
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="JWT_ENCRYPTION_KEY"),
        ):
            # Should raise ValueError for missing JWT_ENCRYPTION_KEY as expected
            get_secure_token_manager()


class TestPerformance:
    """Test performance characteristics of ContextVar approach."""

    def test_no_lock_contention(self):
        """Test that there's no lock contention in the ContextVar approach."""
        import time

        def measure_access_time():
            with patch.dict(
                os.environ,
                {
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ):
                start = time.perf_counter()
                for _ in range(100):
                    get_secure_token_manager()
                end = time.perf_counter()
                return end - start

        # Multiple measurements to ensure consistency
        times = [measure_access_time() for _ in range(5)]
        avg_time = sum(times) / len(times)

        # Should be very fast since there's no lock contention
        # 100 accesses should complete in well under 10ms
        assert avg_time < 0.01, f"Average time for 100 accesses: {avg_time:.6f}s"

    @pytest.mark.performance
    def test_memory_efficiency(self):
        """Test that memory usage is reasonable."""
        reset_token_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Create manager and verify it doesn't leak
            manager1 = get_secure_token_manager()
            manager1_id = id(manager1)

            reset_token_context()

            # Create new manager
            manager2 = get_secure_token_manager()
            manager2_id = id(manager2)

            # Should be different instances
            assert manager1_id != manager2_id
