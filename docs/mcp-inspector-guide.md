# MCP Inspector Guide for LLM Agents

Complete guide for using MCP Inspector to discover, test, and validate the Shared Context Server tools programmatically. This guide is optimized for LLM agents who need systematic tool discovery and testing workflows.

## Table of Contents

- [Quick Start](#quick-start)
- [Available Methods](#available-methods)
- [Tool Discovery](#tool-discovery)
- [Resource Templates](#resource-templates)
- [Prompt Templates](#prompt-templates)
- [Tool Testing](#tool-testing)
- [LLM Integration Patterns](#llm-integration-patterns)
- [Troubleshooting](#troubleshooting)
- [Development Workflow](#development-workflow)

---

## Quick Start

### Prerequisites
```bash
# Ensure you have the server dependencies
uv sync

# Set environment variables (required for authentication)
export API_KEY="ueCdNbbvVvTK89qSn1tQpZP4rHi4oMVYhvVzg7/7m8A="
export JWT_SECRET_KEY="test-secret-key-for-jwt-signing-123456"
export JWT_ENCRYPTION_KEY="3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="
```

### Preferred: STDIO (Clean Pattern)

Use this for local development without polluting your shell environment.

```bash
# List tools
npx @modelcontextprotocol/inspector --cli -e MCP_TRANSPORT=stdio --method tools/list \
  uv run python -m shared_context_server.scripts.cli

# List prompts
npx @modelcontextprotocol/inspector --cli -e MCP_TRANSPORT=stdio --method prompts/list \
  uv run python -m shared_context_server.scripts.cli

# List resource templates
npx @modelcontextprotocol/inspector --cli -e MCP_TRANSPORT=stdio --method resources/templates/list \
  uv run python -m shared_context_server.scripts.cli
```

### Alternative: HTTP Transport (for remote or header-based auth)

```bash
# Start the server in HTTP mode (separate terminal)
make dev  # http://localhost:24456

# Use MCP Inspector over HTTP
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method tools/list
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method prompts/list
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method resources/templates/list
```

Note: Custom tools may still require authentication over HTTP. See [Tool Testing](#tool-testing).

---

## Available Methods

The MCP Inspector supports these methods for the Shared Context Server:

### Core Methods
- `tools/list` - List all available tools with complete schemas
- `tools/call` - Execute a specific tool with parameters
- `resources/list` - List available MCP resources
- `resources/read` - Read a specific resource
- `resources/templates/list` - List resource templates with URI patterns
- `prompts/list` - List available prompt templates
- `prompts/get` - Get a specific prompt template
- `logging/setLevel` - Configure logging level

### Authentication Model

The server uses **selective authentication** as of v1.1.10:

**✅ No Authentication Required (MCP Protocol Methods):**
- `initialize` - Server initialization
- `tools/list` - Tool discovery
- `resources/list` - Resource discovery
- `resources/templates/list` - Resource template discovery
- `prompts/list` - Prompt template discovery
- `ping` - Server health check

**🔐 Authentication Required (Custom Tools):**
- `create_session` - Session management
- `add_message` - Message operations
- `authenticate_agent` - Token generation
- `search_context` - Search operations
- `get_memory` - Memory access
- All other custom server functionality

This design enables **MCP Inspector CLI compatibility** while maintaining security for operational tools.

### Method Syntax

**STDIO (Clean pattern - recommended for local dev)**:
```bash
npx @modelcontextprotocol/inspector --cli -e MCP_TRANSPORT=stdio --method METHOD_NAME \
  uv run python -m shared_context_server.scripts.cli
```

**HTTP (Alternative - remote/auth scenarios)**:
```bash
# Optional: set auth headers via env if needed
export AUTH_APIKEY_HEADER_NAME="X-API-Key"
export AUTH_APIKEY_VALUE="your-api-key"

npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method METHOD_NAME
```

---

## Tool Discovery

### List All Tools
```bash
# Get complete tool catalog with schemas (HTTP transport)
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method tools/list
```

**Available Tools:**
- `get_usage_guidance` - Get operational capabilities and permissions
- `get_performance_metrics` - Get server performance metrics (admin only)
- `authenticate_agent` - Generate JWT tokens for multi-agent coordination
- `refresh_token` - Refresh JWT tokens
- `set_memory` - Store values in agent private memory
- `get_memory` - Retrieve values from agent memory
- `list_memory` - List agent memory entries
- `search_context` - Fuzzy search messages using RapidFuzz
- `search_by_sender` - Search messages by sender
- `search_by_timerange` - Search messages by time range
- `create_session` - Create collaboration session
- `get_session` - Retrieve session information
- `add_message` - Add message to session
- `get_messages` - Retrieve messages from session

### Extract Specific Tool Information
```bash
# Get tool names only
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method tools/list | jq '.tools[].name'

# Get specific tool schema
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method tools/list | \
  jq '.tools[] | select(.name == "create_session")'

# Get tool parameter requirements
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method tools/list | \
  jq '.tools[] | select(.name == "add_message") | {name, required: .inputSchema.required, properties: .inputSchema.properties | keys}'
```

---

## Resource Templates

Resource templates define URI patterns for accessing dynamic server resources.

### List Resource Templates
```bash
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method resources/templates/list
```

**Available Resource Templates:**

1. **Session Resource**: `session://{session_id}`
   - Real-time session data with message history
   - Supports subscriptions for live updates

2. **Agent Memory Resource**: `agent://{agent_id}/memory`
   - Agent's private memory store (security-controlled)
   - Only accessible by the agent itself

3. **Session Messages**: `session://{session_id}/messages/{limit}`
   - Enhanced session messages resource with pagination support
   - Provides parameterized message retrieval with limit control (default: 50, max: 500)

4. **Server Info**: `server://info/{_}`
   - Static server information and capabilities discovery
   - Essential server metadata for client capability detection

5. **Tool Documentation**: `docs://tools/{_}`
   - Comprehensive tool documentation with usage examples
   - Detailed documentation organized by category with practical examples

### Extract Resource Template Information
```bash
# Get resource template URI patterns
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method resources/templates/list | \
  jq '.resourceTemplates[] | {name, uriTemplate, description}'
```

---

## Prompt Templates

The server provides pre-built prompt templates for common multi-agent workflows.

### List Prompt Templates
```bash
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method prompts/list
```

**Available Prompt Templates:**

1. **setup-collaboration**
   - Initialize a multi-agent collaboration session with proper configuration
   - Automates creation of collaboration sessions and JWT token generation for agents
   - Required: `purpose` (string)
   - Optional: `agent_types` (array, default: ["claude", "admin"]), `project_name` (string)

2. **debug-session**
   - Analyze session state and provide troubleshooting guidance
   - Examines session health, message patterns, agent activity, and provides actionable debugging recommendations
   - Required: `session_id` (string)

### Get Prompt Template Details
```bash
# Get specific prompt template information
npx @modelcontextprotocol/inspector --cli http://localhost:24456/mcp --method prompts/list | \
  jq '.prompts[] | select(.name == "setup-collaboration")'
```

---

## Tool Testing

### Basic Tool Testing
The Inspector provides `tools/call` for testing tools, but requires proper parameter syntax:

```bash
# Test create_session (working example)
npx @modelcontextprotocol/inspector --cli \
  -e MCP_TRANSPORT=stdio \
  -e JWT_SECRET_KEY=test-secret-key-for-jwt-signing-123456 \
  -e JWT_ENCRYPTION_KEY=3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY= \
  --method tools/call \
  --tool-name create_session \
  uv run python -m shared_context_server.scripts.cli
# This will show validation error: 'purpose' is required

# Note: Tool input parameters require specific syntax that varies by inspector version
# For comprehensive tool testing, use the server's test suite or direct API calls
```

### Alternative Testing Approach
For reliable tool testing, use direct server API calls or the development server:

```bash
# Start development server for testing
make dev

# Or use MCP Inspector CLI for direct testing (STDIO)
npx @modelcontextprotocol/inspector --cli \
  -e MCP_TRANSPORT=stdio \
  --method tools/call \
  --tool-name get_usage_guidance \
  uv run python -m shared_context_server.scripts.cli
```

---

## LLM Integration Patterns

### Complete Discovery Workflow for LLM Agents

```bash
#!/bin/bash
# LLM Agent Discovery Script

API_KEY="test-key"
JWT_SECRET_KEY="test-secret-key-for-jwt-signing-123456"
JWT_ENCRYPTION_KEY="3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY="

# 1. Discover server capabilities
echo "🔍 Discovering server capabilities..."
npx @modelcontextprotocol/inspector --cli --method tools/list \
  -e API_KEY=$API_KEY -e JWT_SECRET_KEY=$JWT_SECRET_KEY -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli > server_tools.json

# 2. Get resource templates
echo "📋 Getting resource templates..."
npx @modelcontextprotocol/inspector --cli --method resources/templates/list \
  -e API_KEY=$API_KEY -e JWT_SECRET_KEY=$JWT_SECRET_KEY -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli > resource_templates.json

# 3. Get prompt templates
echo "🎯 Getting prompt templates..."
npx @modelcontextprotocol/inspector --cli --method prompts/list \
  -e API_KEY=$API_KEY -e JWT_SECRET_KEY=$JWT_SECRET_KEY -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli > prompt_templates.json

# 4. Extract key information
echo "📊 Available tools:"
jq -r '.tools[].name' server_tools.json

echo "📋 Resource templates:"
jq -r '.resourceTemplates[].uriTemplate' resource_templates.json

echo "🎯 Prompt templates:"
jq -r '.prompts[].name' prompt_templates.json
```

### Tool Schema Validation
```bash
# Validate tool parameters before use
TOOL_NAME="add_message"
npx @modelcontextprotocol/inspector --cli --method tools/list \
  -e API_KEY=$API_KEY -e JWT_SECRET_KEY=$JWT_SECRET_KEY -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli | \
  jq --arg tool "$TOOL_NAME" '.tools[] | select(.name == $tool) | {
    name,
    required: .inputSchema.required,
    properties: .inputSchema.properties | keys,
    description
  }'
```

### Integration Readiness Check
```bash
# Check if server is ready for integration
echo "🏥 Server Health Check:"

# 1. Tool availability check
TOOL_COUNT=$(npx @modelcontextprotocol/inspector --cli --method tools/list \
  -e API_KEY=$API_KEY -e JWT_SECRET_KEY=$JWT_SECRET_KEY -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli | jq '.tools | length')

echo "✅ Available tools: $TOOL_COUNT"

# 2. Resource template availability
RESOURCE_COUNT=$(npx @modelcontextprotocol/inspector --cli --method resources/templates/list \
  -e API_KEY=$API_KEY -e JWT_SECRET_KEY=$JWT_SECRET_KEY -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli | jq '.resourceTemplates | length')

echo "✅ Resource templates: $RESOURCE_COUNT"

# 3. Prompt template availability
PROMPT_COUNT=$(npx @modelcontextprotocol/inspector --cli --method prompts/list \
  -e API_KEY=$API_KEY -e JWT_SECRET_KEY=$JWT_SECRET_KEY -e JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY \
  uv run python -m shared_context_server.scripts.cli | jq '.prompts | length')

echo "✅ Prompt templates: $PROMPT_COUNT"

echo "🚀 Server ready for integration!"
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "Method is required" Error
```bash
# ❌ Wrong - missing method
npx @modelcontextprotocol/inspector --cli uv run python -m shared_context_server.scripts.cli

# ✅ Correct - method specified
npx @modelcontextprotocol/inspector --cli --method tools/list uv run python -m shared_context_server.scripts.cli
```

#### 2. "Failed to connect to MCP server" Error
```bash
# Check if server starts correctly
uv run python -m shared_context_server.scripts.cli --help

# Verify environment variables are set
echo "API_KEY: $API_KEY"
echo "JWT_SECRET_KEY: $JWT_SECRET_KEY"
echo "JWT_ENCRYPTION_KEY: $JWT_ENCRYPTION_KEY"
```

#### 3. Empty Results
```bash
# Check server capabilities
npx @modelcontextprotocol/inspector --cli --method tools/list \
  -e API_KEY=test-key -e JWT_SECRET_KEY=test-secret-key-for-jwt-signing-123456 -e JWT_ENCRYPTION_KEY=3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY= \
  uv run python -m shared_context_server.scripts.cli

# If tools list is empty, check server initialization
```

#### 4. Authentication Issues

**New in v1.1.10**: Standard MCP methods work without authentication!

```bash
# Test discovery methods (no authentication needed)
curl -X POST 'http://localhost:24456/mcp?sessionId=test' \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}'

# If discovery works but custom tools fail, authentication may be needed
# Test an authenticated tool (requires API_KEY)
curl -X POST 'http://localhost:24456/mcp?sessionId=test' \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-API-Key: your-api-key" \
  -d '{"jsonrpc": "2.0", "id": "2", "method": "create_session", "params": {"purpose": "test"}}'
```

**Expected Behavior:**
- ✅ `tools/list`, `resources/list`, `prompts/list` work without API key
- ❌ `create_session`, `add_message`, etc. require API key in `X-API-Key` header

### Diagnostic Commands

```bash
# 1. Basic connectivity test
npx @modelcontextprotocol/inspector --cli --method tools/list \
  -e API_KEY=test-key -e JWT_SECRET_KEY=test-secret-key-for-jwt-signing-123456 -e JWT_ENCRYPTION_KEY=3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY= \
  uv run python -m shared_context_server.scripts.cli | jq 'keys'

# 2. Check supported methods (from error messages)
npx @modelcontextprotocol/inspector --cli --method invalid/method \
  -e API_KEY=test-key -e JWT_SECRET_KEY=test-secret-key-for-jwt-signing-123456 -e JWT_ENCRYPTION_KEY=3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY= \
  uv run python -m shared_context_server.scripts.cli 2>&1 | grep "Supported methods"

# 3. Validate tool schemas
npx @modelcontextprotocol/inspector --cli --method tools/list \
  -e API_KEY=test-key -e JWT_SECRET_KEY=test-secret-key-for-jwt-signing-123456 -e JWT_ENCRYPTION_KEY=3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY= \
  uv run python -m shared_context_server.scripts.cli | jq '.tools[] | {name, hasInputSchema: (.inputSchema != null)}'
```

---

## Development Workflow

### Makefile Integration

Add these targets to your `Makefile`:

```makefile
.PHONY: inspect-tools inspect-resources inspect-prompts inspect-all

# Environment variables for MCP Inspector
INSPECTOR_ENV = -e API_KEY=test-key -e JWT_SECRET_KEY=test-secret-key-for-jwt-signing-123456 -e JWT_ENCRYPTION_KEY=3LBG8-a0Zs-JXO0cOiLCLhxrPXjL4tV5-qZ6H_ckGBY=
INSPECTOR_CMD = npx @modelcontextprotocol/inspector --cli $(INSPECTOR_ENV) uv run python -m shared_context_server.scripts.cli

inspect-tools:
	$(INSPECTOR_CMD) --method tools/list

inspect-resources:
	$(INSPECTOR_CMD) --method resources/templates/list

inspect-prompts:
	$(INSPECTOR_CMD) --method prompts/list

inspect-all: inspect-tools inspect-resources inspect-prompts
	@echo "✅ Complete server inspection completed"

# Tool-specific inspection
inspect-tool:
	@echo "Usage: make inspect-tool TOOL=tool_name"
	$(INSPECTOR_CMD) --method tools/list | jq --arg tool "$(TOOL)" '.tools[] | select(.name == $$tool)'

# Generate documentation from schemas
generate-tool-docs:
	$(INSPECTOR_CMD) --method tools/list > docs/generated/tools.json
	$(INSPECTOR_CMD) --method resources/templates/list > docs/generated/resources.json
	$(INSPECTOR_CMD) --method prompts/list > docs/generated/prompts.json
	@echo "📚 Generated fresh documentation in docs/generated/"
```

### Usage Examples

```bash
# Daily development workflow
make inspect-all                    # Get overview of all capabilities
make inspect-tool TOOL=add_message  # Check specific tool schema
make generate-tool-docs             # Update documentation

# Integration testing
make inspect-tools | jq '.tools | length'  # Check available tools
make inspect-resources | jq '.resourceTemplates[].uriTemplate'  # Check resource patterns
```

---

## Next Steps

### For LLM Agents
1. **Start with Discovery**: Always run the complete discovery workflow first
2. **Validate Schemas**: Check tool parameters before attempting to call them
3. **Use Resource Templates**: Leverage the URI patterns for dynamic resource access
4. **Test Incrementally**: Start with simple tools like `create_session` before complex workflows

### Integration Resources
- **[API Reference](./api-reference.md)** - Complete reference for all MCP tools
- **[Integration Guide](./integration-guide.md)** - Framework integration patterns
- **[Quick Reference](./quick-reference.md)** - Development commands and environment setup

### Advanced Usage
- **Resource Subscriptions**: Use resource templates for real-time updates
- **Prompt Templates**: Leverage built-in collaboration patterns
- **Performance Monitoring**: Use `get_performance_metrics` for optimization

---

`★ Expert Tip: The MCP Inspector provides the definitive, always-current view of server capabilities. Use it as your primary discovery tool rather than relying on static documentation.`
