#!/usr/bin/env python3
"""
Test if the JSON schema fixes resolve the Gemini CLI issues.
"""

import inspect
import sys
from pathlib import Path
from typing import get_type_hints

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Import the problematic tools
    from shared_context_server.memory_tools import set_memory
    from shared_context_server.search_tools import (
        search_by_sender_tool,
        search_by_timerange_tool,
        search_context_tool,
    )
    from shared_context_server.session_tools import (
        add_message,
        create_session,
        get_messages,
    )

    print("✅ Tool imports successful")

    from pydantic import create_model

    def analyze_tool_schema(func_tool, func_name):
        print(f"\n🔍 Analyzing {func_name}:")

        # Extract the actual function from the FunctionTool wrapper
        if hasattr(func_tool, "fn"):
            func = func_tool.fn
        else:
            func = func_tool

        # Get function signature
        sig = inspect.signature(func)

        # Get type hints
        hints = get_type_hints(func)

        # Extract parameters (skip 'ctx' and excluded fields)
        fields = {}
        for param_name, param in sig.parameters.items():
            if param_name == "ctx":
                continue

            # Skip excluded fields
            if hasattr(param.default, "exclude") and param.default.exclude:
                print(f"  ⏭️  Skipping excluded field: {param_name}")
                continue

            param_type = hints.get(
                param_name,
                type(param.default)
                if param.default != inspect.Parameter.empty
                else str,
            )
            default_value = (
                param.default if param.default != inspect.Parameter.empty else ...
            )

            fields[param_name] = (param_type, default_value)
            print(f"  📝 {param_name}: {param_type}")

        # Create a temporary Pydantic model
        if fields:
            try:
                TempModel = create_model(f"{func_name}Model", **fields)
                schema = TempModel.model_json_schema()

                # Check for schema issues
                issues = []
                clean_properties = 0
                if "properties" in schema:
                    for prop_name, prop_schema in schema["properties"].items():
                        if "type" in prop_schema:
                            clean_properties += 1
                            print(
                                f"    ✅ {prop_name}: has type '{prop_schema['type']}'"
                            )
                        elif "anyOf" in prop_schema:
                            # Check if all anyOf items have types
                            has_all_types = all(
                                "type" in item for item in prop_schema["anyOf"]
                            )
                            if has_all_types:
                                types = [item["type"] for item in prop_schema["anyOf"]]
                                print(f"    ⚠️  {prop_name}: anyOf with types {types}")
                            else:
                                issues.append(
                                    f"Property '{prop_name}' has anyOf without all items having types"
                                )
                                print(f"    ❌ {prop_name}: problematic anyOf")
                        else:
                            issues.append(
                                f"Property '{prop_name}' missing type information"
                            )
                            print(f"    ❌ {prop_name}: missing type")

                print(
                    f"  📊 Summary: {clean_properties} clean properties, {len(issues)} issues"
                )

                if issues:
                    print("  ⚠️  Issues found:")
                    for issue in issues:
                        print(f"    - {issue}")
                else:
                    print("  🎉 Schema looks good for Gemini CLI!")

            except Exception as e:
                print(f"  ❌ Error creating schema: {e}")
                import traceback

                traceback.print_exc()

    # Test the problematic tools
    analyze_tool_schema(set_memory, "set_memory")
    analyze_tool_schema(create_session, "create_session")
    analyze_tool_schema(add_message, "add_message")
    analyze_tool_schema(get_messages, "get_messages")
    analyze_tool_schema(search_context_tool, "search_context")
    analyze_tool_schema(search_by_sender_tool, "search_by_sender")
    analyze_tool_schema(search_by_timerange_tool, "search_by_timerange")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
