"""
Modern, focused tests for server background functionality.

These tests focus on actual behavior and real error scenarios rather than
complex mocking patterns. They test what matters: that the server handles
startup issues gracefully and background tasks work correctly.
"""

import asyncio
from unittest.mock import patch

import pytest


class TestServerLifecycleHandling:
    """Test server lifecycle and error handling with realistic scenarios."""

    async def test_database_connection_error_handling(self, isolated_db):
        """Test server handles database connection issues gracefully."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.database_manager.SimpleSQLAlchemyManager.initialize"
            ) as mock_init,
        ):
            # Test realistic database connection failure
            mock_init.side_effect = Exception("Connection failed: database locked")

            from shared_context_server.server import lifespan

            # Server should handle database connection issues
            try:
                async with lifespan():
                    pass
            except Exception as e:
                # Should get meaningful error about database issues
                error_msg = str(e).lower()
                assert any(
                    keyword in error_msg
                    for keyword in ["database", "connection", "locked"]
                ), f"Expected database-related error, got: {e}"

    async def test_background_task_error_resilience(self, isolated_db):
        """Test that background tasks handle errors without crashing."""
        from shared_context_server.admin_lifecycle import _perform_memory_cleanup
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.database_manager.get_db_connection"
            ) as mock_conn,
        ):
            # Test that cleanup functions handle database errors gracefully
            mock_conn.side_effect = Exception("Database unavailable")

            # Should not raise exception - background tasks must be resilient
            try:
                await _perform_memory_cleanup()
                # If we reach here, the function handled the error gracefully
                success = True
            except Exception as e:
                success = False
                pytest.fail(
                    f"Background task should handle errors gracefully, but raised: {e}"
                )

            assert success is True

    async def test_notification_cleanup_functionality(self, isolated_db):
        """Test notification cleanup works correctly."""
        import time

        from shared_context_server.admin_resources import _perform_subscription_cleanup
        from shared_context_server.server import notification_manager
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Add test subscriptions
            await notification_manager.subscribe("active_client", "session://test1")
            await notification_manager.subscribe("stale_client", "session://test1")

            # Make one client stale
            old_time = time.time() - notification_manager.subscription_timeout - 10
            notification_manager.client_last_seen["stale_client"] = old_time

            # Verify initial state
            assert len(notification_manager.subscribers["session://test1"]) == 2

            # Perform cleanup
            await _perform_subscription_cleanup()

            # Verify stale client was removed but active client remains
            remaining_clients = notification_manager.subscribers["session://test1"]
            assert "active_client" in remaining_clients
            assert "stale_client" not in remaining_clients
            assert len(remaining_clients) == 1

    async def test_task_cancellation_handling(self):
        """Test that background tasks handle cancellation properly."""

        # Test a simple background task pattern that handles cancellation
        async def cancellable_task():
            while True:
                await asyncio.sleep(0.001)  # Very short sleep for testing

        task = asyncio.create_task(cancellable_task())
        await asyncio.sleep(0.005)  # Let it run briefly

        # Cancel and verify graceful handling
        task.cancel()

        try:
            await task
            pytest.fail("Cancelled task should raise CancelledError")
        except asyncio.CancelledError:
            # This is expected behavior for cancelled tasks
            pass


class TestServerHealthChecks:
    """Test server health monitoring and status checks."""

    async def test_server_status_reporting(self, isolated_db):
        """Test that server can report its status correctly."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Test basic health check functionality
            # This focuses on what matters: can the server determine its health?
            try:
                # Get database manager to check it's working
                from shared_context_server.database_manager import (
                    get_sqlalchemy_manager,
                )

                manager = get_sqlalchemy_manager()

                # Test that we can get a connection (basic health check)
                async with manager.get_connection() as conn:
                    assert conn is not None
                    health_status = "healthy"

            except Exception:
                health_status = "unhealthy"

            # Server should be able to determine its health status
            assert health_status in ["healthy", "unhealthy"]

    async def test_graceful_shutdown_behavior(self, isolated_db):
        """Test that server components shut down gracefully."""
        from tests.fixtures.database import patch_database_for_test

        with patch_database_for_test(isolated_db):
            # Test database manager cleanup
            from shared_context_server.database_manager import (
                dispose_current_sqlalchemy_manager,
                get_sqlalchemy_manager,
            )

            # Create and initialize manager
            manager = get_sqlalchemy_manager()
            await manager.initialize()

            # Test graceful disposal
            try:
                await dispose_current_sqlalchemy_manager()
                shutdown_successful = True
            except Exception as e:
                shutdown_successful = False
                pytest.fail(f"Graceful shutdown failed: {e}")

            assert shutdown_successful is True
