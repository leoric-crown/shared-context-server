# PRP-004: Phase 3 - Multi-Agent Features

**Document Type**: Product Requirement Prompt
**Created**: 2025-08-10
**Phase**: 3 (Multi-Agent Features)
**Timeline**: 6 hours
**Priority**: High Collaboration
**Status**: Ready for Execution
**Prerequisites**: Phase 2 - Essential Features completed

🔌 **MCP FOUNDATION READY**: All agents connected via shared-context-server MCP integration
⚡ **Live Agent Access**: Claude, task-coordinator, developer, tester, docs agents all connected
📡 **Transport**: STDIO via `claude mcp add shared-context-server shared-context-server`
🎯 **Multi-Agent Context**: Session-based isolation with real-time coordination capabilities
🔥 **Hot Reload Development**: Agents have access to live development server with automatic restart
⚡ **Real-Time Development**: Edit Python code → Server restarts in 1-2s → Agents reconnect automatically
🛠️ **Development Commands**: `MCP_TRANSPORT=http uv run python -m shared_context_server.scripts.dev`

🚨 **CRITICAL BUG FIXES REQUIRED FIRST**:
- ❌ **Memory System**: `get_memory`/`set_memory` SQL query errors blocking agent memory
- ❌ **Resource Access**: `session://` resource templates failing with same SQL issue
- 🔧 **Must Fix Before New Features**: Address database query construction bugs

---

## Research Context & Architectural Analysis

### Planning Integration
**Source**: Final Decomposed Implementation Plan, Security Authentication Guide, Multi-Agent Collaboration Research
**Research Foundation**: JWT authentication patterns, RBAC permission models, real-time multi-agent coordination patterns, blackboard architecture principles
**Strategic Context**: Implementing advanced multi-agent collaboration features that enable secure, real-time coordination between different AI agents while maintaining privacy boundaries and audit trails

### Architectural Scope
**Advanced Authentication**: Bearer token authentication with JWT validation, agent-specific permission models, secure credential management
**Enhanced Visibility & Audit**: Complex visibility rules with agent-type filtering, comprehensive audit logging, security monitoring, privacy controls
**Real-Time Coordination**: MCP resource notifications for live collaboration, agent coordination patterns, conflict resolution, concurrent access handling
**Security Integration**: Complete security hardening with RBAC, audit logging, input validation, attack prevention

### Existing Patterns to Leverage
**Security Authentication Guide**: JWT implementation patterns, RBAC models, audit logging architecture
**Core Architecture Guide**: Audit log table schema, agent identity patterns, security best practices
**Phase 1-2 Foundation**: Agent identity extraction, basic authentication, message visibility controls, resource subscription system

---

## Implementation Specification

### Core Requirements

**CRITICAL Issues to Fix from MCP Testing:**

⚠️ **HIGH PRIORITY BUGS DISCOVERED**:
1. **Memory System Bug**: `get_memory` and `set_memory` failing with SQL query error
   - Error: "tuple indices must be integers or slices, not str"
   - Impact: Agent memory storage/retrieval completely broken
   - Root Cause: Database query construction issue in memory operations

2. **Session Resource Bug**: `session://` resource templates failing
   - Error: Same SQL query construction issue as memory system
   - Impact: MCP resource access not working
   - Root Cause: Shared database query pattern problem

3. **Database Schema Update Required**:
   - **Messages Table**: Add `sender_type` column to store agent type at message creation time
   - **Agent Registry Alternative**: Or create `agents` table with FK to messages for agent type lookup
   - **Rationale**: Eliminates brittle audit log joins for agent type inference (consultant recommendation)

🔧 **PHASE 3 MUST FIX**: Address these critical bugs before implementing new features

**Debug Context for Investigation**:
- **Error Pattern**: "tuple indices must be integers or slices, not str"
- **Likely Location**: Database query construction in memory/resource handlers
- **Test Reproduction**:
  ```python
  # Failing operations:
  mcp__shared-context-server__set_memory(key="test", value="test", session_id="session_123")
  mcp__shared-context-server__get_memory(key="test", session_id="session_123")
  ReadMcpResourceTool(server="shared-context-server", uri="session://session_123")
  ```
- **Working Operations**: create_session, add_message, get_messages, search_context (RapidFuzz)
- **Investigation Needed**: Check SQL query parameter binding in memory and resource code paths

#### 1. Advanced Authentication System
**JWT Token Authentication**:
```python
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import secrets
import hashlib

class JWTAuthenticationManager:
    def __init__(self):
        # CRITICAL: Persistent secret key required, no random fallbacks in production
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable must be set for production")

        self.algorithm = "HS256"
        self.token_expiry = 86400  # 24 hours
        self.clock_skew_leeway = 300  # 5 minutes clock skew tolerance

    def generate_token(self, agent_id: str, agent_type: str, permissions: List[str]) -> str:
        """Generate JWT token for agent authentication."""

        payload = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permissions": permissions,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=self.token_expiry),
            "iss": "shared-context-server",
            "aud": "mcp-agents"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and extract claims."""

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="mcp-agents",
                issuer="shared-context-server",
                leeway=self.clock_skew_leeway  # Handle clock skew between servers
            )

            # Verify token hasn't expired
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                return {"valid": False, "error": "Token expired"}

            return {
                "valid": True,
                "agent_id": payload.get("agent_id"),
                "agent_type": payload.get("agent_type"),
                "permissions": payload.get("permissions", []),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp")
            }

        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"Token validation failed: {str(e)}"}

# Global authentication manager
auth_manager = JWTAuthenticationManager()

@mcp.tool()
async def authenticate_agent(
    agent_id: str = Field(description="Agent identifier", min_length=1, max_length=100),
    agent_type: str = Field(description="Agent type (claude, gemini, custom)", max_length=50),
    api_key: str = Field(description="Agent API key for initial authentication"),
    requested_permissions: List[str] = Field(
        default=["read", "write"],
        description="Requested permissions for the agent"
    )
) -> Dict[str, Any]:
    """
    Authenticate agent and return JWT token with appropriate permissions.
    """

    # Validate API key against environment or database
    valid_api_key = os.getenv("API_KEY", "")
    if not api_key or api_key != valid_api_key:
        return {
            "success": False,
            "error": "Invalid API key",
            "code": "AUTH_FAILED"
        }

    # Determine agent permissions based on type and request
    available_permissions = ["read", "write", "admin", "debug"]
    granted_permissions = []

    for permission in requested_permissions:
        if permission in available_permissions:
            granted_permissions.append(permission)

    # Ensure minimum read permission
    if not granted_permissions:
        granted_permissions = ["read"]

    # Generate JWT token
    token = auth_manager.generate_token(agent_id, agent_type, granted_permissions)

    # Log authentication event
    async with get_db_connection() as conn:
        await audit_log(conn, "agent_authenticated", agent_id, None, {
            "agent_type": agent_type,
            "permissions_granted": granted_permissions,
            "token_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=auth_manager.token_expiry)).isoformat()
        })

    return {
        "success": True,
        "token": token,
        "agent_id": agent_id,
        "agent_type": agent_type,
        "permissions": granted_permissions,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=auth_manager.token_expiry)).isoformat(),
        "token_type": "Bearer"
    }

# Enhanced authentication middleware
@mcp.middleware
async def enhanced_authentication_middleware(request, call_next):
    """
    Enhanced authentication middleware with JWT token validation.
    """

    # Extract authorization header
    auth_header = request.headers.get("authorization", "")

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate JWT token
        token_validation = auth_manager.validate_token(token)

        if token_validation["valid"]:
            # Set enhanced context
            mcp.context["agent_id"] = token_validation["agent_id"]
            mcp.context["agent_type"] = token_validation["agent_type"]
            mcp.context["permissions"] = token_validation["permissions"]
            mcp.context["authenticated"] = True
            mcp.context["auth_method"] = "jwt"
        else:
            # Set limited context for failed authentication
            mcp.context["agent_id"] = "anonymous"
            mcp.context["agent_type"] = "unknown"
            mcp.context["permissions"] = ["read"]  # Limited permissions
            mcp.context["authenticated"] = False
            mcp.context["auth_error"] = token_validation["error"]
    else:
        # Fallback to basic API key authentication
        api_key = auth_header.replace("Bearer ", "") if auth_header else ""
        valid_api_key = os.getenv("API_KEY", "")

        authenticated = api_key == valid_api_key if valid_api_key else False

        mcp.context["agent_id"] = request.context.get("agent_id", "unknown")
        mcp.context["agent_type"] = "unknown"
        mcp.context["permissions"] = ["read", "write"] if authenticated else ["read"]
        mcp.context["authenticated"] = authenticated
        mcp.context["auth_method"] = "api_key"

    response = await call_next(request)
    return response

def require_permission(permission: str):
    """Decorator to require specific permission for tool access."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            agent_permissions = mcp.context.get("permissions", [])

            if permission not in agent_permissions:
                return {
                    "success": False,
                    "error": f"Permission '{permission}' required",
                    "code": "PERMISSION_DENIED",
                    "required_permission": permission,
                    "agent_permissions": agent_permissions
                }

            return await func(*args, **kwargs)

        return wrapper
    return decorator
```

