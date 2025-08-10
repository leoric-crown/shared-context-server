# Error Handling Guide

## Overview

This guide implements comprehensive error handling patterns for the Shared Context MCP Server, ensuring robust operation, meaningful error messages, and graceful degradation under failure conditions.

## Core Principles

### 1. Fail Fast, Recover Gracefully
- Detect errors early in the flow
- Provide specific, actionable error messages
- Always leave the system in a consistent state

### 2. Error Hierarchy
- Use specific exceptions over generic ones
- Maintain error context through the stack
- Log at appropriate levels

### 3. User-Friendly Responses
- Never expose internal details to clients
- Provide helpful error messages
- Include recovery suggestions when possible

## Error Hierarchy

### Base Exception Classes

```python
from typing import Optional, Dict, Any
from enum import Enum

class ErrorCode(str, Enum):
    """Standardized error codes for client handling."""
    
    # Authentication & Authorization (401-403)
    AUTHENTICATION_FAILED = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    TOKEN_INVALID = "AUTH_003"
    INSUFFICIENT_PERMISSIONS = "AUTH_004"
    
    # Resource Errors (404)
    SESSION_NOT_FOUND = "RESOURCE_001"
    MESSAGE_NOT_FOUND = "RESOURCE_002"
    MEMORY_KEY_NOT_FOUND = "RESOURCE_003"
    
    # Validation Errors (400)
    INVALID_INPUT = "VALIDATION_001"
    INVALID_SESSION_ID = "VALIDATION_002"
    INVALID_AGENT_ID = "VALIDATION_003"
    MESSAGE_TOO_LARGE = "VALIDATION_004"
    
    # Rate Limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_001"
    
    # Database Errors (500)
    DATABASE_CONNECTION_FAILED = "DB_001"
    DATABASE_LOCKED = "DB_002"
    DATABASE_INTEGRITY_ERROR = "DB_003"
    
    # MCP Protocol Errors (500)
    MCP_TOOL_NOT_FOUND = "MCP_001"
    MCP_TOOL_EXECUTION_FAILED = "MCP_002"
    MCP_RESOURCE_UNAVAILABLE = "MCP_003"
    
    # System Errors (500)
    INTERNAL_ERROR = "SYSTEM_001"
    SERVICE_UNAVAILABLE = "SYSTEM_002"
    MEMORY_LIMIT_EXCEEDED = "SYSTEM_003"

class SharedContextError(Exception):
    """Base exception for all Shared Context errors."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": {
                "message": self.message,
                "code": self.code.value,
                "details": self.details
            }
        }

class AuthenticationError(SharedContextError):
    """Authentication failures."""
    
    def __init__(self, message: str, code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED):
        super().__init__(message, code, status_code=401)

class AuthorizationError(SharedContextError):
    """Authorization failures."""
    
    def __init__(self, message: str, code: ErrorCode = ErrorCode.INSUFFICIENT_PERMISSIONS):
        super().__init__(message, code, status_code=403)

class ResourceNotFoundError(SharedContextError):
    """Resource not found errors."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        code: ErrorCode = ErrorCode.SESSION_NOT_FOUND
    ):
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(message, code, status_code=404, details={
            "resource_type": resource_type,
            "resource_id": resource_id
        })

class ValidationError(SharedContextError):
    """Input validation errors."""
    
    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        code: ErrorCode = ErrorCode.INVALID_INPUT
    ):
        message = f"Validation failed for {field}: {reason}"
        super().__init__(message, code, status_code=400, details={
            "field": field,
            "value": str(value)[:100],  # Truncate large values
            "reason": reason
        })

class RateLimitError(SharedContextError):
    """Rate limiting errors."""
    
    def __init__(
        self,
        limit: int,
        window: int,
        retry_after: int
    ):
        message = f"Rate limit exceeded: {limit} requests per {window} seconds"
        super().__init__(
            message,
            ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            details={
                "limit": limit,
                "window": window,
                "retry_after": retry_after
            }
        )

class DatabaseError(SharedContextError):
    """Database operation errors."""
    
    def __init__(
        self,
        operation: str,
        original_error: Optional[Exception] = None,
        code: ErrorCode = ErrorCode.DATABASE_CONNECTION_FAILED
    ):
        message = f"Database operation failed: {operation}"
        details = {"operation": operation}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, code, status_code=500, details=details)

class MCPError(SharedContextError):
    """MCP protocol errors."""
    
    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        code: ErrorCode = ErrorCode.MCP_TOOL_EXECUTION_FAILED
    ):
        details = {}
        if tool_name:
            details["tool"] = tool_name
        super().__init__(message, code, status_code=500, details=details)
```

