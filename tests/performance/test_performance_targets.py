"""
Performance validation tests for Phase 4 production targets.

Tests that the performance optimization system meets production requirements:
- API response time: P95 < 100ms
- Database queries: Average < 50ms
- Connection pool utilization: < 80%
- Cache hit ratio: > 70%
- Support: 20+ concurrent agents

Built according to PRP-005: Phase 4 - Production Ready specification.
"""

import asyncio
import contextlib
import statistics
import tempfile
import time
from pathlib import Path

import pytest

from shared_context_server.utils.caching import cache_manager
from shared_context_server.utils.performance import (
    db_pool,
    get_performance_metrics_dict,
)


class TestPerformanceTargets:
    """Test production performance targets."""

    @pytest.fixture
    async def temp_database(self):
        """Create temporary database for performance testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            yield db_path
        finally:
            # Cleanup
            try:
                db_file = Path(db_path)
                if db_file.exists():
                    db_file.unlink()
            except Exception:
                pass

    @pytest.fixture
    async def initialized_pool(self, temp_database):
        """Initialize isolated connection pool for testing."""
        # Reset the global pool to ensure clean state
        with contextlib.suppress(Exception):
            await db_pool.reset_for_testing()

        # Initialize with test-specific settings
        await db_pool.initialize_pool(temp_database, min_size=3, max_size=25)

        yield db_pool

        # Cleanup - reset to clean state
        with contextlib.suppress(Exception):
            await db_pool.reset_for_testing()

    async def measure_operation_time(
        self, operation_func, iterations: int = 10
    ) -> dict[str, float]:
        """Measure operation performance statistics."""
        times = []

        for _ in range(iterations):
            start_time = time.time()
            await operation_func()
            elapsed_ms = (time.time() - start_time) * 1000
            times.append(elapsed_ms)

        return {
            "avg_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": sorted(times)[int(0.95 * len(times))],
            "min_ms": min(times),
            "max_ms": max(times),
        }

    @pytest.mark.asyncio
    async def test_connection_pool_performance(self, initialized_pool):
        """Test connection pool meets performance targets."""

        async def connection_op():
            async with initialized_pool.get_connection("test_operation") as conn:
                await conn.execute("SELECT 1")
                return True

        stats = await self.measure_operation_time(connection_op, iterations=100)

        # Assert performance targets for database operations
        assert (
            stats["p95_ms"] < 50
        ), f"Database operation P95 {stats['p95_ms']:.1f}ms exceeds 50ms target"
        assert (
            stats["avg_ms"] < 25
        ), f"Database operation average {stats['avg_ms']:.1f}ms exceeds 25ms target"

        # Check pool utilization
        pool_stats = initialized_pool.get_performance_stats()
        utilization = pool_stats["pool_stats"]["pool_utilization"]
        assert (
            utilization < 0.8
        ), f"Pool utilization {utilization:.1%} exceeds 80% target"

        print(
            f"✅ Connection pool performance: {stats['avg_ms']:.1f}ms avg, {stats['p95_ms']:.1f}ms P95"
        )
        print(f"✅ Pool utilization: {utilization:.1%}")

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test cache system meets performance targets."""

        # Test cache set/get performance
        async def cache_set_op():
            await cache_manager.set("test_key", {"data": "test_value"}, ttl=300)
            return True

        async def cache_get_op():
            result = await cache_manager.get("test_key")
            return result is not None

        set_stats = await self.measure_operation_time(cache_set_op, iterations=100)
        get_stats = await self.measure_operation_time(cache_get_op, iterations=100)

        # Assert performance targets for caching (should be very fast)
        assert (
            set_stats["p95_ms"] < 5
        ), f"Cache set P95 {set_stats['p95_ms']:.1f}ms exceeds 5ms target"
        assert (
            get_stats["p95_ms"] < 1
        ), f"Cache get P95 {get_stats['p95_ms']:.1f}ms exceeds 1ms target"

        # Check cache hit ratio after repeated gets
        for _ in range(20):
            await cache_manager.get("test_key")

        cache_stats = cache_manager.get_cache_stats()
        hit_ratio = cache_stats["performance_metrics"]["hit_ratio"]

        # Should have high hit ratio with repeated access
        assert hit_ratio > 0.8, f"Cache hit ratio {hit_ratio:.1%} below 80% threshold"

        print(
            f"✅ Cache set performance: {set_stats['avg_ms']:.1f}ms avg, {set_stats['p95_ms']:.1f}ms P95"
        )
        print(
            f"✅ Cache get performance: {get_stats['avg_ms']:.1f}ms avg, {get_stats['p95_ms']:.1f}ms P95"
        )
        print(f"✅ Cache hit ratio: {hit_ratio:.1%}")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, initialized_pool):
        """Test concurrent database operations performance."""

        async def concurrent_db_operation(operation_id: int):
            """Simulate concurrent database operation."""
            try:
                async with initialized_pool.get_connection(
                    f"concurrent_op_{operation_id}"
                ) as conn:
                    # Simulate work
                    await conn.execute("SELECT 1 WHERE ? > 0", (operation_id,))
                    await asyncio.sleep(0.001)  # 1ms simulated work
                    return {"success": True, "operation_id": operation_id}
            except Exception as e:
                return {"success": False, "error": str(e), "operation_id": operation_id}

        # Test with 20 concurrent operations (meets 20+ concurrent agents requirement)
        concurrent_count = 25
        start_time = time.time()

        tasks = [concurrent_db_operation(i) for i in range(concurrent_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_time = time.time() - start_time

        # Analyze results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        concurrent_count - successful
        success_rate = successful / concurrent_count

        # Assert performance requirements
        assert successful >= 20, f"Only {successful} operations succeeded, need 20+"
        assert (
            success_rate >= 0.95
        ), f"Success rate {success_rate:.1%} below 95% threshold"
        assert (
            elapsed_time < 5
        ), f"Concurrent operations took {elapsed_time:.1f}s, should be <5s"

        # Check final pool utilization
        pool_stats = initialized_pool.get_performance_stats()
        final_utilization = pool_stats["pool_stats"]["pool_utilization"]

        print(f"✅ Concurrent operations: {successful}/{concurrent_count} succeeded")
        print(f"   Success rate: {success_rate:.1%}, Total time: {elapsed_time:.1f}s")
        print(f"   Final pool utilization: {final_utilization:.1%}")

    @pytest.mark.asyncio
    async def test_performance_metrics_availability(self, initialized_pool):
        """Test performance metrics are available and contain expected data."""

        # Generate some activity first
        async def generate_activity():
            for i in range(10):
                async with initialized_pool.get_connection(f"metrics_test_{i}") as conn:
                    await conn.execute("SELECT ?", (i,))

        await generate_activity()

        # Test performance metrics collection
        metrics = get_performance_metrics_dict()

        # Should return success
        assert metrics.get("success") is True, "Performance metrics should be available"

        # Check database performance metrics
        db_performance = metrics.get("database_performance", {})
        assert "connection_stats" in db_performance, "Should contain connection stats"
        assert "pool_stats" in db_performance, "Should contain pool stats"
        assert (
            "performance_indicators" in db_performance
        ), "Should contain performance indicators"

        # Check performance indicators
        indicators = db_performance["performance_indicators"]
        assert "avg_query_time_ms" in indicators, "Should track average query time"
        assert "pool_utilization" in indicators, "Should track pool utilization"
        assert "error_rate" in indicators, "Should track error rate"

        # Performance targets validation
        avg_query_time = indicators["avg_query_time_ms"]
        pool_utilization = indicators["pool_utilization"]
        error_rate = indicators["error_rate"]

        # Verify performance is within acceptable ranges
        assert (
            avg_query_time < 100
        ), f"Average query time {avg_query_time:.1f}ms too high"
        assert (
            pool_utilization < 1.0
        ), f"Pool utilization {pool_utilization:.1%} at maximum"
        assert error_rate < 0.1, f"Error rate {error_rate:.1%} too high"

        print("✅ Performance metrics available:")
        print(f"   Average query time: {avg_query_time:.1f}ms")
        print(f"   Pool utilization: {pool_utilization:.1%}")
        print(f"   Error rate: {error_rate:.1%}")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
