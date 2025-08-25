"""
Intelligent caching system with LRU eviction and performance monitoring.

Implements production-ready multi-level caching including:
1. SmartCacheManager - L1/L2 cache with LRU eviction
2. TTL-based expiration and automatic cleanup
3. Cache performance monitoring and hit ratio tracking
4. Session-based and search-based cache keys
5. Cache invalidation on data changes

Built according to PRP-005: Phase 4 - Production Ready specification.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from .security import secure_hash_short_for_cache_keys

# Removed sanitization imports - using generic logging instead

logger = logging.getLogger(__name__)


# ============================================================================
# SMART CACHE MANAGER
# ============================================================================


class SmartCacheManager:
    """Production-ready multi-level cache with LRU eviction and monitoring."""

    def __init__(self) -> None:
        # L1 Cache - Hot data (in-memory, fast access)
        self.l1_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.max_l1_size = 1000  # Max entries in L1 cache

        # L2 Cache - Warm data (larger, with TTL)
        self.l2_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.max_l2_size = 5000  # Max entries in L2 cache

        # Cache statistics for monitoring
        self.cache_stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "invalidations": 0,
            "cleanup_runs": 0,
        }

        # Cache locks for thread safety
        self.l1_lock = asyncio.Lock()
        self.l2_lock = asyncio.Lock()

        # Default TTL values (seconds)
        self.default_l1_ttl = 300  # 5 minutes for hot data
        self.default_l2_ttl = 1800  # 30 minutes for warm data

    def _generate_cache_key(
        self, key: str, context: dict[str, Any] | None = None
    ) -> str:
        """Generate consistent cache key with context."""

        if context:
            # Sort context for consistent key generation
            context_str = json.dumps(context, sort_keys=True, ensure_ascii=False)
            context_hash = secure_hash_short_for_cache_keys(
                context_str, length=8
            )  # Secure hash for cache keys
            return f"{key}:{context_hash}"

        return key

    async def get(self, key: str, context: dict[str, Any] | None = None) -> Any:
        """Get value from layered cache with LRU behavior."""

        cache_key = self._generate_cache_key(key, context)
        current_time = time.time()

        # Check L1 cache first (hot data)
        async with self.l1_lock:
            if cache_key in self.l1_cache:
                entry = self.l1_cache[cache_key]

                # Check if entry is still valid
                if current_time <= entry["expires_at"]:
                    # Move to end (most recently used)
                    self.l1_cache.move_to_end(cache_key)
                    self.cache_stats["l1_hits"] += 1

                    # Log L1 cache hit without sensitive key
                    logger.debug("L1 cache hit")
                    return entry["value"]
                # Entry expired, remove it
                del self.l1_cache[cache_key]

        # Check L2 cache (warm data)
        async with self.l2_lock:
            if cache_key in self.l2_cache:
                entry = self.l2_cache[cache_key]

                # Check if entry is still valid
                if current_time <= entry["expires_at"]:
                    # Move to end (most recently used)
                    self.l2_cache.move_to_end(cache_key)
                    self.cache_stats["l2_hits"] += 1

                    # Promote to L1 cache for faster future access
                    await self._promote_to_l1(cache_key, entry["value"], entry["ttl"])

                    # Log L2 cache hit without sensitive key
                    logger.debug("L2 cache hit (promoted to L1)")
                    return entry["value"]
                # Entry expired, remove it
                del self.l2_cache[cache_key]

        # Cache miss
        self.cache_stats["misses"] += 1
        # Log cache miss without sensitive key
        logger.debug("Cache miss")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        context: dict[str, Any] | None = None,
        level: str = "auto",
    ) -> None:
        """Set value in layered cache with automatic level selection."""

        cache_key = self._generate_cache_key(key, context)
        current_time = time.time()

        # Determine TTL and cache level
        if ttl is None:
            ttl = self.default_l1_ttl if level == "l1" else self.default_l2_ttl

        expires_at = current_time + ttl

        cache_entry = {
            "value": value,
            "created_at": current_time,
            "expires_at": expires_at,
            "ttl": ttl,
            "access_count": 1,
        }

        # Determine cache level
        if level == "l1" or (level == "auto" and ttl <= self.default_l1_ttl):
            await self._set_l1(cache_key, cache_entry)
        elif level == "l2" or (level == "auto" and ttl > self.default_l1_ttl):
            await self._set_l2(cache_key, cache_entry)
        else:
            # Default to L2 for longer-lived data
            await self._set_l2(cache_key, cache_entry)

        self.cache_stats["sets"] += 1
        # Log cache set without sensitive key
        logger.debug("Cached value (TTL: %ds, Level: %s)", ttl, level)

    async def _set_l1(self, cache_key: str, cache_entry: dict[str, Any]) -> None:
        """Set value in L1 cache with LRU eviction."""

        async with self.l1_lock:
            # Evict LRU items if cache is full
            while len(self.l1_cache) >= self.max_l1_size:
                lru_key, _ = self.l1_cache.popitem(
                    last=False
                )  # Remove least recently used
                self.cache_stats["evictions"] += 1
                # Log L1 eviction without sensitive key
                logger.debug("Evicted LRU item from L1")

            self.l1_cache[cache_key] = cache_entry

    async def _set_l2(self, cache_key: str, cache_entry: dict[str, Any]) -> None:
        """Set value in L2 cache with LRU eviction."""

        async with self.l2_lock:
            # Evict LRU items if cache is full
            while len(self.l2_cache) >= self.max_l2_size:
                lru_key, _ = self.l2_cache.popitem(
                    last=False
                )  # Remove least recently used
                self.cache_stats["evictions"] += 1
                # Log L2 eviction without sensitive key
                logger.debug("Evicted LRU item from L2")

            self.l2_cache[cache_key] = cache_entry

    async def _promote_to_l1(self, cache_key: str, value: Any, ttl: int) -> None:
        """Promote frequently accessed item from L2 to L1."""

        # Only promote if TTL is suitable for L1
        if ttl <= self.default_l1_ttl:
            cache_entry = {
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + ttl,
                "ttl": ttl,
                "access_count": 1,
            }

            await self._set_l1(cache_key, cache_entry)

    async def invalidate(self, key: str, context: dict[str, Any] | None = None) -> None:
        """Invalidate cache entry from both levels."""

        cache_key = self._generate_cache_key(key, context)

        # Remove from L1 cache
        async with self.l1_lock:
            if cache_key in self.l1_cache:
                del self.l1_cache[cache_key]
                self.cache_stats["invalidations"] += 1
                # Log L1 invalidation without sensitive key
                logger.debug("Invalidated L1 cache entry")

        # Remove from L2 cache
        async with self.l2_lock:
            if cache_key in self.l2_cache:
                del self.l2_cache[cache_key]
                self.cache_stats["invalidations"] += 1
                # Log L2 cache invalidation without sensitive key
                logger.debug("Invalidated L2 cache entry")

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching a pattern."""

        invalidated_count = 0

        # Collect matching keys from both caches
        matching_keys = []

        async with self.l1_lock:
            matching_keys.extend([key for key in self.l1_cache if pattern in key])

        async with self.l2_lock:
            matching_keys.extend([key for key in self.l2_cache if pattern in key])

        # Invalidate matching keys
        for key in matching_keys:
            await self.invalidate_key(key)  # Direct key invalidation
            invalidated_count += 1

        if invalidated_count > 0:
            # CodeQL: Pattern not logged to prevent potential sensitive data exposure
            logger.debug(
                f"Invalidated {invalidated_count} cache entries matching pattern"
            )

        return invalidated_count

    async def invalidate_key(self, cache_key: str) -> None:
        """Invalidate cache entry by direct cache key."""

        # Remove from L1 cache
        async with self.l1_lock:
            if cache_key in self.l1_cache:
                del self.l1_cache[cache_key]
                self.cache_stats["invalidations"] += 1

        # Remove from L2 cache
        async with self.l2_lock:
            if cache_key in self.l2_cache:
                del self.l2_cache[cache_key]
                self.cache_stats["invalidations"] += 1

    async def cleanup_expired(self) -> int:
        """Remove expired entries from both cache levels."""

        current_time = time.time()
        expired_count = 0

        # Cleanup L1 cache
        async with self.l1_lock:
            expired_keys = [
                key
                for key, entry in self.l1_cache.items()
                if current_time > entry["expires_at"]
            ]

            for key in expired_keys:
                del self.l1_cache[key]
                expired_count += 1

        # Cleanup L2 cache
        async with self.l2_lock:
            expired_keys = [
                key
                for key, entry in self.l2_cache.items()
                if current_time > entry["expires_at"]
            ]

            for key in expired_keys:
                del self.l2_cache[key]
                expired_count += 1

        if expired_count > 0:
            self.cache_stats["cleanup_runs"] += 1
            # CodeQL: This logging statement uses non-sensitive data only
            logger.debug("Cleaned up %d expired cache entries", expired_count)

        return expired_count

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache performance statistics."""

        total_requests = (
            self.cache_stats["l1_hits"]
            + self.cache_stats["l2_hits"]
            + self.cache_stats["misses"]
        )

        hit_ratio = 0.0
        l1_hit_ratio = 0.0
        l2_hit_ratio = 0.0

        if total_requests > 0:
            hit_ratio = (
                self.cache_stats["l1_hits"] + self.cache_stats["l2_hits"]
            ) / total_requests
            l1_hit_ratio = self.cache_stats["l1_hits"] / total_requests
            l2_hit_ratio = self.cache_stats["l2_hits"] / total_requests

        return {
            "performance_metrics": {
                "hit_ratio": round(hit_ratio, 4),
                "l1_hit_ratio": round(l1_hit_ratio, 4),
                "l2_hit_ratio": round(l2_hit_ratio, 4),
                "miss_ratio": round(1 - hit_ratio, 4) if total_requests > 0 else 0.0,
            },
            "operation_counts": self.cache_stats.copy(),
            "cache_sizes": {
                "l1_entries": len(self.l1_cache),
                "l2_entries": len(self.l2_cache),
                "total_entries": len(self.l1_cache) + len(self.l2_cache),
                "l1_max_size": self.max_l1_size,
                "l2_max_size": self.max_l2_size,
                "l1_utilization": len(self.l1_cache) / self.max_l1_size,
                "l2_utilization": len(self.l2_cache) / self.max_l2_size,
            },
            "total_requests": total_requests,
            "health_status": self._get_cache_health(),
        }

    def _get_cache_health(self) -> str:
        """Determine cache health based on performance metrics."""

        total_requests = (
            self.cache_stats["l1_hits"]
            + self.cache_stats["l2_hits"]
            + self.cache_stats["misses"]
        )

        hit_ratio = 0.0
        if total_requests > 0:
            hit_ratio = (
                self.cache_stats["l1_hits"] + self.cache_stats["l2_hits"]
            ) / total_requests

        # Determine health status
        if hit_ratio >= 0.7:  # >70% hit ratio target
            return "excellent"
        if hit_ratio >= 0.5:  # 50-70% hit ratio
            return "good"
        if hit_ratio >= 0.3:  # 30-50% hit ratio
            return "fair"
        # <30% hit ratio
        return "poor"

    async def clear_all(self) -> None:
        """Clear all cache entries."""

        async with self.l1_lock:
            self.l1_cache.clear()

        async with self.l2_lock:
            self.l2_cache.clear()

        logger.info("Cleared all cache entries")

    async def reset_for_testing(self) -> None:
        """
        Reset cache state for testing environments.

        This method ensures clean state between tests by clearing
        all cache entries and resetting performance statistics.
        """
        # Clear all cache entries
        async with self.l1_lock:
            self.l1_cache.clear()

        async with self.l2_lock:
            self.l2_cache.clear()

        # Reset cache statistics
        self.cache_stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "invalidations": 0,
            "cleanup_runs": 0,
        }

        logger.debug("Cache state reset for testing")


# ============================================================================
# CACHE KEY GENERATORS
# ============================================================================


def generate_session_cache_key(session_id: str, agent_id: str, limit: int = 50) -> str:
    """Generate cache key for session data."""
    return f"session:{session_id}:agent:{agent_id}:limit:{limit}"


def generate_search_cache_key(
    session_id: str,
    query: str,
    fuzzy_threshold: float = 60.0,
    search_scope: str = "all",
    limit: int = 10,
) -> str:
    """Generate cache key for search results."""
    # Hash query for consistent key generation
    query_hash = secure_hash_short_for_cache_keys(query, length=8)
    return f"search:{session_id}:query:{query_hash}:threshold:{fuzzy_threshold}:scope:{search_scope}:limit:{limit}"


def generate_memory_cache_key(agent_id: str, scope: str = "all") -> str:
    """Generate cache key for agent memory data."""
    return f"memory:{agent_id}:scope:{scope}"


# ============================================================================
# CACHE INVALIDATION HOOKS
# ============================================================================


async def invalidate_session_cache(
    cache_manager: SmartCacheManager, session_id: str
) -> None:
    """Invalidate all cached data for a session after mutations."""

    # Invalidate session-specific caches
    patterns = [
        f"session:{session_id}",
        f"search:{session_id}",
    ]

    invalidated_count = 0
    for pattern in patterns:
        invalidated_count += await cache_manager.invalidate_pattern(pattern)

    logger.debug(
        f"Invalidated {invalidated_count} cache entries for session {session_id}"
    )


async def invalidate_agent_memory_cache(
    cache_manager: SmartCacheManager, agent_id: str
) -> None:
    """Invalidate agent memory caches after mutations."""

    pattern = f"memory:{agent_id}"
    invalidated_count = await cache_manager.invalidate_pattern(pattern)

    # Log cache invalidation without sensitive agent ID
    logger.debug("Invalidated %d memory cache entries", invalidated_count)


# ============================================================================
# GLOBAL CACHE INSTANCE
# ============================================================================


# Global cache manager instance
cache_manager = SmartCacheManager()


# ============================================================================
# BACKGROUND CACHE MAINTENANCE
# ============================================================================


async def _perform_cache_maintenance() -> None:
    """Perform a single cache maintenance cycle."""
    # Clean up expired entries
    await cache_manager.cleanup_expired()

    # Log cache statistics periodically (every 5 minutes)
    if int(time.time()) % 300 == 0:
        stats = cache_manager.get_cache_stats()
        hit_ratio = stats["performance_metrics"]["hit_ratio"]
        total_entries = stats["cache_sizes"]["total_entries"]

        logger.info(
            f"Cache stats: {hit_ratio:.1%} hit ratio, "
            f"{total_entries} entries, "
            f"health: {stats['health_status']}"
        )

        # Warn if cache performance is poor
        if hit_ratio < 0.5 and stats["total_requests"] > 100:
            logger.warning(f"Cache hit ratio is low: {hit_ratio:.1%} (target: >70%)")


async def cache_maintenance_task() -> None:
    """Background task for cache maintenance and optimization."""

    logger.info("Starting cache maintenance task")

    while True:
        # Run maintenance every 60 seconds
        await asyncio.sleep(60)

        try:
            await _perform_cache_maintenance()
        except Exception:
            logger.exception("Cache maintenance task failed")
            # Continue the loop - don't add extra sleep here since we already sleep above


async def start_cache_maintenance() -> asyncio.Task[None]:
    """Start the cache maintenance background task."""

    return asyncio.create_task(cache_maintenance_task())


# ============================================================================
# CACHED OPERATION HELPERS
# ============================================================================


async def cached_operation(
    cache_key: str,
    operation_func: Any,
    ttl: int = 300,
    context: dict[str, Any] | None = None,
    force_refresh: bool = False,
) -> Any:
    """Execute operation with caching support."""

    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_result = await cache_manager.get(cache_key, context)
        if cached_result is not None:
            return cached_result

    # Execute operation
    result = await operation_func()

    # Cache the result
    await cache_manager.set(cache_key, result, ttl, context)

    return result


def get_cache_performance_metrics() -> dict[str, Any]:
    """Get cache performance metrics for monitoring."""

    return {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache_performance": cache_manager.get_cache_stats(),
    }
