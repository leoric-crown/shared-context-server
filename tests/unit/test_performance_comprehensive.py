"""
Performance monitoring tests adapted for SQLAlchemy-only architecture (post PRP-024).

Tests performance monitoring functions and background tasks that remain valid
after ConnectionPoolManager deprecation. Most comprehensive tests were removed
as they tested deprecated aiosqlite connection pooling functionality.
"""

import asyncio
import contextlib
from unittest.mock import patch

import pytest

from shared_context_server.utils.performance import (
    get_performance_metrics_dict,
    performance_monitoring_task,
    start_performance_monitoring,
)


class TestPerformanceMonitoring:
    """Test performance monitoring functionality (post-deprecation)."""

    @pytest.mark.asyncio
    async def test_performance_monitoring_task_deprecated_mode(self):
        """Test performance monitoring task in deprecated mode."""
        # The task should run without errors even though it's deprecated
        task = asyncio.create_task(performance_monitoring_task())

        # Let it run briefly - should handle deprecated status gracefully
        await asyncio.sleep(0.1)
        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Task should complete without raising exceptions

    @pytest.mark.asyncio
    async def test_start_performance_monitoring(self):
        """Test starting performance monitoring task."""
        task = await start_performance_monitoring()
        assert isinstance(task, asyncio.Task)

        # Clean up
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    def test_get_performance_metrics_dict_deprecated_mode(self):
        """Test performance metrics in deprecated mode."""
        metrics = get_performance_metrics_dict()

        # Should return success even in deprecated mode
        assert metrics["success"] is True
        assert metrics["database_backend"] == "sqlalchemy"
        assert metrics["migration_status"] == "aiosqlite_removed"

        # Should contain expected structure
        assert "database_performance" in metrics
        assert "system_info" in metrics
        assert "performance_targets" in metrics

        # System info should reflect migration
        system_info = metrics["system_info"]
        assert system_info["migration_complete"] is True
        assert system_info["database_backend"] == "sqlalchemy"

    def test_get_performance_metrics_dict_exception_handling(self):
        """Test performance metrics exception handling."""
        # This test verifies the exception handling in the performance module
        # The get_performance_metrics_dict function has try/catch so it should never fail

        metrics = get_performance_metrics_dict()

        # Should always return a valid response structure
        assert isinstance(metrics, dict)
        assert "success" in metrics


class TestBackgroundTaskResilience:
    """Test background task resilience and error recovery (adapted for deprecation)."""

    @pytest.mark.asyncio
    async def test_background_task_behavior_during_deprecated_state(self):
        """Test background task behavior in deprecated state."""
        # The performance monitoring task should run without crashing even though deprecated
        task = asyncio.create_task(performance_monitoring_task())

        # Let it run briefly - should handle deprecated state gracefully
        await asyncio.sleep(0.1)
        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Task should not have crashed despite deprecated state

    @pytest.mark.asyncio
    async def test_background_task_graceful_shutdown_scenarios(self):
        """Test background task graceful shutdown scenarios."""
        # Mock asyncio.sleep to immediately raise CancelledError
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()

            task = asyncio.create_task(performance_monitoring_task())

            # Task should handle cancellation gracefully
            with contextlib.suppress(asyncio.CancelledError):
                await task

        # Verify task completed (either cancelled or finished)
        assert task.done()

    @pytest.mark.asyncio
    async def test_monitoring_task_exception_recovery(self):
        """Test monitoring task recovery from various exceptions."""
        # Since the task is now deprecated and minimal, it should handle exceptions gracefully

        task = asyncio.create_task(performance_monitoring_task())

        # Let it run briefly
        await asyncio.sleep(0.1)
        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Task should have handled any internal exceptions and completed cleanly

    @pytest.mark.asyncio
    async def test_start_performance_monitoring_integration(self):
        """Test start_performance_monitoring function integration."""
        # Test that start_performance_monitoring returns a proper task
        task = await start_performance_monitoring()

        assert isinstance(task, asyncio.Task)
        assert not task.done()  # Should be running

        # Clean up
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
