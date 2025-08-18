"""
Final coverage push tests to get over 84% threshold.

Targets remaining easy wins in various modules.
"""

from src.shared_context_server.models import (
    AgentMemoryModel,
    MessageModel,
    sanitize_memory_key,
    sanitize_search_input,
    sanitize_text_input,
)


class TestSanitizationFunctions:
    """Test sanitization functions for additional coverage."""

    def test_sanitize_text_input(self):
        """Test text input sanitization."""
        # Test normal text
        result = sanitize_text_input("normal text")
        assert result == "normal text"

        # Test text with extra whitespace
        result = sanitize_text_input("  text with spaces  ")
        assert result == "text with spaces"

    def test_sanitize_memory_key(self):
        """Test memory key sanitization."""
        # Test normal key
        result = sanitize_memory_key("normal_key")
        assert result == "normal_key"

        # Test key with whitespace
        result = sanitize_memory_key("  key_with_spaces  ")
        assert result == "key_with_spaces"

    def test_sanitize_search_input(self):
        """Test search input sanitization."""
        # Test normal search
        result = sanitize_search_input("search term")
        assert result == "search term"

        # Test search with extra whitespace
        result = sanitize_search_input("  search with spaces  ")
        assert result == "search with spaces"


class TestModelInitialization:
    """Test model initialization edge cases."""

    def test_agent_memory_model_with_minimal_data(self):
        """Test AgentMemoryModel with minimal required data."""
        memory = AgentMemoryModel(
            agent_id="a",  # Minimal valid agent ID
            key="k",  # Minimal valid key
            value="{}",  # Minimal valid JSON
        )
        assert memory.agent_id == "a"
        assert memory.key == "k"
        assert memory.value == {}

    def test_message_model_with_minimal_data(self):
        """Test MessageModel with minimal required data."""
        from datetime import datetime, timezone

        message = MessageModel(
            session_id="session_0123456789abcdef",
            sender="a",  # Minimal valid sender
            content="x",  # Minimal valid content
            timestamp=datetime.now(timezone.utc),
        )
        assert message.sender == "a"
        assert message.content == "x"

    def test_message_model_parent_message_id_none(self):
        """Test MessageModel with None parent_message_id."""
        from datetime import datetime, timezone

        message = MessageModel(
            session_id="session_0123456789abcdef",
            sender="test_agent",
            content="test content",
            timestamp=datetime.now(timezone.utc),
            parent_message_id=None,  # Explicitly test None
        )
        assert message.parent_message_id is None


class TestModelStringRepresentations:
    """Test model string representations and serialization."""

    def test_agent_memory_model_repr(self):
        """Test AgentMemoryModel string representation."""
        memory = AgentMemoryModel(
            agent_id="test_agent",
            key="test_key",
            value='{"test": "data"}',
        )
        # Just ensure repr works without errors
        repr_str = repr(memory)
        assert "AgentMemoryModel" in repr_str

    def test_message_model_serialization(self):
        """Test MessageModel JSON serialization."""
        from datetime import datetime, timezone

        message = MessageModel(
            session_id="session_0123456789abcdef",
            sender="test_agent",
            content="test content",
            timestamp=datetime.now(timezone.utc),
        )

        # Test that serialization works
        json_data = message.model_dump()
        assert json_data["sender"] == "test_agent"
        assert json_data["content"] == "test content"
