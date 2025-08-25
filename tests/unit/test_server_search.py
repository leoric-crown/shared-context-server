"""
Unit tests for RapidFuzz search system in the server.

Tests search_context, search_by_sender, and search_by_timerange operations
with comprehensive scenarios including fuzzy matching, metadata search,
visibility controls, performance optimization, and edge cases.
"""

import time
from datetime import datetime, timezone

import pytest

from shared_context_server.database_manager import CompatibleRow
from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestRapidFuzzSearchSystem:
    """Test the RapidFuzz-powered search system."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    @pytest.fixture
    async def search_test_session(self, server_with_db, test_db_manager):
        """Create a session with diverse test data for search testing."""
        ctx = MockContext(agent_id="search_agent")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Search test session"
        )
        session_id = create_result["session_id"]

        # Add diverse test messages
        test_messages = [
            {
                "content": "FastAPI is a modern web framework for Python",
                "visibility": "public",
                "metadata": {
                    "category": "technology",
                    "language": "python",
                    "rating": 5,
                },
            },
            {
                "content": "RapidFuzz provides fast string matching algorithms",
                "visibility": "public",
                "metadata": {
                    "category": "technology",
                    "language": "python",
                    "rating": 4,
                },
            },
            {
                "content": "SQLite is a lightweight database engine",
                "visibility": "private",
                "metadata": {"category": "database", "type": "embedded", "rating": 4},
            },
            {
                "content": "Machine learning models require large datasets",
                "visibility": "agent_only",
                "metadata": {"category": "ai", "complexity": "high", "rating": 3},
            },
            {
                "content": "Python programming language is versatile and powerful",
                "visibility": "public",
                "metadata": {
                    "category": "programming",
                    "language": "python",
                    "rating": 5,
                },
            },
            {
                "content": "API design patterns for scalable web services",
                "visibility": "public",
                "metadata": {"category": "architecture", "scope": "web", "rating": 4},
            },
            {
                "content": "Database indexing improves query performance significantly",
                "visibility": "private",
                "metadata": {"category": "database", "optimization": True, "rating": 5},
            },
            {
                "content": "Test-driven development ensures code quality",
                "visibility": "public",
                "metadata": {"category": "testing", "methodology": "TDD", "rating": 4},
            },
        ]

        for _i, msg_data in enumerate(test_messages):
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=msg_data["content"],
                visibility=msg_data["visibility"],
                metadata=msg_data["metadata"],
            )
            # Small delay to ensure different timestamps
            time.sleep(0.01)

        return session_id, ctx

    async def test_search_context_basic_functionality(
        self, server_with_db, search_test_session, test_db_manager
    ):
        """Test basic fuzzy search functionality."""
        session_id, ctx = search_test_session

        # Use same database as session creation (patched via server_with_db)
        result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="FastAPI",
            fuzzy_threshold=60.0,  # More realistic threshold for partial matches
        )

        assert result["success"] is True
        assert len(result["results"]) > 0
        assert result["query"] == "FastAPI"
        assert result["threshold"] == 60.0

        # Should find the FastAPI message
        found_contents = [r["message"]["content"] for r in result["results"]]
        assert any("FastAPI" in content for content in found_contents)

    async def test_search_context_fuzzy_matching(self, server_with_db, test_db_manager):
        """Test fuzzy string matching with various similarity levels."""
        from shared_context_server.server import search_context

        ctx = MockContext(agent_id="fuzzy_search_agent")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Fuzzy search test"
        )
        session_id = create_result["session_id"]

        # Add test messages
        test_messages = [
            "Python programming language is powerful",
            "Database systems are important",
            "Machine learning models require data",
            "Web framework development is complex",
        ]

        for content in test_messages:
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=content,
                visibility="public",
            )

        # Test fuzzy matching with typos
        test_cases = [
            {"query": "Pyhton", "should_find": "Python", "threshold": 60.0},
            {"query": "databse", "should_find": "Database", "threshold": 60.0},
            {
                "query": "machne learning",
                "should_find": "Machine learning",
                "threshold": 50.0,
            },
            {
                "query": "web framwork",
                "should_find": "Web framework",
                "threshold": 50.0,
            },
        ]

        for case in test_cases:
            result = await call_fastmcp_tool(
                search_context,
                ctx,
                session_id=session_id,
                query=case["query"],
                fuzzy_threshold=case["threshold"],
            )

            assert result["success"] is True

            # Should find messages containing the intended term
            found_contents = [
                r["message"]["content"].lower() for r in result["results"]
            ]
            assert any(
                case["should_find"].lower() in content for content in found_contents
            )

    async def test_search_context_metadata_search(
        self, server_with_db, test_db_manager
    ):
        """Test searching within message metadata."""
        # Create own test data to ensure isolation
        ctx = MockContext(agent_id="metadata_search_agent")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Metadata search test session"
        )
        session_id = create_result["session_id"]

        # Add diverse test messages with metadata
        test_messages = [
            {
                "content": "FastAPI is a modern web framework for Python",
                "visibility": "public",
                "metadata": {
                    "category": "technology",
                    "language": "python",
                    "rating": 5,
                },
            },
            {
                "content": "RapidFuzz provides fast string matching algorithms",
                "visibility": "public",
                "metadata": {
                    "category": "technology",
                    "language": "python",
                    "rating": 4,
                },
            },
            {
                "content": "SQLite is a lightweight database engine",
                "visibility": "public",
                "metadata": {"category": "database", "type": "embedded", "rating": 4},
            },
            {
                "content": "Database indexing improves query performance",
                "visibility": "public",
                "metadata": {"category": "database", "optimization": True, "rating": 5},
            },
        ]

        for msg_data in test_messages:
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=msg_data["content"],
                visibility=msg_data["visibility"],
                metadata=msg_data["metadata"],
            )

        # Search for metadata values using server_with_db consistently
        metadata_queries = [
            {"query": "technology", "expected_count": 2},  # category: technology
            {"query": "database", "expected_count": 2},  # category: database
        ]

        for query_data in metadata_queries:
            result = await call_fastmcp_tool(
                server_with_db.search_context,
                ctx,
                session_id=session_id,
                query=query_data["query"],
                search_metadata=True,
                fuzzy_threshold=70.0,
            )

            assert result["success"] is True
            # Should find expected number of matches or close to it
            assert len(result["results"]) >= query_data["expected_count"] - 1

    async def test_search_context_without_metadata(
        self, server_with_db, test_db_manager
    ):
        """Test search with metadata disabled."""
        from shared_context_server.server import search_context

        ctx = MockContext(agent_id="no_metadata_agent")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="No metadata search test"
        )
        session_id = create_result["session_id"]

        # Add message with metadata that contains TDD
        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Test-driven development ensures code quality",
            visibility="public",
            metadata={"methodology": "TDD", "category": "testing"},
        )

        # Search for a term that only appears in metadata
        result = await call_fastmcp_tool(
            search_context,
            ctx,
            session_id=session_id,
            query="TDD",  # Only in metadata
            search_metadata=False,
            fuzzy_threshold=70.0,
        )

        assert result["success"] is True
        # Should find fewer results since metadata is excluded
        # But should still find the message content that might contain "Test-driven development"

    async def test_search_context_visibility_controls(
        self, server_with_db, search_test_session
    ):
        """Test search with different visibility scopes."""
        session_id, ctx = search_test_session

        # Test different search scopes
        scopes = ["all", "public", "private"]

        for scope in scopes:
            result = await call_fastmcp_tool(
                server_with_db.search_context,
                ctx,
                session_id=session_id,
                query="database",
                search_scope=scope,
                fuzzy_threshold=60.0,
            )

            assert result["success"] is True
            assert result["search_scope"] == scope

            # Verify visibility filtering
            for match in result["results"]:
                visibility = match["message"]["visibility"]
                if scope == "public":
                    assert visibility == "public"
                elif scope == "private":
                    assert visibility == "private"
                # For "all", should include public and private (owned by agent)

    async def test_search_context_multi_agent_visibility(
        self, server_with_db, test_db_manager
    ):
        """Test search visibility controls across different agents."""
        agent1_ctx = MockContext(agent_id="agent_1")
        agent2_ctx = MockContext(agent_id="agent_2")

        # Create session with agent 1
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, agent1_ctx, purpose="Multi-agent search test"
        )
        session_id = create_result["session_id"]

        # Agent 1 adds messages
        await call_fastmcp_tool(
            server_with_db.add_message,
            agent1_ctx,
            session_id=session_id,
            content="Agent 1 public message about testing",
            visibility="public",
        )

        await call_fastmcp_tool(
            server_with_db.add_message,
            agent1_ctx,
            session_id=session_id,
            content="Agent 1 private message about testing",
            visibility="private",
        )

        # Agent 2 adds messages
        await call_fastmcp_tool(
            server_with_db.add_message,
            agent2_ctx,
            session_id=session_id,
            content="Agent 2 private message about testing",
            visibility="private",
        )

        # Agent 1 searches
        agent1_results = await call_fastmcp_tool(
            server_with_db.search_context,
            agent1_ctx,
            session_id=session_id,
            query="testing",
            fuzzy_threshold=80.0,
        )

        agent1_contents = [r["message"]["content"] for r in agent1_results["results"]]

        # Agent 1 should see: public + own private
        assert any("Agent 1 public" in content for content in agent1_contents)
        assert any("Agent 1 private" in content for content in agent1_contents)
        assert not any("Agent 2 private" in content for content in agent1_contents)

        # Agent 2 searches
        agent2_results = await call_fastmcp_tool(
            server_with_db.search_context,
            agent2_ctx,
            session_id=session_id,
            query="testing",
            fuzzy_threshold=80.0,
        )

        agent2_contents = [r["message"]["content"] for r in agent2_results["results"]]

        # Agent 2 should see: public + own private
        assert any("Agent 1 public" in content for content in agent2_contents)
        assert any("Agent 2 private" in content for content in agent2_contents)
        assert not any("Agent 1 private" in content for content in agent2_contents)

    async def test_search_context_performance_features(
        self, server_with_db, search_test_session
    ):
        """Test performance optimization features."""
        session_id, ctx = search_test_session

        # Test search with performance metrics
        result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="framework",
            fuzzy_threshold=70.0,
            limit=5,
        )

        assert result["success"] is True
        assert "search_time_ms" in result
        assert result["search_time_ms"] > 0
        assert "performance_note" in result
        assert "RapidFuzz" in result["performance_note"]

        # Verify result limit is respected
        assert len(result["results"]) <= 5

    async def test_search_context_result_structure(
        self, server_with_db, search_test_session
    ):
        """Test the structure and content of search results."""
        session_id, ctx = search_test_session

        result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="Python",
            fuzzy_threshold=70.0,
        )

        assert result["success"] is True
        assert len(result["results"]) > 0

        # Verify result structure
        for match in result["results"]:
            assert "message" in match
            assert "score" in match
            assert "match_preview" in match
            assert "relevance" in match

            # Verify message structure
            message = match["message"]
            required_fields = [
                "id",
                "sender",
                "content",
                "timestamp",
                "visibility",
                "metadata",
            ]
            for field in required_fields:
                assert field in message

            # Verify score and relevance
            assert isinstance(match["score"], (int, float))
            assert match["score"] >= 0
            assert match["relevance"] in ["high", "medium", "low"]

    async def test_search_by_sender_functionality(
        self, server_with_db, search_test_session
    ):
        """Test search_by_sender tool."""
        session_id, ctx = search_test_session

        # All messages were sent by search_agent, so should find all visible ones
        result = await call_fastmcp_tool(
            server_with_db.search_by_sender,
            ctx,
            session_id=session_id,
            sender="search_agent",
            limit=10,
        )

        assert result["success"] is True
        assert result["sender"] == "search_agent"
        assert len(result["messages"]) > 0
        assert result["count"] > 0

        # Verify all returned messages are from the specified sender
        for message in result["messages"]:
            assert message["sender"] == "search_agent"

    async def test_search_by_sender_multi_agent(self, server_with_db, test_db_manager):
        """Test search_by_sender with multiple agents."""
        agent1_ctx = MockContext(agent_id="sender_agent_1")
        agent2_ctx = MockContext(agent_id="sender_agent_2")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, agent1_ctx, purpose="Sender search test"
        )
        session_id = create_result["session_id"]

        # Add messages from both agents
        await call_fastmcp_tool(
            server_with_db.add_message,
            agent1_ctx,
            session_id=session_id,
            content="Message from agent 1",
            visibility="public",
        )

        await call_fastmcp_tool(
            server_with_db.add_message,
            agent2_ctx,
            session_id=session_id,
            content="Message from agent 2",
            visibility="public",
        )

        # Search for agent 1 messages
        result1 = await call_fastmcp_tool(
            server_with_db.search_by_sender,
            agent1_ctx,
            session_id=session_id,
            sender="sender_agent_1",
        )

        assert result1["success"] is True
        assert len(result1["messages"]) == 1
        assert result1["messages"][0]["content"] == "Message from agent 1"

        # Search for agent 2 messages from agent 1's perspective
        result2 = await call_fastmcp_tool(
            server_with_db.search_by_sender,
            agent1_ctx,
            session_id=session_id,
            sender="sender_agent_2",
        )

        assert result2["success"] is True
        assert len(result2["messages"]) == 1  # Public message visible
        assert result2["messages"][0]["content"] == "Message from agent 2"

    async def test_search_by_timerange_functionality(
        self, server_with_db, test_db_manager
    ):
        """Test search_by_timerange tool."""
        ctx = MockContext(agent_id="time_agent")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Time search test"
        )
        session_id = create_result["session_id"]

        # Add messages at different times
        base_time = datetime.now(timezone.utc)

        # Message 1: Current time
        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Message at current time",
            visibility="public",
        )

        # Small delay and add another message (increased for SQLite timestamp precision)
        time.sleep(1.1)  # Ensure different seconds in SQLite CURRENT_TIMESTAMP
        mid_time = datetime.now(timezone.utc)

        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Message after delay",
            visibility="public",
        )

        time.sleep(0.1)
        end_time = datetime.now(timezone.utc)

        # Search for messages in specific time range
        async with test_db_manager.get_connection() as test_conn:
            test_conn.row_factory = CompatibleRow

            result = await call_fastmcp_tool(
                server_with_db.search_by_timerange,
                ctx,
                session_id=session_id,
                start_time=base_time.isoformat(),
                end_time=end_time.isoformat(),
            )

        assert result["success"] is True
        assert len(result["messages"]) == 2
        assert result["count"] == 2
        assert "timerange" in result
        assert result["timerange"]["start"] == base_time.isoformat()
        assert result["timerange"]["end"] == end_time.isoformat()

        # Test narrower time range
        async with test_db_manager.get_connection() as test_conn:
            test_conn.row_factory = CompatibleRow

            narrow_result = await call_fastmcp_tool(
                server_with_db.search_by_timerange,
                ctx,
                session_id=session_id,
                start_time=mid_time.isoformat(),
                end_time=end_time.isoformat(),
            )

        assert narrow_result["success"] is True
        assert len(narrow_result["messages"]) == 1
        assert "after delay" in narrow_result["messages"][0]["content"]

    async def test_search_context_edge_cases(self, server_with_db, search_test_session):
        """Test search with edge case inputs."""
        session_id, ctx = search_test_session

        # Test empty query
        empty_result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="",
            fuzzy_threshold=70.0,
        )

        assert empty_result["success"] is True
        # Empty query should return some results (depends on implementation)

        # Test very high threshold (should return fewer results)
        high_threshold_result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="Python",
            fuzzy_threshold=95.0,
        )

        assert high_threshold_result["success"] is True

        # Test very low threshold (should return more results)
        low_threshold_result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="Python",
            fuzzy_threshold=10.0,
        )

        assert low_threshold_result["success"] is True
        assert len(low_threshold_result["results"]) >= len(
            high_threshold_result["results"]
        )

        # Test limit = 1
        limited_result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="database",
            fuzzy_threshold=60.0,
            limit=1,
        )

        assert limited_result["success"] is True
        assert len(limited_result["results"]) <= 1

    async def test_search_nonexistent_session(self, server_with_db, test_db_manager):
        """Test search operations on nonexistent sessions."""
        ctx = MockContext(agent_id="nonexistent_agent")
        fake_session_id = "session_fake123"

        # Test search_context on nonexistent session
        result = await call_fastmcp_tool(
            server_with_db.search_context, ctx, session_id=fake_session_id, query="test"
        )

        assert result["success"] is False
        assert result["code"] == "SESSION_NOT_FOUND"

        # Test search_by_sender on nonexistent session
        sender_result = await call_fastmcp_tool(
            server_with_db.search_by_sender,
            ctx,
            session_id=fake_session_id,
            sender="any_sender",
        )

        assert sender_result["success"] is False

        # Test search_by_timerange on nonexistent session
        now = datetime.now(timezone.utc)
        timerange_result = await call_fastmcp_tool(
            server_with_db.search_by_timerange,
            ctx,
            session_id=fake_session_id,
            start_time=now.isoformat(),
            end_time=now.isoformat(),
        )

        assert timerange_result["success"] is False

    async def test_search_empty_session(self, server_with_db, test_db_manager):
        """Test search operations on empty sessions."""
        ctx = MockContext(agent_id="empty_search_agent")

        # Create empty session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Empty session for search"
        )
        session_id = create_result["session_id"]

        # Search empty session
        result = await call_fastmcp_tool(
            server_with_db.search_context, ctx, session_id=session_id, query="anything"
        )

        assert result["success"] is True
        assert len(result["results"]) == 0
        assert result["message_count"] == 0

    async def test_search_performance_optimization(
        self, server_with_db, test_db_manager
    ):
        """Test search performance optimizations like pre-filtering."""
        ctx = MockContext(agent_id="performance_agent")

        # Create session with many messages
        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Performance test session"
        )
        session_id = create_result["session_id"]

        # Add many messages to test pre-filtering
        for i in range(20):
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=f"Performance test message {i} with keyword target",
                visibility="public" if i % 2 == 0 else "private",
            )

        # Search should use pre-filtering optimizations
        start_time = time.time()
        result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="target",
            fuzzy_threshold=80.0,
        )
        end_time = time.time()

        assert result["success"] is True
        assert len(result["results"]) > 0

        # Should complete quickly due to optimizations
        search_time = end_time - start_time
        assert search_time < 1.0  # Should be under 1 second

        # Verify search_time_ms is reported
        assert "search_time_ms" in result
        assert result["search_time_ms"] > 0

    async def test_search_unicode_and_special_chars(
        self, server_with_db, test_db_manager
    ):
        """Test search with unicode and special characters."""
        ctx = MockContext(agent_id="unicode_agent")

        create_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Unicode search test"
        )
        session_id = create_result["session_id"]

        # Add messages with unicode and special characters
        unicode_messages = [
            "Hello 世界! Testing unicode search 🚀",
            "Café résumé naïve façade élève",
            "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?",
            "Math symbols: ∞ ∑ ∏ ∆ ∇ ∂ ∫ √ ≤ ≥ ≠ ≈",
            "Emoji mix: 🎉🔥💯⭐🚀🌟✨🎯",
        ]

        for msg in unicode_messages:
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=msg,
                visibility="public",
            )

        # Test searching for unicode terms
        unicode_searches = [
            {"query": "世界", "should_find": "Hello 世界"},
            {"query": "café", "should_find": "Café"},
            {"query": "emoji", "should_find": "Emoji mix"},
            {"query": "🚀", "should_find": "🚀"},
        ]

        for search_case in unicode_searches:
            result = await call_fastmcp_tool(
                server_with_db.search_context,
                ctx,
                session_id=session_id,
                query=search_case["query"],
                fuzzy_threshold=60.0,
            )

            assert result["success"] is True
            # Should find relevant unicode content
            found_contents = [r["message"]["content"] for r in result["results"]]
            assert any(
                search_case["should_find"] in content for content in found_contents
            )
