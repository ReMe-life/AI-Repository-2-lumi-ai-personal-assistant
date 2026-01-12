"""
Intelligent caching for activity recommendations
Optimizes recommendation performance with smart cache invalidation
"""

import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import json

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with metadata"""
    
    def __init__(self, data: Any, ttl_seconds: int = 300):
        self.data = data
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.access_count = 0
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    def access(self) -> Any:
        """Access the cached data"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
        return self.data


class RecommendationCache:
    """Cache for activity recommendations with intelligent invalidation"""
    
    def __init__(
        self,
        max_entries: int = 1000,
        default_ttl: int = 300,
        enable_stats: bool = True
    ):
        """
        Initialize recommendation cache
        
        Args:
            max_entries: Maximum cache entries
            default_ttl: Default TTL in seconds
            enable_stats: Whether to track statistics
        """
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._enable_stats = enable_stats
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._invalidations = 0
        
        # User activity tracking for smart invalidation
        self._user_last_activity: Dict[str, datetime] = {}
    
    def get(self, user_id: str, interests: List[str], difficulty: Optional[float] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached recommendations
        
        Args:
            user_id: User identifier
            interests: User interests
            difficulty: Difficulty level
        
        Returns:
            Cached recommendations or None
        """
        cache_key = self._generate_key(user_id, interests, difficulty)
        
        with self._lock:
            if cache_key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Check if expired
            if entry.is_expired():
                del self._cache[cache_key]
                self._misses += 1
                logger.debug(f"Cache entry expired: {cache_key}")
                return None
            
            # Check if user has had activity since cache
            if self._should_invalidate_for_user(user_id, entry.created_at):
                del self._cache[cache_key]
                self._invalidations += 1
                self._misses += 1
                logger.debug(f"Cache invalidated due to user activity: {cache_key}")
                return None
            
            # Access and move to end (LRU)
            data = entry.access()
            self._cache.move_to_end(cache_key)
            self._hits += 1
            
            logger.debug(
                f"Cache hit: {cache_key}",
                extra={
                    "user_id": user_id,
                    "access_count": entry.access_count,
                    "age_seconds": (datetime.utcnow() - entry.created_at).total_seconds()
                }
            )
            
            return data
    
    def set(
        self,
        user_id: str,
        interests: List[str],
        recommendations: List[Dict[str, Any]],
        difficulty: Optional[float] = None,
        ttl: Optional[int] = None
    ):
        """
        Cache recommendations
        
        Args:
            user_id: User identifier
            interests: User interests
            recommendations: Recommendations to cache
            difficulty: Difficulty level
            ttl: Custom TTL
        """
        cache_key = self._generate_key(user_id, interests, difficulty)
        ttl_seconds = ttl or self._default_ttl
        
        with self._lock:
            # Create entry
            entry = CacheEntry(recommendations, ttl_seconds)
            
            # Remove old entry if exists
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            # Add new entry
            self._cache[cache_key] = entry
            
            # Evict if necessary
            while len(self._cache) > self._max_entries:
                # Remove least recently used
                evicted_key, _ = self._cache.popitem(last=False)
                self._evictions += 1
                logger.debug(f"Evicted cache entry: {evicted_key}")
            
            logger.debug(
                f"Cached recommendations: {cache_key}",
                extra={
                    "user_id": user_id,
                    "count": len(recommendations),
                    "ttl_seconds": ttl_seconds
                }
            )
    
    def invalidate_user(self, user_id: str):
        """
        Invalidate all cache entries for a user
        
        Args:
            user_id: User identifier
        """
        with self._lock:
            # Track user activity
            self._user_last_activity[user_id] = datetime.utcnow()
            
            # Find and remove all entries for this user
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(f"{user_id}:")
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
                self._invalidations += 1
            
            if keys_to_remove:
                logger.info(
                    f"Invalidated {len(keys_to_remove)} cache entries for user",
                    extra={"user_id": user_id, "count": len(keys_to_remove)}
                )
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate entries matching pattern
        
        Args:
            pattern: Pattern to match (substring)
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if pattern in key
            ]
            
            for key in keys_to_remove:
                del self._cache[key]
                self._invalidations += 1
            
            if keys_to_remove:
                logger.info(
                    f"Invalidated {len(keys_to_remove)} cache entries matching pattern",
                    extra={"pattern": pattern, "count": len(keys_to_remove)}
                )
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._user_last_activity.clear()
            logger.info(f"Cleared cache ({count} entries)")
    
    def _generate_key(self, user_id: str, interests: List[str], difficulty: Optional[float]) -> str:
        """Generate cache key from parameters"""
        # Sort interests for consistent hashing
        sorted_interests = sorted(interests) if interests else []
        
        # Create key string
        key_parts = [
            user_id,
            ",".join(sorted_interests),
            str(difficulty) if difficulty is not None else "default"
        ]
        key_string = ":".join(key_parts)
        
        # Hash for shorter key
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"{user_id}:{key_hash}"
    
    def _should_invalidate_for_user(self, user_id: str, cache_time: datetime) -> bool:
        """
        Check if cache should be invalidated due to user activity
        
        Args:
            user_id: User identifier
            cache_time: When entry was cached
        
        Returns:
            Whether to invalidate
        """
        if user_id not in self._user_last_activity:
            return False
        
        last_activity = self._user_last_activity[user_id]
        
        # Invalidate if user had activity after cache was created
        return last_activity > cache_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100.0) if total_requests > 0 else 0.0
            
            # Calculate average access count
            access_counts = [entry.access_count for entry in self._cache.values()]
            avg_access = sum(access_counts) / len(access_counts) if access_counts else 0.0
            
            return {
                "entries": len(self._cache),
                "max_entries": self._max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "evictions": self._evictions,
                "invalidations": self._invalidations,
                "average_access_count": round(avg_access, 2),
                "tracked_users": len(self._user_last_activity)
            }
    
    def get_hot_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequently accessed entries
        
        Args:
            limit: Number of entries to return
        
        Returns:
            List of hot entry info
        """
        with self._lock:
            # Sort by access count
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count,
                reverse=True
            )[:limit]
            
            return [
                {
                    "key": key,
                    "access_count": entry.access_count,
                    "age_seconds": (datetime.utcnow() - entry.created_at).total_seconds(),
                    "recommendation_count": len(entry.data) if isinstance(entry.data, list) else 0
                }
                for key, entry in sorted_entries
            ]


