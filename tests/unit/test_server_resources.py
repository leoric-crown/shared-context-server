"""
Unit tests for MCP resource system in the server.

Tests MCP resources, notification system, subscription management,
and resource content generation for session and agent memory resources.
"""

import json
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestMCPResourceSystem:
    """Test the MCP resource system and notifications."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    @pytest.fixture
    async def resource_test_session(self, server_with_db, test_db_manager):
        """Create a session with test data for resource testing."""
        ctx = MockContext(agent_id="resource_agent")

        # Create session
        create_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="Resource test session",
            metadata={"test": "resource", "priority": "high"},
        )
        session_id = create_result["session_id"]

        # Add test messages
        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Public resource test message",
            visibility="public",
            metadata={"type": "test", "order": 1},
        )

        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Private resource test message",
            visibility="private",
            metadata={"type": "test", "order": 2},
        )

        # Add some memory entries
        await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="resource_test_global",
            value={
                "data": "global_resource_test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            session_id=session_id,
            key="resource_test_session",
            value={"data": "session_resource_test", "scope": "session"},
        )

        return session_id, ctx

    async def test_get_session_resource(self, server_with_db, resource_test_session):
        """Test get_session_resource functionality."""
        from shared_context_server.server import get_session_resource

        session_id, ctx = resource_test_session

        # Create a real Context for the resource function
        from fastmcp import Context

        real_ctx = Context(server_with_db)
        real_ctx.agent_id = ctx.agent_id  # Set agent_id directly on context

        # Get session resource (access the underlying function from the template)
        resource = await get_session_resource.fn(session_id, real_ctx)

        assert resource is not None
        assert str(resource.uri) == f"session://{session_id}"
        assert "Session:" in resource.name
        assert "shared context session" in resource.description.lower()
        assert resource.mime_type == "application/json"

        # Parse resource content
        content_text = await resource.read()
        content = json.loads(content_text)

        # Verify resource structure
        assert "session" in content
        assert "messages" in content
        assert "statistics" in content
        assert "resource_info" in content

        # Verify session data
        session_data = content["session"]
        assert session_data["id"] == session_id
        assert session_data["purpose"] == "Resource test session"
        assert session_data["created_by"] == "resource_agent"
        assert session_data["is_active"] is True

        # Verify messages (should include visible messages)
        messages = content["messages"]
        assert len(messages) >= 2  # At least the test messages

        message_contents = [msg["content"] for msg in messages]
        assert "Public resource test message" in message_contents
        assert (
            "Private resource test message" in message_contents
        )  # Visible to same agent

        # Verify statistics
        stats = content["statistics"]
        assert stats["message_count"] >= 2
        assert stats["visible_message_count"] >= 2
        assert stats["unique_agents"] >= 1

        # Verify resource info
        resource_info = content["resource_info"]
        assert "last_updated" in resource_info
        assert (
            resource_info["requesting_agent"] == "resource_agent"
        )  # Updated for Phase 3 - proper agent context extraction
        assert resource_info["supports_subscriptions"] is True

    async def test_get_session_resource_nonexistent(
        self, server_with_db, test_db_manager
    ):
        """Test get_session_resource with nonexistent session."""
        from fastmcp import Context

        from shared_context_server.server import get_session_resource

        # Create a real Context for the resource function
        real_ctx = Context(server_with_db)
        real_ctx.agent_id = "test_agent"

        with pytest.raises(ValueError, match="Session .* not found"):
            await get_session_resource.fn("session_nonexistent123", real_ctx)

    async def test_get_agent_memory_resource(
        self, server_with_db, resource_test_session
    ):
        """Test get_agent_memory_resource functionality."""
        from fastmcp import Context

        from shared_context_server.server import get_agent_memory_resource

        session_id, ctx = resource_test_session

        # Create a real Context for the resource function
        real_ctx = Context(server_with_db)
        real_ctx.agent_id = ctx.agent_id  # Set agent_id directly on context

        # Get agent memory resource
        resource = await get_agent_memory_resource.fn("resource_agent", real_ctx)

        assert resource is not None
        assert str(resource.uri) == "agent://resource_agent/memory"
        assert "Agent Memory:" in resource.name
        assert "Private memory store" in resource.description
        assert resource.mime_type == "application/json"

        # Parse resource content
        content_text = await resource.read()
        content = json.loads(content_text)

        # Verify resource structure
        assert "agent_id" in content
        assert "memory" in content
        assert "statistics" in content
        assert "resource_info" in content

        assert content["agent_id"] == "resource_agent"

        # Verify memory organization
        memory = content["memory"]
        assert "global" in memory
        assert "sessions" in memory

        # Verify global memory
        global_memory = memory["global"]
        assert "resource_test_global" in global_memory

        global_entry = global_memory["resource_test_global"]
        assert global_entry["value"]["data"] == "global_resource_test"

        # Verify session-scoped memory
        sessions = memory["sessions"]
        assert session_id in sessions

        session_memory = sessions[session_id]
        assert "resource_test_session" in session_memory

        session_entry = session_memory["resource_test_session"]
        assert session_entry["value"]["data"] == "session_resource_test"

        # Verify statistics
        stats = content["statistics"]
        assert stats["global_keys"] >= 1
        assert stats["session_scopes"] >= 1
        assert stats["total_entries"] >= 2

    async def test_get_agent_memory_resource_unauthorized(
        self, server_with_db, test_db_manager
    ):
        """Test get_agent_memory_resource with unauthorized access."""
        from fastmcp import Context

        from shared_context_server.server import get_agent_memory_resource

        # Create a real Context with different agent_id
        real_ctx = Context(server_with_db)
        real_ctx.agent_id = "requesting_agent"  # Different from target agent

        # Try to access another agent's memory
        with pytest.raises(ValueError, match="Unauthorized access"):
            await get_agent_memory_resource.fn("different_agent", real_ctx)

    async def test_resource_notification_manager_basic(
        self, server_with_db, test_db_manager
    ):
        """Test ResourceNotificationManager basic functionality."""
        from shared_context_server.server import ResourceNotificationManager

        manager = ResourceNotificationManager()

        # Test subscription
        await manager.subscribe("client_1", "session://test_session")
        await manager.subscribe("client_2", "session://test_session")
        await manager.subscribe("client_1", "agent://test_agent/memory")

        # Verify subscriptions
        assert "session://test_session" in manager.subscribers
        assert "client_1" in manager.subscribers["session://test_session"]
        assert "client_2" in manager.subscribers["session://test_session"]

        assert "agent://test_agent/memory" in manager.subscribers
        assert "client_1" in manager.subscribers["agent://test_agent/memory"]

        # Test client tracking
        assert "client_1" in manager.client_last_seen
        assert "client_2" in manager.client_last_seen

        # Test unsubscribe from specific resource
        await manager.unsubscribe("client_1", "session://test_session")
        assert "client_1" not in manager.subscribers["session://test_session"]
        assert "client_2" in manager.subscribers["session://test_session"]

        # Client_1 should still be tracked (has other subscriptions)
        assert "client_1" in manager.client_last_seen

        # Test unsubscribe from all resources
        await manager.unsubscribe("client_1")
        assert "client_1" not in manager.subscribers.get(
            "agent://test_agent/memory", set()
        )
        assert "client_1" not in manager.client_last_seen

    async def test_resource_notification_manager_cleanup(
        self, server_with_db, test_db_manager
    ):
        """Test ResourceNotificationManager stale subscription cleanup."""
        from shared_context_server.server import ResourceNotificationManager

        manager = ResourceNotificationManager()

        # Subscribe clients
        await manager.subscribe("fresh_client", "session://test")
        await manager.subscribe("stale_client", "session://test")

        # Simulate stale client by manipulating timestamp
        old_time = time.time() - manager.subscription_timeout - 1
        manager.client_last_seen["stale_client"] = old_time

        # Cleanup should remove stale client
        await manager.cleanup_stale_subscriptions()

        assert "fresh_client" in manager.subscribers["session://test"]
        assert "stale_client" not in manager.subscribers["session://test"]
        assert "stale_client" not in manager.client_last_seen

    async def test_resource_notification_manager_notify(
        self, server_with_db, test_db_manager
    ):
        """Test ResourceNotificationManager notification system."""
        from shared_context_server.server import ResourceNotificationManager

        manager = ResourceNotificationManager()

        # Mock the notification method to track calls
        original_notify = manager._notify_single_client
        notify_calls = []

        async def mock_notify(client_id: str, resource_uri: str) -> bool:
            notify_calls.append((client_id, resource_uri))
            return await original_notify(client_id, resource_uri)

        manager._notify_single_client = mock_notify

        # Subscribe clients
        await manager.subscribe("client_1", "session://test")
        await manager.subscribe("client_2", "session://test")

        # Notify resource update
        await manager.notify_resource_updated("session://test")

        # Verify notifications were sent
        assert len(notify_calls) == 2
        client_ids = {call[0] for call in notify_calls}
        assert client_ids == {"client_1", "client_2"}

    async def test_trigger_resource_notifications(
        self, server_with_db, resource_test_session
    ):
        """Test trigger_resource_notifications function."""
        from shared_context_server.server import (
            notification_manager,
            trigger_resource_notifications,
        )

        session_id, ctx = resource_test_session

        # Mock notification manager to track calls
        original_notify = notification_manager.notify_resource_updated
        notify_calls = []

        async def mock_notify_updated(resource_uri: str, debounce_ms: int = 100):
            notify_calls.append(resource_uri)
            return await original_notify(resource_uri, debounce_ms)

        notification_manager.notify_resource_updated = mock_notify_updated

        try:
            # Trigger notifications
            await trigger_resource_notifications(session_id, "resource_agent")

            # Verify both session and agent memory resources were notified
            assert len(notify_calls) == 2
            assert f"session://{session_id}" in notify_calls
            assert "agent://resource_agent/memory" in notify_calls

        finally:
            # Restore original method
            notification_manager.notify_resource_updated = original_notify

    async def test_resource_notifications_on_message_add(
        self, server_with_db, resource_test_session
    ):
        """Test that resource notifications are triggered when messages are added."""
        from shared_context_server.server import notification_manager

        session_id, ctx = resource_test_session

        # Mock notification manager
        original_notify = notification_manager.notify_resource_updated
        notify_calls = []

        async def mock_notify_updated(resource_uri: str, debounce_ms: int = 100):
            notify_calls.append(resource_uri)
            # Don't call original to avoid actual notifications during test

        notification_manager.notify_resource_updated = mock_notify_updated

        try:
            # Add a message (should trigger notifications)
            result = await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content="Message that should trigger notifications",
                visibility="public",
            )

            assert result["success"] is True

            # Verify notifications were triggered
            assert len(notify_calls) >= 2  # At least session and agent memory resources

            # Should include session resource
            session_resource_notified = any(
                f"session://{session_id}" in uri for uri in notify_calls
            )
            assert session_resource_notified

            # Should include agent memory resource
            agent_resource_notified = any(
                "agent://resource_agent/memory" in uri for uri in notify_calls
            )
            assert agent_resource_notified

        finally:
            # Restore original method
            notification_manager.notify_resource_updated = original_notify

    async def test_resource_notifications_on_memory_set(
        self, server_with_db, resource_test_session
    ):
        """Test that resource notifications are triggered when memory is set."""
        from shared_context_server.server import notification_manager

        session_id, ctx = resource_test_session

        # Mock notification manager
        original_notify = notification_manager.notify_resource_updated
        notify_calls = []

        async def mock_notify_updated(resource_uri: str, debounce_ms: int = 100):
            notify_calls.append(resource_uri)

        notification_manager.notify_resource_updated = mock_notify_updated

        try:
            # Set memory (should trigger notifications)
            result = await call_fastmcp_tool(
                server_with_db.set_memory,
                ctx,
                key="notification_test_key",
                value={"test": "notification"},
            )

            assert result["success"] is True

            # Verify notifications were triggered
            # Global memory should trigger notifications for "global" session
            assert len(notify_calls) >= 2

            # Should include agent memory resource
            agent_resource_notified = any(
                "agent://resource_agent/memory" in uri for uri in notify_calls
            )
            assert agent_resource_notified

        finally:
            # Restore original method
            notification_manager.notify_resource_updated = original_notify

    async def test_concrete_resource_implementation(
        self, server_with_db, test_db_manager
    ):
        """Test ConcreteResource implementation."""
        from shared_context_server.server import ConcreteResource

        # Create resource
        test_content = {"test": "resource content", "data": [1, 2, 3]}
        resource = ConcreteResource(
            uri="test://example",
            name="Test Resource",
            description="A test resource for unit testing",
            mime_type="application/json",
            text=json.dumps(test_content),
        )

        # Verify properties
        assert str(resource.uri) == "test://example"
        assert resource.name == "Test Resource"
        assert resource.description == "A test resource for unit testing"
        assert resource.mime_type == "application/json"

        # Verify content reading
        content = await resource.read()
        assert content == json.dumps(test_content)

    async def test_resource_content_with_complex_data(
        self, server_with_db, test_db_manager
    ):
        """Test resource content generation with complex session data."""
        ctx = MockContext(agent_id="complex_agent")

        # Create session with complex data
        create_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="Complex resource test",
            metadata={
                "complex": {
                    "nested": {"deep": "value"},
                    "array": [1, 2, {"item": "value"}],
                    "unicode": "🚀 测试 世界",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        session_id = create_result["session_id"]

        # Add messages with complex metadata
        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Message with complex metadata",
            visibility="public",
            metadata={
                "processing": {
                    "steps": ["parse", "validate", "store"],
                    "duration_ms": 125.5,
                    "success": True,
                },
                "references": ["ref1", "ref2"],
                "tags": ["important", "processed"],
            },
        )

        # Get resource and verify complex data is preserved
        from fastmcp import Context

        from shared_context_server.server import get_session_resource

        # Create a real Context for the resource function
        real_ctx = Context(server_with_db)
        real_ctx.agent_id = ctx.agent_id

        resource = await get_session_resource.fn(session_id, real_ctx)

        content_text = await resource.read()
        content = json.loads(content_text)

        # Verify complex session metadata
        session_metadata = content["session"]["metadata"]
        assert session_metadata["complex"]["nested"]["deep"] == "value"
        assert session_metadata["complex"]["unicode"] == "🚀 测试 世界"

        # Verify complex message metadata
        message_metadata = content["messages"][0]["metadata"]
        assert message_metadata["processing"]["steps"] == ["parse", "validate", "store"]
        assert message_metadata["processing"]["duration_ms"] == 125.5

    async def test_resource_error_handling(self, server_with_db, test_db_manager):
        """Test resource error handling scenarios."""
        from fastmcp import Context

        from shared_context_server.server import (
            get_agent_memory_resource,
            get_session_resource,
        )

        # Create real Context objects for testing
        session_ctx = Context(server_with_db)
        session_ctx.agent_id = "test_agent"

        memory_ctx = Context(server_with_db)
        memory_ctx.agent_id = "test_agent"

        # Test database connection error during resource generation
        with patch(
            "shared_context_server.admin_resources.get_db_connection"
        ) as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            with pytest.raises(ValueError, match="Failed to get session resource"):
                await get_session_resource.fn("session_test123", session_ctx)

        # Test agent memory resource with database error
        with patch(
            "shared_context_server.admin_resources.get_db_connection"
        ) as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            with pytest.raises(ValueError, match="Failed to get agent memory resource"):
                await get_agent_memory_resource.fn("test_agent", memory_ctx)

    async def test_resource_subscription_integration(
        self, server_with_db, resource_test_session
    ):
        """Test integration between resources and subscription system."""
        from shared_context_server.server import notification_manager

        session_id, ctx = resource_test_session

        # Subscribe to resources
        await notification_manager.subscribe("test_client", f"session://{session_id}")
        await notification_manager.subscribe(
            "test_client", "agent://resource_agent/memory"
        )

        # Verify subscriptions exist
        assert f"session://{session_id}" in notification_manager.subscribers
        assert "agent://resource_agent/memory" in notification_manager.subscribers
        assert (
            "test_client" in notification_manager.subscribers[f"session://{session_id}"]
        )

        # Mock notification to track calls
        original_notify_single = notification_manager._notify_single_client
        notification_calls = []

        async def mock_notify_single(client_id: str, resource_uri: str) -> bool:
            notification_calls.append((client_id, resource_uri))
            return True

        notification_manager._notify_single_client = mock_notify_single

        try:
            # Perform operations that should trigger notifications
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content="Message for subscription test",
                visibility="public",
            )

            # Allow time for debounced notifications
            time.sleep(0.2)

            # Verify notifications were sent to subscribed client
            assert len(notification_calls) >= 2  # At least session and memory resources

            # All notifications should be to test_client
            for client_id, _resource_uri in notification_calls:
                assert client_id == "test_client"

        finally:
            # Restore original method
            notification_manager._notify_single_client = original_notify_single
