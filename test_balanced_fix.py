#!/usr/bin/env python3
"""
Test the balanced metadata validation fix.
"""

import json
from typing import Any

from pydantic import BaseModel, Field


def test_balanced_metadata_validation():
    """Test the balanced metadata field validation."""

    print("TESTING BALANCED METADATA VALIDATION")
    print("=" * 60)

    # Simulate the balanced field definition
    class BalancedSessionModel(BaseModel):
        purpose: str = Field(description="Purpose or description of the session")
        metadata: dict[str, Any] | None = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
        )

    # Test values - objects and null should work
    valid_cases = [
        {"test": "value"},
        {"test": True, "version": 1},
        None,
        {},
        {"nested": {"deep": {"object": True}}},
        {"list_value": [1, 2, 3]},
        {"mixed": {"string": "value", "number": 42, "bool": True}},
    ]

    # These should fail with dict validation
    invalid_cases = [
        [],  # List, not dict
        "string_metadata",  # String, not dict
        42,  # Number, not dict
        [1, 2, 3],  # List, not dict
    ]

    print("Testing VALID cases (should work):")
    for value in valid_cases:
        try:
            model = BalancedSessionModel(purpose="test", metadata=value)
            print(f"  {value!r:30} -> ✅ PASS")
        except Exception as e:
            print(f"  {value!r:30} -> ❌ FAIL: {e}")

    print("\nTesting INVALID cases (should fail gracefully):")
    for value in invalid_cases:
        try:
            model = BalancedSessionModel(purpose="test", metadata=value)
            print(f"  {value!r:30} -> ⚠️  UNEXPECTED PASS")
        except Exception as e:
            print(f"  {value!r:30} -> ✅ EXPECTED FAIL: {type(e).__name__}")

    # Check JSON schema generation
    print("\nJSON Schema for balanced metadata:")
    schema = BalancedSessionModel.model_json_schema()
    metadata_schema = schema.get("properties", {}).get("metadata", {})
    print(json.dumps(metadata_schema, indent=2))


if __name__ == "__main__":
    test_balanced_metadata_validation()
