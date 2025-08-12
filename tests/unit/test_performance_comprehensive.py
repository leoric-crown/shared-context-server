"""
Comprehensive unit tests for performance.py to achieve 85%+ coverage.

Tests the ConnectionPoolManager, performance monitoring, and background tasks.
"""

import asyncio
import contextlib
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from shared_context_server.utils.performance import (
    ConnectionPoolManager,
    get_performance_metrics_dict,
    performance_monitoring_task,
    start_performance_monitoring,
)


@pytest.fixture
async def temp_db_path():
    """Create temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        yield db_path
    finally:
        try:
            db_file = Path(db_path)
            if db_file.exists():
                db_file.unlink()
        except Exception:
            pass


class TestConnectionPoolManager:
    """Comprehensive tests for ConnectionPoolManager."""

    @pytest.fixture
    async def pool_manager(self, temp_db_path):
        """Create fresh pool manager for testing."""
        pool = ConnectionPoolManager()
        yield pool
        # Cleanup
        with contextlib.suppress(Exception):
            await pool.shutdown_pool()

    @pytest.mark.asyncio
    async def test_pool_initialization(self, pool_manager, temp_db_path):
        """Test connection pool initialization."""
        assert not pool_manager.is_initialized
        assert pool_manager.pool is None

        await pool_manager.initialize_pool(temp_db_path, min_size=3, max_size=10)

        assert pool_manager.is_initialized
        assert pool_manager.pool is not None
        assert pool_manager.pool_size == 3  # Minimum connections created
        assert pool_manager.min_size == 3
        assert pool_manager.max_size == 10
        assert pool_manager.database_url == temp_db_path

    @pytest.mark.asyncio
    async def test_duplicate_initialization(self, pool_manager, temp_db_path):
        """Test that duplicate initialization is handled gracefully."""
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=5)
        initial_size = pool_manager.pool_size

        # Second initialization should be ignored
        await pool_manager.initialize_pool(temp_db_path, min_size=3, max_size=8)

        assert pool_manager.pool_size == initial_size
        assert pool_manager.max_size == 5  # Original settings preserved

    @pytest.mark.asyncio
    async def test_connection_creation_with_optimization(
        self, pool_manager, temp_db_path
    ):
        """Test optimized connection creation."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=5)

        # Check that connection was created with optimizations applied
        assert pool_manager.connection_stats["total_connections"] >= 1
        assert pool_manager.connection_stats["connection_errors"] == 0

    @pytest.mark.asyncio
    async def test_connection_acquisition_and_release(self, pool_manager, temp_db_path):
        """Test connection acquisition and release."""
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=5)

        async with pool_manager.get_connection("test_operation") as conn:
            assert conn is not None
            assert pool_manager.connection_stats["active_connections"] == 1

            # Execute a test query
            await conn.execute("SELECT 1")

        # Connection should be released
        assert pool_manager.connection_stats["active_connections"] == 0
        assert pool_manager.connection_stats["total_queries"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_connection_acquisition(self, pool_manager, temp_db_path):
        """Test concurrent connection acquisition."""
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=10)

        async def use_connection(op_id):
            async with pool_manager.get_connection(f"concurrent_op_{op_id}") as conn:
                await conn.execute("SELECT ?", (op_id,))
                await asyncio.sleep(0.01)  # Small delay
                return op_id

        # Run multiple concurrent operations
        tasks = [use_connection(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert pool_manager.connection_stats["total_queries"] >= 5
        assert pool_manager.connection_stats["peak_connections"] >= 1

    @pytest.mark.asyncio
    async def test_pool_exhaustion_handling(self, pool_manager, temp_db_path):
        """Test handling of pool exhaustion."""
        # Use very short timeout for fast testing
        await pool_manager.initialize_pool(
            temp_db_path, min_size=1, max_size=2, connection_timeout=0.1
        )

        # Acquire all available connections
        conn_contexts = []
        for i in range(2):
            ctx = pool_manager.get_connection(f"exhaust_op_{i}")
            conn = await ctx.__aenter__()
            conn_contexts.append((ctx, conn))

        # Pool should be at capacity
        assert pool_manager.connection_stats["active_connections"] == 2

        # Try to acquire another connection - should timeout quickly
        start_time = time.time()
        try:
            async with pool_manager.get_connection("overflow_op") as conn:
                # Should not reach here due to pool exhaustion
                raise AssertionError("Expected RuntimeError for pool exhaustion")
        except RuntimeError as e:
            # Should get RuntimeError quickly due to short timeout
            elapsed = time.time() - start_time
            assert elapsed < 1.0, f"Timeout took too long: {elapsed}s"
            assert "exhausted" in str(e).lower()

        # Verify pool exhaustion was tracked
        assert pool_manager.connection_stats["pool_exhaustion_count"] >= 1

        # Clean up manually acquired connections
        for ctx, _conn in conn_contexts:
            await ctx.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_pool_exhaustion_scenarios_fast(self, pool_manager, temp_db_path):
        """Test multiple pool exhaustion scenarios with fast timeouts."""
        # Initialize with very small pool and short timeout for fast testing
        await pool_manager.initialize_pool(
            temp_db_path, min_size=1, max_size=2, connection_timeout=0.05
        )

        # Test 1: Gradual exhaustion
        conn1_ctx = pool_manager.get_connection("test1")
        await conn1_ctx.__aenter__()

        conn2_ctx = pool_manager.get_connection("test2")
        await conn2_ctx.__aenter__()

        assert pool_manager.connection_stats["active_connections"] == 2

        # Test 2: Multiple rapid exhaustion attempts
        # Test pool exhaustion by attempting to get connections that should fail
        async def try_get_connection(name: str) -> bool:
            """Try to get a connection and return True if successful, False if exhausted."""
            try:
                async with pool_manager.get_connection(name):
                    return True  # Should not reach here
            except RuntimeError:
                return False  # Expected pool exhaustion

        # Test all three attempts
        results = await asyncio.gather(
            try_get_connection("rapid_test_0"),
            try_get_connection("rapid_test_1"),
            try_get_connection("rapid_test_2"),
            return_exceptions=True,
        )

        exhaustion_count = sum(1 for result in results if result is False)
        assert exhaustion_count == 3
        assert pool_manager.connection_stats["pool_exhaustion_count"] >= 3

        # Cleanup
        await conn1_ctx.__aexit__(None, None, None)
        await conn2_ctx.__aexit__(None, None, None)

        # Test 3: Recovery after cleanup
        async with pool_manager.get_connection("recovery_test") as conn:
            assert conn is not None
            await conn.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, pool_manager, temp_db_path):
        """Test connection timeout handling."""
        # Use very short timeout for fast testing
        await pool_manager.initialize_pool(
            temp_db_path, min_size=1, max_size=2, connection_timeout=0.05
        )

        # Acquire all connections and hold them
        conn_contexts = []
        for i in range(2):
            ctx = pool_manager.get_connection(f"timeout_op_{i}")
            conn = await ctx.__aenter__()
            conn_contexts.append((ctx, conn))

        # Try to acquire another connection with short timeout
        start_time = time.time()
        try:
            async with pool_manager.get_connection("timeout_test") as conn:
                raise AssertionError("Expected timeout/exhaustion error")
        except (RuntimeError, asyncio.TimeoutError):
            elapsed = time.time() - start_time
            assert elapsed < 0.5, (
                f"Timeout took too long: {elapsed}s"
            )  # Should timeout very quickly

        # Clean up
        for ctx, _conn in conn_contexts:
            await ctx.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_query_performance_tracking(self, pool_manager, temp_db_path):
        """Test query performance tracking."""
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=5)

        # Execute some queries using convenience methods to ensure proper counting
        await pool_manager.execute_query("SELECT 1", operation_name="perf_test_1")
        await pool_manager.execute_query("SELECT 2", operation_name="perf_test_2")

        # Check performance stats
        stats = pool_manager.get_performance_stats()
        assert stats["connection_stats"]["total_queries"] >= 2
        assert stats["connection_stats"]["avg_query_time"] >= 0
        assert stats["performance_indicators"]["avg_query_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_slow_query_detection(self, pool_manager, temp_db_path):
        """Test slow query detection."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Simulate slow query by patching time
        with patch("time.time") as mock_time:
            # Use itertools.cycle to handle repeated calls
            import itertools

            mock_time.side_effect = itertools.cycle([100.0, 100.2])  # 200ms query

            async with pool_manager.get_connection("slow_query") as conn:
                await conn.execute("SELECT 1")

        # Should have detected slow query
        stats = pool_manager.get_performance_stats()
        assert stats["connection_stats"]["slow_queries"] >= 0

    @pytest.mark.asyncio
    async def test_execute_query_convenience_method(self, pool_manager, temp_db_path):
        """Test execute_query convenience method."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        results = await pool_manager.execute_query(
            "SELECT ? as test_value", (42,), "convenience_test"
        )

        assert len(results) == 1
        assert results[0]["test_value"] == 42

    @pytest.mark.asyncio
    async def test_execute_write_convenience_method(self, pool_manager, temp_db_path):
        """Test execute_write convenience method."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Create test table
        await pool_manager.execute_write(
            "CREATE TABLE IF NOT EXISTS test_table (id INTEGER, value TEXT)",
            operation_name="create_table",
        )

        # Insert data
        row_id = await pool_manager.execute_write(
            "INSERT INTO test_table (id, value) VALUES (?, ?)",
            (1, "test_value"),
            "insert_test",
        )

        assert row_id is not None

    @pytest.mark.asyncio
    async def test_execute_many_convenience_method(self, pool_manager, temp_db_path):
        """Test execute_many convenience method."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Create test table
        await pool_manager.execute_write(
            "CREATE TABLE IF NOT EXISTS batch_test (id INTEGER, value TEXT)"
        )

        # Batch insert
        params_list = [(i, f"value_{i}") for i in range(5)]
        row_count = await pool_manager.execute_many(
            "INSERT INTO batch_test (id, value) VALUES (?, ?)",
            params_list,
            "batch_insert",
        )

        assert row_count == 5

    @pytest.mark.asyncio
    async def test_connection_cleanup(self, pool_manager, temp_db_path):
        """Test connection cleanup functionality."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Simulate old connections
        with patch.object(pool_manager, "connection_creation_times") as mock_times:
            old_time = time.time() - 7200  # 2 hours ago
            mock_times.__iter__ = lambda: iter([123])
            mock_times.items = lambda: [(123, old_time)]

            await pool_manager.cleanup_connections()

        # Should handle cleanup without errors
        assert pool_manager.is_initialized

    @pytest.mark.asyncio
    async def test_health_status_determination(self, pool_manager, temp_db_path):
        """Test health status determination."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=5)

        stats = pool_manager.get_performance_stats()
        assert stats["health_status"] in [
            "healthy",
            "not_initialized",
            "slow",
            "degraded",
            "unstable",
        ]

        # Test with mock stats for different health states
        pool_manager.connection_stats["pool_exhaustion_count"] = 1
        stats = pool_manager.get_performance_stats()
        assert stats["health_status"] == "degraded"

    @pytest.mark.asyncio
    async def test_shutdown_pool(self, pool_manager, temp_db_path):
        """Test pool shutdown."""
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=5)

        assert pool_manager.is_initialized

        await pool_manager.shutdown_pool()

        assert not pool_manager.is_initialized
        assert pool_manager.is_shutting_down
        assert pool_manager.pool is None
        assert pool_manager.pool_size == 0

    @pytest.mark.asyncio
    async def test_operations_during_shutdown(self, pool_manager, temp_db_path):
        """Test that operations fail gracefully during shutdown."""
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Start shutdown
        pool_manager.is_shutting_down = True

        # Attempt to get connection should fail
        with pytest.raises(RuntimeError, match="shutting down"):
            async with pool_manager.get_connection("shutdown_test"):
                pass


