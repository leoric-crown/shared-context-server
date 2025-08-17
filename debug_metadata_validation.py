#!/usr/bin/env python3
"""
Debug script to isolate metadata validation issue.
Tests different Field configurations to understand the root cause.
"""

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError


def test_field_configuration(field_def, test_values, description):
    """Test a specific field configuration with various inputs."""
    print(f"\n{'=' * 60}")
    print(f"TESTING: {description}")
    print(f"{'=' * 60}")

    class TestModel(BaseModel):
        metadata: Any = field_def

    # Print the JSON schema to see what's generated
    schema = TestModel.model_json_schema()
    print(
        f"Generated JSON Schema: {json.dumps(schema.get('properties', {}).get('metadata', {}), indent=2)}"
    )

    for value, expected in test_values:
        try:
            model = TestModel(metadata=value)
            result = "✅ PASS"
            print(f"  {value!r:25} -> {result}")
        except ValidationError as e:
            result = f"❌ FAIL: {e.errors()[0]['msg']}"
            print(f"  {value!r:25} -> {result}")


def main():
    """Run validation tests for different field configurations."""

    # Test values that should work in main branch
    test_values = [
        ({"test": "value"}, "should pass"),
        ({"test": True, "version": 1}, "should pass"),
        (None, "should pass"),
        ({}, "should pass"),
        ([], "should pass"),  # Edge case
        ("string", "should pass with Any"),  # Edge case
    ]

    print("METADATA VALIDATION DEBUG")
    print("Testing various Field configurations...")

    # 1. Current refactor implementation
    current_field = Field(
        default=None,
        description="Optional metadata for the session (JSON object or null)",
        examples=[{"test": True, "version": 1}, None],
        json_schema_extra={"anyOf": [{"type": "object"}, {"type": "null"}]},
    )
    test_field_configuration(
        current_field, test_values, "Current refactor implementation"
    )

    # 2. Simple Any field (baseline)
    simple_field = Field(default=None, description="Simple Any field")
    test_field_configuration(simple_field, test_values, "Simple Any field (baseline)")

    # 3. Union type approach
    from typing import Union

    union_field: Union[dict, None] = Field(
        default=None,
        description="Union[dict, None] approach",
        examples=[{"test": True}, None],
    )
    test_field_configuration(union_field, test_values, "Union[dict, None] approach")

    # 4. Dict with Any values
    dict_field: dict[str, Any] | None = Field(
        default=None,
        description="dict[str, Any] | None approach",
        examples=[{"test": True}, None],
    )
    test_field_configuration(dict_field, test_values, "dict[str, Any] | None approach")

    # 5. No json_schema_extra
    no_extra_field = Field(
        default=None,
        description="Any field without json_schema_extra",
        examples=[{"test": True, "version": 1}, None],
    )
    test_field_configuration(
        no_extra_field, test_values, "Any field without json_schema_extra"
    )


if __name__ == "__main__":
    main()
