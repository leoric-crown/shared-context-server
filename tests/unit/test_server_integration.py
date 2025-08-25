"""
Unit tests for multi-component integration workflows in the server.

Tests complex workflows that involve multiple server components working together,
including authentication + sessions + search, resource notifications + memory updates,
and end-to-end agent collaboration scenarios.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from tests.conftest import MockContext, call_fastmcp_tool, patch_database_connection


class TestMultiComponentIntegration:
    """Test integration workflows across multiple server components."""

    @pytest.fixture
    async def server_with_db(self, test_db_manager):
        """Create server instance with test database."""
        from shared_context_server import server

        with patch_database_connection(test_db_manager):
            yield server

    async def test_complete_agent_workflow(self, server_with_db, test_db_manager):
        """Test complete agent workflow: authenticate -> create session -> add messages -> search -> memory."""
        # Step 1: Authenticate agent
        auth_ctx = MockContext(session_id="auth_session", agent_id="workflow_agent")
        auth_ctx.headers = {"X-API-Key": "workflow_test_key"}  # Add API key header

        with patch.dict(
            "os.environ",
            {
                "API_KEY": "workflow_test_key",
                "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
                "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            },
        ):
            auth_result = await call_fastmcp_tool(
                server_with_db.authenticate_agent,
                auth_ctx,
                agent_id="workflow_agent",
                agent_type="claude",
                requested_permissions=["read", "write", "admin"],
            )

        assert auth_result["success"] is True
        assert auth_result["agent_id"] == "workflow_agent"

        # Step 2: Create session with the authenticated agent context
        session_ctx = MockContext(agent_id="workflow_agent")
        session_result = await call_fastmcp_tool(
            server_with_db.create_session,
            session_ctx,
            purpose="Complete workflow test",
            metadata={"workflow": "integration_test", "stage": "session_creation"},
        )

        assert session_result["success"] is True
        session_id = session_result["session_id"]
        assert session_result["created_by"] == "workflow_agent"

        # Step 3: Add diverse messages
        messages_data = [
            {
                "content": "Initial workflow message",
                "visibility": "public",
                "metadata": {"step": 1},
            },
            {
                "content": "Private workflow note",
                "visibility": "private",
                "metadata": {"step": 2},
            },
            {
                "content": "Agent-only workflow data",
                "visibility": "agent_only",
                "metadata": {"step": 3},
            },
            {
                "content": "Final workflow summary",
                "visibility": "public",
                "metadata": {"step": 4, "final": True},
            },
        ]

        message_ids = []
        for msg_data in messages_data:
            msg_result = await call_fastmcp_tool(
                server_with_db.add_message,
                session_ctx,
                session_id=session_id,
                content=msg_data["content"],
                visibility=msg_data["visibility"],
                metadata=msg_data["metadata"],
            )
            assert msg_result["success"] is True
            message_ids.append(msg_result["message_id"])

        # Step 4: Search for workflow content
        search_result = await call_fastmcp_tool(
            server_with_db.search_context,
            session_ctx,
            session_id=session_id,
            query="workflow",
            fuzzy_threshold=70.0,
            search_metadata=True,
        )

        assert search_result["success"] is True
        assert len(search_result["results"]) >= 4  # Should find all workflow messages

        # Verify search found relevant content
        found_contents = [r["message"]["content"] for r in search_result["results"]]
        assert any("Initial workflow" in content for content in found_contents)
        assert any("Final workflow" in content for content in found_contents)

        # Step 5: Store workflow state in memory
        workflow_state = {
            "session_id": session_id,
            "message_count": len(message_ids),
            "workflow_complete": True,
            "completion_time": datetime.now(timezone.utc).isoformat(),
        }

        memory_result = await call_fastmcp_tool(
            server_with_db.set_memory,
            session_ctx,
            key="workflow_state",
            value=workflow_state,
            metadata={"workflow": "integration_test"},
        )

        assert memory_result["success"] is True

        # Step 6: Retrieve and verify complete session
        session_get_result = await call_fastmcp_tool(
            server_with_db.get_session, session_ctx, session_id=session_id
        )

        assert session_get_result["success"] is True
        assert len(session_get_result["messages"]) == 4
        assert session_get_result["message_count"] == 4

        # Step 7: Verify memory state persists
        memory_get_result = await call_fastmcp_tool(
            server_with_db.get_memory, session_ctx, key="workflow_state"
        )

        assert memory_get_result["success"] is True
        stored_state = memory_get_result["value"]
        assert stored_state["session_id"] == session_id
        assert stored_state["workflow_complete"] is True

    async def test_multi_agent_collaboration_workflow(
        self, server_with_db, test_db_manager
    ):
        """Test workflow involving multiple agents collaborating in the same session."""
        # Set up multiple agent contexts
        agent1_ctx = MockContext(agent_id="collab_agent_1")
        agent2_ctx = MockContext(agent_id="collab_agent_2")
        agent3_ctx = MockContext(agent_id="collab_agent_3")

        # Agent 1 creates the session
        session_result = await call_fastmcp_tool(
            server_with_db.create_session,
            agent1_ctx,
            purpose="Multi-agent collaboration session",
            metadata={
                "type": "collaboration",
                "participants": ["agent_1", "agent_2", "agent_3"],
            },
        )
        session_id = session_result["session_id"]

        # Agent 1 adds initial message
        await call_fastmcp_tool(
            server_with_db.add_message,
            agent1_ctx,
            session_id=session_id,
            content="Agent 1: Starting collaboration on project planning",
            visibility="public",
            metadata={"phase": "initiation", "from": "agent_1"},
        )

        # Agent 2 responds with public and private content
        await call_fastmcp_tool(
            server_with_db.add_message,
            agent2_ctx,
            session_id=session_id,
            content="Agent 2: I can help with technical architecture",
            visibility="public",
            metadata={
                "phase": "response",
                "from": "agent_2",
                "expertise": "architecture",
            },
        )

        await call_fastmcp_tool(
            server_with_db.add_message,
            agent2_ctx,
            session_id=session_id,
            content="Agent 2 private note: Need to check resource availability",
            visibility="private",
            metadata={"phase": "internal", "from": "agent_2", "type": "note"},
        )

        # Agent 3 adds specialized input
        await call_fastmcp_tool(
            server_with_db.add_message,
            agent3_ctx,
            session_id=session_id,
            content="Agent 3: I'll handle data analysis and reporting",
            visibility="public",
            metadata={"phase": "response", "from": "agent_3", "expertise": "data"},
        )

        # Each agent stores their individual memory
        for i, ctx in enumerate([agent1_ctx, agent2_ctx, agent3_ctx], 1):
            await call_fastmcp_tool(
                server_with_db.set_memory,
                ctx,
                key="collaboration_role",
                value={
                    "session_id": session_id,
                    "agent_role": f"agent_{i}",
                    "expertise": ["planning", "architecture", "data"][i - 1],
                    "join_time": datetime.now(timezone.utc).isoformat(),
                },
                session_id=session_id,  # Session-scoped memory
            )

        # Test cross-agent visibility
        # Agent 1's view
        agent1_view = await call_fastmcp_tool(
            server_with_db.get_session, agent1_ctx, session_id=session_id
        )
        agent1_contents = [msg["content"] for msg in agent1_view["messages"]]

        # Agent 1 should see all public messages but not Agent 2's private message
        assert any("Starting collaboration" in content for content in agent1_contents)
        assert any("technical architecture" in content for content in agent1_contents)
        assert any("data analysis" in content for content in agent1_contents)
        assert not any(
            "check resource availability" in content for content in agent1_contents
        )

        # Agent 2's view
        agent2_view = await call_fastmcp_tool(
            server_with_db.get_session, agent2_ctx, session_id=session_id
        )
        agent2_contents = [msg["content"] for msg in agent2_view["messages"]]

        # Agent 2 should see public messages + own private message
        assert any("Starting collaboration" in content for content in agent2_contents)
        assert any(
            "check resource availability" in content for content in agent2_contents
        )
        assert any("data analysis" in content for content in agent2_contents)

        # Test collaborative search
        # Agent 3 searches for expertise-related content
        search_result = await call_fastmcp_tool(
            server_with_db.search_context,
            agent3_ctx,
            session_id=session_id,
            query="architecture analysis",
            fuzzy_threshold=50.0,  # Lower threshold for broader matching
            search_metadata=True,
        )

        assert search_result["success"] is True
        assert len(search_result["results"]) >= 2  # Should find relevant messages

        # Test memory isolation between agents
        for i, ctx in enumerate([agent1_ctx, agent2_ctx, agent3_ctx], 1):
            memory_result = await call_fastmcp_tool(
                server_with_db.get_memory,
                ctx,
                key="collaboration_role",
                session_id=session_id,
            )
            assert memory_result["success"] is True
            assert memory_result["value"]["agent_role"] == f"agent_{i}"

    async def test_resource_notification_integration_workflow(
        self, server_with_db, test_db_manager
    ):
        """Test integration between resource system and real-time notifications."""
        from shared_context_server.server import notification_manager

        ctx = MockContext(agent_id="notification_agent")

        # Set up notification tracking
        notifications_received = []
        original_notify = notification_manager._notify_single_client

        async def track_notifications(client_id: str, resource_uri: str) -> bool:
            notifications_received.append(
                {"client": client_id, "resource": resource_uri, "time": time.time()}
            )
            return True

        notification_manager._notify_single_client = track_notifications

        try:
            # Subscribe to resources before they exist
            await notification_manager.subscribe(
                "test_client", "session://future_session"
            )
            await notification_manager.subscribe(
                "test_client", "agent://notification_agent/memory"
            )

            # Create session (should trigger session resource notification)
            session_result = await call_fastmcp_tool(
                server_with_db.create_session,
                ctx,
                purpose="Resource notification test",
                metadata={"test": "notifications"},
            )
            session_id = session_result["session_id"]

            # Update subscription to actual session
            await notification_manager.unsubscribe(
                "test_client", "session://future_session"
            )
            await notification_manager.subscribe(
                "test_client", f"session://{session_id}"
            )

            # Add message (should trigger both session and agent memory notifications)
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content="Message for notification testing",
                visibility="public",
                metadata={"triggers": "notifications"},
            )

            # Set memory (should trigger agent memory notifications)
            await call_fastmcp_tool(
                server_with_db.set_memory,
                ctx,
                key="notification_test",
                value={"test": "notification_value"},
                metadata={"triggers": "memory_notification"},
            )

            # Allow time for notifications to be processed
            await asyncio.sleep(0.2)

            # Verify notifications were sent
            assert len(notifications_received) >= 2

            # Should have session resource notifications
            session_notifications = [
                n
                for n in notifications_received
                if f"session://{session_id}" in n["resource"]
            ]
            assert len(session_notifications) >= 1

            # Should have agent memory notifications
            memory_notifications = [
                n
                for n in notifications_received
                if "agent://notification_agent/memory" in n["resource"]
            ]
            assert len(memory_notifications) >= 1

            # All notifications should be for test_client
            for notification in notifications_received:
                assert notification["client"] == "test_client"

        finally:
            # Restore original notification method
            notification_manager._notify_single_client = original_notify

    async def test_search_across_memory_and_messages_workflow(
        self, server_with_db, test_db_manager
    ):
        """Test workflow that involves searching both message content and memory data."""
        ctx = MockContext(agent_id="search_integration_agent")

        # Create session with searchable content
        session_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="Search integration test with machine learning focus",
            metadata={"domain": "ai", "technology": "machine_learning"},
        )
        session_id = session_result["session_id"]

        # Add messages with related content
        ml_messages = [
            {
                "content": "Training neural networks requires large datasets",
                "metadata": {"topic": "training", "category": "ml"},
            },
            {
                "content": "Deep learning models show impressive results on image classification",
                "metadata": {"topic": "deep_learning", "category": "computer_vision"},
            },
            {
                "content": "Natural language processing using transformer architectures",
                "metadata": {"topic": "nlp", "category": "transformers"},
            },
        ]

        for msg_data in ml_messages:
            await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content=msg_data["content"],
                visibility="public",
                metadata=msg_data["metadata"],
            )

        # Store related memory with searchable content
        memory_entries = [
            {
                "key": "ml_frameworks",
                "value": {
                    "frameworks": ["tensorflow", "pytorch", "keras"],
                    "use_cases": ["deep_learning", "neural_networks", "training"],
                    "notes": "Popular frameworks for machine learning development",
                },
            },
            {
                "key": "model_architectures",
                "value": {
                    "types": ["cnn", "rnn", "transformer"],
                    "applications": [
                        "image_classification",
                        "nlp",
                        "sequence_modeling",
                    ],
                    "description": "Common neural network architectures",
                },
            },
            {
                "key": "dataset_sources",
                "value": {
                    "sources": ["imagenet", "common_crawl", "openwebtext"],
                    "purpose": "training data for various machine learning tasks",
                },
            },
        ]

        for entry in memory_entries:
            await call_fastmcp_tool(
                server_with_db.set_memory,
                ctx,
                key=entry["key"],
                value=entry["value"],
                metadata={"searchable": True, "category": "ml_reference"},
            )

        # Test comprehensive search across messages
        message_search = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="learning",
            fuzzy_threshold=40.0,  # Lower threshold for broader matching
            search_metadata=True,
        )

        assert message_search["success"] is True
        assert len(message_search["results"]) >= 2

        # Verify search found relevant content
        found_contents = [
            r["message"]["content"].lower() for r in message_search["results"]
        ]
        assert any("learning" in content for content in found_contents)
        # The search should find at least 2 messages with our query
        # Note: "deep learning" might not match "neural networks training" well enough

        # Test search with different terms
        framework_search = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="transformer architecture",
            fuzzy_threshold=70.0,
        )

        assert framework_search["success"] is True
        # Should find the NLP transformer message
        transformer_contents = [
            r["message"]["content"] for r in framework_search["results"]
        ]
        assert any("transformer" in content.lower() for content in transformer_contents)

        # List memory to see what's stored
        memory_list = await call_fastmcp_tool(server_with_db.list_memory, ctx, limit=10)

        assert memory_list["success"] is True
        assert len(memory_list["entries"]) == 3

        memory_keys = [entry["key"] for entry in memory_list["entries"]]
        assert "ml_frameworks" in memory_keys
        assert "model_architectures" in memory_keys
        assert "dataset_sources" in memory_keys

        # Search by sender to find all messages from this agent
        sender_search = await call_fastmcp_tool(
            server_with_db.search_by_sender,
            ctx,
            session_id=session_id,
            sender="search_integration_agent",
        )

        assert sender_search["success"] is True
        assert len(sender_search["messages"]) == 3
        assert all(
            msg["sender"] == "search_integration_agent"
            for msg in sender_search["messages"]
        )

    async def test_error_propagation_across_components(
        self, server_with_db, test_db_manager
    ):
        """Test that errors in one component are properly handled by dependent components."""
        ctx = MockContext(agent_id="error_test_agent")

        # Create valid session first
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Error propagation test"
        )
        session_id = session_result["session_id"]

        # Test database error during message addition affects search
        with patch(
            "shared_context_server.session_tools.get_db_connection"
        ) as mock_conn:
            # First call succeeds (for session verification), second fails
            call_count = [0]

            async def mock_get_connection():
                call_count[0] += 1
                if call_count[0] > 1:  # Fail on subsequent calls

                    class DatabaseConnectionError(Exception):
                        """Custom exception for database connection testing."""

                        pass

                    raise DatabaseConnectionError(
                        "Database connection failed during message addition"
                    )
                else:
                    # Return real connection for session verification
                    async with test_db_manager.get_connection() as conn:
                        yield conn

            mock_conn.return_value.__aenter__ = (
                lambda _: mock_get_connection().__anext__()
            )
            mock_conn.return_value.__aexit__ = lambda _, __, ___, ____: None

            # Message addition should fail
            msg_result = await call_fastmcp_tool(
                server_with_db.add_message,
                ctx,
                session_id=session_id,
                content="This should fail",
                visibility="public",
            )

            assert msg_result["success"] is False
            assert "error" in msg_result

        # Test that search handles empty sessions gracefully
        empty_search = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="nonexistent content",
        )

        # Should succeed but return empty results
        assert empty_search["success"] is True
        assert len(empty_search["results"]) == 0

        # Test memory operations with invalid session references
        invalid_memory = await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="test_key",
            value={"test": "value"},
            session_id="nonexistent_session",
        )

        # Should fail gracefully
        assert invalid_memory["success"] is False
        assert "not found" in invalid_memory["error"].lower()

    async def test_basic_concurrent_operations(self, server_with_db, test_db_manager):
        """Test basic concurrent operations (optimized from slow load test)."""
        # Reduced from 5 agents to 2 for speed
        agent_contexts = [MockContext(agent_id=f"load_agent_{i}") for i in range(2)]

        # Create sessions concurrently
        session_creation_tasks = [
            call_fastmcp_tool(
                server_with_db.create_session,
                ctx,
                purpose=f"Concurrent test session {i}",
                metadata={"concurrent_test": True, "agent_index": i},
            )
            for i, ctx in enumerate(agent_contexts)
        ]

        session_results = await asyncio.gather(*session_creation_tasks)
        session_ids = [result["session_id"] for result in session_results]

        # Verify all sessions were created
        assert all(result["success"] for result in session_results)
        assert len(set(session_ids)) == 2  # All unique session IDs

        # Add one message per session (reduced from 3 for speed)
        message_tasks = []
        for i, (ctx, session_id) in enumerate(zip(agent_contexts, session_ids)):
            message_tasks.append(
                call_fastmcp_tool(
                    server_with_db.add_message,
                    ctx,
                    session_id=session_id,
                    content=f"Concurrent test message from agent {i}",
                    visibility="public",
                    metadata={"agent_index": i},
                )
            )

        message_results = await asyncio.gather(*message_tasks)
        assert all(result["success"] for result in message_results)
        assert len(message_results) == 2  # 2 agents * 1 message

        # Test basic search functionality
        search_result = await call_fastmcp_tool(
            server_with_db.search_context,
            agent_contexts[0],
            session_id=session_ids[0],
            query="Concurrent test",
            fuzzy_threshold=70.0,
        )
        assert search_result["success"] is True
        assert len(search_result["results"]) == 1

        # Test basic memory operations
        memory_result = await call_fastmcp_tool(
            server_with_db.set_memory,
            agent_contexts[0],
            key="concurrent_test",
            value={"test": True},
        )
        assert memory_result["success"] is True

    async def test_comprehensive_audit_trail_workflow(
        self, server_with_db, test_db_manager
    ):
        """Test that all major operations create proper audit trail entries."""
        ctx = MockContext(agent_id="audit_agent")

        # Perform various operations that should generate audit logs

        # 1. Create session
        session_result = await call_fastmcp_tool(
            server_with_db.create_session,
            ctx,
            purpose="Audit trail test session",
            metadata={"audit": "test"},
        )
        session_id = session_result["session_id"]

        # 2. Add messages
        await call_fastmcp_tool(
            server_with_db.add_message,
            ctx,
            session_id=session_id,
            content="Audit test message",
            visibility="public",
        )

        # 3. Set memory
        await call_fastmcp_tool(
            server_with_db.set_memory,
            ctx,
            key="audit_test",
            value={"audit": "memory_test"},
        )

        # 4. Search operations (should generate audit logs)
        await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="audit test",
        )

        # Verify audit log entries were created
        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT event_type FROM audit_log WHERE agent_id = ? ORDER BY timestamp",
                ("audit_agent",),
            )
            audit_events = [row[0] for row in await cursor.fetchall()]

        # Should have audit entries for major operations
        expected_events = [
            "session_created",
            "message_added",
            "memory_set",
            "context_searched",
        ]
        for expected_event in expected_events:
            assert expected_event in audit_events

        # Verify audit log contains proper metadata
        async with test_db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT metadata FROM audit_log WHERE event_type = ? AND agent_id = ?",
                ("context_searched", "audit_agent"),
            )
            search_audit = await cursor.fetchone()

            if search_audit:
                metadata = json.loads(search_audit[0])
                assert "query" in metadata
                assert "results_count" in metadata
                assert metadata["query"] == "audit test"

    async def test_data_consistency_across_operations(
        self, server_with_db, test_db_manager
    ):
        """Test data consistency when multiple operations modify the same entities."""
        ctx = MockContext(agent_id="consistency_agent")

        # Create session
        session_result = await call_fastmcp_tool(
            server_with_db.create_session, ctx, purpose="Consistency test"
        )
        session_id = session_result["session_id"]

        # Perform concurrent operations that might conflict
        async def add_messages_batch(batch_id: int):
            results = []
            for i in range(3):
                result = await call_fastmcp_tool(
                    server_with_db.add_message,
                    ctx,
                    session_id=session_id,
                    content=f"Batch {batch_id} message {i}",
                    visibility="public",
                    metadata={"batch": batch_id, "index": i},
                )
                results.append(result)
            return results

        # Run concurrent batches
        batch_results = await asyncio.gather(
            add_messages_batch(1), add_messages_batch(2), add_messages_batch(3)
        )

        # Verify all operations succeeded
        for batch in batch_results:
            for result in batch:
                assert result["success"] is True

        # Verify data consistency
        session_data = await call_fastmcp_tool(
            server_with_db.get_session, ctx, session_id=session_id
        )

        assert session_data["success"] is True
        assert len(session_data["messages"]) == 9  # 3 batches * 3 messages

        # Verify message ordering and content integrity
        messages = sorted(session_data["messages"], key=lambda x: x["timestamp"])
        for _i, msg in enumerate(messages):
            assert "Batch" in msg["content"]
            assert "message" in msg["content"]
            # Each message should have unique content

        # Verify search consistency
        search_result = await call_fastmcp_tool(
            server_with_db.search_context,
            ctx,
            session_id=session_id,
            query="Batch",
            fuzzy_threshold=80.0,
        )

        assert search_result["success"] is True
        assert len(search_result["results"]) == 9  # Should find all batch messages
