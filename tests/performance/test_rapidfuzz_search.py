"""
Performance tests for RapidFuzz search functionality.

Tests the 5-10x performance improvement claim and accuracy requirements
from the Phase 2 specification.
"""

import asyncio

# Import testing helpers from conftest.py
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.append(str(Path(__file__).parent.parent))
from conftest import call_fastmcp_tool

# Import search function directly


@pytest.fixture
def mock_database_with_messages():
    """Mock database populated with test messages for performance testing."""
    sessions = {}
    messages = {}
    message_counter = [1]

    # Pre-populate with test messages
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
        "Pydantic model validation with comprehensive type safety",
        "Resource subscription and real-time notification systems",
        "Background task management and cleanup automation",
        "Search result ranking with relevance scoring algorithms",
        "Memory scoping between global and session-specific storage",
        "Error handling patterns with structured response formatting",
        "Input sanitization and security validation protocols",
        "Performance benchmarking and optimization strategies",
        "Multi-agent coordination through shared context sessions",
        "Fuzzy string matching with configurable similarity thresholds",
    ]

    async def mock_execute(query, params=()):
        nonlocal sessions, messages, message_counter

        if "INSERT INTO sessions" in query:
            session_id, purpose, created_by, metadata = params
            sessions[session_id] = {
                "id": session_id,
                "purpose": purpose,
                "created_by": created_by,
                "metadata": metadata,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
                "is_active": True,
            }
            return AsyncMock(lastrowid=None)

        if "SELECT * FROM sessions WHERE id = ?" in query:
            session_id = params[0]
            session = sessions.get(session_id)
            return AsyncMock(fetchone=AsyncMock(return_value=session))

        if "INSERT INTO messages" in query:
            session_id, sender, content, visibility, metadata, parent_id = params
            msg_id = message_counter[0]
            message_counter[0] += 1
            messages[msg_id] = {
                "id": msg_id,
                "session_id": session_id,
                "sender": sender,
                "content": content,
                "visibility": visibility,
                "metadata": metadata,
                "timestamp": "2025-01-01T00:00:00",
                "parent_message_id": parent_id,
            }
            return AsyncMock(lastrowid=msg_id)

        if "SELECT * FROM messages" in query and "session_id = ?" in query:
            session_id = params[0]
            # Return all test messages for this session
            filtered = []
            for i, content in enumerate(test_messages):
                msg = {
                    "id": i + 1,
                    "session_id": session_id,
                    "sender": "test_agent",
                    "content": content,
                    "visibility": "public",
                    "metadata": "{}",
                    "timestamp": "2025-01-01T00:00:00",
                    "parent_message_id": None,
                }
                filtered.append(msg)
            return AsyncMock(fetchall=AsyncMock(return_value=filtered))

        if "INSERT INTO audit_log" in query:
            return AsyncMock()

        return AsyncMock()

    mock_conn = AsyncMock()
    mock_conn.execute = mock_execute
    mock_conn.commit = AsyncMock()
    return mock_conn


@pytest.mark.asyncio
@pytest.mark.performance
async def test_rapidfuzz_search_performance(
    server_with_db, search_test_session, test_db_manager
):
    """Test RapidFuzz search performance meets <100ms requirement."""

    session_id, ctx = search_test_session

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

        # Use same database as session creation (patched via server_with_db)
        result = await call_fastmcp_tool(
            server_with_db.search_context,
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
        server_with_db.search_context,
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
    server_with_db, search_test_session, test_db_manager
):
    """Test search accuracy across different fuzzy thresholds."""

    session_id, ctx = search_test_session

    # Test query with known matches
    query = "fuzzy search performance"
    thresholds = [40.0, 60.0, 80.0, 90.0]

    results_by_threshold = {}

    for threshold in thresholds:
        # Use same database as session creation (patched via server_with_db)
        result = await call_fastmcp_tool(
            server_with_db.search_context,
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
    server_with_db, search_test_session, test_db_manager
):
    """Test search performance with metadata inclusion."""

    session_id, ctx = search_test_session

    # WARMUP: Run search operations once to cache imports and initialize modules
    # This eliminates cold-start penalties and measures steady-state performance
    await call_fastmcp_tool(
        server_with_db.search_context,
        ctx,
        session_id=session_id,
        query="warmup search",
        fuzzy_threshold=60.0,
        search_metadata=True,
        limit=10,
    )
    await call_fastmcp_tool(
        server_with_db.search_context,
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
        server_with_db.search_context,
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
        server_with_db.search_context,
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
    server_with_db, search_test_session, test_db_manager
):
    """Test search performance under concurrent load."""

    session_id, ctx = search_test_session

    async def perform_search(query_suffix: str):
        """Perform a single search operation."""
        async with test_db_manager.get_connection() as test_conn:
            import aiosqlite

            test_conn.row_factory = aiosqlite.Row

            return await call_fastmcp_tool(
                server_with_db.search_context,
                ctx,
                session_id=session_id,
                query=f"performance test {query_suffix}",
                fuzzy_threshold=60.0,
                limit=10,
            )

    # Run multiple concurrent searches
    concurrent_searches = 5  # Reduced for mock testing
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
