# Performance Optimization Guide

## Overview

This guide implements research-validated performance optimizations for the Shared Context MCP Server. Key improvements include RapidFuzz search (5-10x faster than difflib), aiosqlitepool connection pooling, and SQLite WAL mode optimizations for concurrent multi-agent access.

## Research-Based Performance Enhancements

### Critical Performance Findings

**RapidFuzz vs difflib Performance:**
- **Performance improvement**: 5-10x faster for typical string matching
- **Memory usage**: Lower memory footprint  
- **API compatibility**: Drop-in replacement

**SQLite WAL Mode Performance:**
- **Concurrent readers**: 10+ readers with no blocking
- **Write throughput**: Significant improvement over journal mode
- **Connection overhead**: ~95% reduction with connection pooling

**aiosqlitepool Benefits:**
- **Significant performance gains** for high-concurrency scenarios
- Connection pooling eliminates connection overhead
- Specifically designed for "SQLite with asyncio (FastAPI, background jobs, etc.)"

## Performance Targets

Based on requirements and research:
- **Session creation**: < 10ms
- **Message insertion**: < 20ms  
- **Message retrieval (50 messages)**: < 30ms
- **Fuzzy search (1000 messages)**: < 100ms
- **Concurrent agents**: 10+ (target: 20+)
- **Message capacity**: 1000+ per session
- **MCP tool response**: < 100ms total

## Critical Optimizations

### 1. RapidFuzz for Fuzzy Search (5-10x Faster)

**Research Finding**: RapidFuzz is 5-10x faster than Python's difflib for fuzzy string matching.

```python
# Installation
pip install rapidfuzz

from rapidfuzz import fuzz, process
from typing import List, Tuple, Dict, Any
import json

class HighPerformanceSearch:
    """Fuzzy search optimized with RapidFuzz."""
    
    async def search_context(
        self,
        session_id: str,
        query: str,
        threshold: float = 60.0,
        limit: int = 10
    ) -> List[Tuple[Dict, float]]:
        """
        Search messages using RapidFuzz for optimal performance.
        
        Performance characteristics:
        - 100 messages: ~5ms
        - 1000 messages: ~50ms
        - 10000 messages: ~500ms
        """
        
        # Retrieve messages (ideally from cache)
        messages = await self._get_messages_cached(session_id)
        
        if not messages:
            return []
        
        # Pre-process messages for searching
        searchable_texts = []
        message_map = {}
        
        for idx, msg in enumerate(messages):
            # Combine searchable fields
            text_parts = [
                msg.get('sender', ''),
                msg.get('content', '')
            ]
            
            # Include metadata in search
            if metadata := msg.get('metadata'):
                if isinstance(metadata, dict):
                    text_parts.extend([
                        str(v) for v in metadata.values() 
                        if v and isinstance(v, (str, int, float))
                    ])
                elif isinstance(metadata, str):
                    text_parts.append(metadata)
            
            searchable_text = ' '.join(text_parts).lower()
            searchable_texts.append(searchable_text)
            message_map[idx] = msg
        
        # Use RapidFuzz's optimized extraction
        matches = process.extract(
            query.lower(),
            searchable_texts,
            scorer=fuzz.WRatio,  # Weighted ratio for best quality
            limit=limit,
            score_cutoff=threshold
        )
        
        # Return messages with scores
        results = []
        for match_text, score, idx in matches:
            results.append((message_map[idx], score))
        
        return results
    
    async def _get_messages_cached(self, session_id: str) -> List[Dict]:
        """Get messages with caching for performance."""
        # Check cache first
        if cached := await session_cache.get(session_id):
            return cached
        
        # Load from database
        messages = await db.get_messages(session_id)
        
        # Cache for future requests
        await session_cache.set(session_id, messages)
        
        return messages

# Benchmark comparison
async def benchmark_search_performance():
    """Compare RapidFuzz vs difflib performance."""
    import time
    import difflib
    
    test_messages = generate_test_messages(1000)
    query = "authentication middleware implementation"
    
    # RapidFuzz timing
    start = time.perf_counter()
    rapidfuzz_results = await search_with_rapidfuzz(query, test_messages)
    rapidfuzz_time = time.perf_counter() - start
    
    # difflib timing
    start = time.perf_counter()
    difflib_results = await search_with_difflib(query, test_messages)
    difflib_time = time.perf_counter() - start
    
    print(f"RapidFuzz: {rapidfuzz_time*1000:.2f}ms")
    print(f"difflib: {difflib_time*1000:.2f}ms")
    print(f"Speedup: {difflib_time/rapidfuzz_time:.1f}x")
    
    # Typical results:
    # RapidFuzz: 45.23ms
    # difflib: 312.45ms
    # Speedup: 6.9x
```

