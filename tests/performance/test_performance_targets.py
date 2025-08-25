"""
Performance validation tests adapted for SQLAlchemy-only architecture (post PRP-024).

Tests basic performance metrics and caching functionality:
- Cache performance validation
- Performance metrics availability
- Basic database connection validation

Note: Connection pool performance tests removed as aiosqlite ConnectionPoolManager
was deprecated in PRP-024. SQLAlchemy handles connection pooling internally.
"""

import statistics
import time

import pytest

from shared_context_server.utils.caching import cache_manager
from shared_context_server.utils.performance import get_performance_metrics_dict


class TestPerformanceTargets:
    """Test basic performance targets with SQLAlchemy backend."""

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
        assert set_stats["p95_ms"] < 5, (
            f"Cache set P95 {set_stats['p95_ms']:.1f}ms exceeds 5ms target"
        )
        assert get_stats["p95_ms"] < 1, (
            f"Cache get P95 {get_stats['p95_ms']:.1f}ms exceeds 1ms target"
        )

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
    async def test_performance_metrics_availability(self):
        """Test performance metrics are available and return expected structure."""

        # Test performance metrics collection
        metrics = get_performance_metrics_dict()

        # Should return success (even if deprecated)
        assert metrics.get("success") is True, "Performance metrics should be available"

        # Check that SQLAlchemy migration status is indicated
        assert metrics.get("database_backend") == "sqlalchemy", (
            "Should indicate SQLAlchemy backend"
        )
        assert metrics.get("migration_status") == "aiosqlite_removed", (
            "Should indicate migration complete"
        )

        # Check database performance metrics structure (even if zeroed)
        db_performance = metrics.get("database_performance", {})
        assert "connection_stats" in db_performance, "Should contain connection stats"
        assert "pool_stats" in db_performance, "Should contain pool stats"
        assert "performance_indicators" in db_performance, (
            "Should contain performance indicators"
        )

        # Check performance indicators exist (values may be zero in deprecated mode)
        indicators = db_performance["performance_indicators"]
        assert "avg_query_time_ms" in indicators, "Should track average query time"
        assert "pool_utilization" in indicators, "Should track pool utilization"
        assert "error_rate" in indicators, "Should track error rate"

        # Check system info indicates migration
        system_info = metrics.get("system_info", {})
        assert system_info.get("migration_complete") is True, (
            "Should indicate migration complete"
        )
        assert system_info.get("database_backend") == "sqlalchemy", (
            "Should show SQLAlchemy backend"
        )

        print("✅ Performance metrics available (post-migration):")
        print(f"   Database backend: {metrics.get('database_backend')}")
        print(f"   Migration status: {metrics.get('migration_status')}")
        print(f"   Migration complete: {system_info.get('migration_complete')}")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
