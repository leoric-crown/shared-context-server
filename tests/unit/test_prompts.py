"""
Unit tests for MCP Prompts.

Tests workflow automation prompts for session setup and debugging,
verifying parameter validation and generated instructions.
"""

from unittest.mock import AsyncMock, patch

from mcp.types import PromptMessage, TextContent

from shared_context_server.prompts import (
    debug_session_prompt,
    setup_collaboration_prompt,
)


def extract_prompt_text(result):
    """Helper to extract actual prompt text from FastMCP wrapped result."""
    import json

    # FastMCP wraps the result in a PromptMessage with JSON content
    wrapper_message = result[0]
    json_content = json.loads(wrapper_message.content.text)
    actual_message = json_content["messages"][0]
    return actual_message["content"]["text"]


class TestSetupCollaborationPrompt:
    """Test setup-collaboration workflow prompt."""

    async def test_basic_setup_prompt(self):
        """Test basic collaboration setup prompt generation."""
        # FastMCP prompts are called via render method with parameter dict
        result = await setup_collaboration_prompt.render(
            {"purpose": "Test feature development"}
        )

        # FastMCP render returns list of PromptMessage objects directly
        assert isinstance(result, list)
        assert len(result) == 1

        message = result[0]
        assert isinstance(message, PromptMessage)
        assert message.role == "user"
        assert isinstance(message.content, TextContent)

        # Check content includes key elements
        content = extract_prompt_text(result)
        assert "Test feature development" in content
        assert "create_session" in content
        assert "authenticate_agent" in content
        assert "claude" in content.lower()
        assert "admin" in content.lower()

    async def test_custom_agent_types(self):
        """Test setup prompt with custom agent types."""
        result = await setup_collaboration_prompt.render(
            {
                "purpose": "Custom workflow",
                "agent_types": ["gemini", "system", "test"],
                "project_name": "TestProject",
            }
        )

        content = extract_prompt_text(result)

        # Should include all specified agent types
        assert "gemini" in content
        assert "system" in content
        assert "test" in content
        assert "TestProject" in content

        # Should have token generation for each agent
        assert content.count("authenticate_agent") >= 3

    async def test_invalid_agent_types(self):
        """Test setup prompt with invalid agent types."""
        result = await setup_collaboration_prompt.render(
            {
                "purpose": "Test purpose",
                "agent_types": ["invalid_type", "claude", "another_invalid"],
            }
        )

        content = extract_prompt_text(result)

        # Should return error message about invalid types
        assert "Invalid agent types" in content
        assert "invalid_type" in content
        assert "another_invalid" in content
        assert "Valid types:" in content

    async def test_setup_prompt_with_context(self):
        """Test setup prompt with MCP context."""
        mock_ctx = type(
            "MockCtx", (), {"agent_id": "test_agent", "session_id": "test_session"}
        )()

        result = await setup_collaboration_prompt.render(
            {"purpose": "Context test", "ctx": mock_ctx}
        )

        # Should work the same way regardless of context
        content = extract_prompt_text(result)
        assert "Context test" in content
        assert "create_session" in content

    async def test_setup_prompt_json_metadata(self):
        """Test that generated metadata is valid JSON."""
        result = await setup_collaboration_prompt.render(
            {
                "purpose": "JSON test",
                "agent_types": ["claude"],
                "project_name": "JSONProject",
            }
        )

        content = extract_prompt_text(result)

        # Extract JSON from create_session call
        # Should contain valid JSON structure
        assert "setup_date" in content
        assert "agent_types_requested" in content
        assert "setup_method" in content
        assert '"project": "JSONProject"' in content

    async def test_empty_agent_types_default(self):
        """Test setup prompt with None agent_types uses default."""
        result = await setup_collaboration_prompt.render(
            {"purpose": "Default test", "agent_types": None}
        )

        content = extract_prompt_text(result)

        # Should default to claude and admin
        assert "claude" in content.lower()
        assert "admin" in content.lower()
        assert content.count("authenticate_agent") >= 2