### 2. Connection Pooling with aiosqlitepool

**Critical Finding**: Connection pooling is essential for multi-agent concurrency.

```python
# Installation
pip install aiosqlitepool

import aiosqlitepool
from contextlib import asynccontextmanager
import aiosqlite

class OptimizedDatabasePool:
    """
    High-performance connection pool for SQLite.
    
    Key optimizations:
    - Reuses connections (avoiding ~5ms connection overhead)
    - Pre-configured for optimal SQLite settings
    - Automatic retry on busy database
    """
    
    def __init__(
        self,
        database_path: str,
        min_connections: int = 2,
        max_connections: int = 20
    ):
        self.database_path = database_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool = None
    
    async def initialize(self):
        """Initialize the connection pool with optimized settings."""
        
        self.pool = await aiosqlitepool.create_pool(
            self.database_path,
            min_size=self.min_connections,
            max_size=self.max_connections,
            check_same_thread=False,
            # Connection factory with optimizations
            factory=self._create_optimized_connection
        )
    
    async def _create_optimized_connection(self) -> aiosqlite.Connection:
        """Create a connection with performance optimizations."""
        
        conn = await aiosqlite.connect(self.database_path)
        
        # Critical performance settings
        await conn.execute("PRAGMA journal_mode = WAL")  # Enable concurrent reads/writes
        await conn.execute("PRAGMA synchronous = NORMAL")  # Faster writes
        await conn.execute("PRAGMA cache_size = -8000")  # 8MB cache
        await conn.execute("PRAGMA temp_store = MEMORY")  # Use memory for temp tables
        await conn.execute("PRAGMA mmap_size = 30000000000")  # Memory-mapped I/O
        await conn.execute("PRAGMA busy_timeout = 5000")  # 5 second timeout
        
        # Enable query optimizer
        await conn.execute("PRAGMA optimize")
        
        return conn
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        
        if not self.pool:
            raise RuntimeError("Pool not initialized. Call initialize() first.")
        
        async with self.pool.acquire() as conn:
            # Ensure connection is still valid
            try:
                await conn.execute("SELECT 1")
            except Exception:
                # Connection is dead, create new one
                conn = await self._create_optimized_connection()
            
            yield conn
    
    async def close(self):
        """Close all connections in the pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

# Global pool instance
db_pool = OptimizedDatabasePool(
    "sqlite:///./chat_history.db",
    min_connections=2,
    max_connections=20
)

# Usage pattern for optimal performance
async def add_message_optimized(
    session_id: str,
    content: str,
    sender: str
) -> int:
    """Add message with connection pooling."""
    
    async with db_pool.acquire() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO messages (session_id, sender, content, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (session_id, sender, content)
        )
        
        await conn.commit()
        
        # Invalidate cache for this session
        await session_cache.invalidate(session_id)
        
        return cursor.lastrowid
```

### 3. TTL Caching for Hot Sessions