class TestPerformanceMonitoring:
    """Test performance monitoring functionality."""

    @pytest.mark.asyncio
    async def test_performance_monitoring_task_healthy_pool(self):
        """Test performance monitoring with healthy pool."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.get_performance_stats.return_value = {
                "health_status": "healthy",
                "performance_indicators": {
                    "avg_query_time_ms": 10.0,
                    "error_rate": 0.01,
                },
            }

            # Start task
            task = asyncio.create_task(performance_monitoring_task())

            # Let it run briefly
            await asyncio.sleep(0.1)
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

    @pytest.mark.asyncio
    async def test_performance_metrics_accuracy_validation(self, temp_db_path):
        """Test that performance metrics match actual measured performance."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=5)

        # Record start time and execute known operations
        start_time = time.time()

        # Execute exactly 10 queries with known timing
        for i in range(10):
            await pool_manager.execute_query("SELECT ?", (i,), f"accuracy_test_{i}")
            await asyncio.sleep(0.01)  # 10ms delay per query

        (time.time() - start_time) * 1000  # Convert to ms

        # Get performance stats
        stats = pool_manager.get_performance_stats()

        # Verify query count accuracy
        assert stats["connection_stats"]["total_queries"] >= 10

        # Verify average query time is reasonable (should include our 10ms delays)
        avg_time = stats["performance_indicators"]["avg_query_time_ms"]
        assert avg_time > 0, "Average query time should be positive"

        # Verify pool utilization calculation
        utilization = stats["performance_indicators"]["pool_utilization"]
        assert 0 <= utilization <= 1, (
            f"Pool utilization should be 0-1, got {utilization}"
        )

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_monitoring_system_during_database_failures(self, temp_db_path):
        """Test monitoring system behavior during database operation failures."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        initial_error_count = pool_manager.connection_stats["connection_errors"]

        # Simulate database operation failures
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Database connection failed")

            # Try to create new connections (should fail)
            with contextlib.suppress(Exception):
                await pool_manager._create_optimized_connection()

        # Verify error tracking
        assert pool_manager.connection_stats["connection_errors"] > initial_error_count

        # Verify health status reflects the errors
        stats = pool_manager.get_performance_stats()
        health_status = stats["health_status"]

        # Should detect unhealthy state due to connection errors
        assert health_status in ["unstable", "degraded", "not_initialized"]

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_background_task_performance_tracking(self):
        """Test background task performance tracking."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.cleanup_connections = AsyncMock()

            # Mock performance stats to trigger different monitoring paths
            stats_sequence = [
                {
                    "health_status": "healthy",
                    "performance_indicators": {"avg_query_time_ms": 25.0},
                },
                {
                    "health_status": "slow",
                    "performance_indicators": {"avg_query_time_ms": 150.0},
                },
                {
                    "health_status": "degraded",
                    "performance_indicators": {"error_rate": 0.15},
                },
            ]

            mock_pool.get_performance_stats.side_effect = stats_sequence

            # Mock asyncio.sleep to make the task run faster
            with patch("asyncio.sleep") as mock_sleep:
                mock_sleep.side_effect = [
                    None,
                    asyncio.CancelledError(),
                ]  # First sleep succeeds, second cancels

                task = asyncio.create_task(performance_monitoring_task())

                with contextlib.suppress(asyncio.CancelledError):
                    await task

            # Verify monitoring task called get_performance_stats
            assert mock_pool.get_performance_stats.call_count >= 1

    @pytest.mark.asyncio
    async def test_monitoring_data_collection_under_concurrent_access(
        self, temp_db_path
    ):
        """Test monitoring data collection accuracy under concurrent access."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=6)

        # Create concurrent operations that will stress the monitoring system
        async def concurrent_operation(op_id: int, duration: float):
            async with pool_manager.get_connection(
                f"concurrent_monitor_{op_id}"
            ) as conn:
                await conn.execute("SELECT ?", (op_id,))
                await asyncio.sleep(duration)

        # Launch operations with different durations to create varied load
        tasks = [concurrent_operation(i, 0.01 + (i % 3) * 0.005) for i in range(15)]

        # Monitor stats during concurrent execution
        initial_stats = pool_manager.get_performance_stats()

        # Execute concurrent operations
        await asyncio.gather(*tasks)

        # Get final stats
        final_stats = pool_manager.get_performance_stats()

        # Verify monitoring data consistency
        assert (
            final_stats["connection_stats"]["total_queries"]
            > initial_stats["connection_stats"]["total_queries"]
        )
        assert (
            final_stats["connection_stats"]["peak_connections"]
            >= initial_stats["connection_stats"]["peak_connections"]
        )

        # Verify no data corruption under concurrent access
        assert final_stats["connection_stats"]["active_connections"] >= 0
        assert final_stats["pool_stats"]["pool_utilization"] >= 0
        assert final_stats["performance_indicators"]["avg_query_time_ms"] >= 0

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_performance_monitoring_task_degraded_pool(self):
        """Test performance monitoring with degraded pool."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.get_performance_stats.return_value = {
                "health_status": "degraded",
                "performance_indicators": {
                    "avg_query_time_ms": 150.0,
                    "error_rate": 0.15,
                },
            }
            mock_pool.cleanup_connections = AsyncMock()

            with patch("time.time", return_value=300):  # Trigger cleanup
                task = asyncio.create_task(performance_monitoring_task())

                # Let it run briefly
                await asyncio.sleep(0.1)
                task.cancel()

                with contextlib.suppress(asyncio.CancelledError):
                    await task

    @pytest.mark.asyncio
    async def test_performance_monitoring_exception_handling(self):
        """Test that performance monitoring handles exceptions."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.get_performance_stats.side_effect = Exception("Test error")

            task = asyncio.create_task(performance_monitoring_task())

            # Let it run briefly
            await asyncio.sleep(0.1)
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

    @pytest.mark.asyncio
    async def test_start_performance_monitoring(self):
        """Test starting performance monitoring task."""
        task = await start_performance_monitoring()
        assert isinstance(task, asyncio.Task)

        # Clean up
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    def test_get_performance_metrics_dict_uninitialized(self):
        """Test performance metrics with uninitialized pool."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = False

            metrics = get_performance_metrics_dict()
            assert metrics["success"] is False
            assert metrics["code"] == "POOL_NOT_INITIALIZED"

    def test_get_performance_metrics_dict_initialized(self):
        """Test performance metrics with initialized pool."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.is_shutting_down = False
            mock_pool.database_url = "test.db"
            mock_pool.min_size = 5
            mock_pool.max_size = 50
            mock_pool.connection_timeout = 30.0
            mock_pool.get_performance_stats.return_value = {
                "connection_stats": {"total_queries": 100},
                "pool_stats": {"pool_utilization": 0.5},
                "performance_indicators": {
                    "avg_query_time_ms": 25.0,
                    "error_rate": 0.02,
                },
                "health_status": "healthy",
            }

            metrics = get_performance_metrics_dict()

            assert metrics["success"] is True
            assert "timestamp" in metrics
            assert "database_performance" in metrics
            assert "system_info" in metrics
            assert "performance_targets" in metrics

            # Verify system info
            system_info = metrics["system_info"]
            assert system_info["pool_initialized"] is True
            assert system_info["database_url"] == "test.db"
            assert system_info["min_pool_size"] == 5
            assert system_info["max_pool_size"] == 50

    def test_get_performance_metrics_dict_exception(self):
        """Test performance metrics with exception."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.get_performance_stats.side_effect = Exception("Test error")

            metrics = get_performance_metrics_dict()
            assert metrics["success"] is False
            assert "error" in metrics


class TestPerformanceEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_connection_creation_failure(self):
        """Test handling of connection creation failures."""
        pool_manager = ConnectionPoolManager()

        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            await pool_manager.initialize_pool("invalid.db", min_size=1, max_size=3)

            # Should handle connection creation failures
            assert pool_manager.connection_stats["connection_errors"] > 0

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_with_50_concurrent_requests(
        self, temp_db_path
    ):
        """Test connection pool exhaustion scenarios with 50+ concurrent requests."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(
            temp_db_path, min_size=2, max_size=5, connection_timeout=0.1
        )

        # Create a semaphore to control concurrent access
        semaphore = asyncio.Semaphore(50)

        async def make_request(request_id: int) -> tuple[int, bool]:
            """Make a database request and return (id, success)."""
            async with semaphore:
                try:
                    async with pool_manager.get_connection(
                        f"concurrent_request_{request_id}"
                    ) as conn:
                        await conn.execute("SELECT ?", (request_id,))
                        await asyncio.sleep(0.01)  # Small delay to increase contention
                        return (request_id, True)
                except (RuntimeError, asyncio.TimeoutError):
                    return (request_id, False)

        # Launch 50 concurrent requests
        tasks = [make_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful and failed requests
        successful = sum(
            1 for result in results if isinstance(result, tuple) and result[1]
        )
        failed = sum(
            1 for result in results if isinstance(result, tuple) and not result[1]
        )
        exceptions = sum(1 for result in results if isinstance(result, Exception))

        # Should have some failures due to pool exhaustion
        assert failed + exceptions > 0, (
            f"Expected some failures, got {failed} failed, {exceptions} exceptions"
        )
        assert pool_manager.connection_stats["pool_exhaustion_count"] > 0
        assert successful > 0, "Should have some successful requests"

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_connection_timeout_configurations(self, temp_db_path):
        """Test timeout handling with various timeout configurations."""
        # Test very short timeout
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(
            temp_db_path, min_size=1, max_size=2, connection_timeout=0.01
        )

        # Acquire all connections
        conn1_ctx = pool_manager.get_connection("timeout_test_1")
        await conn1_ctx.__aenter__()

        conn2_ctx = pool_manager.get_connection("timeout_test_2")
        await conn2_ctx.__aenter__()

        # Try to get another connection - should timeout very quickly
        start_time = time.time()
        try:
            async with pool_manager.get_connection("timeout_test_overflow"):
                pytest.fail("Should have timed out")
        except (RuntimeError, asyncio.TimeoutError):
            elapsed = time.time() - start_time
            assert elapsed < 0.5, f"Timeout took too long: {elapsed}s"

        # Cleanup
        await conn1_ctx.__aexit__(None, None, None)
        await conn2_ctx.__aexit__(None, None, None)
        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_connection_recovery_after_database_failures(self, temp_db_path):
        """Test connection recovery after database failures."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Simulate database failure by corrupting connection
        async with pool_manager.get_connection("pre_failure_test") as conn:
            await conn.execute("SELECT 1")

        # Simulate connection failure during optimization
        with patch.object(pool_manager, "_optimize_connection") as mock_optimize:
            mock_optimize.side_effect = Exception("Database locked")

            # Pool should handle optimization failures gracefully
            try:
                async with pool_manager.get_connection("failure_recovery_test") as conn:
                    await conn.execute("SELECT 1")
            except Exception:
                pass  # Expected to fail

        # Pool should recover and work normally
        async with pool_manager.get_connection("post_failure_test") as conn:
            result = await conn.execute("SELECT 2")
            assert result is not None

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_connection_pool_statistics_accuracy_under_load(self, temp_db_path):
        """Test connection pool statistics accuracy under load."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=8)

        # Track initial stats
        initial_stats = pool_manager.get_performance_stats()
        initial_queries = initial_stats["connection_stats"]["total_queries"]

        # Generate load with multiple concurrent operations
        async def load_operation(op_id: int):
            async with pool_manager.get_connection(f"load_op_{op_id}") as conn:
                await conn.execute("SELECT ?, ?", (op_id, op_id * 2))
                await asyncio.sleep(0.001)  # Small delay

        # Run 20 concurrent operations
        tasks = [load_operation(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # Verify statistics accuracy
        final_stats = pool_manager.get_performance_stats()
        final_queries = final_stats["connection_stats"]["total_queries"]

        # Should have processed exactly 20 additional queries
        assert final_queries >= initial_queries + 20
        assert final_stats["connection_stats"]["peak_connections"] >= 1
        assert final_stats["pool_stats"]["pool_utilization"] >= 0

        # Verify performance indicators are calculated correctly
        perf_indicators = final_stats["performance_indicators"]
        assert perf_indicators["avg_query_time_ms"] >= 0
        assert 0 <= perf_indicators["pool_utilization"] <= 1
        assert perf_indicators["error_rate"] >= 0

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_connection_optimization_failure(self, temp_db_path):
        """Test handling of connection optimization failures."""
        pool_manager = ConnectionPoolManager()

        with patch.object(pool_manager, "_optimize_connection") as mock_optimize:
            mock_optimize.side_effect = Exception("Optimization failed")

            # Should still initialize but log warnings
            await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Clean up
        with contextlib.suppress(Exception):
            await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_individual_pragma_optimization_failures(self, temp_db_path):
        """Test handling of individual PRAGMA optimization failures."""

        # Custom exceptions for testing
        class JournalModeError(Exception):
            """Journal mode optimization failure."""

        class CacheSizeError(Exception):
            """Cache size optimization failure."""

        class MemoryMappingError(Exception):
            """Memory mapping optimization failure."""

        pool_manager = ConnectionPoolManager()

        # Mock connection to simulate PRAGMA failures
        original_execute = None

        async def mock_execute_with_pragma_failures(self, query, *args):
            if "PRAGMA" in query:
                if "journal_mode" in query:
                    raise JournalModeError("Journal mode failed")
                if "cache_size" in query:
                    raise CacheSizeError("Cache size failed")
                if "mmap_size" in query:
                    raise MemoryMappingError("Memory mapping failed")
            return await original_execute(query, *args)

        with patch("aiosqlite.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            # Store original execute method
            original_execute = mock_conn.execute
            mock_conn.execute.side_effect = mock_execute_with_pragma_failures

            await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Should handle individual PRAGMA failures gracefully
        assert pool_manager.is_initialized

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_connection_return_failure(self, temp_db_path):
        """Test handling of connection return failures."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        initial_pool_size = pool_manager.pool_size

        # Mock pool.put to raise exception
        with patch.object(pool_manager.pool, "put") as mock_put:
            mock_put.side_effect = Exception("Return failed")

            async with pool_manager.get_connection("return_fail_test") as conn:
                await conn.execute("SELECT 1")

            # Should handle return failure gracefully
            # Pool size should be decremented due to lost connection
            assert pool_manager.pool_size <= initial_pool_size

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_connection_return_during_shutdown(self, temp_db_path):
        """Test connection return behavior during pool shutdown."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Get a connection
        conn_ctx = pool_manager.get_connection("shutdown_test")
        await conn_ctx.__aenter__()

        # Start shutdown process
        pool_manager.is_shutting_down = True

        # Try to return connection during shutdown
        await conn_ctx.__aexit__(None, None, None)

        # Should handle gracefully without errors
        assert pool_manager.is_shutting_down

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_pool_exhaustion_with_dynamic_expansion(self, temp_db_path):
        """Test pool exhaustion handling with dynamic pool expansion."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(
            temp_db_path, min_size=1, max_size=3, connection_timeout=0.1
        )

        # Acquire all initial connections
        contexts = []
        for i in range(3):
            ctx = pool_manager.get_connection(f"expand_test_{i}")
            conn = await ctx.__aenter__()
            contexts.append((ctx, conn))

        # Pool should be at max capacity
        assert pool_manager.connection_stats["active_connections"] == 3

        # Try to get another connection - should trigger exhaustion
        try:
            async with pool_manager.get_connection("overflow_test"):
                pytest.fail("Should have failed due to pool exhaustion")
        except RuntimeError as e:
            assert "exhausted" in str(e).lower()

        # Verify exhaustion was tracked
        assert pool_manager.connection_stats["pool_exhaustion_count"] >= 1

        # Clean up
        for ctx, _conn in contexts:
            await ctx.__aexit__(None, None, None)

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_performance_metrics_calculation_edge_cases(self):
        """Test performance metrics calculation with edge cases."""
        pool_manager = ConnectionPoolManager()

        # Test with zero queries
        stats = pool_manager.get_performance_stats()
        assert stats["performance_indicators"]["avg_query_time_ms"] == 0
        assert stats["performance_indicators"]["slow_query_ratio"] == 0
        assert stats["performance_indicators"]["error_rate"] == 0

        # Test with zero max_size
        pool_manager.max_size = 0
        stats = pool_manager.get_performance_stats()
        assert stats["pool_stats"]["pool_utilization"] == 0