class TestDebugSessionPrompt:
    """Test debug-session troubleshooting prompt."""

    @patch("shared_context_server.prompts.get_db_connection")
    async def test_debug_existing_session(self, mock_get_db):
        """Test debug prompt for existing session with messages."""
        # Mock database connection and data
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock session data
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = {
            "id": "test_session",
            "purpose": "Test session purpose",
            "created_at": "2023-01-01T00:00:00Z",
            "created_by": "test_agent",
            "metadata": {"project": "test"},
        }

        # Mock message statistics
        mock_msg_cursor = AsyncMock()
        mock_msg_cursor.fetchall.return_value = [
            {"total": 5, "visibility": "public", "sender": "agent1"},
            {"total": 3, "visibility": "private", "sender": "agent2"},
        ]

        # Mock recent messages
        mock_recent_cursor = AsyncMock()
        mock_recent_cursor.fetchall.return_value = [
            {
                "sender": "agent1",
                "visibility": "public",
                "content": "Test message content",
                "timestamp": "2023-01-01T01:00:00Z",
            }
        ]

        # Setup mock execute calls
        mock_conn.execute.side_effect = [
            mock_session_cursor,
            mock_msg_cursor,
            mock_recent_cursor,
        ]

        result = await debug_session_prompt.render({"session_id": "test_session"})

        assert len(result) == 1
        content = extract_prompt_text(result)

        # Should contain session analysis
        assert "test_session" in content
        assert "Test session purpose" in content
        assert "Total Messages" in content
        assert "public: 5" in content
        assert "private: 3" in content
        assert "agent1: 5" in content
        assert "agent2: 3" in content

    @patch("shared_context_server.prompts.get_db_connection")
    async def test_debug_nonexistent_session(self, mock_get_db):
        """Test debug prompt for non-existent session."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock empty session result
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_session_cursor

        result = await debug_session_prompt.render({"session_id": "nonexistent"})

        content = extract_prompt_text(result)

        # Should indicate session not found
        assert "Session not found" in content
        assert "nonexistent" in content
        assert "verify the session ID" in content

    @patch("shared_context_server.prompts.get_db_connection")
    async def test_debug_empty_session(self, mock_get_db):
        """Test debug prompt for session with no messages."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock session exists but no messages
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = {
            "id": "empty_session",
            "purpose": "Empty session",
            "created_at": "2023-01-01T00:00:00Z",
            "created_by": "test_agent",
            "metadata": {},
        }

        mock_msg_cursor = AsyncMock()
        mock_msg_cursor.fetchall.return_value = []

        mock_recent_cursor = AsyncMock()
        mock_recent_cursor.fetchall.return_value = []

        mock_conn.execute.side_effect = [
            mock_session_cursor,
            mock_msg_cursor,
            mock_recent_cursor,
        ]

        result = await debug_session_prompt.render({"session_id": "empty_session"})
        content = extract_prompt_text(result)

        # Should identify as inactive session
        assert "Inactive Session" in content
        assert "No messages found" in content
        assert "agents are properly authenticated" in content

    @patch("shared_context_server.prompts.get_db_connection")
    async def test_debug_single_agent_session(self, mock_get_db):
        """Test debug prompt for session with single agent activity."""
        mock_conn = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_conn

        # Mock session with single agent
        mock_session_cursor = AsyncMock()
        mock_session_cursor.fetchone.return_value = {
            "id": "single_agent_session",
            "purpose": "Single agent session",
            "created_at": "2023-01-01T00:00:00Z",
            "created_by": "agent1",
            "metadata": {},
        }

        mock_msg_cursor = AsyncMock()
        mock_msg_cursor.fetchall.return_value = [
            {"total": 10, "visibility": "public", "sender": "agent1"}
        ]

        mock_recent_cursor = AsyncMock()
        mock_recent_cursor.fetchall.return_value = []

        mock_conn.execute.side_effect = [
            mock_session_cursor,
            mock_msg_cursor,
            mock_recent_cursor,
        ]

        result = await debug_session_prompt.render(
            {"session_id": "single_agent_session"}
        )
        content = extract_prompt_text(result)

        # Should identify single agent activity
        assert "Single Agent Activity" in content
        assert "Only one agent is active" in content
        assert "Verify other agents have proper session access" in content

    @patch("shared_context_server.prompts.get_db_connection")
    async def test_debug_database_error(self, mock_get_db):
        """Test debug prompt handles database errors gracefully."""
        mock_get_db.side_effect = Exception("Database connection failed")

        result = await debug_session_prompt.render({"session_id": "error_session"})
        content = extract_prompt_text(result)

        # Should contain error information
        assert "Error analyzing session" in content
        assert "error_session" in content
        assert "Database connection failed" in content
        assert "Troubleshooting Steps" in content

    async def test_debug_prompt_with_context(self):
        """Test debug prompt with MCP context."""
        mock_ctx = type(
            "MockCtx", (), {"agent_id": "debug_agent", "session_id": "debug_context"}
        )()

        # This will likely fail due to database, but test the context handling
        with patch("shared_context_server.prompts.get_db_connection") as mock_get_db:
            mock_get_db.side_effect = Exception("Expected test error")

            result = await debug_session_prompt.render(
                {"session_id": "test_session", "ctx": mock_ctx}
            )

            # Should handle context gracefully even with errors
            assert len(result) == 1
            content = extract_prompt_text(result)
            assert "Error analyzing session" in content


class TestPromptIntegration:
    """Integration tests for prompt functionality."""

    async def test_prompt_return_types(self):
        """Test that prompts return correct MCP types."""
        setup_result = await setup_collaboration_prompt.render({"purpose": "Type test"})

        # FastMCP render returns list with wrapper PromptMessage containing JSON
        assert isinstance(setup_result, list)
        assert len(setup_result) == 1

        wrapper_message = setup_result[0]
        assert isinstance(wrapper_message, PromptMessage)
        assert hasattr(wrapper_message, "role")
        assert hasattr(wrapper_message, "content")
        assert isinstance(wrapper_message.content, TextContent)

        # Verify the JSON content contains the expected structure
        import json

        json_content = json.loads(wrapper_message.content.text)
        assert "messages" in json_content
        assert isinstance(json_content["messages"], list)

    async def test_prompts_handle_unicode(self):
        """Test prompts handle unicode characters properly."""
        result = await setup_collaboration_prompt.render(
            {
                "purpose": "Unicode test: 🚀 émojis and spéciâl characters",
                "project_name": "Тест Project",
            }
        )

        content = extract_prompt_text(result)
        assert "🚀 émojis and spéciâl characters" in content
        assert "Тест Project" in content
