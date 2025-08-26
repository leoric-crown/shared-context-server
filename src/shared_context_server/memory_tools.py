"""
Agent Memory Management Tools for Shared Context MCP Server.

Provides MCP tools for agent memory storage and retrieval:
- set_memory: Store values with TTL, scope, and metadata support
- get_memory: Retrieve values with automatic cleanup
- list_memory: List memory entries with filtering options

Built for multi-agent coordination with session isolation and global memory support.
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

# aiosqlite removed in favor of SQLAlchemy-only backend
from fastmcp import Context  # noqa: TC002
from pydantic import Field

# PERFORMANCE OPTIMIZATION: Pre-import commonly used modules
# to avoid repeated import overhead during function execution
from .auth import validate_agent_context_or_error

# Import core dependencies
from .core_server import mcp
from .database import get_db_connection
from .models import parse_mcp_metadata
from .utils.llm_errors import (
    ERROR_MESSAGE_PATTERNS,
    ErrorSeverity,
    create_llm_error_response,
    create_system_error,
)

logger = logging.getLogger(__name__)

# PERFORMANCE OPTIMIZATION: Lazy loading to avoid import overhead
# WebSocket and admin tools are loaded only when actually needed

# Cache for lazy-loaded modules
_lazy_imports = {}


def _get_websocket_handlers() -> dict[str, Any]:
    """Lazy load WebSocket handlers to avoid import overhead."""
    if "websocket" not in _lazy_imports:
        try:
            from .websocket_handlers import notify_websocket_server, websocket_manager

            _lazy_imports["websocket"] = {
                "notify_websocket_server": notify_websocket_server,
                "websocket_manager": websocket_manager,
                "available": True,
            }
        except ImportError:

            async def _no_op_notify(*_args: Any, **_kwargs: Any) -> None:
                logger.debug("WebSocket support not available, skipping notification")

            class _NoOpWebSocketManager:
                async def broadcast_to_session(
                    self, session_id: str, message: dict
                ) -> None:
                    logger.debug("WebSocket support not available, skipping broadcast")

            _lazy_imports["websocket"] = {
                "notify_websocket_server": _no_op_notify,
                "websocket_manager": _NoOpWebSocketManager(),
                "available": False,
            }
    return _lazy_imports["websocket"]


def _get_admin_tools() -> dict[str, Any]:
    """Lazy load admin tools to avoid import overhead."""
    if "admin" not in _lazy_imports:
        try:
            from .admin_tools import trigger_resource_notifications

            _lazy_imports["admin"] = {
                "trigger_resource_notifications": trigger_resource_notifications,
                "available": True,
            }
        except ImportError:

            async def _no_op_notifications(*_args: Any, **_kwargs: Any) -> None:
                logger.debug("Admin tools not available, skipping notifications")

            _lazy_imports["admin"] = {
                "trigger_resource_notifications": _no_op_notifications,
                "available": False,
            }
    return _lazy_imports["admin"]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def normalize_null_params(**kwargs: Any) -> dict[str, Any]:
    """
    Normalize null parameters for better API usability.

    Converts explicit null values to None and removes them from the parameter dict,
    making the API more forgiving of common JSON null value patterns.

    Args:
        **kwargs: Input parameters that may contain explicit null values

    Returns:
        Cleaned parameter dict with null values normalized
    """
    normalized = {}
    for key, value in kwargs.items():
        # Convert string "null" to None and remove from params
        if value == "null":
            continue
        # Keep all other values, including actual None
        normalized[key] = value
    return normalized


# Audit logging utility
async def audit_log(
    _conn: Any,  # SQLAlchemy connection wrapper
    action: str,
    agent_id: str,
    session_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add audit log entry for security tracking."""
    try:
        from .auth import audit_log_auth_event

        await audit_log_auth_event(action, agent_id, session_id, details)
    except Exception as e:
        logger.warning(f"Failed to write audit log: {e}")


# ============================================================================
# AGENT MEMORY SYSTEM
# ============================================================================