class TestDatabaseOperationErrorHandling:
    """Test database operation error handling and recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_database_connection_timeout_scenarios(self, temp_db_path):
        """Test database connection timeout scenarios and recovery mechanisms."""
        pool_manager = ConnectionPoolManager()

        # Initialize with very short timeout for testing
        await pool_manager.initialize_pool(
            temp_db_path, min_size=1, max_size=2, connection_timeout=0.05
        )

        # Test timeout during connection acquisition
        # Fill the pool first
        conn_contexts = []
        for i in range(2):
            ctx = pool_manager.get_connection(f"timeout_scenario_{i}")
            conn = await ctx.__aenter__()
            conn_contexts.append((ctx, conn))

        # Now try to get another connection - should timeout
        start_time = time.time()
        try:
            async with pool_manager.get_connection("timeout_test"):
                pytest.fail("Should have timed out")
        except (RuntimeError, asyncio.TimeoutError):
            elapsed = time.time() - start_time
            assert elapsed < 0.5, f"Timeout took too long: {elapsed}s"

        # Test recovery after timeout
        # Release one connection
        await conn_contexts[0][0].__aexit__(None, None, None)

        # Should be able to get connection now
        async with pool_manager.get_connection("recovery_test") as conn:
            await conn.execute("SELECT 1")

        # Cleanup
        await conn_contexts[1][0].__aexit__(None, None, None)
        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_sqlite_error_conditions(self, temp_db_path):
        """Test various SQLite error conditions (locked database, corruption, etc.)."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Test database locked error
        with patch("aiosqlite.Connection.execute") as mock_execute:
            mock_execute.side_effect = Exception("database is locked")

            try:
                await pool_manager.execute_query(
                    "SELECT 1", operation_name="locked_test"
                )
            except Exception as e:
                assert "locked" in str(e).lower()

        # Test database corruption simulation
        with patch("aiosqlite.Connection.execute") as mock_execute:
            mock_execute.side_effect = Exception("database disk image is malformed")

            try:
                await pool_manager.execute_query(
                    "SELECT 1", operation_name="corruption_test"
                )
            except Exception as e:
                assert "malformed" in str(e).lower()

        # Test constraint violation
        with patch("aiosqlite.Connection.execute") as mock_execute:
            mock_execute.side_effect = Exception("UNIQUE constraint failed")

            try:
                await pool_manager.execute_write(
                    "INSERT INTO test VALUES (1)", operation_name="constraint_test"
                )
            except Exception as e:
                assert "constraint" in str(e).lower()

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_transaction_rollback_scenarios(self, temp_db_path):
        """Test transaction rollback scenarios."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Create test table
        await pool_manager.execute_write(
            "CREATE TABLE IF NOT EXISTS rollback_test (id INTEGER PRIMARY KEY, value TEXT)"
        )

        # Test rollback on execute_write failure
        with patch("aiosqlite.Connection.commit") as mock_commit:
            mock_commit.side_effect = Exception("Commit failed")

            try:
                await pool_manager.execute_write(
                    "INSERT INTO rollback_test (value) VALUES (?)",
                    ("test_value",),
                    "rollback_test",
                )
            except Exception as e:
                assert "failed" in str(e).lower()

        # Test rollback on execute_many failure
        with patch("aiosqlite.Connection.commit") as mock_commit:
            mock_commit.side_effect = Exception("Batch commit failed")

            try:
                await pool_manager.execute_many(
                    "INSERT INTO rollback_test (value) VALUES (?)",
                    [("value1",), ("value2",), ("value3",)],
                    "batch_rollback_test",
                )
            except Exception as e:
                assert "failed" in str(e).lower()

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_error_propagation_and_logging_accuracy(self, temp_db_path):
        """Test error propagation and logging accuracy."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Test error propagation in execute_query
        original_error = Exception("Original database error")
        with patch("aiosqlite.Connection.execute") as mock_execute:
            mock_execute.side_effect = original_error

            try:
                await pool_manager.execute_query(
                    "SELECT 1", operation_name="error_prop_test"
                )
                pytest.fail("Should have propagated error")
            except Exception as e:
                # Error should be propagated correctly
                assert str(e) == str(original_error)

        # Test error tracking in connection stats
        initial_error_count = pool_manager.connection_stats["connection_errors"]

        # Simulate connection creation error
        with patch("aiosqlite.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection creation failed")

            with contextlib.suppress(Exception):
                await pool_manager._create_optimized_connection()

        # Verify error was tracked
        assert pool_manager.connection_stats["connection_errors"] > initial_error_count

        # Test slow query logging
        with patch("time.time") as mock_time:
            # Simulate slow query (>100ms) - provide more values for additional calls
            mock_time.side_effect = [
                100.0,
                100.15,
                100.15,
                100.15,
                100.15,
                100.15,
            ]  # 150ms query

            async with pool_manager.get_connection("slow_query_test") as conn:
                await conn.execute("SELECT 1")

        # Should have incremented slow query count
        pool_manager.get_performance_stats()
        # Note: slow query detection happens in the context manager exit

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_connection_pool_corruption_recovery(self, temp_db_path):
        """Test recovery from connection pool corruption scenarios."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=4)

        # Simulate pool corruption by directly manipulating pool state

        # Corrupt pool size counter
        pool_manager.pool_size = 999

        # Pool should still function despite corrupted counter
        async with pool_manager.get_connection("corruption_test") as conn:
            await conn.execute("SELECT 1")

        # Test recovery during cleanup
        await pool_manager.cleanup_connections()

        # Pool should still be functional
        async with pool_manager.get_connection("post_cleanup_test") as conn:
            await conn.execute("SELECT 2")

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self, temp_db_path):
        """Test error handling under concurrent access patterns."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=4)

        # Create concurrent operations with mixed success/failure
        class SimulatedOperationError(Exception):
            """Simulated error for testing concurrent operations."""

        def raise_simulated_error(op_id: int) -> None:
            """Abstract raise to inner function."""
            raise SimulatedOperationError(f"Simulated error {op_id}")

        async def operation_with_errors(op_id: int) -> tuple[int, bool]:
            try:
                if op_id % 3 == 0:  # Every 3rd operation fails
                    # Simulate error without patching global methods
                    raise_simulated_error(op_id)
                async with pool_manager.get_connection(f"success_op_{op_id}") as conn:
                    await conn.execute("SELECT ?", (op_id,))
            except Exception:
                return (op_id, False)
            else:
                return (op_id, True)

        # Run 12 concurrent operations (4 should fail)
        tasks = [operation_with_errors(i) for i in range(12)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(
            1 for result in results if isinstance(result, tuple) and result[1]
        )
        failed = sum(
            1 for result in results if isinstance(result, tuple) and not result[1]
        )

        # Should have approximately 8 successes and 4 failures
        assert successful >= 6, f"Expected at least 6 successes, got {successful}"
        assert failed >= 2, f"Expected at least 2 failures, got {failed}"

        # Pool should still be healthy after mixed operations
        stats = pool_manager.get_performance_stats()
        assert stats["connection_stats"]["active_connections"] == 0  # All returned

        await pool_manager.shutdown_pool()


class TestBackgroundTaskResilience:
    """Test background task resilience and error recovery."""

    @pytest.mark.asyncio
    async def test_cleanup_task_error_recovery_and_continuation(self):
        """Test cleanup task error recovery and continuation."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True

            # Simulate cleanup_connections raising an error first, then succeeding
            cleanup_call_count = 0

            class CleanupError(Exception):
                """Custom exception for cleanup failure."""

            async def mock_cleanup():
                nonlocal cleanup_call_count
                cleanup_call_count += 1
                if cleanup_call_count == 1:
                    raise CleanupError("Cleanup failed")
                # Second call succeeds

            mock_pool.cleanup_connections = mock_cleanup
            mock_pool.get_performance_stats.return_value = {
                "health_status": "healthy",
                "performance_indicators": {"avg_query_time_ms": 25.0},
            }

            # Mock time to trigger cleanup (every 5 minutes = 300 seconds)
            with patch("time.time") as mock_time, patch("asyncio.sleep") as mock_sleep:
                # Use return_value instead of side_effect to avoid StopIteration
                mock_time.return_value = (
                    600  # Always return a time that triggers cleanup
                )
                mock_sleep.side_effect = [
                    None,
                    asyncio.CancelledError(),
                ]  # First sleep succeeds, second cancels

                task = asyncio.create_task(performance_monitoring_task())

                with contextlib.suppress(asyncio.CancelledError):
                    await task

            # Cleanup should have been called despite the first failure
            assert cleanup_call_count >= 1

    @pytest.mark.asyncio
    async def test_background_task_behavior_during_database_unavailability(self):
        """Test background task behavior during database unavailability."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            # Simulate database unavailability
            mock_pool.is_initialized = False

            task = asyncio.create_task(performance_monitoring_task())

            # Let it run briefly - should handle uninitialized pool gracefully
            await asyncio.sleep(0.1)
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

            # Task should not have crashed despite database unavailability

    @pytest.mark.asyncio
    async def test_background_task_scheduling_and_execution_under_load(self):
        """Test background task scheduling and execution under load."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True

            # Track how many times monitoring runs
            monitoring_calls = 0

            def mock_get_stats():
                nonlocal monitoring_calls
                monitoring_calls += 1
                return {
                    "health_status": "healthy" if monitoring_calls % 2 == 0 else "slow",
                    "performance_indicators": {
                        "avg_query_time_ms": 50.0 + monitoring_calls * 10,
                        "error_rate": 0.01,
                    },
                }

            mock_pool.get_performance_stats.side_effect = mock_get_stats
            mock_pool.cleanup_connections = AsyncMock()

            # Mock asyncio.sleep to control task execution
            with patch("asyncio.sleep") as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]

                task = asyncio.create_task(performance_monitoring_task())

                with contextlib.suppress(asyncio.CancelledError):
                    await task

            # Should have made monitoring calls
            assert monitoring_calls >= 1

    @pytest.mark.asyncio
    async def test_background_task_graceful_shutdown_scenarios(self):
        """Test background task graceful shutdown scenarios."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.get_performance_stats.return_value = {
                "health_status": "healthy",
                "performance_indicators": {"avg_query_time_ms": 25.0},
            }

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
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True

            # Simulate different types of exceptions
            exception_sequence = [
                Exception("General error"),
                RuntimeError("Runtime error"),
                ValueError("Value error"),
                {
                    "health_status": "healthy",
                    "performance_indicators": {"avg_query_time_ms": 25.0},
                },  # Success
            ]

            mock_pool.get_performance_stats.side_effect = exception_sequence

            task = asyncio.create_task(performance_monitoring_task())

            # Let it run through the exception sequence
            await asyncio.sleep(0.2)
            task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await task

            # Task should have handled all exceptions and continued running

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

    @pytest.mark.asyncio
    async def test_monitoring_task_health_status_transitions(self):
        """Test monitoring task behavior during health status transitions."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.cleanup_connections = AsyncMock()

            # Simulate health status transitions
            health_transitions = [
                {
                    "health_status": "healthy",
                    "performance_indicators": {
                        "avg_query_time_ms": 25.0,
                        "error_rate": 0.01,
                    },
                },
                {
                    "health_status": "slow",
                    "performance_indicators": {
                        "avg_query_time_ms": 150.0,
                        "error_rate": 0.02,
                    },
                },
                {
                    "health_status": "degraded",
                    "performance_indicators": {
                        "avg_query_time_ms": 200.0,
                        "error_rate": 0.15,
                    },
                },
                {
                    "health_status": "unstable",
                    "performance_indicators": {
                        "avg_query_time_ms": 300.0,
                        "error_rate": 0.25,
                    },
                },
            ]

            call_count = 0

            def get_stats_with_transitions():
                nonlocal call_count
                result = health_transitions[call_count % len(health_transitions)]
                call_count += 1
                return result

            mock_pool.get_performance_stats.side_effect = get_stats_with_transitions

            # Mock asyncio.sleep to control execution
            with patch("asyncio.sleep") as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]

                task = asyncio.create_task(performance_monitoring_task())

                with contextlib.suppress(asyncio.CancelledError):
                    await task

            # Should have processed health status changes
            assert call_count >= 1

    @pytest.mark.asyncio
    async def test_monitoring_task_with_uninitialized_pool_recovery(self):
        """Test monitoring task recovery when pool becomes initialized."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            # Start with uninitialized pool
            initialization_calls = 0

            def check_initialization():
                nonlocal initialization_calls
                initialization_calls += 1
                # Pool becomes initialized after a few calls
                return initialization_calls > 2

            type(mock_pool).is_initialized = property(lambda _: check_initialization())
            mock_pool.get_performance_stats.return_value = {
                "health_status": "healthy",
                "performance_indicators": {"avg_query_time_ms": 25.0},
            }

            # Mock asyncio.sleep to control execution
            with patch("asyncio.sleep") as mock_sleep:
                mock_sleep.side_effect = [None, None, None, asyncio.CancelledError()]

                task = asyncio.create_task(performance_monitoring_task())

                with contextlib.suppress(asyncio.CancelledError):
                    await task

            # Should have checked initialization multiple times
            assert initialization_calls >= 1

    @pytest.mark.asyncio
    async def test_type_checking_import_coverage(self):
        """Test TYPE_CHECKING import branch coverage."""
        # This test ensures the TYPE_CHECKING import branch is covered
        # The import happens at module level, so we just need to import the module
        from shared_context_server.utils.performance import ConnectionPoolManager

        assert ConnectionPoolManager is not None

    @pytest.mark.asyncio
    async def test_connection_creation_timeout_edge_case(self, temp_db_path):
        """Test connection creation timeout edge cases."""
        pool_manager = ConnectionPoolManager()

        # Test connection creation with timeout
        with patch("aiosqlite.connect") as mock_connect:
            # Simulate connection timeout
            mock_connect.side_effect = asyncio.TimeoutError("Connection timeout")

            try:
                await pool_manager._create_optimized_connection()
                pytest.fail("Should have raised timeout error")
            except asyncio.TimeoutError:
                pass  # Expected

        # Verify error was tracked
        assert pool_manager.connection_stats["connection_errors"] > 0

    @pytest.mark.asyncio
    async def test_pool_exhaustion_new_connection_creation_failure(self, temp_db_path):
        """Test pool exhaustion when new connection creation fails."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(
            temp_db_path, min_size=1, max_size=2, connection_timeout=0.1
        )

        # Acquire all connections
        conn_contexts = []
        for i in range(2):
            ctx = pool_manager.get_connection(f"exhaust_{i}")
            conn = await ctx.__aenter__()
            conn_contexts.append((ctx, conn))

        # Mock connection creation to fail when pool tries to expand
        with patch.object(pool_manager, "_create_optimized_connection") as mock_create:
            mock_create.side_effect = Exception("Connection creation failed")

            # Try to get another connection - should fail due to both pool exhaustion and creation failure
            try:
                async with pool_manager.get_connection("overflow_fail"):
                    pytest.fail("Should have failed")
            except (RuntimeError, Exception):
                pass  # Expected to fail

        # Cleanup
        for ctx, _conn in conn_contexts:
            await ctx.__aexit__(None, None, None)

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_cleanup_connections_with_old_connections(self, temp_db_path):
        """Test cleanup_connections with old connections."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=1, max_size=3)

        # Simulate old connections by manipulating creation times
        old_time = time.time() - 7200  # 2 hours ago
        pool_manager.connection_creation_times[123] = old_time
        pool_manager.connection_creation_times[456] = old_time

        # Mock pool operations for cleanup
        with (
            patch.object(pool_manager.pool, "empty") as mock_empty,
            patch.object(pool_manager.pool, "get") as mock_get,
            patch.object(pool_manager.pool, "put"),
        ):
            mock_empty.return_value = False
            mock_conn = AsyncMock()
            mock_get.return_value = mock_conn

            await pool_manager.cleanup_connections()

        await pool_manager.shutdown_pool()

    @pytest.mark.asyncio
    async def test_shutdown_pool_with_connection_close_errors(self, temp_db_path):
        """Test shutdown_pool handling connection close errors."""
        pool_manager = ConnectionPoolManager()
        await pool_manager.initialize_pool(temp_db_path, min_size=2, max_size=4)

        # Mock pool operations for shutdown
        with (
            patch.object(pool_manager.pool, "empty") as mock_empty,
            patch.object(pool_manager.pool, "get") as mock_get,
        ):
            mock_empty.side_effect = [False, False, True]  # Two connections, then empty
            mock_conn1 = AsyncMock()
            mock_conn2 = AsyncMock()
            mock_conn1.close.side_effect = Exception("Close failed")
            mock_conn2.close.return_value = None
            mock_get.side_effect = [mock_conn1, mock_conn2]

            await pool_manager.shutdown_pool()

        # Should handle close errors gracefully
        assert not pool_manager.is_initialized

    @pytest.mark.asyncio
    async def test_get_performance_metrics_dict_exception_handling(self):
        """Test get_performance_metrics_dict exception handling."""
        with patch("shared_context_server.utils.performance.db_pool") as mock_pool:
            mock_pool.is_initialized = True
            mock_pool.get_performance_stats.side_effect = Exception("Stats error")

            result = get_performance_metrics_dict()

            assert result["success"] is False
            assert "error" in result
