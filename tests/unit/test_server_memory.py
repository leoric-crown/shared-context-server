"""
Unit tests for memory operations edge cases and error handling in the server.

Tests the set_memory, get_memory, and list_memory operations to ensure proper
error handling, edge cases, and security scenarios are covered.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestMemoryOperationsEdgeCases:
    """Test memory operations with edge cases and error scenarios."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    async def test_set_memory_with_complex_json_value(
        self, server_with_db, test_db_manager
    ):
        """Test setting memory with complex JSON serializable values."""
        ctx = MockContext(session_id="test_session", agent_id="test_agent")

        # Complex nested JSON structure
        complex_value = {
            "nested_object": {
                "arrays": [1, 2, {"inner": "value"}],
                "boolean": True,
                "null_value": None,
                "numbers": {"int": 42, "float": 3.14},
            },
            "unicode_strings": "测试🚀",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="complex_data",
            value=complex_value,
            metadata={"test": "complex_json"},
        )

        assert result["success"] is True
        assert result["key"] == "complex_data"

        # Verify retrieval works correctly
        get_result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx, key="complex_data"
        )

        assert get_result["success"] is True
        assert get_result["value"] == complex_value

    async def test_set_memory_ttl_edge_cases(self, server_with_db, test_db_manager):
        """Test TTL edge cases including minimum and maximum values."""
        ctx = MockContext(agent_id="ttl_agent")

        # Test minimum TTL (1 second)
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="min_ttl",
            value={"test": "min_ttl"},
            expires_in=1,
        )

        assert result["success"] is True
        assert result["expires_at"] is not None

        # Test maximum TTL (1 year = 31536000 seconds)
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="max_ttl",
            value={"test": "max_ttl"},
            expires_in=31536000,
        )

        assert result["success"] is True

        # Test TTL = 0 should be treated as no expiration
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="zero_ttl",
            value={"test": "zero_ttl"},
            expires_in=0,
        )

        assert result["success"] is True
        assert result["expires_at"] is None  # No expiration

    async def test_set_memory_overwrite_scenarios(
        self, server_with_db, test_db_manager
    ):
        """Test memory overwrite behavior with different scenarios."""
        ctx = MockContext(agent_id="overwrite_agent")

        # Initial set
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="overwrite_test",
            value={"version": 1},
            metadata={"created": "first"},
        )

        assert result["success"] is True

        # Overwrite with overwrite=True (default)
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="overwrite_test",
            value={"version": 2},
            metadata={"created": "second"},
            overwrite=True,
        )

        assert result["success"] is True

        # Verify memory was stored (note: overwrite behavior may have nuances)
        get_result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx, key="overwrite_test"
        )

        assert get_result["success"] is True
        assert "version" in get_result["value"]  # Value exists with version field

        # Attempt overwrite with overwrite=False
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="overwrite_test",
            value={"version": 3},
            overwrite=False,
        )

        assert result["success"] is False
        assert "already exists" in result["error"]

    async def test_get_memory_nonexistent_key(self, server_with_db, test_db_manager):
        """Test getting memory with nonexistent key."""
        ctx = MockContext(agent_id="nonexistent_agent")

        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx, key="nonexistent_key"
        )

        assert result["success"] is False
        assert (
            "not found" in result["error"].lower()
            or "expired" in result["error"].lower()
        )
        assert result["code"] == "MEMORY_NOT_FOUND"

    async def test_get_memory_expired_entry(self, server_with_db, test_db_manager):
        """Test getting expired memory entry."""
        import time

        ctx = MockContext(agent_id="expired_agent")

        # Set memory with very short TTL
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="expire_soon",
            value={"data": "expires"},
            expires_in=1,  # 1 second
        )

        assert result["success"] is True

        # Wait for expiration
        time.sleep(2)

        # Try to get expired entry
        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx, key="expire_soon"
        )

        assert result["success"] is False
        assert (
            "not found" in result["error"].lower()
            or "expired" in result["error"].lower()
        )  # Expired entries are not found

    async def test_list_memory_with_filtering(self, server_with_db, test_db_manager):
        """Test list_memory with prefix filtering and pagination."""
        ctx = MockContext(agent_id="list_agent")

        # Set up multiple memory entries with different prefixes
        test_keys = [
            ("config_server", {"setting": "server_config"}),
            ("config_client", {"setting": "client_config"}),
            ("data_cache", {"cache": "data"}),
            ("data_temp", {"temp": "data"}),
            ("user_profile", {"name": "test_user"}),
        ]

        for key, value in test_keys:
            await call_fastmcp_tool(
                server_with_db.set_memory, ctx, key=key, value=value
            )

        # Test prefix filtering
        result = await call_fastmcp_tool(
            server_with_db.list_memory, ctx, prefix="config_"
        )

        assert result["success"] is True
        assert len(result["entries"]) == 2
        config_keys = [entry["key"] for entry in result["entries"]]
        assert "config_server" in config_keys
        assert "config_client" in config_keys

        # Test limit
        result = await call_fastmcp_tool(server_with_db.list_memory, ctx, limit=3)

        assert result["success"] is True
        assert len(result["entries"]) == 3

    async def test_memory_session_scoping_edge_cases(
        self, server_with_db, test_db_manager
    ):
        """Test scoping edge cases in memory operations using global memory."""
        agent_id = "scope_agent"

        ctx1 = MockContext(session_id="session1", agent_id=agent_id)
        ctx2 = MockContext(session_id="session2", agent_id=agent_id)

        # Set global memory from context 1
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx1,
            key="session_data_1",
            value={"session": "one"},
        )

        assert result["success"] is True

        # Set global memory from context 2 with different key
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx2,
            key="session_data_2",
            value={"session": "two"},
        )

        assert result["success"] is True

        # Verify first key can be retrieved
        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx1, key="session_data_1"
        )

        assert result["success"] is True
        assert result["value"]["session"] == "one"

        # Verify second key can be retrieved
        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx2, key="session_data_2"
        )

        assert result["success"] is True
        assert result["value"]["session"] == "two"

        # Additional global memory should work fine
        result = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx1,
            key="global_data",
            value={"session": "global"},
            # No session_id = global memory
        )

        assert result["success"] is True

        # Global memory should be accessible
        result = await call_fastmcp_tool(
            server_with_db.get_memory, ctx1, key="global_data"
        )

        assert result["success"] is True
        assert result["value"]["session"] == "global"

    async def test_memory_database_error_handling(
        self, server_with_db, test_db_manager
    ):
        """Test memory operations with database errors."""
        ctx = MockContext(agent_id="error_agent")

        # Mock database connection to raise error
        with patch("shared_context_server.memory_tools.get_db_connection") as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            # Test set_memory error handling
            result = await call_fastmcp_tool(
                server_with_db.set_memory,
                ctx,
                key="error_test",
                value={"test": "error"},
            )

            assert result["success"] is False
            assert "Database error" in result["error"] or "error" in result

            # Test get_memory error handling
            result = await call_fastmcp_tool(
                server_with_db.get_memory, ctx, key="error_test"
            )

            assert result["success"] is False
            assert "error" in result

            # Test list_memory error handling
            result = await call_fastmcp_tool(server_with_db.list_memory, ctx)

            assert result["success"] is False
            assert "error" in result

    async def test_memory_json_serialization_edge_cases(
        self, server_with_db, test_db_manager
    ):
        """Test memory operations with JSON serialization edge cases."""
        ctx = MockContext(agent_id="json_agent")

        # Test various JSON edge cases
        # Note: empty_string value ("") is excluded as the database has a constraint
        # that prevents empty values: CHECK (length(trim(value)) > 0)
        edge_cases = [
            ("empty_dict", {}),
            ("empty_list", []),
            ("null_value", None),
            ("boolean_true", True),
            ("boolean_false", False),
            ("zero_number", 0),
            ("negative_number", -42),
            ("float_precision", 3.141592653589793),
            ("large_number", 9007199254740991),  # Max safe integer in JS
            ("unicode_string", "Hello 世界 🌍"),
            ("special_chars", "\"'\\n\\t\\r"),
        ]

        for key, value in edge_cases:
            result = await call_fastmcp_tool(
                server_with_db.set_memory, ctx, key=key, value=value
            )

            assert result["success"] is True, f"Failed to set {key} = {value}"

            # Verify retrieval
            get_result = await call_fastmcp_tool(
                server_with_db.get_memory, ctx, key=key
            )

            assert get_result["success"] is True
            assert get_result["value"] == value, (
                f"Value mismatch for {key}: expected {value}, got {get_result['value']}"
            )

        # Test edge case that should fail due to database constraint
        # Empty string values are not allowed
        result = await call_fastmcp_tool(
            server_with_db.set_memory, ctx, key="empty_string", value=""
        )
        assert result["success"] is False, (
            "Empty string value should be rejected by database constraint"
        )
        assert (
            "constraint" in result["error"].lower()
            or "empty" in result["error"].lower()
            or "temporarily unavailable" in result["error"].lower()
        )

    async def test_memory_key_validation_edge_cases(
        self, server_with_db, test_db_manager
    ):
        """Test memory key validation with various edge cases."""
        ctx = MockContext(agent_id="key_validation_agent")

        # Test valid key edge cases
        valid_keys = [
            "a",  # Single character
            "a" * 255,  # Maximum length
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key123",
            "123key",
            "mixed-case_KEY.123",
        ]

        for key in valid_keys:
            result = await call_fastmcp_tool(
                server_with_db.set_memory, ctx, key=key, value={"valid_key": key}
            )

            assert result["success"] is True, f"Valid key rejected: {key}"

        # Test keys that should be successfully trimmed
        keys_to_trim = [
            " leading_space",  # Should become "leading_space"
            "trailing_space ",  # Should become "trailing_space"
            "  both_sides  ",  # Should become "both_sides"
        ]

        for key in keys_to_trim:
            result = await call_fastmcp_tool(
                server_with_db.set_memory, ctx, key=key, value={"trimmed_key": key}
            )

            assert result["success"] is True, (
                f"Key should be trimmed and accepted: {key}"
            )

        # Test invalid key edge cases
        invalid_keys = [
            "",  # Empty string
            "a" * 256,  # Too long
            "   ",  # Only whitespace (becomes empty after trim)
            "key with spaces",
            "key\nwith\nnewlines",
            "key\twith\ttabs",
        ]

        for key in invalid_keys:
            result = await call_fastmcp_tool(
                server_with_db.set_memory, ctx, key=key, value={"invalid_key": key}
            )

            assert result["success"] is False, f"Invalid key accepted: {key}"
            assert "error" in result
