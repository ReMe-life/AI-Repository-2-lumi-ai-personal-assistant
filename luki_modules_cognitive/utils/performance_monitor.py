"""
Performance monitoring for LUKi Cognitive Module
Tracks recommendation quality, latency, and system performance
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class RecommendationMetrics:
    """Metrics for recommendation quality"""
    total_recommendations: int = 0
    accepted_recommendations: int = 0
    rejected_recommendations: int = 0
    completed_activities: int = 0
    average_rating: float = 0.0
    total_completion_time: float = 0.0
    feedback_count: int = 0
    
    @property
    def acceptance_rate(self) -> float:
        """Calculate acceptance rate"""
        if self.total_recommendations == 0:
            return 0.0
        return (self.accepted_recommendations / self.total_recommendations) * 100.0
    
    @property
    def completion_rate(self) -> float:
        """Calculate completion rate"""
        if self.accepted_recommendations == 0:
            return 0.0
        return (self.completed_activities / self.accepted_recommendations) * 100.0
    
    @property
    def average_completion_time(self) -> float:
        """Calculate average completion time"""
        if self.completed_activities == 0:
            return 0.0
        return self.total_completion_time / self.completed_activities


@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time"""
    timestamp: datetime
    operation: str
    latency_seconds: float
    success: bool
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Monitor cognitive module performance"""
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize performance monitor
        
        Args:
            window_size: Number of recent operations to track
        """
        self._lock = threading.Lock()
        self._window_size = window_size
        
        # Operation latency tracking
        self._operation_latencies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._operation_errors: Dict[str, int] = defaultdict(int)
        
        # Recommendation quality tracking
        self._user_metrics: Dict[str, RecommendationMetrics] = {}
        self._global_metrics = RecommendationMetrics()
        
        # Recent performance snapshots
        self._recent_snapshots: deque = deque(maxlen=window_size)
        
        # Start time for uptime calculation
        self._start_time = datetime.utcnow()
    
    def record_operation(
        self,
        operation: str,
        latency_seconds: float,
        success: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record an operation
        
        Args:
            operation: Operation name
            latency_seconds: Operation duration
            success: Whether operation succeeded
            error_type: Error type if failed
            metadata: Additional metadata
        """
        with self._lock:
            # Track latency
            self._operation_latencies[operation].append(latency_seconds)
            self._operation_counts[operation] += 1
            
            if not success:
                self._operation_errors[operation] += 1
            
            # Create snapshot
            snapshot = PerformanceSnapshot(
                timestamp=datetime.utcnow(),
                operation=operation,
                latency_seconds=latency_seconds,
                success=success,
                error_type=error_type,
                metadata=metadata or {}
            )
            self._recent_snapshots.append(snapshot)
            
            # Log slow operations
            if latency_seconds > 5.0:
                logger.warning(
                    f"Slow operation: {operation}",
                    extra={
                        "operation": operation,
                        "latency_seconds": round(latency_seconds, 3),
                        "success": success
                    }
                )
    
    def record_recommendation(
        self,
        user_id: str,
        accepted: bool = False,
        completed: bool = False,
        rating: Optional[float] = None,
        completion_time_seconds: Optional[float] = None
    ):
        """
        Record recommendation outcome
        
        Args:
            user_id: User identifier
            accepted: Whether user accepted recommendation
            completed: Whether user completed activity
            rating: User rating (0-1)
            completion_time_seconds: Time to complete
        """
        with self._lock:
            # Get or create user metrics
            if user_id not in self._user_metrics:
                self._user_metrics[user_id] = RecommendationMetrics()
            
            user_metrics = self._user_metrics[user_id]
            
            # Update user metrics
            user_metrics.total_recommendations += 1
            self._global_metrics.total_recommendations += 1
            
            if accepted:
                user_metrics.accepted_recommendations += 1
                self._global_metrics.accepted_recommendations += 1
            
            if completed:
                user_metrics.completed_activities += 1
                self._global_metrics.completed_activities += 1
                
                if completion_time_seconds:
                    user_metrics.total_completion_time += completion_time_seconds
                    self._global_metrics.total_completion_time += completion_time_seconds
            
            if rating is not None:
                user_metrics.feedback_count += 1
                self._global_metrics.feedback_count += 1
                
                # Update rolling average rating
                total_ratings = user_metrics.average_rating * (user_metrics.feedback_count - 1)
                user_metrics.average_rating = (total_ratings + rating) / user_metrics.feedback_count
                
                global_total = self._global_metrics.average_rating * (self._global_metrics.feedback_count - 1)
                self._global_metrics.average_rating = (global_total + rating) / self._global_metrics.feedback_count
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """
        Get statistics for specific operation
        
        Args:
            operation: Operation name
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            latencies = list(self._operation_latencies.get(operation, []))
            
            if not latencies:
                return {
                    "operation": operation,
                    "sample_count": 0
                }
            
            sorted_latencies = sorted(latencies)
            
            return {
                "operation": operation,
                "sample_count": len(latencies),
                "total_calls": self._operation_counts[operation],
                "errors": self._operation_errors[operation],
                "error_rate_percent": (self._operation_errors[operation] / self._operation_counts[operation] * 100.0) 
                    if self._operation_counts[operation] > 0 else 0.0,
                "latency": {
                    "min_seconds": round(sorted_latencies[0], 3),
                    "max_seconds": round(sorted_latencies[-1], 3),
                    "mean_seconds": round(sum(latencies) / len(latencies), 3),
                    "median_seconds": round(sorted_latencies[len(sorted_latencies) // 2], 3),
                    "p95_seconds": round(sorted_latencies[int(len(sorted_latencies) * 0.95)], 3),
                    "p99_seconds": round(sorted_latencies[int(len(sorted_latencies) * 0.99)], 3)
                }
            }
    
    def get_all_operation_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all operations"""
        with self._lock:
            operations = list(self._operation_latencies.keys())
            return [self.get_operation_stats(op) for op in operations]
    
    def get_user_recommendation_metrics(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get recommendation metrics for specific user
        
        Args:
            user_id: User identifier
        
        Returns:
            User metrics dictionary or None
        """
        with self._lock:
            metrics = self._user_metrics.get(user_id)
            
            if not metrics:
                return None
            
            return {
                "user_id": user_id,
                "total_recommendations": metrics.total_recommendations,
                "acceptance_rate_percent": round(metrics.acceptance_rate, 2),
                "completion_rate_percent": round(metrics.completion_rate, 2),
                "average_rating": round(metrics.average_rating, 2),
                "average_completion_time_seconds": round(metrics.average_completion_time, 2),
                "feedback_count": metrics.feedback_count
            }
    
    def get_global_recommendation_metrics(self) -> Dict[str, Any]:
        """Get global recommendation metrics"""
        with self._lock:
            return {
                "total_recommendations": self._global_metrics.total_recommendations,
                "acceptance_rate_percent": round(self._global_metrics.acceptance_rate, 2),
                "completion_rate_percent": round(self._global_metrics.completion_rate, 2),
                "average_rating": round(self._global_metrics.average_rating, 2),
                "average_completion_time_seconds": round(self._global_metrics.average_completion_time, 2),
                "total_users": len(self._user_metrics),
                "feedback_count": self._global_metrics.feedback_count
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status
        
        Returns:
            Health status dictionary
        """
        with self._lock:
            # Calculate error rate
            total_calls = sum(self._operation_counts.values())
            total_errors = sum(self._operation_errors.values())
            error_rate = (total_errors / total_calls * 100.0) if total_calls > 0 else 0.0
            
            # Determine health status
            if error_rate < 1.0:
                status = "healthy"
            elif error_rate < 5.0:
                status = "degraded"
            else:
                status = "unhealthy"
            
            # Calculate average latency across all operations
            all_latencies = []
            for latencies in self._operation_latencies.values():
                all_latencies.extend(latencies)
            
            avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
            
            uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
            
            return {
                "status": status,
                "uptime_seconds": round(uptime_seconds, 2),
                "total_operations": total_calls,
                "error_rate_percent": round(error_rate, 2),
                "average_latency_seconds": round(avg_latency, 3),
                "recommendation_quality": {
                    "acceptance_rate": round(self._global_metrics.acceptance_rate, 2),
                    "average_rating": round(self._global_metrics.average_rating, 2)
                }
            }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors
        
        Args:
            limit: Number of errors to return
        
        Returns:
            List of error snapshots
        """
        with self._lock:
            error_snapshots = [
                s for s in reversed(self._recent_snapshots)
                if not s.success
            ][:limit]
            
            return [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "operation": s.operation,
                    "error_type": s.error_type,
                    "latency_seconds": round(s.latency_seconds, 3)
                }
                for s in error_snapshots
            ]
    
    def reset(self, operation: Optional[str] = None):
        """
        Reset metrics
        
        Args:
            operation: Specific operation to reset, or None for all
        """
        with self._lock:
            if operation:
                if operation in self._operation_latencies:
                    del self._operation_latencies[operation]
                    del self._operation_counts[operation]
                    del self._operation_errors[operation]
                    logger.info(f"Reset metrics for operation: {operation}")
            else:
                self._operation_latencies.clear()
                self._operation_counts.clear()
                self._operation_errors.clear()
                self._user_metrics.clear()
                self._global_metrics = RecommendationMetrics()
                self._recent_snapshots.clear()
                self._start_time = datetime.utcnow()
                logger.info("Reset all performance metrics")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def track_performance(operation: str):
    """Decorator to track operation performance"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                latency = time.time() - start_time
                get_performance_monitor().record_operation(
                    operation=operation,
                    latency_seconds=latency,
                    success=success,
                    error_type=error_type
                )
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                latency = time.time() - start_time
                get_performance_monitor().record_operation(
                    operation=operation,
                    latency_seconds=latency,
                    success=success,
                    error_type=error_type
                )
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
