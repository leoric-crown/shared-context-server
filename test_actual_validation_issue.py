#!/usr/bin/env python3
"""
Test the actual validation issue by calling the create_session tool directly.
"""

import asyncio
import os
import sys

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from shared_context_server.session_tools import create_session


class MockContext:
    """Mock FastMCP context for testing."""

    def __init__(self):
        self.params = {}
        self.session = {}
        # Set the API key for authentication
        os.environ["API_KEY"] = "test-key-for-validation"

    @property
    def request_meta(self):
        return {"headers": {"api_key": "test-key-for-validation"}}


async def test_validation_issue():
    """Test the validation issue directly."""
    print("TESTING ACTUAL VALIDATION ISSUE")
    print("=" * 60)

    ctx = MockContext()

    # Test cases that should work
    test_cases = [
        {"purpose": "test session", "metadata": {"test": "value"}},
        {"purpose": "test session", "metadata": {"test": True, "version": 1}},
        {"purpose": "test session", "metadata": None},
        {"purpose": "test session", "metadata": {}},
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case}")
        try:
            result = await create_session(ctx, **test_case)
            print(f"  ✅ SUCCESS: {result.get('session_id', 'Unknown')}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            print(f"     Type: {type(e).__name__}")
            if hasattr(e, "errors"):
                print(f"     Details: {e.errors()}")


async def main():
    """Run the test."""
    await test_validation_issue()


if __name__ == "__main__":
    asyncio.run(main())