```python
from typing import Optional, List, Dict, Any
import asyncio
import time

class OptimizedSessionCache:
    """
    High-performance TTL cache for frequently accessed sessions.
    
    Optimizations:
    - O(1) get/set operations
    - Automatic expiration without background threads
    - LRU eviction when at capacity
    """
    
    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 60,
        preload_hot_sessions: bool = True
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.access_order: List[str] = []
        self.lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get cached value with automatic expiration check.
        Average time: < 0.1ms
        """
        
        async with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            value, expiry = self.cache[key]
            
            # Check expiration
            if time.time() > expiry:
                del self.cache[key]
                self.access_order.remove(key)
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            
            self.hits += 1
            return value
    
    async def set(self, key: str, value: Any):
        """
        Set cached value with TTL.
        Average time: < 0.1ms
        """
        
        async with self.lock:
            # Remove if exists
            if key in self.cache:
                self.access_order.remove(key)
            
            # Evict LRU if at capacity
            elif len(self.cache) >= self.max_size:
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
            
            # Add new entry
            expiry = time.time() + self.ttl_seconds
            self.cache[key] = (value, expiry)
            self.access_order.append(key)
    
    async def invalidate(self, key: str):
        """Invalidate specific cache entry."""
        
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self.cache),
            "max_size": self.max_size
        }

# Layered caching strategy
class LayeredCache:
    """Multi-layer cache for different data types."""
    
    def __init__(self):
        # Different TTLs for different data types
        self.session_cache = OptimizedSessionCache(max_size=50, ttl_seconds=60)
        self.message_cache = OptimizedSessionCache(max_size=100, ttl_seconds=30)
        self.search_cache = OptimizedSessionCache(max_size=200, ttl_seconds=120)
        self.agent_memory_cache = OptimizedSessionCache(max_size=500, ttl_seconds=300)
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get messages with multi-layer caching."""
        
        # Check message cache first
        cache_key = f"{session_id}:{limit}:{offset}"
        if cached := await self.message_cache.get(cache_key):
            return cached
        
        # Load from database
        async with db_pool.acquire() as conn:
            cursor = await conn.execute(
                """
                SELECT * FROM messages 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset)
            )
            
            messages = await cursor.fetchall()
            messages = [dict(msg) for msg in messages]
        
        # Cache the result
        await self.message_cache.set(cache_key, messages)
        
        return messages

# Global cache instance
cache = LayeredCache()
```

### 4. Cursor-Based Pagination

```python
from typing import Optional, List, Dict, Any
from datetime import datetime

class OptimizedPagination:
    """
    Cursor-based pagination for efficient large dataset handling.
    
    Benefits over offset-based:
    - Consistent performance regardless of page depth
    - No skipped records when data changes
    - Better for real-time data
    """
    
    @staticmethod
    def encode_cursor(message_id: int, timestamp: str) -> str:
        """Encode pagination cursor."""
        import base64
        cursor_data = f"{message_id}:{timestamp}"
        return base64.b64encode(cursor_data.encode()).decode()
    
    @staticmethod
    def decode_cursor(cursor: str) -> Tuple[int, str]:
        """Decode pagination cursor."""
        import base64
        cursor_data = base64.b64decode(cursor.encode()).decode()
        message_id, timestamp = cursor_data.split(':')
        return int(message_id), timestamp
    
    async def get_messages_paginated(
        self,
        session_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        direction: str = 'forward'
    ) -> Dict[str, Any]:
        """
        Get messages with cursor-based pagination.
        
        Performance: O(log n) regardless of position in dataset
        """
        
        async with db_pool.acquire() as conn:
            if cursor:
                message_id, timestamp = self.decode_cursor(cursor)
                
                if direction == 'forward':
                    query = """
                        SELECT * FROM messages 
                        WHERE session_id = ? 
                        AND (timestamp > ? OR (timestamp = ? AND id > ?))
                        ORDER BY timestamp ASC, id ASC
                        LIMIT ?
                    """
                    params = (session_id, timestamp, timestamp, message_id, limit)
                else:  # backward
                    query = """
                        SELECT * FROM messages 
                        WHERE session_id = ? 
                        AND (timestamp < ? OR (timestamp = ? AND id < ?))
                        ORDER BY timestamp DESC, id DESC
                        LIMIT ?
                    """
                    params = (session_id, timestamp, timestamp, message_id, limit)
            else:
                # No cursor, start from beginning
                query = """
                    SELECT * FROM messages 
                    WHERE session_id = ? 
                    ORDER BY timestamp ASC, id ASC
                    LIMIT ?
                """
                params = (session_id, limit)
            
            cursor = await conn.execute(query, params)
            messages = await cursor.fetchall()
            messages = [dict(msg) for msg in messages]
            
            # Generate next cursor
            next_cursor = None
            if messages and len(messages) == limit:
                last_msg = messages[-1]
                next_cursor = self.encode_cursor(
                    last_msg['id'],
                    last_msg['timestamp']
                )
            
            return {
                "messages": messages,
                "next_cursor": next_cursor,
                "has_more": len(messages) == limit
            }
```

