"""
Unit tests for MCP Resources.

Tests the static resource implementations for server information
and tool documentation, verifying JSON structure and content.
"""

import json
from unittest.mock import patch

from shared_context_server.resources import (
    get_server_info_resource,
    get_tools_documentation_resource,
)


class TestServerInfoResource:
    """Test server://info static resource."""

    async def test_server_info_basic_structure(self):
        """Test basic server info resource structure."""
        # Use create_resource method for template-based resources
        resource = await get_server_info_resource.create_resource(
            "server://info/default", {"_": "default"}
        )

        assert str(resource.uri) == "server://info/default"
        assert resource.name == "get_server_info_resource"
        assert resource.mime_type == "text/plain"

        # Parse and validate JSON structure
        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)
        assert "server_info" in content
        assert "tools" in content
        assert "features" in content
        assert "architecture" in content

    async def test_server_info_content_validation(self):
        """Test server info content accuracy."""
        resource = await get_server_info_resource.create_resource(
            "server://info/default", {"_": "default"}
        )
        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)

        # Validate server metadata
        server_info = content["server_info"]
        assert server_info["name"] == "shared-context-server"
        assert server_info["version"] == "1.1.1"
        assert "tools" in server_info["capabilities"]
        assert "resources" in server_info["capabilities"]
        assert "prompts" in server_info["capabilities"]

        # Validate features
        features = content["features"]
        assert "session_management" in features
        assert "agent_memory" in features
        assert "context_search" in features
        assert features["websocket_support"] is True

    async def test_server_info_ignores_parameter(self):
        """Test server info resource ignores the dummy parameter value."""
        resource1 = await get_server_info_resource.create_resource(
            "server://info/default", {"_": "default"}
        )
        resource2 = await get_server_info_resource.create_resource(
            "server://info/ignored_value", {"_": "ignored_value"}
        )

        # Should produce identical content regardless of parameter
        resource1_content = await resource1.read()
        resource2_content = await resource2.read()
        assert resource1_content == resource2_content
        assert resource1.name == resource2.name
        assert resource1.description == resource2.description


class TestToolsDocumentationResource:
    """Test docs://tools resource."""

    async def test_tools_docs_basic_structure(self):
        """Test basic tools documentation structure."""
        resource = await get_tools_documentation_resource.create_resource(
            "docs://tools/default", {"_": "default"}
        )

        assert str(resource.uri) == "docs://tools/default"
        assert resource.name == "get_tools_documentation_resource"
        assert resource.mime_type == "text/plain"

        # Parse and validate JSON structure
        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)
        assert "tools_documentation" in content
        assert "getting_started" in content

    async def test_tools_docs_content_validation(self):
        """Test tools documentation content accuracy."""
        resource = await get_tools_documentation_resource.create_resource(
            "docs://tools/default", {"_": "default"}
        )
        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)

        tools_doc = content["tools_documentation"]

        # Should have tools organized by category
        assert "tools_by_category" in tools_doc
        assert "usage_examples" in tools_doc
        assert isinstance(tools_doc["total_tools"], int)
        assert tools_doc["total_tools"] > 0

        # Validate usage examples structure
        usage_examples = tools_doc["usage_examples"]
        assert "session_management" in usage_examples
        assert "agent_memory" in usage_examples
        assert "context_search" in usage_examples

        # Check getting started section
        getting_started = content["getting_started"]
        assert "authentication" in getting_started
        assert "workflow" in getting_started
        assert "client_integration" in getting_started

    @patch("shared_context_server.resources.TOOL_REGISTRY")
    async def test_tools_docs_with_mock_registry(self, mock_registry):
        """Test tools documentation with mocked tool registry."""
        from shared_context_server.tools import ToolCategory, ToolMetadata

        # Mock tool registry
        mock_registry.values.return_value = [
            ToolMetadata(
                name="test_tool",
                category=ToolCategory.SESSION_MANAGEMENT,
                description="Test tool description",
                tags=["test"],
            )
        ]
        mock_registry.items.return_value = [
            (
                "test_tool",
                ToolMetadata(
                    name="test_tool",
                    category=ToolCategory.SESSION_MANAGEMENT,
                    description="Test tool description",
                    tags=["test"],
                ),
            )
        ]
        mock_registry.__len__.return_value = 1

        resource = await get_tools_documentation_resource.create_resource(
            "docs://tools/default", {"_": "default"}
        )
        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)

        # Should reflect mocked registry
        tools_doc = content["tools_documentation"]
        assert tools_doc["total_tools"] == 1

        # Should have session_management category
        tools_by_cat = tools_doc["tools_by_category"]
        assert "session_management" in tools_by_cat
        assert len(tools_by_cat["session_management"]) == 1
        assert tools_by_cat["session_management"][0]["name"] == "test_tool"

    async def test_tools_docs_json_serialization(self):
        """Test that tools documentation is properly JSON serializable."""
        resource = await get_tools_documentation_resource.create_resource(
            "docs://tools/default", {"_": "default"}
        )

        # Should be valid JSON
        # FastMCP resource templates return content via read() method
        resource_content = await resource.read()
        content = json.loads(resource_content)

        # Should be able to re-serialize
        re_serialized = json.dumps(content)
        assert isinstance(re_serialized, str)

        # Should have consistent structure after re-serialization
        re_parsed = json.loads(re_serialized)
        assert re_parsed == content

    async def test_tools_docs_ignores_parameter(self):
        """Test tools docs resource ignores the dummy parameter value."""
        resource1 = await get_tools_documentation_resource.create_resource(
            "docs://tools/default", {"_": "default"}
        )
        resource2 = await get_tools_documentation_resource.create_resource(
            "docs://tools/another_value", {"_": "another_value"}
        )

        # Should produce identical content regardless of parameter
        resource1_content = await resource1.read()
        resource2_content = await resource2.read()
        assert resource1_content == resource2_content
        assert resource1.name == resource2.name


