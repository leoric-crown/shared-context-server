#!/usr/bin/env python3
"""
Test that the metadata validation fix works correctly.
"""

import json
from typing import Any

from pydantic import BaseModel, Field


def test_fixed_metadata_validation():
    """Test the fixed metadata field validation."""

    print("TESTING FIXED METADATA VALIDATION")
    print("=" * 60)

    # Simulate the fixed field definition
    class FixedSessionModel(BaseModel):
        purpose: str = Field(description="Purpose or description of the session")
        metadata: Any = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
        )

    class FixedMessageModel(BaseModel):
        session_id: str = Field(description="Session ID")
        content: str = Field(description="Message content")
        metadata: Any = Field(
            default=None,
            description="Optional message metadata (JSON object or null)",
            examples=[{"message_type": "test", "priority": "high"}, None],
        )

    # Test values that should now work
    test_cases = [
        # Standard cases
        {"test": "value"},
        {"test": True, "version": 1},
        None,
        {},
        # Edge cases that should now work
        [],
        "string_metadata",
        42,
        [1, 2, 3],
        {"nested": {"deep": {"object": True}}},
    ]

    print("Testing create_session metadata field:")
    for value in test_cases:
        try:
            model = FixedSessionModel(purpose="test", metadata=value)
            print(f"  {value!r:30} -> ✅ PASS")
        except Exception as e:
            print(f"  {value!r:30} -> ❌ FAIL: {e}")

    print("\nTesting add_message metadata field:")
    for value in test_cases:
        try:
            model = FixedMessageModel(session_id="test", content="test", metadata=value)
            print(f"  {value!r:30} -> ✅ PASS")
        except Exception as e:
            print(f"  {value!r:30} -> ❌ FAIL: {e}")

    # Check JSON schema generation
    print("\nJSON Schema for session metadata:")
    session_schema = FixedSessionModel.model_json_schema()
    metadata_schema = session_schema.get("properties", {}).get("metadata", {})
    print(json.dumps(metadata_schema, indent=2))

    print("\nJSON Schema for message metadata:")
    message_schema = FixedMessageModel.model_json_schema()
    metadata_schema = message_schema.get("properties", {}).get("metadata", {})
    print(json.dumps(metadata_schema, indent=2))


if __name__ == "__main__":
    test_fixed_metadata_validation()
