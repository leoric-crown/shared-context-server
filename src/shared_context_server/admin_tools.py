"""
Administration and Monitoring Tools for Shared Context MCP Server.

Main facade module that maintains backward compatibility while delegating
to specialized submodules for better maintainability.

Provides MCP tools for system administration and monitoring:
- get_usage_guidance: Context-aware operational guidance based on access level
- get_performance_metrics: Comprehensive performance monitoring for admin users
- ResourceNotificationManager: Real-time resource update notifications
- Background tasks: Subscription cleanup and memory management

Built for production monitoring with admin-level security controls.
"""

# Import all public functions and classes to maintain 100% backward compatibility

# Import database functions that were previously available in admin_tools
# From admin_guidance.py - Guidance system
from .admin_guidance import (
    _generate_coordination_guidance,
    _generate_guidance_content,
    _generate_guidance_examples,
    _generate_operations_guidance,
    _generate_security_guidance,
    _generate_troubleshooting_guidance,
    _raise_session_not_found_error,
    _raise_unauthorized_access_error,
    audit_log,
    get_usage_guidance,
)

# From admin_lifecycle.py - Lifecycle and performance
from .admin_lifecycle import (
    cleanup_expired_memory_task,
    get_performance_metrics,
    lifespan,
    shutdown_server,
)

# From admin_resources.py - Resource management
from .admin_resources import (
    ResourceNotificationManager,
    cleanup_subscriptions_task,
    get_agent_memory_resource,
    get_session_resource,
    notification_manager,
    trigger_resource_notifications,
)

# Import auth functions that were previously available in admin_tools
from .auth import validate_agent_context_or_error
from .database import get_db_connection, initialize_database

# Export all public items for backward compatibility
__all__ = [
    # Database functions (previously available in admin_tools)
    "get_db_connection",
    "initialize_database",
    # Auth functions (previously available in admin_tools)
    "validate_agent_context_or_error",
    # Guidance system
    "get_usage_guidance",
    "_generate_guidance_content",
    "_generate_guidance_examples",
    "_generate_operations_guidance",
    "_generate_coordination_guidance",
    "_generate_security_guidance",
    "_generate_troubleshooting_guidance",
    "audit_log",
    "_raise_session_not_found_error",
    "_raise_unauthorized_access_error",
    # Resource management
    "ResourceNotificationManager",
    "notification_manager",
    "get_session_resource",
    "get_agent_memory_resource",
    "trigger_resource_notifications",
    "cleanup_subscriptions_task",
    # Lifecycle and performance
    "get_performance_metrics",
    "cleanup_expired_memory_task",
    "lifespan",
    "shutdown_server",
]