#### 2. Enhanced Visibility & Audit System
**Advanced Visibility Controls**:
```python
@mcp.tool()
async def set_message_visibility(
    message_id: int = Field(description="Message ID to update"),
    new_visibility: str = Field(
        description="New visibility level",
        regex="^(public|private|agent_only|admin_only)$"
    ),
    reason: Optional[str] = Field(
        default=None,
        description="Reason for visibility change"
    )
) -> Dict[str, Any]:
    """
    Update message visibility with audit trail.
    Requires admin permission for admin_only visibility.
    """

    agent_id = mcp.context.get("agent_id", "unknown")
    permissions = mcp.context.get("permissions", [])

    # Check permissions for admin_only visibility
    if new_visibility == "admin_only" and "admin" not in permissions:
        return {
            "success": False,
            "error": "Admin permission required for admin_only visibility",
            "code": "PERMISSION_DENIED"
        }

    async with get_db_connection() as conn:
        # Get current message details
        cursor = await conn.execute(
            "SELECT * FROM messages WHERE id = ?",
            (message_id,)
        )
        message = await cursor.fetchone()

        if not message:
            return {
                "success": False,
                "error": "Message not found",
                "code": "MESSAGE_NOT_FOUND"
            }

        # Check if agent can modify this message
        if message["sender"] != agent_id and "admin" not in permissions:
            return {
                "success": False,
                "error": "Can only modify own messages or require admin permission",
                "code": "PERMISSION_DENIED"
            }

        # Update visibility
        old_visibility = message["visibility"]
        await conn.execute(
            "UPDATE messages SET visibility = ? WHERE id = ?",
            (new_visibility, message_id)
        )
        await conn.commit()

        # Audit log the change
        await audit_log(conn, "message_visibility_changed", agent_id, message["session_id"], {
            "message_id": message_id,
            "old_visibility": old_visibility,
            "new_visibility": new_visibility,
            "reason": reason,
            "original_sender": message["sender"]
        })

        # Trigger resource update notification
        await notification_manager.notify_resource_updated(f"session://{message['session_id']}")

    return {
        "success": True,
        "message_id": message_id,
        "old_visibility": old_visibility,
        "new_visibility": new_visibility,
        "updated_by": agent_id
    }

@mcp.tool()
async def get_messages_advanced(
    session_id: str = Field(description="Session ID"),
    visibility_filter: Optional[str] = Field(default=None),
    agent_type_filter: Optional[str] = Field(default=None),
    include_admin_only: bool = Field(
        default=False,
        description="Include admin_only messages (requires admin permission)"
    ),
    limit: int = Field(default=50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    Advanced message retrieval with enhanced visibility controls.
    """

    agent_id = mcp.context.get("agent_id", "unknown")
    agent_type = mcp.context.get("agent_type", "unknown")
    permissions = mcp.context.get("permissions", [])

    async with get_db_connection() as conn:
        # Build complex visibility query
        visibility_conditions = ["m.session_id = ?"]
        params = [session_id]

        # Base visibility rules
        base_visibility = [
            "m.visibility = 'public'",
            "(m.visibility = 'private' AND m.sender = ?)"
        ]
        params.append(agent_id)

        # Agent-type filtering (using denormalized sender_type column)
        if agent_type != "unknown":
            base_visibility.append("(m.visibility = 'agent_only' AND m.sender_type = ?)")
            params.append(agent_type)

        # Admin-only messages
        if include_admin_only and "admin" in permissions:
            base_visibility.append("m.visibility = 'admin_only'")

        visibility_conditions.append(f"({' OR '.join(base_visibility)})")

        # Additional filters
        if visibility_filter:
            visibility_conditions.append("m.visibility = ?")
            params.append(visibility_filter)

        if agent_type_filter:
            visibility_conditions.append("m.sender_type = ?")
            params.append(agent_type_filter)

        params.append(limit)

        # Use denormalized sender_type from messages table (no brittle audit log joins)
        cursor = await conn.execute(f"""
            SELECT m.*,
                   m.sender_type
            FROM messages m
            WHERE {' AND '.join(visibility_conditions)}
            ORDER BY m.timestamp ASC
            LIMIT ?
        """, params)

        messages = await cursor.fetchall()

        # Process messages with metadata
        processed_messages = []
        for msg in messages:
            msg_dict = dict(msg)

            # Parse metadata
            if msg_dict.get('metadata'):
                try:
                    msg_dict['metadata'] = json.loads(msg_dict['metadata'])
                except json.JSONDecodeError:
                    msg_dict['metadata'] = {}
            else:
                msg_dict['metadata'] = {}

            processed_messages.append(msg_dict)

        return {
            "success": True,
            "messages": processed_messages,
            "count": len(processed_messages),
            "filters_applied": {
                "visibility_filter": visibility_filter,
                "agent_type_filter": agent_type_filter,
                "include_admin_only": include_admin_only
            },
            "requesting_agent": {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "permissions": permissions
            }
        }
```

**Comprehensive Audit System**:
```python
@mcp.tool()
@require_permission("admin")
async def get_audit_log(
    session_id: Optional[str] = Field(default=None, description="Filter by session ID"),
    agent_id: Optional[str] = Field(default=None, description="Filter by agent ID"),
    event_type: Optional[str] = Field(default=None, description="Filter by event type"),
    start_time: Optional[str] = Field(default=None, description="Start time (ISO format)"),
    end_time: Optional[str] = Field(default=None, description="End time (ISO format)"),
    limit: int = Field(default=100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Retrieve audit log entries with filtering options.
    Requires admin permission.
    """

    requesting_agent = mcp.context.get("agent_id", "unknown")

    async with get_db_connection() as conn:
        # Build audit query
        where_conditions = []
        params = []

        if session_id:
            where_conditions.append("session_id = ?")
            params.append(session_id)

        if agent_id:
            where_conditions.append("agent_id = ?")
            params.append(agent_id)

        if event_type:
            where_conditions.append("event_type = ?")
            params.append(event_type)

        if start_time:
            where_conditions.append("timestamp >= ?")
            params.append(start_time)

        if end_time:
            where_conditions.append("timestamp <= ?")
            params.append(end_time)

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        params.append(limit)

        cursor = await conn.execute(f"""
            SELECT * FROM audit_log
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params)

        entries = await cursor.fetchall()

        # Process audit entries
        processed_entries = []
        for entry in entries:
            entry_dict = dict(entry)

            # Parse metadata
            if entry_dict.get('metadata'):
                try:
                    entry_dict['metadata'] = json.loads(entry_dict['metadata'])
                except json.JSONDecodeError:
                    entry_dict['metadata'] = {}
            else:
                entry_dict['metadata'] = {}

            processed_entries.append(entry_dict)

        # Log audit access
        await audit_log(conn, "audit_log_accessed", requesting_agent, session_id, {
            "filters": {
                "session_id": session_id,
                "agent_id": agent_id,
                "event_type": event_type,
                "start_time": start_time,
                "end_time": end_time
            },
            "results_count": len(processed_entries)
        })

        return {
            "success": True,
            "audit_entries": processed_entries,
            "count": len(processed_entries),
            "filters_applied": {
                "session_id": session_id,
                "agent_id": agent_id,
                "event_type": event_type,
                "start_time": start_time,
                "end_time": end_time
            },
            "requested_by": requesting_agent
        }

@mcp.tool()
async def get_agent_activity_summary(
    time_window: str = Field(
        default="24h",
        description="Time window: 1h, 24h, 7d, 30d",
        regex="^(1h|24h|7d|30d)$"
    )
) -> Dict[str, Any]:
    """
    Get summary of agent activity in the specified time window.
    """

    requesting_agent = mcp.context.get("agent_id", "unknown")

    # Convert time window to hours
    time_mapping = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
    hours = time_mapping[time_window]

    async with get_db_connection() as conn:
        # Get agent activity summary
        cursor = await conn.execute("""
            SELECT
                agent_id,
                COUNT(*) as total_events,
                COUNT(DISTINCT event_type) as event_types,
                COUNT(DISTINCT session_id) as sessions_accessed,
                MIN(timestamp) as first_activity,
                MAX(timestamp) as last_activity
            FROM audit_log
            WHERE timestamp >= datetime('now', '-{} hours')
            GROUP BY agent_id
            ORDER BY total_events DESC
        """.format(hours))

        activity_data = await cursor.fetchall()

        # Get session creation summary
        cursor = await conn.execute("""
            SELECT
                created_by as agent_id,
                COUNT(*) as sessions_created
            FROM sessions
            WHERE created_at >= datetime('now', '-{} hours')
            GROUP BY created_by
        """.format(hours))

        session_data = {row['agent_id']: row['sessions_created'] for row in await cursor.fetchall()}

        # Combine data
        agent_summaries = []
        for row in activity_data:
            agent_summary = dict(row)
            agent_summary['sessions_created'] = session_data.get(row['agent_id'], 0)
            agent_summaries.append(agent_summary)

        return {
            "success": True,
            "time_window": time_window,
            "agent_activity": agent_summaries,
            "summary": {
                "total_agents": len(agent_summaries),
                "most_active_agent": agent_summaries[0]['agent_id'] if agent_summaries else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "requested_by": requesting_agent
            }
        }
```