@mcp.tool(exclude_args=["ctx"])
async def set_memory(
    key: str = Field(description="Memory key", min_length=1, max_length=255),
    value: Any = Field(
        description="Value to store (JSON serializable - objects will be auto-converted)",
        json_schema_extra={"type": "object", "additionalProperties": True},
    ),
    session_id: str | None = Field(
        default=None,
        description="Session scope (null for global memory)",
    ),
    expires_in: int | str | None = Field(
        default=None,
        description="TTL in seconds (null for permanent)",
    ),
    metadata: Any = Field(
        default=None,
        description="Optional metadata for the memory entry (JSON object or null)",
        examples=[{"source": "user_input", "tags": ["important"]}, None],
        json_schema_extra={"type": "object", "additionalProperties": True},
    ),
    overwrite: bool = Field(
        default=True, description="Whether to overwrite existing key"
    ),
    auth_token: str | None = Field(
        default=None,
        description="Optional JWT token for elevated permissions",
    ),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Store value in agent's private memory with TTL and scope management.

    Memory can be session-scoped (isolated to specific session) or global
    (available across all sessions for the agent).
    """
    # Normalize null parameters for better API usability
    normalized_params = normalize_null_params(
        session_id=session_id,
        expires_in=expires_in,
        metadata=metadata,
        auth_token=auth_token,
    )
    session_id = normalized_params.get("session_id", None)
    expires_in = normalized_params.get("expires_in", None)
    metadata = normalized_params.get("metadata", None)
    auth_token = normalized_params.get("auth_token", None)

    try:
        # Validate and sanitize the key
        key = key.strip()
        if not key:
            return create_llm_error_response(
                error="Memory key cannot be empty after trimming whitespace",
                code="INVALID_KEY",
                suggestions=[
                    "Provide a non-empty memory key",
                    "Use descriptive key names like 'user_preferences' or 'session_state'",
                    "Keys should be alphanumeric with underscores or dashes",
                ],
                context={"field": "key", "requirement": "non_empty_string"},
                severity=ErrorSeverity.WARNING,
            )

        # Parse metadata from MCP client (handles both string and dict inputs)
        try:
            metadata = parse_mcp_metadata(metadata)
        except ValueError as e:
            return create_llm_error_response(
                error=f"Invalid metadata format: {str(e)}",
                code="INVALID_METADATA_FORMAT",
                suggestions=[
                    "Provide metadata as a JSON object (dictionary)",
                    "Use null for no metadata",
                    'Example: {"key": "value", "nested": {"data": "example"}}',
                ],
                context={"field": "metadata", "expected_type": "dict or null"},
                severity=ErrorSeverity.WARNING,
            )

        if len(key) > 255:
            return create_llm_error_response(
                error="Memory key too long (max 255 characters)",
                code="INVALID_KEY",
                suggestions=[
                    "Shorten the memory key to 255 characters or less",
                    "Use abbreviated key names",
                    "Consider using hierarchical keys with dots or underscores",
                ],
                context={"key_length": len(key), "max_length": 255},
                severity=ErrorSeverity.WARNING,
            )

        if "\n" in key or "\t" in key or " " in key:
            return ERROR_MESSAGE_PATTERNS["memory_key_invalid"](key)  # type: ignore[no-any-return,operator]

        # Extract and validate agent context (with token validation error handling)
        agent_context = await validate_agent_context_or_error(ctx, auth_token)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]

        # Check write permission
        if "write" not in agent_context.get("permissions", []):
            return ERROR_MESSAGE_PATTERNS["write_required"](  # type: ignore[no-any-return,operator]
                agent_context.get("permissions", [])
            )

        # Validate and process expires_in parameter
        expires_in_seconds = None
        if expires_in is not None:
            try:
                # Convert string to int if needed
                if isinstance(expires_in, str):
                    expires_in_seconds = int(expires_in)
                else:
                    expires_in_seconds = expires_in

                # Validate range - treat 0 as "no expiration"
                if expires_in_seconds < 0:
                    return create_llm_error_response(
                        error="expires_in cannot be negative",
                        code="INVALID_TTL_VALUE",
                        suggestions=[
                            "Use 0 for no expiration or positive integer for TTL",
                            "Example: expires_in: 3600 (1 hour)",
                        ],
                    )

                if expires_in_seconds > 86400 * 365:  # Max 1 year
                    return create_llm_error_response(
                        error="expires_in cannot exceed 1 year (31536000 seconds)",
                        code="INVALID_TTL_VALUE",
                        suggestions=[
                            "Use a smaller TTL value",
                            "Maximum is 31536000 seconds (1 year)",
                        ],
                    )

            except (ValueError, TypeError) as e:
                return create_llm_error_response(
                    error=f"Invalid expires_in format: {str(e)}",
                    code="INVALID_TTL_FORMAT",
                    suggestions=[
                        "Use an integer value for expires_in",
                        "Example: expires_in: 3600 (for 1 hour)",
                    ],
                )

        # TTL validation and warning for short durations
        if expires_in_seconds and expires_in_seconds < 10:
            logger.warning(
                f"Short TTL detected ({expires_in_seconds}s) for key '{key}' - "
                "may expire faster than expected due to processing time"
            )

        # Serialize value to JSON with error handling
        try:
            if not isinstance(value, str):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = value
        except (TypeError, ValueError) as e:
            return create_llm_error_response(
                error=f"Value is not JSON serializable: {str(e)}",
                code="SERIALIZATION_ERROR",
                suggestions=[
                    "Ensure the value contains only JSON-compatible data types",
                    "Supported types: strings, numbers, booleans, lists, dictionaries",
                    "Remove or convert unsupported types like functions, classes, or custom objects",
                ],
                context={"value_type": type(value).__name__, "error_detail": str(e)},
                severity=ErrorSeverity.WARNING,
            )

        async with get_db_connection() as conn:
            conn.row_factory = None  # Use SQLAlchemy row type

            # Calculate timestamps just before database operations to minimize timing gap
            now_timestamp = datetime.now(timezone.utc)
            created_at_timestamp = now_timestamp.timestamp()
            expires_at = None
            if expires_in_seconds and expires_in_seconds > 0:
                expires_at = created_at_timestamp + expires_in_seconds

            # Check if session exists (if session-scoped)
            if session_id:
                cursor = await conn.execute(
                    "SELECT id FROM sessions WHERE id = ?", (session_id,)
                )
                if not await cursor.fetchone():
                    return ERROR_MESSAGE_PATTERNS["session_not_found"](session_id)  # type: ignore[no-any-return,operator]

            # Check for existing key if overwrite is False
            if not overwrite:
                cursor = await conn.execute(
                    """
                    SELECT key FROM agent_memory
                    WHERE agent_id = ? AND key = ?
                    AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
                    AND (expires_at IS NULL OR expires_at > ?)
                """,
                    (
                        agent_id,
                        key,
                        session_id,
                        session_id,
                        datetime.now(timezone.utc).timestamp(),
                    ),
                )

                if await cursor.fetchone():
                    return ERROR_MESSAGE_PATTERNS["memory_key_exists"](key)  # type: ignore[no-any-return,operator]

            # Insert or update memory entry using manual upsert
            # Check if entry already exists
            cursor = await conn.execute(
                """
                SELECT id FROM agent_memory
                WHERE agent_id = ? AND key = ?
                AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
            """,
                (agent_id, key, session_id, session_id),
            )
            existing_row = await cursor.fetchone()

            if existing_row:
                # Update existing entry
                await conn.execute(
                    """
                    UPDATE agent_memory
                    SET value = ?, metadata = ?, updated_at = ?, expires_at = ?
                    WHERE agent_id = ? AND key = ?
                    AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
                """,
                    (
                        serialized_value,
                        json.dumps(metadata or {}),
                        now_timestamp.isoformat(),
                        expires_at,
                        agent_id,
                        key,
                        session_id,
                        session_id,
                    ),
                )
            else:
                # Insert new entry
                await conn.execute(
                    """
                    INSERT INTO agent_memory
                    (agent_id, session_id, key, value, metadata, created_at, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        agent_id,
                        session_id,
                        key,
                        serialized_value,
                        json.dumps(metadata or {}),
                        created_at_timestamp,  # Explicit created_at to ensure constraint works
                        expires_at,
                        now_timestamp.isoformat(),
                    ),
                )
            await conn.commit()

            # Audit log
            await audit_log(
                conn,
                "memory_set",
                agent_id,
                session_id,
                {
                    "key": key,
                    "session_scoped": session_id is not None,
                    "has_expiration": expires_at is not None,
                    "value_size": len(serialized_value),
                },
            )

            # Trigger resource notifications using lazy-loaded admin tools
            admin_tools = _get_admin_tools()
            try:
                await admin_tools["trigger_resource_notifications"](
                    session_id or "global", agent_id
                )
            except Exception as e:
                logger.warning(f"Failed to trigger resource notifications: {e}")

            # Send WebSocket notification for memory updates
            if session_id:  # Only notify for session-scoped memory
                websocket_handlers = _get_websocket_handlers()
                try:
                    memory_data = {
                        "type": "memory_update",
                        "data": {
                            "agent_id": agent_id,
                            "key": key,
                            "value": value,
                            "session_id": session_id,
                            "scope": "session",
                            "created_at": created_at_timestamp,
                            "updated_at": now_timestamp.isoformat(),
                        },
                    }

                    # OPTIMIZED: Use lazy-loaded WebSocket functions
                    # Broadcast to session via WebSocket manager
                    await websocket_handlers["websocket_manager"].broadcast_to_session(
                        session_id, memory_data
                    )

                    # HTTP bridge notification to WebSocket server
                    await websocket_handlers["notify_websocket_server"](
                        session_id, memory_data
                    )
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket memory notification: {e}")

        return {
            "success": True,
            "key": key,
            "session_scoped": session_id is not None,
            "expires_at": expires_at,
            "scope": "session" if session_id else "global",
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        logger.exception("Failed to set memory")
        logger.debug(traceback.format_exc())
        return create_system_error("set_memory", "database", temporary=True)


@mcp.tool(exclude_args=["ctx"])
async def get_memory(
    key: str = Field(description="Memory key to retrieve"),
    session_id: str | None = Field(
        default=None,
        description="Session scope (null for global memory)",
    ),
    auth_token: str | None = Field(
        default=None,
        description="Optional JWT token for elevated permissions",
    ),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    Retrieve value from agent's private memory with automatic cleanup.
    """
    # Normalize null parameters for better API usability
    normalized_params = normalize_null_params(
        session_id=session_id, auth_token=auth_token
    )
    session_id = normalized_params.get("session_id", None)
    auth_token = normalized_params.get("auth_token", None)

    try:
        # Extract and validate agent context (with token validation error handling)
        agent_context = await validate_agent_context_or_error(ctx, auth_token)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]
        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            conn.row_factory = None  # Use SQLAlchemy row type
            # Clean expired entries first
            await conn.execute(
                """
                DELETE FROM agent_memory
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """,
                (current_timestamp,),
            )

            # Retrieve memory entry
            # Note: Global memory (session_id IS NULL) is only accessible when session_id parameter is NULL
            # This ensures session-scoped calls don't accidentally access global memory
            cursor = await conn.execute(
                """
                SELECT key, value, metadata, created_at, updated_at, expires_at
                FROM agent_memory
                WHERE agent_id = ? AND key = ?
                AND (session_id = ? OR (? IS NULL AND session_id IS NULL))
                AND (expires_at IS NULL OR expires_at > ?)
            """,
                (agent_id, key, session_id, session_id, current_timestamp),
            )

            row = await cursor.fetchone()

            if not row:
                return ERROR_MESSAGE_PATTERNS["memory_not_found"](key)  # type: ignore[no-any-return,operator]

            # Parse stored value
            stored_value = row["value"]
            try:
                # Try to deserialize JSON
                parsed_value = json.loads(stored_value)
            except json.JSONDecodeError:
                # If not JSON, return as string
                parsed_value = stored_value

            # Parse metadata
            metadata = {}
            if row["metadata"]:
                try:
                    metadata = json.loads(row["metadata"])
                except json.JSONDecodeError:
                    metadata = {}

            return {
                "success": True,
                "key": key,
                "value": parsed_value,
                "metadata": metadata,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"],
                "scope": "session" if session_id else "global",
            }

    except Exception:
        logger.exception("Failed to get memory")
        logger.debug(traceback.format_exc())
        return create_system_error("get_memory", "database", temporary=True)


@mcp.tool(exclude_args=["ctx"])
async def list_memory(
    session_id: str | None = Field(
        default=None, description="Session scope (null for global, 'all' for both)"
    ),
    prefix: str | None = Field(
        default=None,
        description="Key prefix filter",
    ),
    auth_token: str | None = Field(
        default=None,
        description="Optional JWT token for elevated permissions",
    ),
    limit: int = Field(default=50, ge=1, le=200),
    ctx: Context = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """
    List agent's memory entries with filtering options.
    """
    # Normalize null parameters for better API usability
    normalized_params = normalize_null_params(
        session_id=session_id, prefix=prefix, auth_token=auth_token
    )
    session_id = normalized_params.get("session_id", None)
    prefix = normalized_params.get("prefix", None)
    auth_token = normalized_params.get("auth_token", None)

    try:
        # Extract and validate agent context (with token validation error handling)
        agent_context = await validate_agent_context_or_error(ctx, auth_token)

        # If validation failed, return the error response immediately
        if "error" in agent_context and agent_context.get("code") in [
            "INVALID_TOKEN_FORMAT",
            "TOKEN_AUTHENTICATION_FAILED",
        ]:
            return agent_context

        agent_id = agent_context["agent_id"]
        current_timestamp = datetime.now(timezone.utc).timestamp()

        async with get_db_connection() as conn:
            conn.row_factory = None  # Use SQLAlchemy row type
            # Clean expired entries
            await conn.execute(
                """
                DELETE FROM agent_memory
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """,
                (current_timestamp,),
            )

            # Build query based on scope
            where_conditions = ["agent_id = ?"]
            params = [agent_id]

            if session_id == "all":
                # Include both global and session-scoped entries
                pass
            elif session_id:
                # Specific session scope
                where_conditions.append("session_id = ?")
                params.append(session_id)
            else:
                # Global scope only (session_id is None or empty)
                where_conditions.append("session_id IS NULL")

            if prefix:
                where_conditions.append("key LIKE ?")
                params.append(f"{prefix}%")

            where_conditions.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(current_timestamp)

            params.append(limit)

            cursor = await conn.execute(
                f"""
                SELECT key, session_id, created_at, updated_at, expires_at,
                       length(value) as value_size
                FROM agent_memory
                WHERE {" AND ".join(where_conditions)}
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                params,
            )

            entries_rows = await cursor.fetchall()
            entries = [
                {
                    "key": entry["key"],
                    "scope": "session" if entry["session_id"] else "global",
                    "session_id": entry["session_id"],
                    "created_at": entry["created_at"],
                    "updated_at": entry["updated_at"],
                    "expires_at": entry["expires_at"],
                    "value_size": entry["value_size"],
                }
                for entry in entries_rows
            ]

            return {
                "success": True,
                "entries": entries,
                "count": len(entries),
                "scope_filter": session_id or "global",
            }

    except Exception:
        logger.exception("Failed to list memory")
        logger.debug(traceback.format_exc())
        return create_system_error("list_memory", "database", temporary=True)
