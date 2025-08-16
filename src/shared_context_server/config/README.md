# Agent Permissions Configuration

This directory contains configuration files for defining agent types and their permissions in the Shared Context Server.

## Files

- `agent_permissions.json` - Default agent permissions configuration
- `agent_permissions_schema.json` - JSON schema for validating configurations
- `README.md` - This documentation file

## Configuration Format

### Environment Variable

Set the `PERMISSIONS_CONFIG_FILE` environment variable to specify a custom configuration file:

```bash
export PERMISSIONS_CONFIG_FILE=path/to/your/config.json
# or for relative paths (relative to this config directory):
export PERMISSIONS_CONFIG_FILE=agent_permissions.json
```

### JSON Structure

```json
{
  "description": "Agent permissions configuration",
  "version": "1.0.0",
  "config": {
    "available_permissions": ["read", "write", "admin", "debug"],
    "default_permissions": ["read"],
    "agent_types": {
      "agent_type_name": {
        "permissions": ["list", "of", "permissions"],
        "description": "Human readable description"
      }
    }
  }
}
```

### Available Permissions

The system supports these standard permissions:
- `read` - Read access to sessions and messages
- `write` - Write access to create sessions and messages
- `admin` - Administrative access to system functions
- `debug` - Debug capabilities for development

You can define custom permissions in your configuration file.

### Agent Types

Define agent types with their granted permissions:

```json
"agent_types": {
  "claude": {
    "permissions": ["read", "write"],
    "description": "Standard Claude agent"
  },
  "admin": {
    "permissions": ["read", "write", "admin", "debug"],
    "description": "Administrator with full access"
  },
  "readonly": {
    "permissions": ["read"],
    "description": "Read-only access agent"
  }
}
```

## Usage

### Programmatic Access

```python
from src.shared_context_server.config import get_agent_permissions_config

# Get configuration
config = get_agent_permissions_config()

# Get permissions for agent type
permissions = config.get_permissions_for_agent_type("claude")

# Get description
description = config.get_agent_type_description("claude")

# Generate documentation
docstring = config.generate_agent_types_docstring()
```

### Authentication

The `authenticate_agent` tool automatically uses the configuration:

```python
# Agent type determines permissions based on configuration
token = await authenticate_agent(
    agent_id="my-agent",
    agent_type="claude",  # Uses permissions from config
    requested_permissions=["read", "write", "admin"]  # Filtered by agent type
)
```

## Dynamic Documentation

The system automatically generates documentation from your configuration:

- The `authenticate_agent` tool's docstring updates based on configured agent types
- Field descriptions dynamically reflect available agent types
- Admin-capable agent types are automatically identified

## Validation

The configuration system includes comprehensive validation:

- Ensures all agent permissions are from `available_permissions`
- Validates that at least one agent type has admin permissions
- Checks JSON schema compliance (if using the schema file)
- Provides helpful error messages for configuration issues

## Examples

See `example_custom_permissions.json` in the repository root for an example of a custom configuration with specialized agent types like `data_scientist` and `researcher`.