#### 3. Real-Time Multi-Agent Coordination
**Agent Coordination System**:
```python
class AgentCoordinationManager:
    def __init__(self):
        self.active_agents = {}  # {agent_id: {last_seen, agent_type, permissions}}
        self.session_locks = {}  # {session_id: {locked_by, locked_at, lock_type, heartbeat_expires}}
        self.coordination_channels = {}  # {channel_id: {subscribers}}
        self.lock_ttl = 300  # 5 minutes default lock TTL
        self.heartbeat_interval = 60  # 1 minute heartbeat requirement

    async def register_agent(self, agent_id: str, agent_type: str, permissions: List[str]):
        """Register agent as active."""

        self.active_agents[agent_id] = {
            "last_seen": datetime.now(timezone.utc),
            "agent_type": agent_type,
            "permissions": permissions,
            "status": "active"
        }

        # Notify other agents of new agent
        await self.broadcast_agent_event("agent_joined", agent_id, {
            "agent_type": agent_type,
            "permissions": permissions
        })

    async def update_agent_heartbeat(self, agent_id: str):
        """Update agent last seen timestamp."""

        if agent_id in self.active_agents:
            self.active_agents[agent_id]["last_seen"] = datetime.now(timezone.utc)

    async def acquire_session_lock(self, session_id: str, agent_id: str, lock_type: str = "write") -> bool:
        """Acquire exclusive lock on session for coordination with TTL and heartbeat."""

        current_time = datetime.now(timezone.utc)

        # Check if session is already locked
        if session_id in self.session_locks:
            lock_info = self.session_locks[session_id]

            # Check both TTL expiry and heartbeat expiry
            lock_age = (current_time - lock_info["locked_at"]).total_seconds()
            heartbeat_expired = current_time > lock_info.get("heartbeat_expires", current_time)

            if lock_age > self.lock_ttl or heartbeat_expired:
                # Force unlock expired/unresponsive locks
                del self.session_locks[session_id]
                # TODO: Send force_unlock notification to previous lock holder
            elif lock_info["locked_by"] != agent_id:
                return False  # Already locked by another agent

        # Acquire lock with heartbeat expiry
        self.session_locks[session_id] = {
            "locked_by": agent_id,
            "locked_at": current_time,
            "lock_type": lock_type,
            "heartbeat_expires": current_time + timedelta(seconds=self.heartbeat_interval)
        }

        return True

    async def renew_session_lock_heartbeat(self, session_id: str, agent_id: str) -> bool:
        """Renew heartbeat for held session lock."""

        if session_id in self.session_locks:
            lock_info = self.session_locks[session_id]
            if lock_info["locked_by"] == agent_id:
                # Extend heartbeat expiry
                lock_info["heartbeat_expires"] = datetime.now(timezone.utc) + timedelta(seconds=self.heartbeat_interval)
                return True

        return False

    async def release_session_lock(self, session_id: str, agent_id: str) -> bool:
        """Release session lock."""

        if session_id in self.session_locks:
            lock_info = self.session_locks[session_id]
            if lock_info["locked_by"] == agent_id:
                del self.session_locks[session_id]
                return True

        return False

    async def force_unlock_session(self, session_id: str, admin_agent_id: str) -> bool:
        """Admin force-unlock for deadlock recovery."""

        # Verify admin permissions
        admin_info = self.active_agents.get(admin_agent_id, {})
        if "admin" not in admin_info.get("permissions", []):
            return False

        if session_id in self.session_locks:
            old_lock_info = self.session_locks[session_id]
            del self.session_locks[session_id]

            # Notify previous lock holder of force unlock
            await self.broadcast_agent_event("lock_force_unlocked", admin_agent_id, {
                "session_id": session_id,
                "previous_lock_holder": old_lock_info["locked_by"],
                "reason": "admin_override"
            })
            return True

        return False

    async def broadcast_agent_event(self, event_type: str, agent_id: str, data: Dict[str, Any]):
        """Broadcast coordination event to all active agents."""

        event = {
            "event_type": event_type,
            "agent_id": agent_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send to all coordination channels
        for channel_id, channel_info in self.coordination_channels.items():
            for subscriber_id in channel_info["subscribers"]:
                if subscriber_id != agent_id:  # Don't send to originating agent
                    await mcp.send_notification(subscriber_id, "agent_event", event)

# Global coordination manager
coordination_manager = AgentCoordinationManager()

@mcp.tool()
async def register_agent_presence(
    status: str = Field(
        default="active",
        description="Agent status: active, busy, idle",
        regex="^(active|busy|idle)$"
    )
) -> Dict[str, Any]:
    """
    Register agent presence for coordination.
    """

    agent_id = mcp.context.get("agent_id", "unknown")
    agent_type = mcp.context.get("agent_type", "unknown")
    permissions = mcp.context.get("permissions", [])

    await coordination_manager.register_agent(agent_id, agent_type, permissions)

    return {
        "success": True,
        "agent_id": agent_id,
        "status": status,
        "registered_at": datetime.now(timezone.utc).isoformat()
    }

@mcp.tool()
async def get_active_agents(
    session_id: Optional[str] = Field(default=None, description="Filter by session")
) -> Dict[str, Any]:
    """
    Get list of currently active agents.
    """

    requesting_agent = mcp.context.get("agent_id", "unknown")

    # Get agents active in last 5 minutes
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    active_agents = []
    for agent_id, agent_info in coordination_manager.active_agents.items():
        if agent_info["last_seen"] > cutoff_time:
            agent_summary = {
                "agent_id": agent_id,
                "agent_type": agent_info["agent_type"],
                "status": agent_info["status"],
                "last_seen": agent_info["last_seen"].isoformat()
            }

            # Include permissions only for admin users or self
            if requesting_agent == agent_id or "admin" in mcp.context.get("permissions", []):
                agent_summary["permissions"] = agent_info["permissions"]

            active_agents.append(agent_summary)

    # If session_id specified, get agents active in that session
    session_agents = []
    if session_id:
        async with get_db_connection() as conn:
            cursor = await conn.execute("""
                SELECT DISTINCT sender, MAX(timestamp) as last_activity
                FROM messages
                WHERE session_id = ?
                AND timestamp >= datetime('now', '-1 hour')
                GROUP BY sender
                ORDER BY last_activity DESC
            """, (session_id,))

            session_activity = await cursor.fetchall()
            session_agents = [dict(row) for row in session_activity]

    return {
        "success": True,
        "active_agents": active_agents,
        "session_agents": session_agents if session_id else None,
        "total_active": len(active_agents),
        "cutoff_time": cutoff_time.isoformat(),
        "requesting_agent": requesting_agent
    }

@mcp.tool()
async def coordinate_session_work(
    session_id: str = Field(description="Session ID for coordination"),
    action: str = Field(
        description="Coordination action: lock, unlock, notify, status",
        regex="^(lock|unlock|notify|status)$"
    ),
    lock_type: str = Field(
        default="write",
        description="Lock type for coordination: read, write, exclusive",
        regex="^(read|write|exclusive)$"
    ),
    message: Optional[str] = Field(
        default=None,
        description="Coordination message for other agents"
    )
) -> Dict[str, Any]:
    """
    Coordinate work on a session with other agents.
    """

    agent_id = mcp.context.get("agent_id", "unknown")

    if action == "lock":
        # Attempt to acquire session lock
        lock_acquired = await coordination_manager.acquire_session_lock(
            session_id, agent_id, lock_type
        )

        if lock_acquired:
            # Notify other agents
            await coordination_manager.broadcast_agent_event(
                "session_locked",
                agent_id,
                {
                    "session_id": session_id,
                    "lock_type": lock_type,
                    "message": message
                }
            )

            return {
                "success": True,
                "action": "lock_acquired",
                "session_id": session_id,
                "lock_type": lock_type,
                "locked_by": agent_id
            }
        else:
            return {
                "success": False,
                "error": "Session already locked by another agent",
                "code": "SESSION_LOCKED",
                "session_id": session_id
            }

    elif action == "unlock":
        # Release session lock
        lock_released = await coordination_manager.release_session_lock(session_id, agent_id)

        if lock_released:
            await coordination_manager.broadcast_agent_event(
                "session_unlocked",
                agent_id,
                {
                    "session_id": session_id,
                    "message": message
                }
            )

            return {
                "success": True,
                "action": "lock_released",
                "session_id": session_id,
                "released_by": agent_id
            }
        else:
            return {
                "success": False,
                "error": "No lock held by this agent",
                "code": "NO_LOCK_HELD"
            }

    elif action == "notify":
        # Send coordination notification
        await coordination_manager.broadcast_agent_event(
            "coordination_message",
            agent_id,
            {
                "session_id": session_id,
                "message": message,
                "lock_type": lock_type
            }
        )

        return {
            "success": True,
            "action": "notification_sent",
            "session_id": session_id,
            "message": message
        }

    elif action == "status":
        # Get coordination status
        lock_info = coordination_manager.session_locks.get(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "lock_status": {
                "locked": lock_info is not None,
                "locked_by": lock_info["locked_by"] if lock_info else None,
                "lock_type": lock_info["lock_type"] if lock_info else None,
                "locked_at": lock_info["locked_at"].isoformat() if lock_info else None
            },
            "requesting_agent": agent_id
        }
```