class TestResourceIntegration:
    """Integration tests for resource functionality."""

    async def test_both_resources_available(self):
        """Test that both resources can be retrieved simultaneously."""
        server_info = await get_server_info_resource.create_resource(
            "server://info/default", {"_": "default"}
        )
        tools_docs = await get_tools_documentation_resource.create_resource(
            "docs://tools/default", {"_": "default"}
        )

        # Both should be valid resources
        assert str(server_info.uri) == "server://info/default"
        assert str(tools_docs.uri) == "docs://tools/default"

        # Both should have valid JSON content
        server_info_content = await server_info.read()
        tools_docs_content = await tools_docs.read()
        server_content = json.loads(server_info_content)
        tools_content = json.loads(tools_docs_content)

        assert "server_info" in server_content
        assert "tools_documentation" in tools_content

    async def test_resource_consistency(self):
        """Test consistency between server info and tools documentation."""
        server_info = await get_server_info_resource.create_resource(
            "server://info/default", {"_": "default"}
        )
        tools_docs = await get_tools_documentation_resource.create_resource(
            "docs://tools/default", {"_": "default"}
        )

        server_info_content = await server_info.read()
        tools_docs_content = await tools_docs.read()
        server_content = json.loads(server_info_content)
        tools_content = json.loads(tools_docs_content)

        # Tool count should be consistent
        server_tool_count = server_content["tools"]["count"]
        docs_tool_count = tools_content["tools_documentation"]["total_tools"]

        # Should be the same (both reflect TOOL_REGISTRY)
        assert server_tool_count == docs_tool_count

    async def test_resource_template_behavior(self):
        """Test resource template behavior with various parameter values."""
        # Test with different parameter values
        test_params = ["default", "test", "anything", ""]

        resources = []
        for param in test_params:
            server_resource = await get_server_info_resource.create_resource(
                f"server://info/{param}", {"_": param}
            )
            tools_resource = await get_tools_documentation_resource.create_resource(
                f"docs://tools/{param}", {"_": param}
            )
            resources.append((server_resource, tools_resource))

        # All should be valid resources
        for server_res, tools_res in resources:
            assert str(server_res.uri).startswith("server://info/")
            assert str(tools_res.uri).startswith("docs://tools/")

            # Content should be valid JSON
            server_res_content = await server_res.read()
            tools_res_content = await tools_res.read()
            json.loads(server_res_content)
            json.loads(tools_res_content)

        # Content should be identical regardless of parameter value (static resources)
        first_server, first_tools = resources[0]
        first_server_content = await first_server.read()
        first_tools_content = await first_tools.read()
        for server_res, tools_res in resources[1:]:
            server_res_content = await server_res.read()
            tools_res_content = await tools_res.read()
            assert server_res_content == first_server_content
            assert tools_res_content == first_tools_content
