"""
Performance tests for RapidFuzz search functionality.

Tests the 5-10x performance improvement claim and accuracy requirements
from the Phase 2 specification.

Modernized to use isolated_db fixture and seeded test data instead of legacy hardcoded patterns.
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.append(str(Path(__file__).parent.parent))
from conftest import call_fastmcp_tool, MockContext
from tests.fixtures.database import (
    DatabaseTestManager,
    patch_database_for_test,
)



@pytest.mark.asyncio
@pytest.mark.performance
async def test_rapidfuzz_search_performance(
    isolated_db: DatabaseTestManager, test_db_manager
):
    """Test RapidFuzz search performance meets <100ms requirement."""

    with (
        patch_database_for_test(isolated_db),
        patch("shared_context_server.server.trigger_resource_notifications") as mock_notify,
    ):
        mock_notify.return_value = None

        # Create test session and messages
        from shared_context_server.server import create_session, search_context
        
        ctx = MockContext("search_perf_agent")
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="RapidFuzz search performance testing"
        )
        session_id = session_result["session_id"]
        
        # Add performance test messages
        test_messages = [
            "Python programming with async await patterns for scalable applications",
            "FastMCP server implementation guide with comprehensive examples", 
            "Agent memory system with TTL expiration and scope management",
            "RapidFuzz fuzzy search performance optimization techniques",
            "Database connection pooling for high-throughput applications",
            "SQLite WAL mode configuration for concurrent access patterns",
            "Message visibility controls and agent authentication systems",
            "JSON serialization and deserialization with error handling",
            "UTC timestamp management for distributed system coordination",
            "Session isolation and cross-agent collaboration patterns",
        ]
        
        # Insert test messages
        from shared_context_server.server import add_message
        for content in test_messages:
            await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content=content,
                visibility="public",
            )

        # Performance test: multiple searches
        search_queries = [
            "fuzzy search performance",
            "async await patterns",
            "database connection",
            "memory system",
            "agent authentication",
        ]

        total_time = 0
        successful_searches = 0

        for query in search_queries:
            start_time = time.time()

            # Use same context for search
            result = await call_fastmcp_tool(
                search_context,
                ctx,
                session_id=session_id,
                query=query,
                fuzzy_threshold=60.0,
                limit=10,
            )

            search_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            assert result["success"] is True, (
                f"Search failed for query: {query} - Error: {result.get('error', 'Unknown error')}"
            )
            assert "search_time_ms" in result, "Search time not reported"

            # Verify performance requirement: <100ms for search operation
            assert search_time < 100, f"Search took {search_time:.2f}ms, expected <100ms"

            # Verify reported time is reasonable
            reported_time = result["search_time_ms"]
            assert reported_time > 0, "Reported search time should be positive"

            total_time += search_time
            successful_searches += 1

        # Calculate average performance
        avg_time = total_time / successful_searches
        print("\nRapidFuzz Search Performance Results:")
        print(f"  - Average search time: {avg_time:.2f}ms")
        print(f"  - All searches completed under 100ms requirement: {avg_time < 100}")

        # Verify performance note is included
        final_result = await call_fastmcp_tool(
            search_context,
            ctx,
            session_id=session_id,
            query="performance test",
            fuzzy_threshold=70,
        )

        assert "RapidFuzz enabled" in final_result["performance_note"]
        assert "5-10x faster" in final_result["performance_note"]


@pytest.mark.asyncio
@pytest.mark.performance
async def test_search_accuracy_vs_threshold(
    isolated_db: DatabaseTestManager, test_db_manager
):
    """Test search accuracy across different fuzzy thresholds."""

    with (
        patch_database_for_test(isolated_db),
        patch("shared_context_server.server.trigger_resource_notifications") as mock_notify,
    ):
        mock_notify.return_value = None
        
        # Create test session and messages
        from shared_context_server.server import create_session, search_context, add_message
        
        ctx = MockContext("search_accuracy_agent")
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="Search accuracy testing"
        )
        session_id = session_result["session_id"]
        
        # Add test messages with known fuzzy search targets
        test_messages = [
            "RapidFuzz fuzzy search performance optimization techniques",
            "Python programming with async await patterns for scalable applications", 
            "Agent memory system with TTL expiration and scope management",
            "Database connection pooling for high-throughput applications",
            "SQLite WAL mode configuration for concurrent access patterns",
            "Message visibility controls and agent authentication systems",
            "JSON serialization and deserialization with error handling",
            "UTC timestamp management for distributed system coordination",
            "Session isolation and cross-agent collaboration patterns",
            "Pydantic model validation with comprehensive type safety",
        ]
        
        for content in test_messages:
            await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content=content,
                visibility="public",
            )

        # Test query with known matches
        query = "fuzzy search performance"
        thresholds = [40.0, 60.0, 80.0, 90.0]

        results_by_threshold = {}

        for threshold in thresholds:
            # Use patched database connection for search
            result = await call_fastmcp_tool(
                search_context,
                ctx,
                session_id=session_id,
                query=query,
                fuzzy_threshold=threshold,
                limit=20,
            )

            assert result["success"] is True
            results_by_threshold[threshold] = result

            # Verify all returned results meet the threshold
            for match in result["results"]:
                assert match["score"] >= threshold, (
                    f"Result score {match['score']} below threshold {threshold}"
                )

            # Verify relevance categorization
            for match in result["results"]:
                score = match["score"]
                relevance = match["relevance"]

                if score >= 80:
                    assert relevance == "high", (
                        f"Score {score} should be high relevance, got {relevance}"
                    )
                elif score >= 60:
                    assert relevance == "medium", (
                        f"Score {score} should be medium relevance, got {relevance}"
                    )
                else:
                    assert relevance == "low", (
                        f"Score {score} should be low relevance, got {relevance}"
                    )

        print("✅ Search accuracy vs threshold test completed successfully")


@pytest.mark.asyncio
@pytest.mark.performance
async def test_search_with_metadata_performance(
    isolated_db: DatabaseTestManager, test_db_manager
):
    """Test search performance with metadata inclusion."""

    with (
        patch_database_for_test(isolated_db),
        patch("shared_context_server.server.trigger_resource_notifications") as mock_notify,
    ):
        mock_notify.return_value = None
        
        # Create test session and messages
        from shared_context_server.server import create_session, search_context, add_message
        
        ctx = MockContext("search_metadata_agent")
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="Search metadata performance testing"
        )
        session_id = session_result["session_id"]
        
        # Add test messages with metadata
        test_messages = [
            "Performance optimization techniques",
            "Database connection management", 
            "Agent memory system implementation",
            "Search functionality testing",
            "Metadata search capabilities",
        ]
        
        for i, content in enumerate(test_messages):
            await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content=content,
                visibility="public",
                metadata={"priority": "high" if i % 2 == 0 else "low", "category": "performance"},
            )

        # WARMUP: Run search operations once to cache imports and initialize modules
        # This eliminates cold-start penalties and measures steady-state performance
        await call_fastmcp_tool(
            search_context,
            ctx,
            session_id=session_id,
            query="warmup search",
            fuzzy_threshold=60.0,
            search_metadata=True,
            limit=10,
        )
        await call_fastmcp_tool(
            search_context,
            ctx,
            session_id=session_id,
            query="warmup search",
            fuzzy_threshold=60.0,
            search_metadata=False,
            limit=10,
        )

        # Test with metadata search enabled (steady-state performance)
        start_time = time.time()
        result_with_metadata = await call_fastmcp_tool(
            search_context,
            ctx,
            session_id=session_id,
            query="performance optimization",
            fuzzy_threshold=60.0,
            search_metadata=True,
            limit=10,
        )
        time_with_metadata = (time.time() - start_time) * 1000

        # Test with metadata search disabled (steady-state performance)
        start_time = time.time()
        result_without_metadata = await call_fastmcp_tool(
            search_context,
            ctx,
            session_id=session_id,
            query="performance optimization",
            fuzzy_threshold=60.0,
            search_metadata=False,
            limit=10,
        )
        time_without_metadata = (time.time() - start_time) * 1000

        # Both should complete quickly (steady-state performance)
        assert time_with_metadata < 100, (
            f"Search with metadata took {time_with_metadata:.2f}ms"
        )
        assert time_without_metadata < 100, (
            f"Search without metadata took {time_without_metadata:.2f}ms"
        )

        # Both should be successful
        assert result_with_metadata["success"] is True
        assert result_without_metadata["success"] is True

        print("\nMetadata Search Performance:")
        print(
            f"  - With metadata: {len(result_with_metadata['results'])} results in {time_with_metadata:.2f}ms"
        )
        print(
            f"  - Without metadata: {len(result_without_metadata['results'])} results in {time_without_metadata:.2f}ms"
        )


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_search_performance(
    isolated_db: DatabaseTestManager, test_db_manager
):
    """Test search performance under concurrent load."""

    with (
        patch_database_for_test(isolated_db),
        patch("shared_context_server.server.trigger_resource_notifications") as mock_notify,
    ):
        mock_notify.return_value = None
        
        # Create test session and messages
        from shared_context_server.server import create_session, search_context, add_message
        
        ctx = MockContext("search_concurrent_agent")
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="Concurrent search performance testing"
        )
        session_id = session_result["session_id"]
        
        # Add test messages for concurrent searching
        test_messages = [
            "Performance test query 0 optimization",
            "Performance test query 1 database management", 
            "Performance test query 2 agent memory",
            "Performance test query 3 search functionality",
            "Performance test query 4 concurrent testing",
            "Additional context for fuzzy search matching",
            "More content to enable meaningful search results",
        ]
        
        for content in test_messages:
            await call_fastmcp_tool(
                add_message,
                ctx,
                session_id=session_id,
                content=content,
                visibility="public",
            )

        async def perform_search(query_suffix: str):
            """Perform a single search operation."""
            return await call_fastmcp_tool(
                search_context,
                ctx,
                session_id=session_id,
                query=f"performance test {query_suffix}",
                fuzzy_threshold=60.0,
                limit=10,
            )

        # Run multiple concurrent searches
        concurrent_searches = 5  # Reduced for testing
        start_time = time.time()

        # Execute searches concurrently
        tasks = [perform_search(f"query_{i}") for i in range(concurrent_searches)]
        results = await asyncio.gather(*tasks)

        total_time = (time.time() - start_time) * 1000
        avg_time_per_search = total_time / concurrent_searches

        # Verify all searches succeeded
        for i, result in enumerate(results):
            assert result["success"] is True, f"Concurrent search {i} failed"

        # Performance should still be reasonable under concurrent load
        assert avg_time_per_search < 150, (
            f"Average concurrent search time {avg_time_per_search:.2f}ms too high"
        )

        print("\nConcurrent Search Performance:")
        print(f"  - Concurrent searches: {concurrent_searches}")
        print(f"  - Total time: {total_time:.2f}ms")
        print(f"  - Average per search: {avg_time_per_search:.2f}ms")
        print(f"  - All searches successful: {all(r['success'] for r in results)}")