## Error Handling Patterns

### Pattern 1: Graceful Database Error Handling

```python
import aiosqlite
import asyncio
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class DatabaseOperations:
    """Database operations with comprehensive error handling."""
    
    async def execute_with_retry(
        self,
        query: str,
        params: tuple,
        max_retries: int = 3,
        retry_delay: float = 0.1
    ):
        """Execute query with retry logic for transient errors."""
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with self.get_connection() as conn:
                    cursor = await conn.execute(query, params)
                    await conn.commit()
                    return cursor
                    
            except aiosqlite.OperationalError as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Handle specific operational errors
                if "database is locked" in error_msg:
                    logger.warning(f"Database locked, attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        raise DatabaseError(
                            "execute_query",
                            e,
                            ErrorCode.DATABASE_LOCKED
                        )
                
                elif "no such table" in error_msg:
                    # Non-retryable error
                    raise DatabaseError(
                        "execute_query",
                        e,
                        ErrorCode.DATABASE_INTEGRITY_ERROR
                    )
                
                else:
                    raise DatabaseError("execute_query", e)
            
            except aiosqlite.IntegrityError as e:
                # Constraint violations
                error_msg = str(e).lower()
                
                if "unique constraint failed" in error_msg:
                    # Extract field from error message
                    field = self._extract_constraint_field(error_msg)
                    raise ValidationError(
                        field,
                        params,
                        "Value already exists",
                        ErrorCode.INVALID_INPUT
                    )
                else:
                    raise DatabaseError(
                        "execute_query",
                        e,
                        ErrorCode.DATABASE_INTEGRITY_ERROR
                    )
            
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                raise DatabaseError("execute_query", e)
        
        # If we get here, all retries failed
        raise DatabaseError(
            "execute_query",
            last_error,
            ErrorCode.DATABASE_LOCKED
        )
    
    async def get_session_safe(self, session_id: str) -> Optional[Dict]:
        """Get session with proper error handling."""
        
        try:
            # Validate input first
            if not self._is_valid_session_id(session_id):
                raise ValidationError(
                    "session_id",
                    session_id,
                    "Invalid format",
                    ErrorCode.INVALID_SESSION_ID
                )
            
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT * FROM sessions WHERE id = ?",
                    (session_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    raise ResourceNotFoundError(
                        "Session",
                        session_id,
                        ErrorCode.SESSION_NOT_FOUND
                    )
                
                return dict(row)
                
        except SharedContextError:
            raise  # Re-raise our errors
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise DatabaseError("get_session", e)
    
    def _is_valid_session_id(self, session_id: str) -> bool:
        """Validate session ID format."""
        import re
        return bool(re.match(r'^[a-zA-Z0-9-_]{8,64}$', session_id))
    
    def _extract_constraint_field(self, error_msg: str) -> str:
        """Extract field name from constraint error."""
        # Parse SQLite error message
        import re
        match = re.search(r'(\w+)\.(\w+)', error_msg)
        if match:
            return match.group(2)
        return "field"
```

### Pattern 2: MCP Tool Error Handling

