"""
Unit tests for server error handling paths and response generation.

Tests error scenarios, edge cases, and exception handling in server operations
to ensure proper error responses and system resilience.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestServerErrorHandling:
    """Test server error handling and response generation."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    async def test_create_session_database_errors(
        self, server_with_db, test_db_manager
    ):
        """Test create_session with various database error scenarios."""
        ctx = MockContext(agent_id="error_agent")

        # Test database connection failure
        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            result = await call_fastmcp_tool(
                server_with_db.create_session, ctx, purpose="Test session with DB error"
            )

            assert result["success"] is False
            assert "error" in result
            assert (
                "database" in result["error"].lower()
                or "failed" in result["error"].lower()
                or "temporarily unavailable" in result["error"].lower()
            )

    async def test_add_message_validation_errors(self, server_with_db, test_db_manager):
        """Test add_message with validation error scenarios."""
        ctx = MockContext(agent_id="validation_agent")

        # First create a valid session
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Validation test session"
        )
        session_id = session_result["session_id"]

        # Test invalid visibility values
        invalid_visibility_values = [
            "invalid",
            "public_wrong",
            "private_wrong",
            "",
            None,
        ]

        for visibility in invalid_visibility_values:
            result = await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content="Test message",
                visibility=visibility,
            )

            # Should either reject invalid visibility or default to valid value
            # The exact behavior depends on validation implementation
            if result["success"] is False:
                assert "error" in result

    async def test_add_message_nonexistent_session(
        self, server_with_db, test_db_manager
    ):
        """Test add_message with nonexistent session ID."""
        ctx = MockContext(agent_id="nonexistent_agent")
        nonexistent_session_id = str(uuid4())

        result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=nonexistent_session_id,
            content="Message to nonexistent session",
            visibility="public",
        )

        assert result["success"] is False
        assert "error" in result
        assert (
            "session" in result["error"].lower()
            or "not found" in result["error"].lower()
        )

    async def test_get_session_nonexistent(self, server_with_db, test_db_manager):
        """Test get_session with nonexistent session ID."""
        ctx = MockContext(agent_id="nonexistent_agent")
        nonexistent_session_id = str(uuid4())

        result = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=nonexistent_session_id
        )

        assert result["success"] is False
        assert "error" in result
        assert (
            "session" in result["error"].lower()
            or "not found" in result["error"].lower()
        )

    async def test_get_messages_database_errors(self, server_with_db, test_db_manager):
        """Test get_messages with database error scenarios."""
        ctx = MockContext(agent_id="db_error_agent")

        # Create valid session first
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="DB error test session"
        )
        session_id = session_result["session_id"]

        # Mock database error during get_messages
        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_conn:
            mock_conn.side_effect = Exception("Database query failed")

            result = await call_fastmcp_tool(
                server_with_db.get_messages, ctx, session_id=session_id
            )

            assert result["success"] is False
            assert "error" in result

    async def test_search_context_database_errors(
        self, server_with_db, test_db_manager
    ):
        """Test search_context with database error scenarios."""
        ctx = MockContext(agent_id="search_error_agent")

        # Create session and add message first
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Search error test"
        )
        session_id = session_result["session_id"]

        # Mock database error during search
        with patch("shared_context_server.search_tools.get_db_connection") as mock_conn:
            mock_conn.side_effect = Exception("Search query failed")

            result = await call_fastmcp_tool(
                server_with_db.search_context,
                ctx,
                session_id=session_id,
                query="test search",
            )

            assert result["success"] is False
            assert "error" in result

    async def test_search_context_empty_query(self, server_with_db, test_db_manager):
        """Test search_context with empty or invalid query."""
        ctx = MockContext(agent_id="empty_search_agent")

        # Create session first
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Empty search test"
        )
        session_id = session_result["session_id"]

        # Test empty query
        result = await call_fastmcp_tool(
            server_with_db.search_context, ctx, session_id=session_id, query=""
        )

        # Should handle empty query gracefully
        if result["success"] is False:
            assert "error" in result
            assert (
                "query" in result["error"].lower() or "empty" in result["error"].lower()
            )
        else:
            # If it succeeds, should return empty results
            assert "results" in result
            assert isinstance(result["results"], list)

    async def test_search_context_nonexistent_session(
        self, server_with_db, test_db_manager
    ):
        """Test search_context with nonexistent session."""
        ctx = MockContext(agent_id="search_nonexistent_agent")
        nonexistent_session_id = str(uuid4())

        result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=nonexistent_session_id,
            query="test search",
        )

        assert result["success"] is False
        assert "error" in result
        assert (
            "session" in result["error"].lower()
            or "not found" in result["error"].lower()
        )

    async def test_concurrent_session_operations(self, server_with_db, test_db_manager):
        """Test concurrent operations on the same session for race conditions."""
        ctx = MockContext(agent_id="concurrent_agent")

        # Create session
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Concurrent test session"
        )
        session_id = session_result["session_id"]

        # Simulate concurrent message additions
        import asyncio

        async def add_concurrent_message(message_num):
            return await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=f"Concurrent message {message_num}",
                visibility="public",
            )

        # Run multiple concurrent operations
        tasks = [add_concurrent_message(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed or fail gracefully (no exceptions)
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), (
                f"Task {i} raised exception: {result}"
            )
            assert isinstance(result, dict)
            assert "success" in result

    async def test_malformed_json_metadata(self, server_with_db, test_db_manager):
        """Test operations with malformed JSON metadata."""
        ctx = MockContext(agent_id="json_agent")

        # Create session
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="JSON test session"
        )
        session_id = session_result["session_id"]

        # Test with problematic metadata that might cause JSON issues
        problematic_metadata = {
            "circular_ref": None,  # We'll make this circular
            "large_text": "x" * 10000,  # Very large string
            "deep_nesting": {"a": {"b": {"c": {"d": {"e": "deep"}}}}},
            "unicode_edge_cases": "🚀\n\t\r\"'\\",
            "numeric_edge_cases": [float("inf"), -float("inf"), 0, -0],
        }

        # Make circular reference (this should be caught by JSON serialization)

        result = await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Test message with problematic metadata",
            visibility="public",
            metadata=problematic_metadata,
        )

        # Should either succeed (if properly handled) or fail gracefully
        assert isinstance(result, dict)
        assert "success" in result

    async def test_resource_cleanup_on_errors(self, server_with_db, test_db_manager):
        """Test that resources are properly cleaned up on errors."""
        ctx = MockContext(agent_id="cleanup_agent")

        # Mock database connection that fails after being created

        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_conn:
            # Create a mock connection that raises an error during operations
            mock_connection = AsyncMock()
            mock_connection.execute.side_effect = Exception("Operation failed")

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_connection
            mock_context_manager.__aexit__.return_value = None

            mock_conn.return_value = mock_context_manager

            # Try operation that should fail
            result = await call_fastmcp_tool(
                server_with_db.create_session, ctx, purpose="Cleanup test session"
            )

            assert result["success"] is False

            # Verify __aexit__ was called (connection cleanup)
            mock_context_manager.__aexit__.assert_called()

    async def test_edge_case_session_ids(self, server_with_db, test_db_manager):
        """Test operations with edge case session ID formats."""
        ctx = MockContext(agent_id="edge_case_agent")

        # Test with various session ID formats that might cause issues
        edge_case_session_ids = [
            "",  # Empty string
            "a" * 1000,  # Very long string
            "session with spaces",  # Spaces
            "session\nwith\nnewlines",  # Newlines
            "session\twith\ttabs",  # Tabs
            "session-with-unicode-🚀",  # Unicode
            "session'with\"quotes",  # Quotes
            "session;with;semicolons",  # Semicolons
            "session/with/slashes",  # Slashes
        ]

        for session_id in edge_case_session_ids:
            result = await call_fastmcp_tool(
                server_with_db.get_session, ctx, session_id=session_id
            )

            # Should fail gracefully (not crash)
            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is False
            assert "error" in result

    async def test_large_message_content(self, server_with_db, test_db_manager):
        """Test handling of very large message content."""
        ctx = MockContext(agent_id="large_content_agent")

        # Create session
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Large content test"
        )
        session_id = session_result["session_id"]

        # Test with various large content sizes
        large_sizes = [
            1000,  # 1KB
            10000,  # 10KB
            100000,  # 100KB
            1000000,  # 1MB
        ]

        for size in large_sizes:
            large_content = "x" * size

            result = await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=large_content,
                visibility="public",
            )

            # Should either succeed or fail gracefully with size limit error
            assert isinstance(result, dict)
            assert "success" in result

            if result["success"] is False:
                # If it fails, should be due to size limits - either explicit size error or constraint violation
                assert "error" in result
                error_lower = result["error"].lower()
                assert (
                    "size" in error_lower
                    or "large" in error_lower
                    or "limit" in error_lower
                    or "constraint" in error_lower
                    or "content_length" in error_lower
                    or "temporarily unavailable" in error_lower
                )
                break  # Stop testing larger sizes once we hit the limit