# Global cache instance
_recommendation_cache: Optional[RecommendationCache] = None


def get_recommendation_cache() -> RecommendationCache:
    """Get the global recommendation cache instance"""
    global _recommendation_cache
    if _recommendation_cache is None:
        _recommendation_cache = RecommendationCache()
    return _recommendation_cache


def cache_recommendations(ttl: Optional[int] = None):
    """Decorator to cache recommendation function results"""
    def decorator(func):
        async def async_wrapper(user_id: str, interests: List[str], difficulty: Optional[float] = None, *args, **kwargs):
            cache = get_recommendation_cache()
            
            # Try cache first
            cached = cache.get(user_id, interests, difficulty)
            if cached is not None:
                return cached
            
            # Call function
            result = await func(user_id, interests, difficulty, *args, **kwargs)
            
            # Cache result
            cache.set(user_id, interests, result, difficulty, ttl)
            
            return result
        
        def sync_wrapper(user_id: str, interests: List[str], difficulty: Optional[float] = None, *args, **kwargs):
            cache = get_recommendation_cache()
            
            # Try cache first
            cached = cache.get(user_id, interests, difficulty)
            if cached is not None:
                return cached
            
            # Call function
            result = func(user_id, interests, difficulty, *args, **kwargs)
            
            # Cache result
            cache.set(user_id, interests, result, difficulty, ttl)
            
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
