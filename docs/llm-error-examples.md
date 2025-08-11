# LLM-Optimized Error Messages - Examples & Best Practices

Complete reference for error messages optimized for AI agent understanding and recovery in the Shared Context MCP Server.

## Table of Contents

- [Error Response Structure](#error-response-structure)
- [Common Error Patterns](#common-error-patterns)
- [Authentication Errors](#authentication-errors)
- [Session Management Errors](#session-management-errors)
- [Message System Errors](#message-system-errors)
- [Search & Discovery Errors](#search--discovery-errors)
- [Memory System Errors](#memory-system-errors)
- [Coordination Errors](#coordination-errors)
- [Performance & Resource Errors](#performance--resource-errors)
- [Recovery Strategies](#recovery-strategies)

---

## Error Response Structure

All error responses follow a standardized structure optimized for LLM understanding:

```json
{
  "success": false,
  "error": "Clear, actionable description of what went wrong",
  "code": "SEMANTIC_ERROR_CODE",
  "severity": "warning|error|critical",
  "recoverable": true,
  "suggestions": [
    "Specific action 1 to resolve the issue",
    "Alternative approach 2 if action 1 fails",
    "Context about why this error occurred"
  ],
  "context": {
    "relevant_field": "value that caused the error",
    "expected_format": "what was expected",
    "additional_info": "helpful context for decision making"
  },
  "retry_after": 5,
  "related_resources": [
    "create_session",
    "authenticate_agent"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Error Severity Levels

- **warning**: Non-critical, operation may continue with adjustments
- **error**: Operation failed, retry possible with corrections
- **critical**: System issue requiring immediate attention or admin intervention

---

## Common Error Patterns

### Input Validation Errors

**Pattern**: Invalid parameter format or value

```json
{
  "success": false,
  "error": "Invalid session_id format. Expected session_[16-hex-characters]",
  "code": "INVALID_INPUT_FORMAT",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Check the session_id parameter format",
    "Expected format: session_ followed by 16 hexadecimal characters",
    "Use create_session to generate a valid session ID",
    "Example valid session_id: session_a1b2c3d4e5f6g7h8"
  ],
  "context": {
    "invalid_field": "session_id",
    "provided_value": "invalid_session_123",
    "expected_format": "session_[16-hex-chars]",
    "regex_pattern": "^session_[a-f0-9]{16}$"
  },
  "related_resources": [
    "create_session"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**LLM Recovery Pattern**: Parse the expected format from suggestions and context, then either correct the parameter or call the suggested resource.

### Resource Not Found Errors

**Pattern**: Requested resource does not exist

```json
{
  "success": false,
  "error": "Session 'session_nonexistent123' not found",
  "code": "SESSION_NOT_FOUND",
  "severity": "error",
  "recoverable": true,
  "suggestions": [
    "Verify the session_id is correct",
    "Use create_session to create a new session",
    "Check if session was deleted or expired",
    "Available active sessions: session_abc123def456, session_xyz789uvw012"
  ],
  "context": {
    "resource_type": "session",
    "resource_id": "session_nonexistent123",
    "available_alternatives": [
      "session_abc123def456",
      "session_xyz789uvw012",
      "session_mno345pqr678"
    ],
    "total_active_sessions": 3
  },
  "related_resources": [
    "create_session",
    "list_sessions"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**LLM Recovery Pattern**: Either create a new resource using suggested tools or select from available alternatives in context.

---

## Authentication Errors

### Invalid API Key

```json
{
  "success": false,
  "error": "Invalid API key provided. Authentication failed",
  "code": "INVALID_API_KEY",
  "severity": "error",
  "recoverable": false,
  "suggestions": [
    "Check that your API key is correct and not expired",
    "Obtain a valid API key from the system administrator",
    "Ensure API key is included in authentication request",
    "Contact support if you believe this is an error"
  ],
  "context": {
    "authentication_method": "api_key",
    "key_length": 12,
    "expected_min_length": 16,
    "error_type": "invalid_format"
  },
  "related_resources": [
    "authenticate_agent"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Expired JWT Token

```json
{
  "success": false,
  "error": "JWT token has expired. Please re-authenticate",
  "code": "TOKEN_EXPIRED",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Call authenticate_agent to get a new token",
    "Store the new token for subsequent requests",
    "Consider implementing automatic token refresh",
    "Check token expiration before making requests"
  ],
  "context": {
    "expired_at": "2025-01-15T10:25:00Z",
    "current_time": "2025-01-15T10:30:00Z",
    "time_since_expiry": "5 minutes",
    "agent_id": "claude-main"
  },
  "related_resources": [
    "authenticate_agent"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Insufficient Permissions

```json
{
  "success": false,
  "error": "Admin permission required for this operation",
  "code": "PERMISSION_DENIED",
  "severity": "error",
  "recoverable": false,
  "suggestions": [
    "Request admin privileges from the user or system administrator",
    "Use operations that require lower permissions",
    "Check agent authentication and role assignment",
    "Available alternatives: use 'public' or 'private' visibility instead"
  ],
  "context": {
    "required_permission": "admin",
    "current_permissions": ["read", "write"],
    "missing_permissions": ["admin"],
    "operation_attempted": "set_message_visibility",
    "requested_visibility": "admin_only"
  },
  "related_resources": [
    "authenticate_agent",
    "get_agent_permissions"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Session Management Errors

### Session Creation Validation

```json
{
  "success": false,
  "error": "Session purpose cannot be empty after sanitization",
  "code": "INVALID_INPUT",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Provide a descriptive purpose for the session",
    "Purpose should describe the collaboration goal clearly",
    "Example: 'Feature planning for user authentication system'",
    "Avoid whitespace-only or empty purpose strings"
  ],
  "context": {
    "field": "purpose",
    "requirement": "non_empty_string",
    "provided_length": 0,
    "after_sanitization": true,
    "min_length": 1,
    "max_length": 500
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Session Capacity Limits

```json
{
  "success": false,
  "error": "Maximum active sessions limit reached (50 sessions). Clean up unused sessions",
  "code": "SESSION_LIMIT_EXCEEDED",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Review and close unused active sessions",
    "Use coordinate_session_work to properly end collaboration",
    "Consider session cleanup after task completion",
    "Contact administrator if limit needs to be increased"
  ],
  "context": {
    "current_active_sessions": 50,
    "max_allowed_sessions": 50,
    "agent_sessions": 12,
    "oldest_session_age": "3 days",
    "recommended_action": "cleanup_old_sessions"
  },
  "related_resources": [
    "coordinate_session_work",
    "list_sessions"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Message System Errors

### Content Validation

```json
{
  "success": false,
  "error": "Message content too large (15,247 characters). Maximum allowed: 10,000",
  "code": "CONTENT_TOO_LARGE",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Reduce message content length to under 10,000 characters",
    "Split large content into multiple messages",
    "Use file attachments for large data instead of inline content",
    "Consider summarizing the content for better collaboration"
  ],
  "context": {
    "content_size": 15247,
    "max_allowed": 10000,
    "excess_characters": 5247,
    "suggested_split": 2,
    "truncation_preview": "Content starts with: 'Here is the detailed analysis...'"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Visibility Conflicts

```json
{
  "success": false,
  "error": "Cannot set message visibility to 'admin_only' without admin permission",
  "code": "VISIBILITY_PERMISSION_DENIED",
  "severity": "error",
  "recoverable": true,
  "suggestions": [
    "Use 'public' or 'private' visibility levels instead",
    "Request admin privileges if admin_only visibility is required",
    "Consider 'private' visibility for sensitive information",
    "Use 'agent_only' to restrict to same agent type"
  ],
  "context": {
    "requested_visibility": "admin_only",
    "allowed_visibilities": ["public", "private", "agent_only"],
    "current_permissions": ["read", "write"],
    "required_permission": "admin",
    "agent_type": "claude"
  },
  "related_resources": [
    "authenticate_agent",
    "add_message"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Search & Discovery Errors

### Search Query Validation

```json
{
  "success": false,
  "error": "Search query too short. Minimum 3 characters required for effective fuzzy matching",
  "code": "INVALID_SEARCH_QUERY",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Provide a search query with at least 3 characters",
    "Use more specific search terms for better results",
    "Consider using exact phrases in quotes for precise matching",
    "Example: 'authentication' or 'user login system'"
  ],
  "context": {
    "query_length": 2,
    "min_required_length": 3,
    "provided_query": "ab",
    "fuzzy_threshold": 70.0,
    "search_scope": "session"
  },
  "related_resources": [
    "search_context"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Search Performance Limits

```json
{
  "success": false,
  "error": "Search limit exceeds maximum allowed (150 > 100). Reduce limit for better performance",
  "code": "SEARCH_LIMIT_EXCEEDED",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Reduce search limit to 100 or fewer results",
    "Use more specific search terms to get relevant results",
    "Consider pagination for large result sets",
    "Use higher fuzzy_threshold to filter results"
  ],
  "context": {
    "requested_limit": 150,
    "max_allowed_limit": 100,
    "recommended_limit": 25,
    "expected_results": "~80 based on query",
    "performance_impact": "high"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Memory System Errors

### Memory Key Validation

```json
{
  "success": false,
  "error": "Memory key contains invalid characters. Keys cannot contain spaces, newlines, or tabs",
  "code": "INVALID_KEY",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Use underscore or dash separators instead of spaces",
    "Example: 'user_preferences' instead of 'user preferences'",
    "Keys should contain only alphanumeric characters, underscores, and dashes",
    "Avoid special characters: spaces, newlines, tabs, quotes"
  ],
  "context": {
    "invalid_key": "user preferences",
    "suggested_key": "user_preferences",
    "allowed_characters": "alphanumeric, underscore, dash",
    "invalid_characters_found": ["space"],
    "key_length": 16
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Memory Storage Limits

```json
{
  "success": false,
  "error": "Agent memory storage limit exceeded (105MB used, 100MB limit)",
  "code": "MEMORY_LIMIT_EXCEEDED",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Remove unused memory entries with delete operations",
    "Set shorter TTL values for temporary data",
    "Use session-scoped memory instead of global memory for temporary data",
    "Contact administrator if limit needs to be increased"
  ],
  "context": {
    "current_usage_mb": 105.2,
    "limit_mb": 100.0,
    "excess_mb": 5.2,
    "global_entries": 25,
    "session_entries": 12,
    "recommended_action": "cleanup_old_entries",
    "largest_entries": [
      {"key": "large_dataset", "size_mb": 15.2},
      {"key": "cached_analysis", "size_mb": 8.7}
    ]
  },
  "related_resources": [
    "list_memory",
    "delete_memory",
    "get_memory_usage"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Coordination Errors

### Session Locking Conflicts

```json
{
  "success": false,
  "error": "Session is currently locked by another agent. Cannot acquire write lock",
  "code": "SESSION_LOCKED",
  "severity": "warning",
  "recoverable": true,
  "retry_after": 30,
  "suggestions": [
    "Wait for current lock holder to complete their operation",
    "Check lock status with coordinate_session_work status query",
    "Consider read-only operations if write access is not required",
    "Retry after 30 seconds when lock may be released"
  ],
  "context": {
    "session_id": "session_abc123def456",
    "lock_type": "write",
    "lock_holder": "developer-agent",
    "lock_acquired_at": "2025-01-15T10:28:00Z",
    "lock_duration_seconds": 120,
    "estimated_release": "2025-01-15T10:32:00Z",
    "queue_position": 2
  },
  "related_resources": [
    "coordinate_session_work"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Agent Presence Conflicts

```json
{
  "success": false,
  "error": "Cannot register as 'active' - agent already registered with different status",
  "code": "PRESENCE_CONFLICT",
  "severity": "warning",
  "recoverable": true,
  "suggestions": [
    "Check current agent presence status first",
    "Update existing presence instead of registering new",
    "Use force_update flag to override existing presence",
    "Consider if multiple agent instances are running"
  ],
  "context": {
    "agent_id": "claude-main",
    "requested_status": "active",
    "current_status": "busy",
    "last_updated": "2025-01-15T10:25:00Z",
    "status_duration": "5 minutes",
    "can_force_update": true
  },
  "related_resources": [
    "register_agent_presence",
    "get_agent_presence"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Performance & Resource Errors

### Database Performance Issues

```json
{
  "success": false,
  "error": "Database operation timed out (10.5s). System may be under high load",
  "code": "DATABASE_TIMEOUT",
  "severity": "error",
  "recoverable": true,
  "retry_after": 5,
  "suggestions": [
    "Retry the operation in a few seconds",
    "Check system performance with get_performance_metrics",
    "Consider reducing operation complexity",
    "Contact administrator if timeouts persist"
  ],
  "context": {
    "operation": "message_search",
    "timeout_seconds": 10.5,
    "max_timeout": 10.0,
    "system_load": "high",
    "connection_pool_usage": "85%",
    "recent_slow_queries": 5
  },
  "related_resources": [
    "get_performance_metrics"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Connection Pool Exhaustion

```json
{
  "success": false,
  "error": "Database connection pool exhausted (50/50 connections in use). Temporary system overload",
  "code": "CONNECTION_POOL_EXHAUSTED",
  "severity": "error",
  "recoverable": true,
  "retry_after": 3,
  "suggestions": [
    "Retry the operation in a few seconds",
    "Reduce concurrent operations if possible",
    "Check for connection leaks in long-running operations",
    "Contact administrator to increase pool size if needed"
  ],
  "context": {
    "pool_size": 50,
    "active_connections": 50,
    "queued_requests": 5,
    "avg_connection_time": "2.5s",
    "pool_utilization": 1.0,
    "recommended_pool_size": 75
  },
  "related_resources": [
    "get_performance_metrics"
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Recovery Strategies

### Automatic Recovery Patterns

**1. Token Refresh Pattern**
```python
async def handle_token_error(error_response):
    """Handle expired token errors automatically."""
    if error_response.get("code") == "TOKEN_EXPIRED":
        # Re-authenticate automatically
        new_token = await authenticate_agent(agent_id, api_key)
        # Retry original operation with new token
        return await retry_with_token(new_token)
```

**2. Resource Creation Pattern**
```python
async def handle_not_found_error(error_response):
    """Handle resource not found by creating if possible."""
    if error_response.get("code") == "SESSION_NOT_FOUND":
        suggested_tools = error_response.get("related_resources", [])
        if "create_session" in suggested_tools:
            # Create session based on context
            new_session = await create_session(purpose="Auto-created session")
            return new_session["session_id"]
```

**3. Parameter Correction Pattern**
```python
def correct_parameter_format(error_response):
    """Correct parameter format based on error context."""
    context = error_response.get("context", {})
    if context.get("expected_format"):
        # Parse expected format and correct parameter
        expected = context["expected_format"]
        if expected == "session_[16-hex-chars]":
            return f"session_{generate_hex_string(16)}"
```

### LLM Decision Trees

**Session Management Decision Tree**:
1. Session not found → Check alternatives in context → Create new session
2. Session locked → Check retry_after → Wait and retry
3. Permission denied → Check alternatives → Use lower privilege operation

**Authentication Decision Tree**:
1. Invalid credentials → Get new credentials → Re-authenticate
2. Token expired → Re-authenticate with same credentials
3. Permission denied → Request higher permissions or use alternatives

**Content Validation Decision Tree**:
1. Content too large → Split into multiple messages
2. Invalid format → Correct format based on context
3. Empty content → Provide meaningful content

### Error Context Utilization

**Using Available Alternatives**:
```python
def select_alternative_resource(error_response):
    """Select from available alternatives in error context."""
    context = error_response.get("context", {})
    alternatives = context.get("available_alternatives", [])

    if alternatives:
        # Select first available alternative
        return alternatives[0]

    # Fallback to creating new resource
    related_resources = error_response.get("related_resources", [])
    if "create_session" in related_resources:
        return "create_new"
```

**Adjusting Based on Limits**:
```python
def adjust_for_limits(error_response):
    """Adjust parameters based on limit information."""
    context = error_response.get("context", {})

    if "max_allowed" in context and "content_size" in context:
        max_size = context["max_allowed"]
        # Truncate content to fit within limits
        return truncate_content(max_size * 0.9)  # 90% of limit for safety
```

---

## Best Practices for LLM Error Handling

### 1. Always Check Error Structure
- Verify `success: false` before processing error
- Extract `code` for programmatic handling
- Use `severity` to determine response urgency

### 2. Prioritize Suggestions
- Follow suggestions in order provided
- Use `related_resources` for alternative approaches
- Consider `retry_after` for timing-sensitive operations

### 3. Utilize Context Information
- Extract parameter corrections from `context`
- Use `available_alternatives` when provided
- Adjust based on limit and capacity information

### 4. Implement Appropriate Retry Logic
- Respect `retry_after` timing
- Implement exponential backoff for system errors
- Avoid retrying non-recoverable errors

### 5. Graceful Degradation
- Use alternative operations when permissions insufficient
- Provide meaningful fallbacks for failed operations
- Maintain user experience despite errors

This comprehensive error handling guide enables AI agents to understand, interpret, and recover from errors effectively in the Shared Context MCP Server environment.