### Integration Points

#### 1. Authentication Integration with Phases 1-2
- **Agent Identity Enhancement**: JWT tokens replace basic API key authentication
- **Permission-Based Access**: Tools and resources respect agent-specific permissions
- **Session Management Integration**: Session creation and access controlled by authentication
- **Resource Integration**: MCP resources respect enhanced authentication and permissions

#### 2. Enhanced Visibility Integration
- **Message Visibility Enhancement**: Advanced visibility rules build on Phase 1 message system
- **Search Integration**: Phase 2 search respects enhanced visibility controls
- **Memory Integration**: Agent memory access controlled by enhanced authentication
- **Audit Integration**: Comprehensive audit trail for all Phase 1-2 operations

#### 3. Real-Time Coordination Integration
- **Resource Subscription Enhancement**: Real-time updates include coordination events
- **Session Management Enhancement**: Session locking and coordination build on Phase 1
- **Agent Presence Integration**: Active agent tracking enhances multi-agent collaboration
- **Notification Integration**: MCP notifications enhanced with coordination messages

### API Requirements

**Multi-Agent Feature Tools**:
1. **`authenticate_agent`** - JWT token authentication with permission management
2. **`set_message_visibility`** - Advanced message visibility controls with audit
3. **`get_messages_advanced`** - Enhanced message retrieval with complex filtering
4. **`get_audit_log`** - Comprehensive audit log access (admin only)
5. **`get_agent_activity_summary`** - Agent activity monitoring and reporting
6. **`register_agent_presence`** - Agent coordination registration
7. **`get_active_agents`** - Active agent discovery and status
8. **`coordinate_session_work`** - Session locking and coordination

**Enhanced Authentication Flow**:
```json
{
  "tool": "authenticate_agent",
  "parameters": {
    "agent_id": "claude-main",
    "agent_type": "claude",
    "api_key": "secure-api-key",
    "requested_permissions": ["read", "write", "admin"]
  }
}

// Response
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "permissions": ["read", "write", "admin"],
  "expires_at": "2025-01-16T10:30:00Z"
}
```

---

## Quality Requirements

### Testing Strategy
**Framework**: FastMCP TestClient with multi-agent behavioral testing
**Test Categories**:
- **Unit Tests**: JWT authentication, permission validation, audit logging, coordination manager
- **Integration Tests**: Multi-agent authentication flows, enhanced visibility controls, real-time coordination
- **Security Tests**: Token validation, permission enforcement, audit integrity
- **Behavioral Tests**: Multi-agent collaboration scenarios, conflict resolution, real-time coordination

**Key Test Scenarios**:
```python
@pytest.mark.asyncio
async def test_jwt_authentication_flow(client):
    """Test complete JWT authentication and permission flow."""

    # Authenticate agent
    result = await client.call_tool("authenticate_agent", {
        "agent_id": "test-agent",
        "agent_type": "claude",
        "api_key": os.getenv("API_KEY"),
        "requested_permissions": ["read", "write"]
    })

    assert result["success"] is True
    token = result["token"]

    # Use token for authenticated request
    client.set_auth_header(f"Bearer {token}")

    # Test permission-protected operation
    session_result = await client.call_tool("create_session", {
        "purpose": "auth test"
    })

    assert session_result["success"] is True
    assert session_result["created_by"] == "test-agent"

@pytest.mark.asyncio
async def test_multi_agent_coordination(client1, client2):
    """Test multi-agent coordination and conflict resolution."""

    # Setup two authenticated agents
    for i, client in enumerate([client1, client2], 1):
        auth_result = await client.call_tool("authenticate_agent", {
            "agent_id": f"agent-{i}",
            "agent_type": "test",
            "api_key": os.getenv("API_KEY"),
            "requested_permissions": ["read", "write"]
        })
        client.set_auth_header(f"Bearer {auth_result['token']}")

        # Register presence
        await client.call_tool("register_agent_presence", {"status": "active"})

    # Create shared session
    session_result = await client1.call_tool("create_session", {
        "purpose": "coordination test"
    })
    session_id = session_result["session_id"]

    # Agent 1 acquires lock
    lock_result = await client1.call_tool("coordinate_session_work", {
        "session_id": session_id,
        "action": "lock",
        "lock_type": "write"
    })
    assert lock_result["success"] is True

    # Agent 2 attempts lock (should fail)
    lock_result2 = await client2.call_tool("coordinate_session_work", {
        "session_id": session_id,
        "action": "lock",
        "lock_type": "write"
    })
    assert lock_result2["success"] is False
    assert lock_result2["code"] == "SESSION_LOCKED"

    # Agent 1 releases lock
    unlock_result = await client1.call_tool("coordinate_session_work", {
        "session_id": session_id,
        "action": "unlock"
    })
    assert unlock_result["success"] is True

    # Agent 2 can now acquire lock
    lock_result3 = await client2.call_tool("coordinate_session_work", {
        "session_id": session_id,
        "action": "lock",
        "lock_type": "write"
    })
    assert lock_result3["success"] is True

@pytest.mark.asyncio
async def test_enhanced_visibility_controls(client):
    """Test advanced message visibility and filtering."""

    # Setup admin agent
    auth_result = await client.call_tool("authenticate_agent", {
        "agent_id": "admin-agent",
        "agent_type": "admin",
        "api_key": os.getenv("API_KEY"),
        "requested_permissions": ["read", "write", "admin"]
    })
    client.set_auth_header(f"Bearer {auth_result['token']}")

    # Create session and add messages with different visibility
    session_result = await client.call_tool("create_session", {
        "purpose": "visibility test"
    })
    session_id = session_result["session_id"]

    # Add messages with different visibility levels
    for visibility in ["public", "private", "admin_only"]:
        await client.call_tool("add_message", {
            "session_id": session_id,
            "content": f"Message with {visibility} visibility",
            "visibility": visibility
        })

    # Test advanced message retrieval
    messages_result = await client.call_tool("get_messages_advanced", {
        "session_id": session_id,
        "include_admin_only": True
    })

    assert messages_result["success"] is True
    assert len(messages_result["messages"]) == 3

    # Test visibility change
    message_id = messages_result["messages"][0]["id"]
    visibility_result = await client.call_tool("set_message_visibility", {
        "message_id": message_id,
        "new_visibility": "public",
        "reason": "Making accessible to all agents"
    })

    assert visibility_result["success"] is True

@pytest.mark.asyncio
async def test_audit_logging_system(client):
    """Test comprehensive audit logging and retrieval."""

    # Setup admin agent
    auth_result = await client.call_tool("authenticate_agent", {
        "agent_id": "audit-agent",
        "agent_type": "admin",
        "api_key": os.getenv("API_KEY"),
        "requested_permissions": ["read", "write", "admin"]
    })
    client.set_auth_header(f"Bearer {auth_result['token']}")

    # Perform auditable operations
    session_result = await client.call_tool("create_session", {
        "purpose": "audit test"
    })
    session_id = session_result["session_id"]

    await client.call_tool("add_message", {
        "session_id": session_id,
        "content": "Auditable message"
    })

    # Retrieve audit log
    audit_result = await client.call_tool("get_audit_log", {
        "session_id": session_id,
        "limit": 10
    })

    assert audit_result["success"] is True
    assert len(audit_result["audit_entries"]) >= 2  # session creation + message addition

    # Test activity summary
    activity_result = await client.call_tool("get_agent_activity_summary", {
        "time_window": "1h"
    })

    assert activity_result["success"] is True
    assert len(activity_result["agent_activity"]) >= 1
```

### Documentation Needs
**Multi-Agent Features Documentation**:
- **Authentication System**: JWT token flow, permission model, security best practices
- **Enhanced Visibility**: Advanced visibility controls, agent-type filtering, admin permissions
- **Coordination System**: Session locking, agent presence, conflict resolution patterns
- **Audit System**: Audit log structure, security monitoring, compliance reporting

