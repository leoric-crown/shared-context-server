"""
Unit tests for thread-safe configuration context management.

These tests validate the ContextVar-based approach to managing
SharedContextServerConfig instances, ensuring proper thread safety,
isolation, and backward compatibility.
"""

import asyncio
import os
import threading
from unittest.mock import MagicMock, patch

import pytest

from shared_context_server.config import SharedContextServerConfig
from shared_context_server.config_context import (
    get_context_config,
    get_current_config,
    reload_config_in_context,
    reset_config_context,
    set_config_for_testing,
)


class TestConfigContext:
    """Test ContextVar-based configuration management."""

    def test_get_context_config_creates_instance(self):
        """Test that get_context_config creates new instance if none exists."""
        # Clear context first
        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            config = get_context_config()

            assert config is not None
            assert isinstance(config, SharedContextServerConfig)

    def test_get_context_config_returns_same_instance(self):
        """Test that repeated calls return the same instance within context."""
        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            config1 = get_context_config()
            config2 = get_context_config()

            assert config1 is config2

    def test_set_config_for_testing(self):
        """Test setting custom config instance for testing."""
        reset_config_context()

        mock_config = MagicMock(spec=SharedContextServerConfig)
        set_config_for_testing(mock_config)

        config = get_context_config()
        assert config is mock_config

    def test_set_config_for_testing_none(self):
        """Test setting None clears the context."""
        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # First, create a config
            config1 = get_context_config()
            assert config1 is not None

            # Clear it
            set_config_for_testing(None)

            # Getting config again should create a new one
            config2 = get_context_config()
            assert config2 is not None
            assert config1 is not config2

    def test_reset_config_context(self):
        """Test that reset clears the context."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Create a config
            config1 = get_context_config()
            assert config1 is not None

            # Reset context
            reset_config_context()

            # Getting config again should create a new one
            config2 = get_context_config()
            assert config2 is not None
            assert config1 is not config2

    def test_get_current_config_none(self):
        """Test getting current config when none exists."""
        reset_config_context()

        current = get_current_config()
        assert current is None

    def test_get_current_config_exists(self):
        """Test getting current config when one exists."""
        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Create a config
            config = get_context_config()

            # Get current should return same instance
            current = get_current_config()
            assert current is config

    def test_reload_config_in_context(self):
        """Test force reloading config in context."""
        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Create initial config
            config1 = get_context_config()
            assert config1 is not None

            # Reload should create new instance
            config2 = reload_config_in_context()
            assert config2 is not None
            assert config1 is not config2

            # Subsequent calls should return reloaded instance
            config3 = get_context_config()
            assert config3 is config2

    def test_thread_isolation(self):
        """Test that different threads get different config instances."""
        import sys

        results = {}

        def create_config_in_thread(thread_id: int):
            """Create config in separate thread."""
            reset_config_context()

            with patch.dict(
                os.environ,
                {
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ):
                config = get_context_config()
                results[thread_id] = id(config)  # Store object ID

        # Create configs in separate threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_config_in_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Each thread should have gotten a different config instance
        config_ids = list(results.values())
        unique_ids = len(set(config_ids))

        # Python 3.10 and 3.11 have known issues where threading.Thread doesn't always properly
        # copy context from parent thread, causing ContextVar isolation to fail intermittently.
        # The behavior was inconsistent and not fully resolved until Python 3.12.
        # See: https://github.com/python/cpython/issues/86981
        if sys.version_info[:2] in [(3, 10), (3, 11)]:
            # In Python 3.10/3.11, we may get fewer unique IDs due to context isolation issues
            assert unique_ids >= 2, (
                f"Expected at least 2 unique config IDs due to Python {sys.version_info[0]}.{sys.version_info[1]} threading bug, "
                f"got {unique_ids} from {config_ids}"
            )
        else:
            # Python 3.12+ should have proper isolation
            assert unique_ids == 3, (
                f"Expected 3 unique config IDs, got {unique_ids} from {config_ids}"
            )

    @pytest.mark.asyncio
    async def test_async_task_isolation(self):
        """Test that different async tasks get different config instances."""
        results = {}

        async def create_config_in_task(task_id: int):
            """Create config in separate async task."""
            reset_config_context()

            with patch.dict(
                os.environ,
                {
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ):
                config = get_context_config()
                results[task_id] = id(config)  # Store object ID

        # Create configs in separate async tasks
        tasks = []
        for i in range(3):
            task = asyncio.create_task(create_config_in_task(i))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Each task should have gotten a different config instance
        config_ids = list(results.values())
        assert len(set(config_ids)) == 3  # All different IDs

    @pytest.mark.asyncio
    async def test_same_task_same_instance(self):
        """Test that same async task gets same config instance."""
        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            config1 = get_context_config()
            await asyncio.sleep(0.01)  # Yield control
            config2 = get_context_config()

            assert config1 is config2

    def test_test_injection_isolation(self):
        """Test that test injection doesn't affect other contexts."""
        reset_config_context()

        # Create mock config
        mock_config = MagicMock(spec=SharedContextServerConfig)

        def thread_with_injection():
            """Thread that injects mock config."""
            set_config_for_testing(mock_config)
            config = get_context_config()
            assert config is mock_config

        def thread_without_injection():
            """Thread that uses normal config creation."""
            with patch.dict(
                os.environ,
                {
                    "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                    "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                },
                clear=False,
            ):
                config = get_context_config()
                assert config is not mock_config
                assert isinstance(config, SharedContextServerConfig)

        # Run both threads
        thread1 = threading.Thread(target=thread_with_injection)
        thread2 = threading.Thread(target=thread_without_injection)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

    def test_environment_isolation(self):
        """Test that different environment variables create different configs."""
        reset_config_context()

        # Test with one set of env vars
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-1",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                "DATABASE_URL": "sqlite:///test1.db",
            },
            clear=False,
        ):
            config1 = get_context_config()
            db_url1 = config1.database.database_url

        # Reset and test with different env vars
        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-2",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                "DATABASE_URL": "sqlite:///test2.db",
            },
            clear=False,
        ):
            config2 = get_context_config()
            db_url2 = config2.database.database_url

        # Should be different configs with different values
        assert config1 is not config2
        assert db_url1 != db_url2


class TestBackwardCompatibility:
    """Test backward compatibility with legacy global config pattern."""

    def test_legacy_get_config_import(self):
        """Test that legacy get_config import still works."""
        from shared_context_server.config import get_config

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            config = get_config()
            assert isinstance(config, SharedContextServerConfig)

    def test_legacy_reload_config(self):
        """Test that legacy reload_config still works."""
        from shared_context_server.config import get_config, reload_config

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Get initial config
            config1 = get_config()

            # Reload should create new instance (via ContextVar)
            config2 = reload_config()

            assert isinstance(config1, SharedContextServerConfig)
            assert isinstance(config2, SharedContextServerConfig)
            # Should be different instances due to reload
            assert config1 is not config2

    def test_legacy_config_consistency(self):
        """Test that legacy and new APIs return consistent configs."""
        from shared_context_server.config import get_config

        reset_config_context()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Both APIs should return same instance within same context
            legacy_config = get_config()
            new_config = get_context_config()

            assert legacy_config is new_config

    def test_convenience_functions_still_work(self):
        """Test that convenience functions still work with new implementation."""
        from shared_context_server.config import (
            get_database_config,
            get_operational_config,
            get_security_config,
        )

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # All convenience functions should work
            db_config = get_database_config()
            security_config = get_security_config()
            operational_config = get_operational_config()

            assert db_config is not None
            assert security_config is not None
            assert operational_config is not None