```python
from fastmcp import FastMCP
from typing import Any, Dict
import traceback

class MCPToolHandler:
    """MCP tool execution with error handling."""
    
    def __init__(self, mcp: FastMCP):
        self.mcp = mcp
    
    async def execute_tool_safe(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_id: str
    ) -> Dict[str, Any]:
        """Execute MCP tool with comprehensive error handling."""
        
        try:
            # Validate tool exists
            if not self._tool_exists(tool_name):
                raise MCPError(
                    f"Tool not found: {tool_name}",
                    tool_name,
                    ErrorCode.MCP_TOOL_NOT_FOUND
                )
            
            # Validate arguments
            validation_result = await self._validate_tool_arguments(
                tool_name,
                arguments
            )
            
            if not validation_result.is_valid:
                raise ValidationError(
                    "arguments",
                    arguments,
                    validation_result.errors[0],
                    ErrorCode.INVALID_INPUT
                )
            
            # Execute tool
            result = await self.mcp.call_tool(
                tool_name,
                arguments,
                context={"agent_id": agent_id}
            )
            
            return {
                "success": True,
                "result": result,
                "tool": tool_name
            }
            
        except MCPError:
            raise
        except ValidationError:
            raise
        except TimeoutError:
            raise MCPError(
                f"Tool execution timeout: {tool_name}",
                tool_name,
                ErrorCode.MCP_TOOL_EXECUTION_FAILED
            )
        except Exception as e:
            # Log full traceback for debugging
            logger.error(
                f"Tool execution failed: {tool_name}\n"
                f"Arguments: {arguments}\n"
                f"Error: {traceback.format_exc()}"
            )
            
            raise MCPError(
                f"Tool execution failed: {str(e)}",
                tool_name,
                ErrorCode.MCP_TOOL_EXECUTION_FAILED
            )
    
    def _tool_exists(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self.mcp.list_tools()
    
    async def _validate_tool_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ValidationResult:
        """Validate tool arguments against schema."""
        # Get tool schema
        tool_schema = self.mcp.get_tool_schema(tool_name)
        
        # Validate against Pydantic model
        try:
            tool_schema.validate(arguments)
            return ValidationResult(True)
        except Exception as e:
            return ValidationResult(False, [str(e)])
```

### Pattern 3: Circuit Breaker Pattern

```python
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls.
    
    Prevents cascading failures by temporarily blocking
    calls to failing services.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.lock = asyncio.Lock()
    
    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ):
        """Execute function through circuit breaker."""
        
        async with self.lock:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise ServiceUnavailableError(
                        f"Circuit breaker {self.name} is OPEN",
                        retry_after=self._get_retry_after()
                    )
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            async with self.lock:
                self._on_success()
            
            return result
            
        except Exception as e:
            async with self.lock:
                self._on_failure()
            
            if self.state == CircuitState.OPEN:
                raise ServiceUnavailableError(
                    f"Circuit breaker {self.name} opened due to failures",
                    retry_after=self._get_retry_after()
                )
            
            raise
    
    def _on_success(self):
        """Handle successful call."""
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.success_threshold:
                # Recovery successful
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit breaker {self.name} recovered")
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Recovery failed, reopen circuit
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker {self.name} reopened")
        
        elif self.failure_count >= self.failure_threshold:
            # Too many failures, open circuit
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker {self.name} opened after "
                f"{self.failure_count} failures"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit."""
        
        if not self.last_failure_time:
            return True
        
        time_since_failure = (
            datetime.now() - self.last_failure_time
        ).total_seconds()
        
        return time_since_failure >= self.recovery_timeout
    
    def _get_retry_after(self) -> int:
        """Get seconds until retry is allowed."""
        
        if not self.last_failure_time:
            return 0
        
        time_since_failure = (
            datetime.now() - self.last_failure_time
        ).total_seconds()
        
        return max(0, self.recovery_timeout - int(time_since_failure))

class ServiceUnavailableError(SharedContextError):
    """Service temporarily unavailable."""
    
    def __init__(self, message: str, retry_after: int = 0):
        super().__init__(
            message,
            ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
            details={"retry_after": retry_after}
        )

# Usage example
db_circuit = CircuitBreaker("database", failure_threshold=3)

async def get_data_with_circuit_breaker(session_id: str):
    return await db_circuit.call(
        database.get_session,
        session_id
    )
```

### Pattern 4: Error Recovery and Cleanup

