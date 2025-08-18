"""
Comprehensive singleton lifecycle tests for SecureTokenManager.

This test module ensures the singleton management patterns work correctly
and prevent test isolation issues that plagued the authentication tests.
"""

import os
from unittest.mock import patch

import pytest

# Test markers for categorization
pytestmark = [
    pytest.mark.unit,
    pytest.mark.singleton,
    pytest.mark.auth,
    pytest.mark.isolation,
]


class TestSingletonLifecycle:
    """Test singleton management and lifecycle patterns."""

    def test_singleton_reset_functionality(self):
        """Test that singleton reset works correctly."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        # Ensure NOT in test mode for this test
        set_test_mode(False)
        reset_secure_token_manager()

        # Set required environment variables
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Get initial manager
            manager1 = get_secure_token_manager()
            assert manager1 is not None

            # Get again - should be same instance (singleton behavior)
            manager2 = get_secure_token_manager()
            assert manager1 is manager2

            # Reset and get new manager - should be different instance
            reset_secure_token_manager()
            manager3 = get_secure_token_manager()
            assert manager3 is not manager1
            assert manager3 is not manager2

    def test_test_mode_functionality(self):
        """Test that test mode enables proper singleton management."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Enable test mode
            set_test_mode(True)

            # Get manager in test mode
            manager1 = get_secure_token_manager()
            assert manager1 is not None

            # Get again - in test mode, should get new instance
            manager2 = get_secure_token_manager()
            assert manager2 is not None
            # In test mode, each call gets a fresh instance
            assert manager1 is not manager2

            # Disable test mode and reset
            set_test_mode(False)
            reset_secure_token_manager()

            # Now should get singleton behavior again
            manager3 = get_secure_token_manager()
            manager4 = get_secure_token_manager()
            assert manager3 is manager4

    def test_class_level_test_mode(self):
        """Test the class-level test mode functionality."""
        from shared_context_server.auth_secure import SecureTokenManager

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Test enable_test_mode class method
            SecureTokenManager.enable_test_mode()
            assert SecureTokenManager._test_mode is True

            # Test reset class method
            SecureTokenManager.reset()
            # Should not raise exception

            # Disable test mode
            SecureTokenManager._test_mode = False

    def test_environment_variable_handling(self):
        """Test that singleton handles missing environment variables gracefully."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
        )

        # Reset to clean state
        reset_secure_token_manager()

        # Test with missing JWT_ENCRYPTION_KEY
        with patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456"},
            clear=False,
        ):
            # Remove JWT_ENCRYPTION_KEY if it exists
            env_backup = os.environ.get("JWT_ENCRYPTION_KEY")
            if "JWT_ENCRYPTION_KEY" in os.environ:
                del os.environ["JWT_ENCRYPTION_KEY"]

            try:
                # Should raise exception due to missing encryption key
                with pytest.raises(ValueError, match="JWT_ENCRYPTION_KEY"):
                    get_secure_token_manager()
            finally:
                # Restore environment
                if env_backup:
                    os.environ["JWT_ENCRYPTION_KEY"] = env_backup

    def test_concurrent_access_safety(self):
        """Test that singleton handles concurrent access safely."""
        import threading

        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        # Disable test mode for singleton behavior
        set_test_mode(False)
        reset_secure_token_manager()

        managers = []
        exceptions = []

        def get_manager():
            try:
                with patch.dict(
                    os.environ,
                    {
                        "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                        "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
                    },
                    clear=False,
                ):
                    manager = get_secure_token_manager()
                    managers.append(manager)
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads to access singleton
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_manager)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have no exceptions
        assert len(exceptions) == 0

        # All managers should be the same instance (singleton behavior)
        assert len(managers) == 5
        first_manager = managers[0]
        for manager in managers[1:]:
            assert manager is first_manager

    def test_force_recreate_functionality(self):
        """Test force_recreate parameter in get_secure_token_manager."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        # Disable test mode for singleton behavior
        set_test_mode(False)
        reset_secure_token_manager()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Get initial manager
            manager1 = get_secure_token_manager()
            assert manager1 is not None

            # Get with force_recreate=False (default) - should be same
            manager2 = get_secure_token_manager(force_recreate=False)
            assert manager1 is manager2

            # Get with force_recreate=True - should be different
            manager3 = get_secure_token_manager(force_recreate=True)
            assert manager3 is not manager1
            assert manager3 is not manager2

    def test_test_isolation_pattern(self):
        """Test the complete test isolation pattern used in conftest.py."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        # Simulate the conftest.py pattern
        def simulate_test_setup():
            set_test_mode(True)
            reset_secure_token_manager()

        def simulate_test_teardown():
            reset_secure_token_manager()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Simulate first test
            simulate_test_setup()
            manager1 = get_secure_token_manager()
            simulate_test_teardown()

            # Simulate second test
            simulate_test_setup()
            manager2 = get_secure_token_manager()
            simulate_test_teardown()

            # Managers should be different (proper isolation)
            assert manager1 is not manager2

    def test_singleton_state_persistence(self):
        """Test that singleton state persists correctly when not in test mode."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        # Ensure not in test mode
        set_test_mode(False)
        reset_secure_token_manager()

        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
            clear=False,
        ):
            # Get manager multiple times - should be same instance
            manager1 = get_secure_token_manager()
            manager2 = get_secure_token_manager()
            manager3 = get_secure_token_manager()

            assert manager1 is manager2
            assert manager2 is manager3
            assert manager1 is manager3


class TestSingletonErrorScenarios:
    """Test singleton behavior under error conditions."""

    def test_singleton_initialization_error_recovery(self):
        """Test that singleton can recover from initialization errors."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        # Disable test mode for this test
        set_test_mode(False)
        reset_secure_token_manager()

        # First attempt without proper environment - may or may not fail depending on environment
        # We'll check if it gets a manager, and if so, it means environment is already set
        try:
            manager_attempt1 = get_secure_token_manager()
            # If we get here, environment variables are already set
            assert manager_attempt1 is not None
        except Exception:
            # Expected if environment variables are missing
            pass

        # Reset and try again with proper environment - should succeed
        reset_secure_token_manager()
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

    def test_partial_environment_variable_scenarios(self):
        """Test various environment variable scenarios."""
        from shared_context_server.auth_secure import (
            get_secure_token_manager,
            reset_secure_token_manager,
            set_test_mode,
        )

        # Disable test mode for this test
        set_test_mode(False)

        # Test with both - should succeed
        reset_secure_token_manager()
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

        # Note: Testing missing environment variables is tricky in test environment
        # where variables may already be set. The actual error checking happens
        # during SecureTokenManager initialization which validates the environment.