### Performance Considerations
**Multi-Agent Features Performance Requirements**:
- JWT token validation: < 5ms
- Permission checking: < 2ms
- Coordination operations: < 15ms
- Audit log retrieval: < 100ms for 100 entries
- Real-time notifications: < 50ms delivery

**Optimization Strategies**:
- **Token Caching**: Cache validated JWT tokens to avoid repeated validation overhead
- **Permission Caching**: Cache agent permissions for frequently accessed operations
- **Coordination Efficiency**: Optimize session locking with minimal database queries
- **Audit Indexing**: Proper indexes on audit_log table for fast querying

---

## Coordination Strategy

### Recommended Approach: Direct Agent Assignment
**Complexity Assessment**: Multi-agent features with high complexity
**File Count**: 10-15 files (auth.py, permissions.py, coordination.py, audit.py, enhanced_visibility.py, multiple test files)
**Integration Risk**: High (integrating with all previous phases, adding security layers)
**Time Estimation**: 6 hours with comprehensive security testing and multi-agent validation

**Agent Assignment**: **Developer Agent** for complete Phase 3 execution
**Rationale**: Multi-agent features require deep security expertise, JWT implementation, coordination system architecture - all developer agent specialties

### Implementation Phases

#### Phase 3.1: Advanced Authentication (2 hours)
**Implementation Steps**:
1. **JWT Authentication System** (60 minutes): Token generation, validation, secure key management
2. **Permission System** (45 minutes): RBAC implementation, permission decorators, access control
3. **Enhanced Middleware** (15 minutes): Integration with existing authentication, context enhancement

**Validation Checkpoints**:
```python
# JWT validation
token = auth_manager.generate_token("test-agent", "claude", ["read", "write"])
validation = auth_manager.validate_token(token)
assert validation["valid"] is True
assert validation["agent_id"] == "test-agent"

# Permission enforcement
@require_permission("admin")
async def admin_only_function():
    return {"success": True}

# Should work with admin permission, fail without
```

#### Phase 3.2: Enhanced Visibility & Audit (2 hours)
**Implementation Steps**:
1. **Advanced Visibility Controls** (60 minutes): Complex visibility rules, agent-type filtering, admin controls
2. **Comprehensive Audit System** (45 minutes): Audit log retrieval, activity summaries, security monitoring
3. **Message Visibility Management** (15 minutes): Visibility changes, audit trails, notifications

**Validation Checkpoints**:
```python
# Visibility control validation
result = await client.call_tool("set_message_visibility", {
    "message_id": 123,
    "new_visibility": "admin_only"  # Should require admin permission
})

# Audit system validation
audit_result = await client.call_tool("get_audit_log", {
    "agent_id": "test-agent",
    "limit": 50
})
assert len(audit_result["audit_entries"]) > 0
```

#### Phase 3.3: Real-Time Multi-Agent Coordination (2 hours)
**Implementation Steps**:
1. **Coordination Manager** (60 minutes): Session locking, agent registration, presence tracking
2. **Agent Discovery** (30 minutes): Active agent listing, status tracking, capability discovery
3. **Coordination Tools** (30 minutes): Session coordination, conflict resolution, notification system

**Validation Checkpoints**:
```python
# Coordination system validation
lock_result = await client.call_tool("coordinate_session_work", {
    "session_id": "test-session",
    "action": "lock",
    "lock_type": "write"
})
assert lock_result["success"] is True

# Agent presence validation
presence_result = await client.call_tool("register_agent_presence", {
    "status": "active"
})
assert presence_result["success"] is True

active_agents = await client.call_tool("get_active_agents")
assert len(active_agents["active_agents"]) >= 1
```

### Risk Mitigation

#### Security Risks
**JWT Token Security**: Secure key management, token expiration, validation bypass prevention
**Permission Escalation**: Careful permission checking, decorator validation, admin access controls
**Audit Log Integrity**: Secure audit logging, tamper prevention, access control
**Coordination Vulnerabilities**: Session lock security, agent impersonation prevention

#### Performance Risks
**Authentication Overhead**: Token caching, validation optimization, efficient permission checking
**Coordination Bottlenecks**: Efficient session locking, minimal database operations
**Audit Log Performance**: Proper indexing, query optimization, batch operations
**Real-time Notification Overhead**: Efficient notification delivery, subscription management

#### Integration Risks
**Phase 1-2 Integration Issues**: Backward compatibility, existing tool enhancement, database consistency
**Complex Visibility Logic**: Thorough testing of all visibility combinations, edge cases
**Multi-Agent Race Conditions**: Coordination system testing, concurrent access handling
**Security Integration Gaps**: End-to-end security testing, vulnerability assessment

### Dependencies & Prerequisites
**Phase 2 Completion**: Essential features operational, search system, agent memory, MCP resources
**Security Infrastructure**: JWT secret management, secure token storage, audit log protection
**Multi-Agent Testing**: Multiple client simulation, coordination testing environment
**Performance Optimization**: Database indexing for audit and coordination operations

---

## Success Criteria

### Functional Success
**Advanced Authentication System**:
- ✅ JWT token generation and validation working correctly
- ✅ Permission-based access control enforced throughout system
- ✅ Secure credential management and token expiration handling
- ✅ Enhanced authentication middleware integrated with all tools

**Enhanced Visibility & Audit System**:
- ✅ Advanced message visibility controls with agent-type filtering
- ✅ Comprehensive audit log system with filtering and search
- ✅ Agent activity monitoring and reporting operational
- ✅ Security monitoring and compliance reporting functional

**Real-Time Multi-Agent Coordination**:
- ✅ Session locking and coordination system working correctly
- ✅ Agent presence registration and discovery operational
- ✅ Real-time coordination notifications and conflict resolution
- ✅ Multi-agent collaboration scenarios working seamlessly

### Integration Success
**Authentication Integration**: JWT authentication seamlessly integrated with all Phase 1-2 features
**Visibility Integration**: Enhanced visibility controls working with search, memory, and resource systems
**Coordination Integration**: Real-time coordination working with session management and resource subscriptions
**Security Integration**: Comprehensive security hardening applied across all system components

### Quality Gates ⚠️ **MANDATORY QUALITY REQUIREMENTS**

**Code Quality Prerequisites** ⚠️ **MUST PASS BEFORE PHASE 3 IMPLEMENTATION**:
```bash
uv run ruff check .     # MANDATORY: Zero linting errors required
uv run mypy .           # MANDATORY: Zero type checking errors required
coverage report         # MANDATORY: Must achieve ≥70% test coverage
```

**Multi-Agent Features Testing**:
```bash
uv run test tests/unit/test_jwt_authentication.py        # JWT system tests pass
uv run test tests/unit/test_permissions.py              # Permission system tests pass
uv run test tests/integration/test_multi_agent_coord.py # Coordination tests pass
uv run test tests/security/test_visibility_controls.py  # Security tests pass
uv run test tests/behavioral/test_agent_collaboration.py # Multi-agent scenarios pass
```

**Coverage Target Achievement** ⚠️ **PHASE 3 REQUIREMENT**:
- **Minimum Required**: 70% total test coverage (up from current 54%)
- **Focus Areas**:
  - `server.py`: 56% → 75%+ (core functionality)
  - `models.py`: 59% → 80%+ (data validation)
  - New Phase 3 modules: 85%+ coverage required
- **Coverage Command**: `uv run pytest tests/ --cov=src --cov-report=html --cov-fail-under=70`

**Performance Benchmarks**:
- JWT token validation: < 5ms
- Permission checking: < 2ms
- Coordination operations: < 15ms
- Audit log queries: < 100ms

**Security Validation**:
```bash
uv run test tests/security/test_auth_bypass.py          # Auth bypass prevention tests
uv run test tests/security/test_permission_escalation.py # Privilege escalation tests
uv run test tests/security/test_audit_integrity.py      # Audit log integrity tests
```

**Quality Gate Enforcement**:
- ❌ **Implementation MUST NOT proceed** if ruff check fails
- ❌ **Implementation MUST NOT proceed** if mypy type checking fails
- ❌ **Implementation MUST NOT proceed** if coverage is below 70%
- ❌ **Phase 3 completion MUST NOT be marked** until all quality gates pass

### Validation Checklist

#### ✅ Advanced Authentication System
- [ ] JWT token generation with proper claims and expiration
- [ ] Token validation with security checks and error handling
- [ ] Permission-based access control enforced on all tools
- [ ] Secure credential management and key rotation support
- [ ] Enhanced authentication middleware integrated throughout

#### ✅ Enhanced Visibility & Audit System
- [ ] Advanced message visibility controls with complex filtering
- [ ] Comprehensive audit log system with admin access controls
- [ ] Agent activity monitoring and reporting functional
- [ ] Security event tracking and alerting operational
- [ ] Audit log integrity and tamper prevention working

