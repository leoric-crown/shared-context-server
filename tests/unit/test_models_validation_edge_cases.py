"""
Quick coverage booster tests for models.py validation edge cases.

Targets specific uncovered validation paths to push coverage over 84%.
"""

import pytest
from pydantic import ValidationError

from src.shared_context_server.models import (
    AgentMemoryModel,
    MessageModel,
    SessionModel,
    validate_agent_id,
    validate_json_metadata,
    validate_session_id,
)


class TestValidationEdgeCases:
    """Test edge cases in validation functions."""

    def test_validate_json_metadata_type_error(self):
        """Test metadata validation with non-dict input."""
        with pytest.raises(TypeError, match="Metadata must be a dictionary"):
            validate_json_metadata("not a dict")

    def test_validate_json_metadata_key_type_error(self):
        """Test metadata with non-string keys."""
        with pytest.raises(TypeError, match="Metadata keys must be strings"):
            validate_json_metadata({123: "value"})

    def test_validate_json_metadata_too_many_keys(self):
        """Test metadata with too many keys."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(51)}
        with pytest.raises(ValueError, match="cannot have more than 50 keys"):
            validate_json_metadata(large_metadata)

    def test_session_model_empty_purpose_after_sanitization(self):
        """Test session with purpose that becomes empty after sanitization."""
        with pytest.raises(ValidationError):
            SessionModel(
                id="session_0123456789abcdef",
                created_by="test_agent",
                purpose="   ",  # Empty after strip
            )

    def test_session_model_naive_datetime_conversion(self):
        """Test session model converts naive datetime to UTC."""
        from datetime import datetime

        session = SessionModel(
            id="session_0123456789abcdef",
            created_by="test_agent",
            purpose="test purpose",
            created_at=datetime(2025, 1, 1, 12, 0, 0),  # Naive datetime
        )
        assert session.created_at.tzinfo is not None

    def test_message_model_timezone_conversion(self):
        """Test message model timezone conversion."""
        from datetime import datetime

        message = MessageModel(
            session_id="session_0123456789abcdef",
            sender="test_agent",
            content="test message",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),  # Naive datetime
        )
        assert message.timestamp.tzinfo is not None

    def test_agent_memory_model_empty_session_id(self):
        """Test agent memory with None session_id validation."""
        memory = AgentMemoryModel(
            agent_id="test_agent",
            session_id=None,  # Should be allowed
            key="test_key",
            value='{"data": "test"}',
        )
        assert memory.session_id is None

    def test_agent_memory_model_key_validation_edge_case(self):
        """Test memory key validation with invalid characters."""
        # Test that invalid characters in key are rejected
        with pytest.raises(
            ValidationError, match="Memory key contains invalid characters"
        ):
            AgentMemoryModel(
                agent_id="test_agent",
                key="test_key_with_symbols!@#",
                value='{"data": "test"}',
            )


class TestValidationFunctionEdgeCases:
    """Test standalone validation functions."""

    def test_validate_session_id_edge_cases(self):
        """Test session ID validation edge cases."""
        # Valid case
        assert (
            validate_session_id("session_0123456789abcdef")
            == "session_0123456789abcdef"
        )

        # Invalid cases should raise ValueError
        with pytest.raises(ValueError):
            validate_session_id("invalid_id")

    def test_validate_agent_id_edge_cases(self):
        """Test agent ID validation edge cases."""
        # Valid case
        assert validate_agent_id("valid_agent_123") == "valid_agent_123"

        # Invalid cases should raise ValueError
        with pytest.raises(ValueError):
            validate_agent_id("")  # Empty string

        with pytest.raises(ValueError):
            validate_agent_id("_invalid_start")  # Can't start with underscore
