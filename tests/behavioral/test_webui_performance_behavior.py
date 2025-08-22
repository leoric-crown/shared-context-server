"""
WebUI Performance Behavioral Tests for Database Initialization Optimization.

Tests that WebUI requests no longer trigger repeated database initialization
and achieve improved response times after removing per-request checks.

Validates user-observable behavior improvements in the web interface.
"""

import asyncio
import logging
import statistics
import sys
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from shared_context_server.server import mcp

sys.path.append(str(Path(__file__).parent.parent))


@pytest.fixture
async def test_client(isolated_db) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create test client for Web UI endpoints."""
    # Use isolated test database instead of production database
    from tests.fixtures.database import patch_database_for_test

    with patch_database_for_test(isolated_db):
        # Create test client with FastMCP HTTP app
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=mcp.http_app()),
            base_url="http://testserver",
        ) as client:
            yield client


class TestWebUIPerformanceBehavior:
    """Test WebUI performance behavior after database optimization."""

    async def measure_endpoint_response_time(
        self, client: httpx.AsyncClient, endpoint: str
    ) -> float:
        """Measure HTTP response time for endpoint in milliseconds."""
        start_time = time.time()
        response = await client.get(endpoint)
        response_time = (time.time() - start_time) * 1000

        assert response.status_code == 200, (
            f"Endpoint {endpoint} returned {response.status_code}"
        )
        return response_time

    async def measure_multiple_requests(
        self, client: httpx.AsyncClient, endpoint: str, count: int = 10
    ) -> dict[str, float]:
        """Measure performance statistics for multiple requests."""
        times = []

        for _ in range(count):
            response_time = await self.measure_endpoint_response_time(client, endpoint)
            times.append(response_time)

        return {
            "avg_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": sorted(times)[int(0.95 * len(times))],
            "min_ms": min(times),
            "max_ms": max(times),
        }

    @pytest.mark.asyncio
    async def test_webui_dashboard_response_optimization(
        self, test_client: httpx.AsyncClient
    ):
        """Test WebUI dashboard loads quickly without initialization delays."""

        stats = await self.measure_multiple_requests(test_client, "/ui/", count=10)

        # WebUI should load quickly without database initialization overhead
        assert stats["avg_ms"] < 200, (
            f"Dashboard average response time {stats['avg_ms']:.1f}ms exceeds 200ms target"
        )
        assert stats["p95_ms"] < 300, (
            f"Dashboard P95 response time {stats['p95_ms']:.1f}ms exceeds 300ms target"
        )
        assert stats["median_ms"] < 150, (
            f"Dashboard median response time {stats['median_ms']:.1f}ms exceeds 150ms target"
        )

        print("✅ WebUI dashboard performance optimized:")
        print(f"   Average: {stats['avg_ms']:.1f}ms (target: <200ms)")
        print(f"   P95: {stats['p95_ms']:.1f}ms (target: <300ms)")
        print(f"   Median: {stats['median_ms']:.1f}ms (target: <150ms)")

    @pytest.mark.asyncio
    async def test_webui_memory_dashboard_response_optimization(
        self, test_client: httpx.AsyncClient
    ):
        """Test WebUI memory dashboard loads quickly after optimization."""

        stats = await self.measure_multiple_requests(
            test_client, "/ui/memory", count=10
        )

        # Memory dashboard should also benefit from optimization
        assert stats["avg_ms"] < 200, (
            f"Memory dashboard average response time {stats['avg_ms']:.1f}ms exceeds 200ms target"
        )
        assert stats["p95_ms"] < 300, (
            f"Memory dashboard P95 response time {stats['p95_ms']:.1f}ms exceeds 300ms target"
        )

        print("✅ WebUI memory dashboard performance optimized:")
        print(f"   Average: {stats['avg_ms']:.1f}ms (target: <200ms)")
        print(f"   P95: {stats['p95_ms']:.1f}ms (target: <300ms)")

    @pytest.mark.asyncio
    async def test_health_endpoint_response_optimization(
        self, test_client: httpx.AsyncClient
    ):
        """Test health endpoint responds quickly after optimization."""

        stats = await self.measure_multiple_requests(test_client, "/health", count=15)

        # Health endpoint should be fastest (minimal database access)
        assert stats["avg_ms"] < 100, (
            f"Health endpoint average response time {stats['avg_ms']:.1f}ms exceeds 100ms target"
        )
        assert stats["p95_ms"] < 150, (
            f"Health endpoint P95 response time {stats['p95_ms']:.1f}ms exceeds 150ms target"
        )

        print("✅ Health endpoint performance optimized:")
        print(f"   Average: {stats['avg_ms']:.1f}ms (target: <100ms)")
        print(f"   P95: {stats['p95_ms']:.1f}ms (target: <150ms)")

    @pytest.mark.asyncio
    async def test_concurrent_webui_requests_performance(
        self, test_client: httpx.AsyncClient
    ):
        """Test concurrent WebUI requests maintain performance."""

        async def concurrent_request_test(endpoint: str, request_id: int):
            """Single concurrent request test."""
            start_time = time.time()
            response = await test_client.get(endpoint)
            response_time = (time.time() - start_time) * 1000

            assert response.status_code == 200
            return response_time

        # Test concurrent requests to different endpoints
        endpoints = ["/ui/", "/ui/memory", "/health"]
        concurrent_count = 15  # 5 requests per endpoint

        start_time = time.time()

        tasks = []
        for i, endpoint in enumerate(endpoints):
            tasks.extend(
                [concurrent_request_test(endpoint, i * 5 + j) for j in range(5)]
            )

        response_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)

        # Performance requirements for concurrent WebUI requests
        assert total_time < 5, (
            f"Concurrent WebUI requests took {total_time:.1f}s, should be <5s"
        )
        assert avg_response_time < 300, (
            f"Average concurrent response time {avg_response_time:.1f}ms exceeds 300ms"
        )
        assert max_response_time < 500, (
            f"Max concurrent response time {max_response_time:.1f}ms exceeds 500ms"
        )

        print("✅ Concurrent WebUI request performance validated:")
        print(f"   {concurrent_count} requests completed in {total_time:.1f}s")
        print(f"   Average response time: {avg_response_time:.1f}ms")
        print(f"   Max response time: {max_response_time:.1f}ms")

    @pytest.mark.asyncio
    async def test_webui_requests_no_repeated_initialization(
        self, test_client: httpx.AsyncClient, caplog
    ):
        """Test WebUI requests don't trigger repeated database initialization."""

        with caplog.at_level(logging.INFO):
            # Multiple WebUI requests should not trigger repeated initialization
            endpoints = ["/ui/", "/ui/memory", "/health"]

            for endpoint in endpoints:
                for _ in range(3):  # 3 requests per endpoint
                    response = await test_client.get(endpoint)
                    assert response.status_code == 200

        # Count initialization messages during WebUI requests
        init_messages = [
            record
            for record in caplog.records
            if "Database initialized successfully" in record.message
        ]

        schema_messages = [
            record
            for record in caplog.records
            if "Database schema validation successful" in record.message
        ]

        # Should have 0 initialization messages during WebUI requests
        assert len(init_messages) == 0, (
            f"Found {len(init_messages)} database initialization messages during WebUI requests. "
            f"Per-request initialization should be eliminated."
        )

        # Should have minimal schema validation messages
        assert len(schema_messages) <= 1, (
            f"Found {len(schema_messages)} schema validation messages during WebUI requests. "
            f"Per-request schema validation should be eliminated."
        )

        print("✅ WebUI requests don't trigger repeated database initialization")

    @pytest.mark.asyncio
    async def test_webui_performance_improvement_validation(
        self, test_client: httpx.AsyncClient
    ):
        """Test and validate WebUI performance improvement from baseline."""

        # Test main dashboard performance
        dashboard_stats = await self.measure_multiple_requests(
            test_client, "/ui/", count=20
        )

        # Document expected improvement (assuming 300ms+ baseline before optimization)
        baseline_ms = 300.0  # Previous slow response time
        improvement_factor = baseline_ms / dashboard_stats["avg_ms"]
        improvement_percentage = (
            (baseline_ms - dashboard_stats["avg_ms"]) / baseline_ms
        ) * 100

        # Should achieve significant improvement
        assert improvement_factor >= 2, (
            f"WebUI performance improvement {improvement_factor:.1f}x below 2x target. "
            f"Average: {dashboard_stats['avg_ms']:.1f}ms vs baseline: {baseline_ms}ms"
        )

        print("✅ WebUI performance improvement validated:")
        print(f"   Baseline: {baseline_ms}ms")
        print(f"   Optimized: {dashboard_stats['avg_ms']:.1f}ms")
        print(
            f"   Improvement: {improvement_factor:.1f}x ({improvement_percentage:.1f}%)"
        )

    @pytest.mark.asyncio
    async def test_webui_session_view_performance(
        self, test_client: httpx.AsyncClient, isolated_db
    ):
        """Test session view performance after optimization."""
        from contextlib import asynccontextmanager

        # Create async mock for database connection
        @asynccontextmanager
        async def mock_get_db_connection():
            async with isolated_db.get_connection() as conn:
                yield conn

        # Create test session
        session_id = "perf_test_session_123456789ab"

        with patch(
            "shared_context_server.web_endpoints.get_db_connection",
            mock_get_db_connection,
        ):
            async with isolated_db.get_connection() as conn:
                # Insert test session
                await conn.execute(
                    "INSERT INTO sessions (id, purpose, created_by, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        "Performance test session",
                        "test_agent",
                        "{}",
                        1692000000.0,
                        1692000000.0,
                    ),
                )
                await conn.commit()

            # Test session view performance
            stats = await self.measure_multiple_requests(
                test_client, f"/ui/sessions/{session_id}", count=10
            )

            # Session view should load quickly
            assert stats["avg_ms"] < 250, (
                f"Session view average response time {stats['avg_ms']:.1f}ms exceeds 250ms target"
            )
            assert stats["p95_ms"] < 400, (
                f"Session view P95 response time {stats['p95_ms']:.1f}ms exceeds 400ms target"
            )

            print("✅ Session view performance optimized:")
            print(f"   Average: {stats['avg_ms']:.1f}ms (target: <250ms)")
            print(f"   P95: {stats['p95_ms']:.1f}ms (target: <400ms)")

    @pytest.mark.asyncio
    async def test_webui_error_handling_performance(
        self, test_client: httpx.AsyncClient
    ):
        """Test error responses maintain good performance."""

        # Test 404 response performance
        start_time = time.time()
        response = await test_client.get("/ui/sessions/nonexistent_session_123")
        response_time = (time.time() - start_time) * 1000

        assert response.status_code == 404

        # Error responses should also be fast
        assert response_time < 100, (
            f"404 error response time {response_time:.1f}ms exceeds 100ms target"
        )

        print(f"✅ Error response performance validated: {response_time:.1f}ms")


if __name__ == "__main__":
    # Run behavioral tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
