#!/usr/bin/env python3
"""
Test script to verify MCP Inspector CLI compatibility with STDIO transport.
"""

import asyncio
import os


async def test_mcp_inspector():
    """Test MCP Inspector CLI with various methods."""

    # Set required environment variables
    env = os.environ.copy()
    env.update(
        {
            "JWT_SECRET_KEY": "test-secret-key-for-jwt-signing-123456",
            "JWT_ENCRYPTION_KEY": "3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=",
            "LOG_LEVEL": "ERROR",  # Reduce noise for testing
        }
    )

    # Test methods that should work without authentication
    test_methods = [
        "tools/list",
        "resources/list",
        "prompts/list",
        "resources/templates/list",
    ]

    print("Testing MCP Inspector CLI with STDIO transport...")
    print("=" * 60)

    for method in test_methods:
        print(f"\n🔍 Testing method: {method}")

        try:
            # Run MCP Inspector CLI
            cmd = [
                "npx",
                "@modelcontextprotocol/inspector",
                "--cli",
                "uv",
                "run",
                "python",
                "-m",
                "shared_context_server.scripts.cli",
                "--transport",
                "stdio",
                "--method",
                method,
            ]

            print(f"Running: {' '.join(cmd)}")

            # Use asyncio subprocess for better control
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=15.0
                )

                if process.returncode == 0:
                    print(f"✅ SUCCESS: {method}")
                    if stdout:
                        print(f"Output preview: {stdout.decode()[:200]}...")
                else:
                    print(f"❌ FAILED: {method} (exit code: {process.returncode})")
                    if stderr:
                        print(f"Error: {stderr.decode()[:300]}")

            except asyncio.TimeoutError:
                print(f"⏰ TIMEOUT: {method} (killed after 15s)")
                process.kill()
                await process.communicate()

        except Exception as e:
            print(f"❌ EXCEPTION: {method} - {e}")

    print("\n" + "=" * 60)
    print("MCP Inspector CLI testing complete!")


if __name__ == "__main__":
    asyncio.run(test_mcp_inspector())