```python
from contextlib import asynccontextmanager
import asyncio

class TransactionManager:
    """Manage transactions with automatic rollback on error."""
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        
        conn = None
        transaction_id = None
        
        try:
            # Acquire connection
            conn = await self.get_connection()
            
            # Start transaction
            await conn.execute("BEGIN")
            transaction_id = self._generate_transaction_id()
            
            logger.debug(f"Transaction {transaction_id} started")
            
            yield conn
            
            # Commit on success
            await conn.execute("COMMIT")
            logger.debug(f"Transaction {transaction_id} committed")
            
        except Exception as e:
            # Rollback on any error
            if conn:
                try:
                    await conn.execute("ROLLBACK")
                    logger.warning(f"Transaction {transaction_id} rolled back")
                except Exception as rollback_error:
                    logger.error(
                        f"Failed to rollback transaction {transaction_id}: "
                        f"{rollback_error}"
                    )
            
            # Re-raise the original error
            raise
            
        finally:
            # Always release connection
            if conn:
                await self.release_connection(conn)

class ResourceCleanup:
    """Ensure resources are cleaned up on error."""
    
    async def process_with_cleanup(
        self,
        session_id: str,
        operation: Callable
    ):
        """Process operation with guaranteed cleanup."""
        
        temp_files = []
        locks_held = []
        
        try:
            # Acquire resources
            lock = await self.acquire_session_lock(session_id)
            locks_held.append(lock)
            
            temp_file = await self.create_temp_file()
            temp_files.append(temp_file)
            
            # Perform operation
            result = await operation(temp_file)
            
            return result
            
        except Exception as e:
            logger.error(f"Operation failed for session {session_id}: {e}")
            
            # Cleanup on error
            await self._emergency_cleanup(session_id)
            
            raise
            
        finally:
            # Always cleanup resources
            for lock in locks_held:
                await self.release_lock(lock)
            
            for temp_file in temp_files:
                await self.delete_temp_file(temp_file)
    
    async def _emergency_cleanup(self, session_id: str):
        """Emergency cleanup on critical failure."""
        
        try:
            # Mark session as requiring cleanup
            await self.mark_session_for_cleanup(session_id)
            
            # Clear any cached data
            await cache.invalidate(session_id)
            
            # Log for manual review
            logger.critical(
                f"Emergency cleanup triggered for session {session_id}"
            )
            
        except Exception as cleanup_error:
            logger.error(f"Emergency cleanup failed: {cleanup_error}")
```

## Global Error Handler

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import traceback

app = FastAPI()

@app.exception_handler(SharedContextError)
async def shared_context_error_handler(
    request: Request,
    exc: SharedContextError
):
    """Handle application-specific errors."""
    
    # Log error with context
    logger.warning(
        f"Application error: {exc.code.value}\n"
        f"Path: {request.url.path}\n"
        f"Message: {exc.message}\n"
        f"Details: {exc.details}"
    )
    
    # Return user-friendly error response
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers=self._get_error_headers(exc)
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request,
    exc: ValidationError
):
    """Handle Pydantic validation errors."""
    
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "message": "Validation failed",
                "code": ErrorCode.INVALID_INPUT.value,
                "details": exc.errors()
            }
        }
    )

@app.exception_handler(Exception)
async def global_error_handler(
    request: Request,
    exc: Exception
):
    """Handle unexpected errors."""
    
    # Generate error ID for tracking
    error_id = generate_error_id()
    
    # Log full traceback
    logger.error(
        f"Unexpected error {error_id}:\n"
        f"Path: {request.url.path}\n"
        f"Error: {traceback.format_exc()}"
    )
    
    # Return generic error (don't expose internals)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An internal error occurred",
                "code": ErrorCode.INTERNAL_ERROR.value,
                "error_id": error_id
            }
        }
    )

def _get_error_headers(exc: SharedContextError) -> Dict[str, str]:
    """Get appropriate headers for error response."""
    
    headers = {}
    
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.details.get("retry_after", 60))
    
    elif isinstance(exc, ServiceUnavailableError):
        headers["Retry-After"] = str(exc.details.get("retry_after", 60))
    
    return headers
```

## Error Logging Strategy

```python
import logging
import logging.handlers
from pythonjsonlogger import jsonlogger

