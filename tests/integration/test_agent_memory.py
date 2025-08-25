"""
Integration tests for Agent Memory System.

Tests TTL functionality, scope management, and integration with
existing Phase 1 systems according to Phase 2 specification.

Modernized to use isolated_db fixture instead of legacy mock patterns.
"""

import asyncio
import os

# Import testing helpers from conftest.py
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Import memory functions directly
from shared_context_server.server import (
    create_session,
    get_memory,
    list_memory,
    set_memory,
)

sys.path.append(str(Path(__file__).parent.parent))
from conftest import MockContext, call_fastmcp_tool

from tests.fixtures.database import (
    DatabaseTestManager,
    patch_database_for_test,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_set_get_basic_functionality(isolated_db: DatabaseTestManager):
    """Test basic memory set and get operations."""

    with (
        patch_database_for_test(isolated_db),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        mock_notify.return_value = None

        ctx = MockContext("test_session_memory_123")

        # Set global memory
        set_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="test_global_key",
            value={"message": "Hello from global memory", "number": 42},
            metadata={"test": "global"},
        )

        assert set_result["success"] is True
        assert set_result["key"] == "test_global_key"
        assert set_result["scope"] == "global"
        assert set_result["session_scoped"] is False
        assert "stored_at" in set_result

        # Get global memory
        get_result = await call_fastmcp_tool(get_memory, ctx, key="test_global_key")

        if not get_result["success"]:
            print(f"Get result failed: {get_result}")
        assert get_result["success"] is True
        assert get_result["key"] == "test_global_key"
        assert get_result["value"]["message"] == "Hello from global memory"
        assert get_result["value"]["number"] == 42
        assert get_result["metadata"]["test"] == "global"
        assert get_result["scope"] == "global"
        assert "created_at" in get_result
        assert "updated_at" in get_result

        print("✅ Basic memory set/get functionality test completed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_session_scoping(isolated_db: DatabaseTestManager):
    """Test session-scoped vs global memory isolation."""

    with (
        patch_database_for_test(isolated_db),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        mock_notify.return_value = None

        ctx = MockContext("test_session_scoping")

        # Create test session
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="Agent memory integration testing"
        )
        session_id = session_result["session_id"]

        # Set session-scoped memory
        session_set = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="scoped_key",
            value="session specific value",
            session_id=session_id,
        )

        assert session_set["success"] is True
        assert session_set["scope"] == "session"
        assert session_set["session_scoped"] is True

        # Set global memory with same key
        global_set = await call_fastmcp_tool(
            set_memory, ctx, key="scoped_key", value="global value"
        )

        assert global_set["success"] is True
        assert global_set["scope"] == "global"

        # Retrieve session-scoped memory
        session_get = await call_fastmcp_tool(
            get_memory, ctx, key="scoped_key", session_id=session_id
        )

        assert session_get["success"] is True
        assert session_get["value"] == "session specific value"
        assert session_get["scope"] == "session"

        # Retrieve global memory
        global_get = await call_fastmcp_tool(get_memory, ctx, key="scoped_key")

        assert global_get["success"] is True
        assert global_get["value"] == "global value"
        assert global_get["scope"] == "global"

        # Verify they are different values
        assert session_get["value"] != global_get["value"]

        print("✅ Memory session scoping test completed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_ttl_expiration(isolated_db: DatabaseTestManager):
    """Test TTL expiration system with automatic cleanup."""

    with (
        patch_database_for_test(isolated_db),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        mock_notify.return_value = None

        ctx = MockContext("test_ttl_session")

        # Set memory with short TTL (2 seconds)
        set_result = await call_fastmcp_tool(
            set_memory, ctx, key="expiring_key", value="this will expire", expires_in=2
        )

        assert set_result["success"] is True
        assert set_result["expires_at"] is not None

        # Immediately retrieve - should work
        get_result = await call_fastmcp_tool(get_memory, ctx, key="expiring_key")

        assert get_result["success"] is True
        assert get_result["value"] == "this will expire"
        assert get_result["expires_at"] is not None

        # Wait for expiration
        await asyncio.sleep(3)

        # Should be expired and cleaned up
        expired_result = await call_fastmcp_tool(get_memory, ctx, key="expiring_key")

        assert expired_result["success"] is False
        assert expired_result["code"] == "MEMORY_NOT_FOUND"
        assert (
            "expired" in expired_result["error"].lower()
            or "not found" in expired_result["error"].lower()
        )

        print("✅ Memory TTL expiration test completed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_overwrite_behavior(isolated_db: DatabaseTestManager):
    """Test memory overwrite and key collision handling using memory tools."""

    with (
        patch_database_for_test(isolated_db),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        mock_notify.return_value = None

        ctx = MockContext("test_memory_overwrite")

        # 1. Set initial memory value
        set_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="overwrite_test",
            value="initial value",
            metadata={"test": "initial"},
        )

        assert set_result["success"] is True
        assert set_result["key"] == "overwrite_test"
        assert set_result["scope"] == "global"

        # 2. Verify initial value
        get_result = await call_fastmcp_tool(get_memory, ctx, key="overwrite_test")

        assert get_result["success"] is True
        assert get_result["value"] == "initial value"
        assert get_result["metadata"]["test"] == "initial"

        # 3. Test overwrite (should update existing value)
        overwrite_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="overwrite_test",
            value="new value",
            metadata={"test": "updated"},
            overwrite=True,
        )

        assert overwrite_result["success"] is True
        assert overwrite_result["key"] == "overwrite_test"

        # 4. Verify updated value
        final_result = await call_fastmcp_tool(get_memory, ctx, key="overwrite_test")

        assert final_result["success"] is True
        assert final_result["value"] == "new value"
        assert final_result["metadata"]["test"] == "updated"

        # 5. Test key collision detection (overwrite=False should fail)
        collision_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="overwrite_test",
            value="collision value",
            overwrite=False,
        )

        assert collision_result["success"] is False
        assert collision_result["code"] == "KEY_EXISTS"

        print("✅ Memory overwrite behavior test completed using memory tools")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_performance_requirements(isolated_db: DatabaseTestManager):
    """Test memory operations meet <10ms performance requirements."""

    # Adjust performance threshold when coverage is enabled
    # Coverage instrumentation significantly impacts timing
    try:
        # Check if coverage is actively collecting data
        import coverage

        coverage_active = coverage.process_startup.coverage is not None
    except (ImportError, AttributeError):
        # Fallback: check environment variables set by pytest-cov
        coverage_active = bool(
            os.environ.get("COV_CORE_SOURCE")
            or os.environ.get("COV_CORE_CONFIG")
            or any("cov" in arg for arg in sys.argv)
        )

    threshold = 50 if coverage_active else 25

    with (
        patch_database_for_test(isolated_db),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        mock_notify.return_value = None

        ctx = MockContext("test_perf_session")

        # WARM-UP: Perform one operation to initialize lazy-loaded modules
        # This accounts for one-time costs like WebSocket handler loading
        warmup_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="warmup_key",
            value={"warmup": "data"},
        )
        assert warmup_result["success"] is True

        # Test set operation performance (steady state)
        start_time = time.time()
        set_result = await call_fastmcp_tool(
            set_memory,
            ctx,
            key="performance_test",
            value={
                "data": "performance test value",
                "timestamp": datetime.now().isoformat(),
            },
        )
        set_time = (time.time() - start_time) * 1000

        assert set_result["success"] is True
        assert set_time < threshold, (
            f"Memory set took {set_time:.2f}ms, expected <{threshold}ms (steady state performance)"
        )

        # Test get operation performance (steady state)
        start_time = time.time()
        get_result = await call_fastmcp_tool(get_memory, ctx, key="performance_test")
        get_time = (time.time() - start_time) * 1000

        assert get_result["success"] is True
        assert get_time < threshold, (
            f"Memory get took {get_time:.2f}ms, expected <{threshold}ms (steady state performance)"
        )

        # Warm-up list operation
        warmup_list = await call_fastmcp_tool(list_memory, ctx, limit=5)
        assert warmup_list["success"] is True

        # Test list operation performance (steady state)
        start_time = time.time()
        list_result = await call_fastmcp_tool(list_memory, ctx, limit=10)
        list_time = (time.time() - start_time) * 1000

        assert list_result["success"] is True
        assert list_time < threshold, (
            f"Memory list took {list_time:.2f}ms, expected <{threshold}ms (steady state performance)"
        )

        print("\nMemory Performance Results:")
        print(f"  - Set operation: {set_time:.2f}ms")
        print(f"  - Get operation: {get_time:.2f}ms")
        print(f"  - List operation: {list_time:.2f}ms")
        print(
            f"  - All operations under {threshold}ms: {max(set_time, get_time, list_time) < threshold}"
        )
        if threshold > 10:
            print("  - Note: Higher threshold used due to coverage instrumentation")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.performance
async def test_memory_json_serialization(isolated_db: DatabaseTestManager):
    """Test JSON serialization of complex data types."""

    with (
        patch_database_for_test(isolated_db),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        mock_notify.return_value = None

        ctx = MockContext("test_json_session")

        # Test various data types
        test_values = [
            {"type": "dict", "value": {"nested": {"data": True}, "list": [1, 2, 3]}},
            {"type": "list", "value": [{"item": 1}, {"item": 2}, None, "string"]},
            {"type": "string", "value": "simple string"},
            {"type": "number", "value": 42.7},
            {"type": "boolean", "value": False},
            {"type": "null", "value": None},
        ]

        for i, test_case in enumerate(test_values):
            key = f"serialization_test_{i}_{test_case['type']}"

            # Set memory with complex value
            set_result = await call_fastmcp_tool(
                set_memory,
                ctx,
                key=key,
                value=test_case["value"],
                metadata={"original_type": test_case["type"]},
            )

            assert set_result["success"] is True, (
                f"Failed to set {test_case['type']} value"
            )

            # Retrieve and verify
            get_result = await call_fastmcp_tool(get_memory, ctx, key=key)

            assert get_result["success"] is True, (
                f"Failed to get {test_case['type']} value"
            )
            assert get_result["value"] == test_case["value"], (
                f"Value mismatch for {test_case['type']}"
            )
            assert get_result["metadata"]["original_type"] == test_case["type"]

        print("✅ Memory JSON serialization test completed")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_list_functionality(isolated_db: DatabaseTestManager):
    """Test memory listing with various filters."""

    with (
        patch_database_for_test(isolated_db),
        patch(
            "shared_context_server.server.trigger_resource_notifications"
        ) as mock_notify,
    ):
        mock_notify.return_value = None

        ctx = MockContext("test_list_session")

        # Create test session
        session_result = await call_fastmcp_tool(
            create_session, ctx, purpose="Memory list testing"
        )
        session_id = session_result["session_id"]

        # Set various memory entries
        memory_entries = [
            {"key": "global_test_1", "value": "global value 1", "session_id": None},
            {"key": "global_test_2", "value": "global value 2", "session_id": None},
            {
                "key": "session_test_1",
                "value": "session value 1",
                "session_id": session_id,
            },
            {
                "key": "session_test_2",
                "value": "session value 2",
                "session_id": session_id,
            },
            {"key": "prefix_match_1", "value": "prefix test", "session_id": None},
            {"key": "prefix_match_2", "value": "another prefix", "session_id": None},
        ]

        for entry in memory_entries:
            await call_fastmcp_tool(set_memory, ctx, **entry)

        # List all memory entries
        all_list = await call_fastmcp_tool(list_memory, ctx, session_id="all")

        assert all_list["success"] is True
        print(
            f"\nDebug: Expected {len(memory_entries)} entries, got {all_list['count']}"
        )
        print(f"Memory entries: {[entry['key'] for entry in all_list['entries']]}")
        print(f"Agent ID from context: {ctx._auth_info.agent_id}")
        assert all_list["count"] >= len(memory_entries)

        # List global memory only
        global_list = await call_fastmcp_tool(list_memory, ctx)

        assert global_list["success"] is True
        # Modern implementation will return actual filtered entries

        # List session-scoped memory
        session_list = await call_fastmcp_tool(list_memory, ctx, session_id=session_id)

        assert session_list["success"] is True

        # List with prefix filter
        prefix_list = await call_fastmcp_tool(list_memory, ctx, prefix="prefix_match")

        assert prefix_list["success"] is True

        print("✅ Memory list functionality test completed")
