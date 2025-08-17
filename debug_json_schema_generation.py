#!/usr/bin/env python3
"""
Debug JSON schema generation to understand how FastMCP creates schemas
and how they might be causing client-side validation issues.
"""

import json
from typing import Any, Union

from pydantic import BaseModel, Field


def analyze_schema_generation():
    """Analyze different approaches to metadata field JSON schema generation."""

    print("JSON SCHEMA GENERATION ANALYSIS")
    print("=" * 60)

    # 1. Current problematic implementation
    class CurrentModel(BaseModel):
        metadata: Any = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
            json_schema_extra={"anyOf": [{"type": "object"}, {"type": "null"}]},
        )

    # 2. Simple Any field
    class SimpleModel(BaseModel):
        metadata: Any = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
        )

    # 3. Union type
    class UnionModel(BaseModel):
        metadata: Union[dict, None] = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
        )

    # 4. Dict union with Any values
    class DictUnionModel(BaseModel):
        metadata: dict[str, Any] | None = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
        )

    # 5. Alternative json_schema_extra approach
    class AlternativeModel(BaseModel):
        metadata: Any = Field(
            default=None,
            description="Optional metadata for the session (JSON object or null)",
            examples=[{"test": True, "version": 1}, None],
            json_schema_extra={"type": ["object", "null"]},  # Different syntax
        )

    models = [
        ("Current (problematic)", CurrentModel),
        ("Simple Any", SimpleModel),
        ("Union[dict, None]", UnionModel),
        ("dict[str, Any] | None", DictUnionModel),
        ("Alternative json_schema_extra", AlternativeModel),
    ]

    for name, model_class in models:
        print(f"\n{name}:")
        print("-" * 40)
        schema = model_class.model_json_schema()
        metadata_schema = schema.get("properties", {}).get("metadata", {})
        print(json.dumps(metadata_schema, indent=2))

        # Check if this creates validation issues
        print(f"Schema type: {metadata_schema.get('type', 'Not specified')}")
        if "anyOf" in metadata_schema:
            print(f"anyOf constraints: {metadata_schema['anyOf']}")
            # This might be the problem - anyOf creates strict validation
            print("⚠️  POTENTIAL ISSUE: anyOf may cause strict client validation")

        print()


def test_json_schema_validation():
    """Test how different values would validate against the generated schemas."""

    print("\nJSON SCHEMA VALIDATION TESTING")
    print("=" * 60)

    # Import jsonschema for client-side validation testing
    try:
        import jsonschema

        # Test the current problematic schema
        current_schema = {
            "anyOf": [{"type": "object"}, {"type": "null"}],
            "default": None,
        }

        test_values = [
            {"test": "value"},
            {"test": True, "version": 1},
            None,
            {},
            [],  # This might fail anyOf validation
            "string",  # This will definitely fail
        ]

        print("Testing current schema with jsonschema validator:")
        print(f"Schema: {json.dumps(current_schema, indent=2)}")
        print()

        for value in test_values:
            try:
                jsonschema.validate(value, current_schema)
                print(f"  {value!r:25} -> ✅ VALID")
            except jsonschema.ValidationError as e:
                print(f"  {value!r:25} -> ❌ INVALID: {e.message}")

    except ImportError:
        print("jsonschema not available for client-side validation testing")


if __name__ == "__main__":
    analyze_schema_generation()
    test_json_schema_validation()