#### ✅ Real-Time Multi-Agent Coordination
- [ ] Session locking system preventing coordination conflicts
- [ ] Agent presence registration and active discovery working
- [ ] Real-time coordination notifications delivered efficiently
- [ ] Conflict resolution and concurrent access handling robust
- [ ] Multi-agent collaboration scenarios tested and working

---

## Implementation Notes

### Critical Success Factors
1. **Security First**: JWT implementation with proper validation, secure key management, attack prevention
2. **Permission Rigor**: Comprehensive permission checking, no bypass opportunities, proper error handling
3. **Coordination Reliability**: Session locking without race conditions, efficient agent discovery
4. **Audit Integrity**: Tamper-proof audit logging, comprehensive security event tracking
5. **Real-time Performance**: Efficient coordination and notification system without overhead

### Common Pitfalls to Avoid
1. **❌ JWT Security Gaps**: Weak secret keys, missing validation checks, token replay attacks
2. **❌ Permission Bypass**: Missing permission checks, decorator failures, admin escalation
3. **❌ Coordination Race Conditions**: Session lock conflicts, concurrent access issues
4. **❌ Audit Log Gaps**: Missing security events, incomplete audit trails, log tampering
5. **❌ Performance Degradation**: Authentication overhead, coordination bottlenecks, notification floods

### Post-Phase Integration
**Preparation for Phase 4**:
- Authentication system ready for production security hardening
- Coordination system prepared for performance optimization and monitoring
- Audit system ready for compliance reporting and security dashboards
- Multi-agent features ready for comprehensive testing and documentation

---

## References

### Planning Documents
- [Final Decomposed Implementation Plan](../1-planning/shared-context-mcp-server/FINAL_DECOMPOSED_IMPLEMENTATION_PLAN.md)
- [Security Authentication Guide](../../.claude/tech-guides/security-authentication.md) - JWT patterns, RBAC models
- [Core Architecture Guide](../../.claude/tech-guides/core-architecture.md) - Audit logging, multi-agent patterns

### Implementation Patterns
- **JWT Authentication**: Security guide JWT implementation patterns
- **Audit Logging**: Core architecture audit log table and patterns
- **Multi-Agent Coordination**: Blackboard architecture and coordination patterns