def setup_error_logging():
    """Configure comprehensive error logging."""
    
    # Create formatters
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    
    # Error file handler (errors and above)
    error_handler = logging.handlers.RotatingFileHandler(
        'errors.log',
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    
    # Warning file handler (warnings and above)
    warning_handler = logging.handlers.RotatingFileHandler(
        'warnings.log',
        maxBytes=10_000_000,
        backupCount=3
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(json_formatter)
    
    # Critical errors handler (send alerts)
    critical_handler = CriticalErrorHandler()
    critical_handler.setLevel(logging.CRITICAL)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(error_handler)
    root_logger.addHandler(warning_handler)
    root_logger.addHandler(critical_handler)

class CriticalErrorHandler(logging.Handler):
    """Send alerts for critical errors."""
    
    async def emit(self, record):
        """Send critical error alert."""
        
        try:
            # Send alert (email, Slack, etc.)
            await send_alert({
                "level": "CRITICAL",
                "message": record.getMessage(),
                "module": record.module,
                "timestamp": record.created
            })
        except Exception:
            # Don't let alert failure crash the app
            pass
```

## Testing Error Handling

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_database_retry_on_lock():
    """Test that database operations retry on lock."""
    
    db_ops = DatabaseOperations()
    
    # Mock connection that fails twice then succeeds
    mock_conn = Mock()
    mock_conn.execute = Mock(
        side_effect=[
            aiosqlite.OperationalError("database is locked"),
            aiosqlite.OperationalError("database is locked"),
            Mock()  # Success on third try
        ]
    )
    
    with patch.object(db_ops, 'get_connection', return_value=mock_conn):
        result = await db_ops.execute_with_retry(
            "SELECT 1",
            (),
            max_retries=3
        )
    
    # Should succeed after retries
    assert result is not None
    assert mock_conn.execute.call_count == 3

@pytest.mark.asyncio
async def test_circuit_breaker_opens():
    """Test circuit breaker opens after failures."""
    
    breaker = CircuitBreaker("test", failure_threshold=2)
    
    async def failing_function():
        raise Exception("Service error")
    
    # First failures should pass through
    with pytest.raises(Exception):
        await breaker.call(failing_function)
    
    with pytest.raises(Exception):
        await breaker.call(failing_function)
    
    # Circuit should now be open
    assert breaker.state == CircuitState.OPEN
    
    # Next call should fail immediately
    with pytest.raises(ServiceUnavailableError) as exc:
        await breaker.call(failing_function)
    
    assert "Circuit breaker" in str(exc.value)

@pytest.mark.asyncio
async def test_transaction_rollback():
    """Test transaction rollback on error."""
    
    manager = TransactionManager()
    
    async with manager.transaction() as conn:
        await conn.execute("INSERT INTO test VALUES (1)")
        
        # Simulate error
        raise Exception("Operation failed")
    
    # Verify rollback was called
    conn.execute.assert_any_call("ROLLBACK")
```

## Best Practices

### 1. Use Specific Exceptions
```python
# GOOD - Specific, actionable
raise ResourceNotFoundError("Session", session_id)

# BAD - Generic
raise Exception("Not found")
```

### 2. Include Context in Errors
```python
# GOOD - Includes context
raise ValidationError(
    field="session_id",
    value=session_id,
    reason="Invalid format"
)

# BAD - No context
raise ValueError("Invalid")
```

### 3. Log at Appropriate Levels
```python
logger.debug("Checking cache")  # Detailed flow
logger.info("Session created")  # Normal operations
logger.warning("Retry attempt")  # Potential issues
logger.error("Operation failed")  # Errors
logger.critical("System failure")  # Critical failures
```

## Common Pitfalls

### 1. ❌ Swallowing Errors
```python
# BAD - Hides errors
try:
    result = await operation()
except:
    pass

# GOOD - Handle appropriately
try:
    result = await operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### 2. ❌ Exposing Internal Details
```python
# BAD - Exposes internals
return {"error": str(exception)}

# GOOD - User-friendly message
return {"error": "Operation failed", "code": "SYSTEM_001"}
```

### 3. ❌ Not Cleaning Up on Error
```python
# BAD - Resource leak
conn = await get_connection()
result = await operation(conn)  # May fail

# GOOD - Guaranteed cleanup
async with get_connection() as conn:
    result = await operation(conn)
```

## References

- FastAPI Error Handling: https://fastapi.tiangolo.com/tutorial/handling-errors/
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
- Research findings: `/RESEARCH_FINDINGS_DEVELOPER.md`
- Testing patterns: `/RESEARCH_FINDINGS_TESTER.md`

## Related Guides

- Security & Authentication Guide - Auth error handling
- Performance Optimization Guide - Timeout handling
- Testing Patterns Guide - Error testing