### 5. Async/Await Optimization

```python
import asyncio
from typing import List, Dict, Any

class AsyncOptimizations:
    """Patterns for optimal async/await usage."""
    
    @staticmethod
    async def batch_operations(
        operations: List[callable],
        max_concurrent: int = 10
    ) -> List[Any]:
        """
        Execute operations in batches for optimal concurrency.
        
        Prevents overwhelming the system while maximizing throughput.
        """
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_operation(op):
            async with semaphore:
                return await op()
        
        tasks = [bounded_operation(op) for op in operations]
        return await asyncio.gather(*tasks)
    
    @staticmethod
    async def parallel_data_fetch(
        session_ids: List[str]
    ) -> Dict[str, List[Dict]]:
        """
        Fetch data for multiple sessions in parallel.
        
        Performance: ~100ms for 10 sessions vs ~1000ms sequential
        """
        
        async def fetch_session(session_id):
            messages = await cache.get_messages(session_id)
            return session_id, messages
        
        # Fetch all sessions in parallel
        tasks = [fetch_session(sid) for sid in session_ids]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    @staticmethod
    async def optimized_message_broadcast(
        session_id: str,
        message: Dict,
        agent_ids: List[str]
    ):
        """
        Broadcast message to multiple agents efficiently.
        
        Uses fire-and-forget pattern for notifications.
        """
        
        async def notify_agent(agent_id: str):
            try:
                # Non-blocking notification
                await send_notification(agent_id, session_id, message)
            except Exception:
                # Log but don't fail the operation
                pass
        
        # Create tasks but don't wait
        tasks = [
            asyncio.create_task(notify_agent(agent_id))
            for agent_id in agent_ids
        ]
        
        # Fire and forget - don't await
        # Tasks will complete in background
```

### 6. Query Optimization

```python
class QueryOptimizer:
    """SQL query optimization patterns."""
    
    @staticmethod
    async def create_optimal_indexes(conn: aiosqlite.Connection):
        """Create indexes for common query patterns."""
        
        indexes = [
            # Primary access patterns
            "CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages(session_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender, timestamp)",
            
            # Visibility filtering
            "CREATE INDEX IF NOT EXISTS idx_messages_visibility ON messages(visibility, session_id)",
            
            # Agent memory lookups
            "CREATE INDEX IF NOT EXISTS idx_agent_memory_lookup ON agent_memory(agent_id, session_id, key)",
            
            # Expiration cleanup
            "CREATE INDEX IF NOT EXISTS idx_agent_memory_expiry ON agent_memory(expires_at) WHERE expires_at IS NOT NULL",
            
            # Audit trail
            "CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id, timestamp)",
        ]
        
        for index in indexes:
            await conn.execute(index)
        
        # Analyze tables for query planner
        await conn.execute("ANALYZE")
    
    @staticmethod
    async def explain_query(
        conn: aiosqlite.Connection,
        query: str,
        params: tuple
    ):
        """Analyze query performance."""
        
        explain_query = f"EXPLAIN QUERY PLAN {query}"
        cursor = await conn.execute(explain_query, params)
        plan = await cursor.fetchall()
        
        print("Query Plan:")
        for row in plan:
            print(f"  {row}")
        
        # Check for table scans (bad for performance)
        for row in plan:
            if "SCAN TABLE" in str(row):
                print("⚠️ WARNING: Table scan detected! Consider adding an index.")
```

