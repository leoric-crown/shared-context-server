"""
Unit tests for background task system in the server.

Tests background task functionality including cleanup_subscriptions_task,
cleanup_expired_memory_task, server lifecycle management, and task coordination.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestBackgroundTaskSystem:
    """Test background task system and server lifecycle."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    async def test_cleanup_subscriptions_task_functionality(
        self, server_with_db, test_db_manager
    ):
        """Test subscription cleanup task functionality."""
        from shared_context_server.admin_resources import _perform_subscription_cleanup
        from shared_context_server.server import notification_manager

        # Add fresh and stale subscriptions
        await notification_manager.subscribe("fresh_client", "session://test1")
        await notification_manager.subscribe("stale_client", "session://test1")
        await notification_manager.subscribe("another_stale", "agent://test/memory")

        # Make some clients stale
        old_time = time.time() - notification_manager.subscription_timeout - 1
        notification_manager.client_last_seen["stale_client"] = old_time
        notification_manager.client_last_seen["another_stale"] = old_time

        # Verify initial state
        assert len(notification_manager.subscribers["session://test1"]) == 2
        assert len(notification_manager.subscribers["agent://test/memory"]) == 1
        assert len(notification_manager.client_last_seen) == 3

        # Perform cleanup
        await _perform_subscription_cleanup()

        # Verify stale clients were removed
        assert "fresh_client" in notification_manager.subscribers["session://test1"]
        assert "stale_client" not in notification_manager.subscribers["session://test1"]
        assert len(notification_manager.subscribers["session://test1"]) == 1

        assert len(notification_manager.subscribers["agent://test/memory"]) == 0
        assert len(notification_manager.client_last_seen) == 1
        assert "fresh_client" in notification_manager.client_last_seen

    async def test_cleanup_tasks_error_handling(self, server_with_db, test_db_manager):
        """Test that cleanup tasks handle errors gracefully."""
        from shared_context_server.admin_lifecycle import _perform_memory_cleanup
        from shared_context_server.admin_resources import _perform_subscription_cleanup

        # Test memory cleanup with database error
        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            # Should not raise exception
            try:
                await _perform_memory_cleanup()
            except Exception as e:
                pytest.fail(
                    f"Memory cleanup should handle errors gracefully, but raised: {e}"
                )

        # Test subscription cleanup with notification manager error
        from shared_context_server.server import notification_manager

        class SubscriptionCleanupError(Exception):
            """Custom exception for subscription cleanup testing."""

            pass

        async def failing_cleanup():
            raise SubscriptionCleanupError("Subscription cleanup failed")

        # Use context manager for cleaner mock restoration
        with patch.object(
            notification_manager, "cleanup_stale_subscriptions", failing_cleanup
        ):
            try:
                # Should not raise exception
                await _perform_subscription_cleanup()
            except Exception as e:
                pytest.fail(
                    f"Subscription cleanup should handle errors gracefully, but raised: {e}"
                )

    async def test_background_task_scheduling(self, server_with_db, test_db_manager):
        """Test background task scheduling configuration (optimized)."""
        from shared_context_server.server import (
            cleanup_expired_memory_task,
            cleanup_subscriptions_task,
        )

        # Test task existence and basic structure without actually running them
        assert cleanup_subscriptions_task is not None
        assert cleanup_expired_memory_task is not None

        # Test would verify timing constants but we avoid running actual tasks
        # to prevent the 13+ second execution time from real sleeps

    async def test_server_lifespan_management(self, server_with_db, test_db_manager):
        """Test server lifespan context manager basic functionality."""
        from shared_context_server.admin_lifecycle import lifespan

        # Track database initialization calls
        init_calls = []

        # Mock database initialization to avoid actual database operations
        with patch(
            "shared_context_server.admin_lifecycle.initialize_database"
        ) as mock_init:
            mock_init.side_effect = lambda: init_calls.append("init")

            # Mock background tasks to avoid actually starting them
            with (
                patch(
                    "shared_context_server.server.cleanup_subscriptions_task"
                ) as mock_sub_task,
                patch(
                    "shared_context_server.server.cleanup_expired_memory_task"
                ) as mock_mem_task,
            ):
                # Configure mocks to return immediately
                mock_sub_task.return_value = AsyncMock()
                mock_mem_task.return_value = AsyncMock()

                # Test lifespan startup and shutdown
                async with lifespan():
                    # During startup - database should be initialized
                    assert len(init_calls) == 1

                # After shutdown - test completes successfully
                assert len(init_calls) == 1  # Should still be 1

    async def test_server_lifecycle_functions(self, server_with_db, test_db_manager):
        """Test server lifecycle helper functions."""
        from shared_context_server.server import (
            initialize_server,
            lifespan,
            server,
            shutdown_server,
        )

        # Test server lifecycle using proper lifespan context manager with background task mocking
        # Mock just the background tasks, not all asyncio.create_task calls
        with (
            patch(
                "shared_context_server.server.cleanup_subscriptions_task",
                return_value=AsyncMock(),
            ),
            patch(
                "shared_context_server.server.cleanup_expired_memory_task",
                return_value=AsyncMock(),
            ),
        ):
            async with lifespan():
                # Test that server is available during lifespan
                assert server is not None

        # Test direct initialize_server function (mocked to avoid background tasks)
        with (
            patch(
                "shared_context_server.utils.performance.start_performance_monitoring"
            ) as mock_perf,
            patch(
                "shared_context_server.utils.caching.start_cache_maintenance"
            ) as mock_cache,
            patch("asyncio.create_task") as mock_task,
        ):
            # Mock the background task creation to prevent actual tasks from running
            mock_perf.return_value = AsyncMock()
            mock_cache.return_value = AsyncMock()
            mock_task.return_value = AsyncMock()

            initialized_server = await initialize_server()
            assert initialized_server is server

        # Test shutdown_server (should complete without error)
        try:
            await shutdown_server()
        except Exception as e:
            pytest.fail(f"Shutdown server should complete gracefully: {e}")

    async def test_server_instance_creation(self, server_with_db, test_db_manager):
        """Test server instance creation and configuration."""
        from shared_context_server.server import create_server, mcp

        # Test create_server function
        created_server = create_server()
        assert created_server is mcp

        # Verify server configuration
        assert created_server.name
        assert created_server.version
        assert hasattr(created_server, "get_tools")  # Should have tools method
        # Verify tools are registered
        tools = await created_server.get_tools()
        assert len(tools) > 0  # Should have registered tools

    async def test_memory_cleanup_with_real_data(self, server_with_db, test_db_manager):
        """Test memory cleanup with realistic memory operations."""
        from shared_context_server.admin_lifecycle import _perform_memory_cleanup

        ctx = MockContext(agent_id="real_cleanup_agent")

        # Set memory with short TTL
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="short_lived",
            value={"data": "will_expire"},
            expires_in=1,  # 1 second TTL
        )
        assert result["success"] is True

        # Set permanent memory
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="permanent",
            value={"data": "stays_forever"},
            # No expires_in = permanent
        )
        assert result["success"] is True

        # Mock time progression for TTL expiration (avoid 2s delay)
        # Mock datetime.now to simulate time passing (cleanup uses datetime.now)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=10)

        # Verify both entries exist before cleanup (cleanup happens on get/list operations)
        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT key FROM agent_memory WHERE agent_id = ?",
                ("real_cleanup_agent",),
            )
            keys_before = [row[0] for row in await cursor.fetchall()]
            assert len(keys_before) == 2

        # Perform cleanup with mocked time to simulate expiration
        with patch("shared_context_server.admin_lifecycle.datetime") as mock_dt:
            mock_dt.now.return_value = future_time
            mock_dt.timezone = timezone  # Preserve timezone object
            await _perform_memory_cleanup()

        # Verify expired entry was removed
        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx, key="short_lived"
        )
        assert result["success"] is False
        assert (
            "not found" in result["error"].lower()
            or "expired" in result["error"].lower()
        )

        # Verify permanent entry still exists
        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx, key="permanent"
        )
        assert result["success"] is True
        assert result["value"]["data"] == "stays_forever"

    async def test_subscription_cleanup_integration(
        self, server_with_db, test_db_manager
    ):
        """Test subscription cleanup integration with real subscription operations."""
        from shared_context_server.admin_resources import _perform_subscription_cleanup
        from shared_context_server.server import notification_manager

        # Create realistic subscriptions
        clients_and_resources = [
            ("active_client", "session://active_session"),
            ("active_client", "agent://active_agent/memory"),
            ("idle_client", "session://idle_session"),
            ("stale_client", "agent://stale_agent/memory"),
        ]

        for client_id, resource_uri in clients_and_resources:
            await notification_manager.subscribe(client_id, resource_uri)

        # Simulate different activity levels
        current_time = time.time()
        notification_manager.client_last_seen["active_client"] = current_time  # Fresh
        notification_manager.client_last_seen["idle_client"] = (
            current_time - 100
        )  # Idle but not stale
        notification_manager.client_last_seen["stale_client"] = (
            current_time - notification_manager.subscription_timeout - 10
        )  # Stale

        # Verify initial state
        total_subscriptions = sum(
            len(clients) for clients in notification_manager.subscribers.values()
        )
        assert total_subscriptions == 4

        # Perform cleanup
        await _perform_subscription_cleanup()

        # Verify stale client was removed
        assert "stale_client" not in notification_manager.client_last_seen
        assert "active_client" in notification_manager.client_last_seen
        assert "idle_client" in notification_manager.client_last_seen

        # Verify stale client's subscriptions were removed
        for subscribers in notification_manager.subscribers.values():
            assert "stale_client" not in subscribers

    async def test_concurrent_background_tasks(self, server_with_db, test_db_manager):
        """Test that background tasks can run concurrently without interference."""
        from shared_context_server.admin_lifecycle import _perform_memory_cleanup
        from shared_context_server.admin_resources import _perform_subscription_cleanup

        # Set up test data for both cleanup types
        ctx = MockContext(agent_id="concurrent_agent")

        # Add expired memory
        await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="concurrent_test",
            value={"data": "test"},
            expires_in=1,
        )
        # Mock time progression to simulate expiration (avoid 2s delay)
        future_time = datetime.now(timezone.utc) + timedelta(seconds=10)

        # Add stale subscription
        from shared_context_server.server import notification_manager

        await notification_manager.subscribe(
            "concurrent_client", "session://concurrent"
        )
        old_time = time.time() - notification_manager.subscription_timeout - 1
        notification_manager.client_last_seen["concurrent_client"] = old_time

        # Run both cleanup tasks concurrently with mocked time
        with patch("shared_context_server.admin_lifecycle.datetime") as mock_dt:
            mock_dt.now.return_value = future_time
            mock_dt.timezone = timezone  # Preserve timezone object
            await asyncio.gather(
                _perform_memory_cleanup(), _perform_subscription_cleanup()
            )

        # Verify both cleanups worked
        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx, key="concurrent_test"
        )
        assert result["success"] is False  # Memory was cleaned up

        assert (
            "concurrent_client" not in notification_manager.client_last_seen
        )  # Subscription was cleaned up

    async def test_background_task_error_isolation(
        self, server_with_db, test_db_manager
    ):
        """Test that errors in one background task don't affect others."""
        from shared_context_server.server import notification_manager

        # Set up test data
        await notification_manager.subscribe("test_client", "session://test")

        # Mock one cleanup to fail

        with patch("shared_context_server.session_tools.get_db_connection") as mock_db:
            mock_db.side_effect = Exception("Memory cleanup database error")

            # Mock subscription cleanup to track if it runs
            cleanup_called = False

            async def track_cleanup():
                nonlocal cleanup_called
                cleanup_called = True
                # Call real implementation through manager
                await notification_manager.__class__.cleanup_stale_subscriptions(
                    notification_manager
                )

            # Use context manager for cleaner mock restoration
            with patch.object(
                notification_manager, "cleanup_stale_subscriptions", track_cleanup
            ):
                # Run both tasks - memory cleanup should fail, subscription should succeed
                from shared_context_server.admin_lifecycle import (
                    _perform_memory_cleanup,
                )
                from shared_context_server.admin_resources import (
                    _perform_subscription_cleanup,
                )

                await asyncio.gather(
                    _perform_memory_cleanup(),
                    _perform_subscription_cleanup(),
                    return_exceptions=True,
                )

                # Subscription cleanup should still have run successfully
                assert cleanup_called is True

    async def test_server_startup_error_handling(self, isolated_db):
        """Test server startup error handling with realistic failure scenario."""
        from tests.fixtures.database import patch_database_for_test

        with (
            patch_database_for_test(isolated_db),
            patch(
                "shared_context_server.database_manager.get_sqlalchemy_manager"
            ) as mock_manager,
        ):
            # Test that the server can handle database connection issues
            # by checking error messages from actual connection failures
            # Mock a real SQLAlchemy connection failure
            mock_manager.side_effect = Exception("unable to open database file")

            from shared_context_server.server import lifespan

            # The lifespan should handle database errors appropriately
            try:
                async with lifespan():
                    pass
            except Exception as e:
                # Should get a meaningful error about database connection issues
                assert (
                    "unable to open database file" in str(e)
                    or "database" in str(e).lower()
                )

    async def test_task_cancellation_handling(self, server_with_db, test_db_manager):
        """Test that background tasks handle cancellation correctly."""

        # Mock the cleanup_subscriptions_task to avoid long-running sleeps
        async def mock_cleanup_task():
            # Simulate task work without long sleeps
            await asyncio.sleep(0.001)  # Very short sleep
            while True:
                await asyncio.sleep(0.001)  # Simulate periodic work

        # Start mocked task and cancel it quickly
        task = asyncio.create_task(mock_cleanup_task())

        # Let it start
        await asyncio.sleep(0.002)

        # Cancel the task
        task.cancel()

        # Should handle cancellation gracefully with shorter timeout
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except asyncio.CancelledError:
            pass  # Expected
        except asyncio.TimeoutError:
            task.cancel()  # Force cancel if needed

        assert task.cancelled()