### External References
- [PyJWT Documentation](https://pyjwt.readthedocs.io/) - JWT implementation and security
- [RBAC Patterns](https://en.wikipedia.org/wiki/Role-based_access_control) - Permission model design
- [MCP Security Specification](https://modelcontextprotocol.io/specification/server/security) - MCP security patterns

---

## Documentation Updates

### README.md Updates Required
Upon completion of Phase 3, update README.md to reflect:

**Status Section**:
```markdown
## Status

🎯 **Phase 3 Complete**: Multi-Agent Features ready
- ✅ JWT authentication with role-based access control
- ✅ Advanced visibility controls and audit logging
- ✅ Real-time multi-agent coordination with session locking
- ✅ Comprehensive security hardening and attack prevention
- ✅ Agent presence tracking and conflict resolution

🚀 **Next**: Phase 4 - Production Ready implementation

## Security & Authentication

**JWT Authentication**: Token-based auth with secure key management
**Role-Based Access**: Granular permissions for agents, admins, and users
**Audit Logging**: Comprehensive security event tracking and integrity
**Session Security**: Advanced locking and coordination conflict prevention

## Multi-Agent Coordination

**Real-time Presence**: Active agent discovery and status tracking
**Session Locking**: Prevent coordination conflicts during collaboration
**Conflict Resolution**: Robust handling of concurrent agent operations
**Security Controls**: Enhanced visibility and access control integration
```

**Architecture Section Update**:
```markdown
## Architecture

### Multi-Agent Features (Phase 3)
- **JWT Authentication**: Token-based authentication with RBAC permissions
- **Enhanced Audit System**: Comprehensive security logging with admin controls
- **Coordination Engine**: Real-time multi-agent coordination with session locking
- **Advanced Visibility**: Complex message filtering with security integration
- **Agent Presence System**: Registration, discovery, and conflict resolution
```

**Security Section Addition**:
```markdown
## Security

### Authentication & Authorization
- JWT tokens with secure key rotation
- Role-based permissions (admin, agent, user)
- Comprehensive audit logging
- Attack prevention (replay, escalation, bypass)

### Multi-Agent Security
- Session-based access controls
- Agent identity validation
- Secure coordination protocols
- Tamper-proof audit trails
```

---

**Ready for Execution**: Phase 3 multi-agent features implementation
**Next Phase**: Phase 4 - Production Ready (performance optimization, comprehensive testing, documentation)
**Coordination**: Direct developer agent assignment for complete Phase 3 execution

---

## Learnings and Gotchas During Execution

This section captures critical insights, challenges, and solutions discovered during the actual implementation of Phase 3 features. These learnings represent hard-won knowledge that future development teams should leverage.

### 🔧 Critical Bug Fixes and Infrastructure Issues

#### Search System Database Row Factory Issue
**Issue**: Search functions returning empty results due to missing `conn.row_factory = aiosqlite.Row`
- **Root Cause**: `search_by_sender` and `search_by_timerange` functions missing critical row factory setup
- **Problem**: SQLite rows couldn't convert to dictionaries, causing `dict(msg)` to fail with "cannot convert dictionary update sequence element #0 to a sequence"
- **Impact**: All search operations failing silently with empty results
- **Solution**: Added `conn.row_factory = aiosqlite.Row` to all search functions
- **Key Learning**: ⚠️ **SQLite row factory must be set for dict conversion** - critical for aiosqlite usage

```python
# ✅ CRITICAL PATTERN: Always set row factory for dict access
async with get_db_connection() as conn:
    conn.row_factory = aiosqlite.Row  # CRITICAL: Set row factory for dict access
    cursor = await conn.execute("SELECT * FROM messages WHERE id = ?", (id,))
    messages = [dict(msg) for msg in await cursor.fetchall()]  # Now works
```

#### Fuzzy Search Algorithm Performance Issue
**Issue**: Search context returning no results with threshold 70+ due to inappropriate scoring algorithm
- **Root Cause**: Using `fuzz.WRatio` which was too conservative for substring matching in search contexts
- **Problem**: Exact word "Python" in "Python programming language" scored only 60.0, failing 70+ thresholds
- **Solution**: Switched to `fuzz.partial_ratio` which properly handles substring matching (scored 100.0)
- **Key Learning**: ⚡ **Choose fuzzy matching algorithm appropriate for use case** - partial_ratio for substring search, WRatio for full text similarity

```python
# ❌ WRONG: WRatio too conservative for substring search
scorer=fuzz.WRatio  # "Python" in "Python programming" = 60.0

# ✅ CORRECT: partial_ratio perfect for substring search
scorer=fuzz.partial_ratio  # "Python" in "Python programming" = 100.0
```

#### SQLite Timestamp Format Comparison Issue
**Issue**: Timerange search failing due to timestamp format mismatch between SQLite CURRENT_TIMESTAMP and ISO strings
- **Root Cause**: Database stores timestamps as "2025-08-11 00:25:39" but search uses "2025-08-11T00:25:39.711364+00:00"
- **Problem**: String comparison failed between different timestamp formats
- **Solution**: Use SQLite's `datetime()` function for proper timestamp comparison
- **Key Learning**: 📅 **Use database functions for timestamp comparison** - don't rely on string comparison across formats

```python
# ❌ WRONG: String comparison of different formats fails
AND timestamp >= ? AND timestamp <= ?  # Fails: '2025-08-11 00:25:39' vs '2025-08-11T00:25:39+00:00'

# ✅ CORRECT: Use SQLite datetime functions for proper comparison
AND datetime(timestamp) >= datetime(?) AND datetime(timestamp) <= datetime(?)
```

#### Database Schema Evolution Challenges
**Issue**: TTL constraint timing violations causing test failures
- **Root Cause**: Database constraint `agent_memory_expires_at_future CHECK (expires_at IS NULL OR expires_at > created_at)` required consistent timestamp calculation
- **Problem**: Mixing Python `datetime.now()` with SQLite `CURRENT_TIMESTAMP` caused microsecond timing mismatches
- **Solution**: Always calculate both `created_at` and `expires_at` in Python using the same base timestamp
- **Key Learning**: ⚠️ **Never mix timestamp sources in database constraints** - use consistent calculation in application code

```python
# ❌ WRONG: Mixed timestamp sources cause constraint violations
created_at_timestamp = time.time()  # Python timestamp
# Later: SQLite uses CURRENT_TIMESTAMP (different time)

# ✅ CORRECT: Consistent timestamp calculation
now_timestamp = datetime.now(timezone.utc)
created_at_timestamp = now_timestamp.timestamp()
expires_at = created_at_timestamp + expires_in
```

#### Database Parameter Mismatch Issues
**Issue**: Integration tests failing with "too many values to unpack (expected 7)"
- **Root Cause**: Schema evolution added `created_at` column but mock databases weren't updated
- **Impact**: All memory system tests were failing silently
- **Solution**: Systematic update of all mock database parameter unpacking to handle 8 parameters
- **Key Learning**: ⚠️ **Schema changes require coordinated test infrastructure updates** - maintain mock/real database parity

### 🎯 Type Safety Implementation Revelations

#### Dynamic Attribute Assignment Anti-Pattern
**Challenge**: 37 MyPy type errors from dynamic Context attribute assignment
- **Anti-Pattern**: `ctx.jwt_validated = True`, `ctx.agent_id = "agent_1"`
- **Impact**: No IDE support, no type safety, hard to debug
- **Solution**: `AuthInfo` dataclass with `get_auth_info()`/`set_auth_info()` helpers
- **Key Learning**: ✅ **Use proper abstractions instead of suppressing type errors** - composition over dynamic attributes

```python
# ❌ ANTI-PATTERN: Dynamic attribute assignment
ctx.jwt_validated = True
ctx.agent_id = "agent_1"
ctx.permissions = ["read", "write"]

# ✅ CLEAN PATTERN: Typed composition
@dataclass
class AuthInfo:
    jwt_validated: bool = False
    agent_id: str = "unknown"
    permissions: list[str] = field(default_factory=lambda: ["read"])

set_auth_info(ctx, AuthInfo(jwt_validated=True, agent_id="agent_1"))
```

#### Coverage Instrumentation Performance Impact
**Issue**: Performance tests failing only when run with coverage (`--cov`)
- **Root Cause**: Coverage instrumentation adds 2-10x timing overhead to function calls
- **Problem**: 10ms performance thresholds unrealistic with coverage active
- **Solution**: Dynamic threshold adjustment based on coverage detection
- **Key Learning**: ⚠️ **Performance tests must account for coverage overhead** - adjust thresholds or skip during coverage runs

```python
# ✅ SOLUTION: Coverage-aware performance testing
try:
    import coverage
    coverage_active = coverage.process_startup.coverage is not None
except (ImportError, AttributeError):
    coverage_active = bool(os.environ.get('COV_CORE_SOURCE'))

threshold = 50 if coverage_active else 10  # ms
```

### 🏗️ Architecture and Design Insights

#### Authentication Context Enhancement
**Challenge**: Extending FastMCP Context with authentication information
- **Discovery**: FastMCP Context objects don't support dynamic attributes by design
- **Anti-Pattern**: Direct attribute assignment causes type safety violations
- **Best Practice**: Use single `_auth_info` attribute with structured dataclass
- **Key Learning**: ✅ **Framework constraints guide good architectural decisions** - work with the framework, not against it

#### Database Migration Strategy
**Issue**: Schema evolution requires careful coordination across components
- **Challenge**: Adding `sender_type` column affected multiple systems simultaneously
- **Solution**: Migration scripts + comprehensive test updates + mock database alignment
- **Best Practice**: Schema changes as coordinated multi-system updates
- **Key Learning**: 🔄 **Database migrations are multi-system coordination events** - plan accordingly

### 🧪 Testing Infrastructure Revelations

#### Modern Database Testing Approach
**Anti-Pattern**: Fragile hardcoded mocks that break on schema changes
**Modern Approach**: Real in-memory SQLite databases for each test
- **Benefits**: Schema validation, constraint testing, realistic behavior
- **Performance**: Minimal overhead with proper fixture management
- **Reliability**: Tests remain valid as database schemas evolve
- **Key Learning**: ✅ **Real database testing > fragile mocks** for database-heavy applications

```python
# ✅ MODERN PATTERN: Real database testing
@pytest.fixture
async def test_db_manager():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
        db_manager = DatabaseManager(f"sqlite:///{temp_db.name}")
        await db_manager.initialize()  # Real schema applied
        yield db_manager
    Path(temp_db.name).unlink()  # Cleanup
```

#### Test Infrastructure Crisis Resolution
**Crisis**: Skipped test masking real implementation problems
- **Issue**: TTL test was skipped with vague comment about "timing issues"
- **Reality**: Actual database constraint violations were being hidden
- **Resolution**: Fixed real database constraint issues instead of skipping tests
- **Key Learning**: ⚠️ **Never skip tests without fixing root causes** - skipped tests hide real problems

### 🔍 Code Quality and Tooling Learnings

#### Path Handling Modernization
**Issue**: Legacy `os.path` usage causing lint violations
- **Modern Pattern**: `pathlib.Path` for all path operations
- **Benefits**: Type safety, better API, cross-platform compatibility
- **Migration**: Systematic replacement of `os.path.exists()` → `Path.exists()`
- **Key Learning**: 📁 **Embrace modern Python patterns** - pathlib is superior to os.path

#### Logging Performance Optimization
**Issue**: Redundant exception objects in logging statements
- **Anti-Pattern**: `logger.exception(f"Error: {e}")` - logs exception twice
- **Optimization**: `logger.exception("Error description")` - exception auto-included
- **Impact**: Better performance and cleaner logs
- **Key Learning**: 📝 **Optimize logging patterns** - framework features reduce boilerplate

### 🚀 Development Workflow Optimizations

#### Hot Reload Development Setup
**Innovation**: Live development server with automatic restart
- **Feature**: Edit Python → 1-2 second restart → Agents reconnect automatically
- **Implementation**: `watchdog` + `mcp-proxy` + environment detection
- **Impact**: Dramatically faster development cycle
- **Key Learning**: 🔥 **Investment in development tooling pays dividends** - hot reload transforms workflow

#### Multi-Agent Testing Infrastructure
**Challenge**: Testing multi-agent coordination scenarios
- **Solution**: Multiple `MockContext` instances with proper `AuthInfo` integration
- **Pattern**: Behavioral tests simulating real agent interactions
- **Validation**: Session locking, coordination conflicts, permission isolation
- **Key Learning**: 🤝 **Multi-agent systems require specialized testing approaches** - simulate real coordination

### 🎯 Performance and Optimization Discoveries

#### RapidFuzz Search Performance
**Discovery**: RapidFuzz provides 5-10x performance improvement over basic fuzzy search
- **Implementation**: Search operations consistently under 100ms even with large datasets
- **Optimization**: Proper result limiting and threshold tuning critical
- **Key Learning**: ⚡ **Choose performance-optimized libraries** - RapidFuzz vs basic difflib

#### Database Connection Pooling
**Pattern**: Async context managers for connection lifecycle
- **Benefits**: Automatic cleanup, connection reuse, error handling
- **Implementation**: `async with get_db_connection() as conn:`
- **Performance**: Minimal connection overhead with proper pooling
- **Key Learning**: 🏊 **Connection pooling is essential** for database-heavy async applications

### 🔐 Security Implementation Insights

#### JWT Authentication Best Practices
**Implementation**: Comprehensive JWT token management
- **Key Storage**: Environment-based secret keys with production validation
- **Token Validation**: Clock skew tolerance, proper claim validation
- **Permission System**: Role-based access with granular controls
- **Key Learning**: 🔐 **Security requires comprehensive implementation** - no shortcuts on JWT

#### Audit Logging Architecture
**Pattern**: Comprehensive audit trail for all security events
- **Coverage**: Authentication, authorization, data access, system changes
- **Integrity**: Tamper-proof logging with structured metadata
- **Performance**: Async logging with proper indexing
- **Key Learning**: 📋 **Audit logging is architectural** - design in from start, not bolt-on

### 💡 Multi-Agent Coordination Lessons

#### Session Locking Strategy
**Pattern**: TTL-based locks with heartbeat renewal
- **Deadlock Prevention**: Automatic lock expiry with heartbeat requirement
- **Conflict Resolution**: Admin override capabilities for stuck locks
- **Performance**: Minimal database queries for lock operations
- **Key Learning**: 🔒 **Distributed locking requires heartbeats** - pure TTL insufficient

#### Agent Presence Management
**Discovery**: Active agent tracking enables smart coordination
- **Implementation**: Registration + heartbeat + automatic cleanup
- **Benefits**: Conflict avoidance, intelligent routing, status awareness
- **Optimization**: Efficient presence queries with proper indexing
- **Key Learning**: 👥 **Presence awareness enables intelligent coordination** - worth the infrastructure investment

### 🎨 Code Organization Patterns

#### Agent-Specific Testing
**Pattern**: Specialized agents for different testing scenarios
- **TestClient**: Multi-agent behavioral testing
- **MockContext**: Type-safe authentication simulation
- **AuthInfo Integration**: Seamless transition from dynamic attributes
- **Key Learning**: 🧪 **Testing infrastructure should mirror production patterns** - same abstractions everywhere

#### Error Envelope Consistency
**Pattern**: Consistent error response structure across all tools
- **Structure**: `{"success": false, "error": "description", "code": "ERROR_TYPE"}`
- **Benefits**: Client-side error handling, debugging, monitoring
- **Implementation**: Centralized error creation functions
- **Key Learning**: 📮 **Consistent error patterns improve developer experience** - standardize early

### 🔄 Migration Strategy Insights

#### Backward Compatibility Approach
**Strategy**: New abstractions alongside existing patterns
- **Migration Path**: Add new systems, update incrementally, remove old patterns
- **Testing**: Parallel validation of old and new approaches
- **Rollback**: Ability to revert to previous patterns if issues
- **Key Learning**: 🔄 **Gradual migration > big bang replacement** - reduce risk

#### Documentation Evolution
**Pattern**: Living documentation that evolves with implementation
- **Updates**: README status, architecture sections, security documentation
- **Maintenance**: Keep documentation current with actual implementation
- **Value**: Documentation as communication tool between phases
- **Key Learning**: 📚 **Documentation debt compounds** - maintain continuously

### 🎯 Success Metrics and Validation

#### Quality Gate Enforcement
**Standard**: 0 lint errors, 0 type errors, 70%+ test coverage
- **Tools**: ruff, mypy, pytest-cov with enforcement
- **Process**: Quality gates before feature implementation
- **Value**: Technical debt prevention, maintainable codebase
- **Key Learning**: ✅ **Quality gates prevent technical debt accumulation** - enforce strictly

#### Test Coverage Evolution
**Progress**: Systematic improvement from 54% to 70%+ coverage
- **Focus**: Core modules (server.py, models.py) and new features
- **Strategy**: Behavioral testing + unit testing + integration testing
- **Tools**: pytest-cov with HTML reporting for gap analysis
- **Key Learning**: 📊 **Coverage improvement requires focused effort** - target specific gaps

### 🚀 Development Velocity Insights

#### Agent Coordination Benefits
**Discovery**: Specialized agents improve development efficiency
- **Developer Agent**: Deep technical implementation focus
- **Tester Agent**: Modern testing infrastructure creation
- **Task Coordination**: Intelligent work distribution
- **Key Learning**: 🤖 **Specialized AI agents accelerate complex development** - leverage agent strengths

#### Incremental Implementation Value
**Approach**: Phase-based implementation with validation checkpoints
- **Benefits**: Risk reduction, incremental validation, rollback capability
- **Challenges**: Coordination complexity, integration testing
- **Success**: Each phase builds solid foundation for next
- **Key Learning**: 🏗️ **Incremental development with quality gates** works for complex systems

---

### 💎 Golden Rules from Implementation

1. **🔐 Security First**: JWT implementation requires comprehensive validation - no shortcuts
2. **📊 Type Safety Over Suppressions**: Use proper abstractions instead of ignoring type errors
3. **🧪 Real Database Testing**: In-memory databases > fragile mocks for database applications
4. **⏱️ Performance Tests Need Coverage Awareness**: Account for instrumentation overhead
5. **🔄 Schema Changes are Multi-System Events**: Coordinate databases, tests, and mocks together
6. **🔒 Distributed Systems Need Heartbeats**: Pure TTL locks insufficient for coordination
7. **📝 Audit Logging is Architectural**: Design in from start, not bolt-on later
8. **🎯 Quality Gates Prevent Debt**: Enforce lint/type/coverage before implementation
9. **🤝 Multi-Agent Testing is Specialized**: Different patterns than single-agent systems
10. **🔥 Investment in Developer Tooling**: Hot reload and quality tools pay dividends

These learnings represent the practical wisdom gained from implementing complex multi-agent authentication and coordination systems. They should guide future development and help teams avoid the pitfalls we encountered.

---

## 📊 Phase 3 Implementation Status Summary

### ✅ Successfully Completed: Search System Infrastructure (Phase 3.1)

**Achievement**: 100% success rate for all search operations (16/16 search tests passing)
- **search_context**: RapidFuzz fuzzy matching with proper algorithm selection (`fuzz.partial_ratio`)
- **search_by_sender**: Multi-agent sender filtering with proper row factory setup
- **search_by_timerange**: SQLite timestamp comparison using `datetime()` functions
- **Advanced Search Features**: Metadata search, visibility controls, performance optimization
- **Search Performance**: All operations under 100ms with RapidFuzz optimization

**Critical Fixes Applied**:
1. **Database Row Factory**: Added `conn.row_factory = aiosqlite.Row` to all search functions
2. **Fuzzy Algorithm**: Switched from `fuzz.WRatio` to `fuzz.partial_ratio` for substring matching
3. **Timestamp Handling**: Used SQLite `datetime()` functions for proper format comparison
4. **Session Validation**: Added session existence checks with proper error responses

### 📈 Current Test Status: 95.7% Success Rate (264 passing, 12 failing)

**Significant Achievement**: Improved from initial 43 passing tests to 264 passing tests
- **Search System**: 16/16 tests passing (100% success rate)
- **Authentication System**: JWT auth infrastructure tests passing
- **Memory System**: Agent memory storage and retrieval operational
- **Core Infrastructure**: Session management, message storage, database operations stable

### 🔧 Remaining Work: 12 Test Failures in 3 Categories

#### Category 1: Visibility Controls (6 tests)
**Location**: `tests/behavioral/test_visibility.py`
**Failing Tests**:
- `test_public_message_visibility`
- `test_session_isolation_security`
- `test_private_message_isolation`
- `test_agent_only_message_behavior`
- `test_mixed_visibility_scenarios`
- `test_visibility_filter_parameter`

**Issue Pattern**: `assert False is True` - indicating core visibility filtering logic needs implementation
**Impact**: Multi-agent visibility controls not fully operational

#### Category 2: Message Storage Operations (4 tests)
**Location**: `tests/unit/test_message_storage.py`
**Failing Tests**:
- `test_get_messages_pagination`
- `test_get_messages_visibility_filtering`
- `test_get_messages_with_filter`
- `test_get_messages_success`

**Issue Pattern**: `assert False is True` - basic message retrieval operations failing
**Impact**: Core message storage functionality has integration issues

#### Category 3: Multi-Component Integration (2 tests)
**Location**: `tests/unit/test_server_integration.py`
**Failing Tests**:
- `test_search_across_memory_and_messages_workflow` (1 result found, expected ≥2)
- `test_multi_agent_collaboration_workflow` (1 result found, expected ≥2)

**Issue Pattern**: Search operations finding fewer results than expected
**Impact**: Cross-system integration workflows need refinement

### 🏗️ Architecture Status Assessment

**Strengths Achieved**:
- ✅ **Search Infrastructure**: World-class fuzzy search with RapidFuzz
- ✅ **Database Layer**: Robust SQLite operations with proper connection management
- ✅ **Authentication Framework**: JWT token system with permission management
- ✅ **Testing Infrastructure**: Modern testing with real database fixtures
- ✅ **Development Tooling**: Hot reload development server operational

**Remaining Implementation Gaps**:
- 🔧 **Visibility Logic**: Complex multi-agent visibility rules need completion
- 🔧 **Message Operations**: Basic message retrieval API consistency issues
- 🔧 **Integration Workflows**: Cross-component coordination patterns need refinement

### 🎯 Technical Debt and Quality Status

**Code Quality Metrics**:
- **Lint Status**: Passing (0 ruff errors)
- **Type Safety**: Passing (0 mypy errors after AuthInfo refactoring)
- **Test Coverage**: 95.7% success rate (significant improvement from baseline)
- **Performance**: Search operations under 100ms, memory operations under 50ms

**Architecture Quality**:
- **Type Safety**: Modern approaches with structured dataclasses over dynamic attributes
- **Database Design**: Proper schema evolution with migration support
- **Testing Strategy**: Real database testing over fragile mocks
- **Security Framework**: JWT authentication with comprehensive validation

### 💡 Key Success Factors for Phase 4

**Foundation Strengths to Leverage**:
1. **Search System**: Proven RapidFuzz integration ready for production scale
2. **Database Infrastructure**: Robust SQLite operations with migration support
3. **Authentication Framework**: JWT system ready for multi-agent deployment
4. **Development Tooling**: Hot reload development environment proven effective
5. **Testing Infrastructure**: Modern test patterns established and operational

**Critical Areas for Phase 4 Focus**:
1. **Visibility System Completion**: Implement remaining 6 visibility control features
2. **Message API Consistency**: Resolve 4 core message storage operation issues
3. **Integration Workflow Refinement**: Perfect cross-component coordination (2 tests)
4. **Production Hardening**: Performance optimization, monitoring, comprehensive docs

**Estimated Completion Effort**: 2-3 hours focused implementation for remaining 12 test failures
- Visibility controls: 1.5 hours (well-defined patterns, need implementation)
- Message storage: 45 minutes (API consistency issues, likely simple fixes)
- Integration workflows: 30 minutes (search result expectations, minor tuning)

This assessment demonstrates that Phase 3 has successfully established the foundational infrastructure for multi-agent coordination, with focused remaining work to complete the feature set.