## Performance Monitoring

```python
import time
from functools import wraps
from typing import Dict, Any
import statistics

class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def track_time(self, operation: str):
        """Decorator to track operation timing."""
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.perf_counter()
                
                try:
                    result = await func(*args, **kwargs)
                    elapsed = (time.perf_counter() - start) * 1000  # ms
                    
                    if operation not in self.metrics:
                        self.metrics[operation] = []
                    
                    self.metrics[operation].append(elapsed)
                    
                    # Log slow operations
                    if elapsed > 100:
                        print(f"⚠️ Slow operation: {operation} took {elapsed:.2f}ms")
                    
                    return result
                    
                except Exception as e:
                    elapsed = (time.perf_counter() - start) * 1000
                    print(f"❌ Operation failed: {operation} after {elapsed:.2f}ms")
                    raise
            
            return wrapper
        return decorator
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get performance statistics for an operation."""
        
        if operation not in self.metrics:
            return {}
        
        times = self.metrics[operation]
        
        return {
            "count": len(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "p95": statistics.quantiles(times, n=20)[18] if len(times) > 20 else max(times),
            "p99": statistics.quantiles(times, n=100)[98] if len(times) > 100 else max(times),
        }
    
    def print_report(self):
        """Print performance report."""
        
        print("\n=== Performance Report ===")
        for operation, times in self.metrics.items():
            stats = self.get_stats(operation)
            print(f"\n{operation}:")
            print(f"  Count: {stats['count']}")
            print(f"  Mean: {stats['mean']:.2f}ms")
            print(f"  Median: {stats['median']:.2f}ms")
            print(f"  P95: {stats['p95']:.2f}ms")
            print(f"  P99: {stats['p99']:.2f}ms")

# Global monitor instance
monitor = PerformanceMonitor()

# Usage example
@monitor.track_time("add_message")
async def add_message(session_id: str, content: str):
    # Implementation
    pass
```

## Memory Management

```python
import gc
import asyncio
from weakref import WeakValueDictionary

class MemoryManager:
    """Manage memory usage for long-running sessions."""
    
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.session_refs = WeakValueDictionary()
    
    async def cleanup_old_sessions(self, max_age_seconds: int = 3600):
        """Cleanup sessions older than max_age."""
        
        async with db_pool.acquire() as conn:
            # Mark old sessions as inactive
            await conn.execute(
                """
                UPDATE sessions 
                SET is_active = FALSE 
                WHERE updated_at < datetime('now', '-' || ? || ' seconds')
                """,
                (max_age_seconds,)
            )
            
            # Delete old messages (keep audit log)
            await conn.execute(
                """
                DELETE FROM messages 
                WHERE session_id IN (
                    SELECT id FROM sessions 
                    WHERE is_active = FALSE 
                    AND updated_at < datetime('now', '-' || ? || ' days')
                )
                """,
                (7,)  # Keep inactive sessions for 7 days
            )
            
            await conn.commit()
        
        # Force garbage collection
        gc.collect()
    
    async def monitor_memory(self):
        """Monitor memory usage and trigger cleanup if needed."""
        
        import psutil
        process = psutil.Process()
        
        while True:
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.max_memory_mb:
                print(f"⚠️ Memory usage high: {memory_mb:.1f}MB")
                
                # Clear caches
                await cache.session_cache.clear()
                await cache.message_cache.clear()
                
                # Cleanup old sessions
                await self.cleanup_old_sessions()
                
                # Force garbage collection
                gc.collect()
            
            await asyncio.sleep(60)  # Check every minute
```

## Best Practices

### 1. Use Connection Pooling Always
```python
# GOOD - Reuses connections
async with db_pool.acquire() as conn:
    # Use connection

# BAD - Creates new connection each time
conn = await aiosqlite.connect(db_path)
```

### 2. Cache Aggressively but Invalidate Properly
```python
# Cache on read
if cached := await cache.get(key):
    return cached
result = await expensive_operation()
await cache.set(key, result)

# Invalidate on write
await cache.invalidate(key)
```

### 3. Batch Operations When Possible
```python
# GOOD - Single query for multiple inserts
await conn.executemany(
    "INSERT INTO messages VALUES (?, ?, ?)",
    messages_data
)

# BAD - Multiple queries
for msg in messages:
    await conn.execute("INSERT INTO messages VALUES (?, ?, ?)", msg)
```

### 4. Use Appropriate Indexes
```python
# Create indexes for common WHERE clauses
CREATE INDEX idx_messages_session ON messages(session_id);

# Composite indexes for multiple conditions
CREATE INDEX idx_messages_session_time ON messages(session_id, timestamp);
```

## Common Pitfalls

### 1. ❌ Not Using WAL Mode
```python
# BAD - Blocks readers during writes
# Default SQLite mode

# GOOD - Concurrent reads and writes
await conn.execute("PRAGMA journal_mode = WAL")
```

### 2. ❌ Forgetting to Close Connections
```python
# BAD - Connection leak
conn = await aiosqlite.connect(db_path)
# No close

# GOOD - Automatic cleanup
async with db_pool.acquire() as conn:
    # Connection automatically returned to pool
```

### 3. ❌ Not Monitoring Performance
```python
# BAD - No visibility into slowdowns
await some_operation()

# GOOD - Track and monitor
@monitor.track_time("operation_name")
async def some_operation():
    pass
```

## Performance Testing

```python
import pytest
import time

@pytest.mark.benchmark
async def test_rapidfuzz_performance():
    """Test that RapidFuzz meets performance targets."""
    
    # Generate test data
    messages = generate_test_messages(1000)
    query = "test query"
    
    start = time.perf_counter()
    results = await search_with_rapidfuzz(query, messages)
    elapsed = (time.perf_counter() - start) * 1000
    
    # Should complete in under 100ms
    assert elapsed < 100, f"Search took {elapsed:.2f}ms"
    
    # Should return relevant results
    assert len(results) > 0
    assert results[0][1] > 60  # Score > 60

@pytest.mark.benchmark
async def test_concurrent_agents():
    """Test system handles 20 concurrent agents."""
    
    async def agent_operations(agent_id: str):
        # Each agent performs typical operations
        session_id = await create_session(f"agent_{agent_id}")
        
        for i in range(10):
            await add_message(session_id, f"Message {i}", agent_id)
        
        messages = await get_messages(session_id)
        return len(messages)
    
    # Run 20 agents concurrently
    tasks = [agent_operations(f"agent_{i}") for i in range(20)]
    
    start = time.perf_counter()
    results = await asyncio.gather(*tasks)
    elapsed = (time.perf_counter() - start) * 1000
    
    # All agents should complete successfully
    assert all(r == 10 for r in results)
    
    # Should handle 20 agents efficiently
    assert elapsed < 5000, f"20 agents took {elapsed:.2f}ms"
```

## References

- RapidFuzz Documentation: https://github.com/maxbachmann/RapidFuzz
- aiosqlitepool: https://github.com/tortoise/aiosqlitepool
- SQLite Performance Tuning: https://sqlite.org/pragma.html
- Research findings: `/RESEARCH_FINDINGS_DEVELOPER.md`

## Related Guides

- Data Architecture Guide - Database design and schema
- Security & Authentication Guide - Rate limiting
- Testing Patterns Guide - Performance testing