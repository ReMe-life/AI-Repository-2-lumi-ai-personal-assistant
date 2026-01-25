"""
Recommendation Feedback Analytics

Tracks and analyzes user feedback on recommendations to improve
recommendation quality and personalization over time.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of user feedback"""
    ACCEPTED = "accepted"  # User chose this recommendation
    REJECTED = "rejected"  # User explicitly rejected
    COMPLETED = "completed"  # User completed the activity
    ABANDONED = "abandoned"  # User started but didn't finish
    RATED = "rated"  # User provided explicit rating
    SKIPPED = "skipped"  # User skipped without engaging


@dataclass
class RecommendationFeedback:
    """Individual feedback event"""
    feedback_id: str
    user_id: str
    recommendation_id: str
    activity_id: str
    feedback_type: FeedbackType
    timestamp: datetime
    rating: Optional[float] = None  # 0-1 scale
    duration_seconds: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RecommendationAnalytics:
    """
    Analytics engine for recommendation feedback.
    
    Tracks and analyzes:
    - Acceptance rates by activity type, time, mood
    - Completion rates
    - User engagement patterns
    - Recommendation quality over time
    """
    
    def __init__(self, retention_days: int = 90):
        """
        Initialize analytics engine.
        
        Args:
            retention_days: Days to retain feedback data
        """
        self.retention_days = retention_days
        
        # In-memory storage (would use database in production)
        self._feedback_events: List[RecommendationFeedback] = []
        
        # Aggregated metrics
        self._activity_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._user_preferences: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        logger.info(f"Initialized recommendation analytics (retention={retention_days} days)")
    
    def record_feedback(
        self,
        user_id: str,
        recommendation_id: str,
        activity_id: str,
        feedback_type: FeedbackType,
        rating: Optional[float] = None,
        duration_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record user feedback on a recommendation.
        
        Args:
            user_id: User identifier
            recommendation_id: Recommendation that generated this activity
            activity_id: Activity identifier
            feedback_type: Type of feedback
            rating: Optional rating (0-1)
            duration_seconds: Time spent on activity
            metadata: Additional context
        
        Returns:
            str: Feedback event ID
        """
        import uuid
        
        feedback_id = str(uuid.uuid4())
        
        feedback = RecommendationFeedback(
            feedback_id=feedback_id,
            user_id=user_id,
            recommendation_id=recommendation_id,
            activity_id=activity_id,
            feedback_type=feedback_type,
            timestamp=datetime.utcnow(),
            rating=rating,
            duration_seconds=duration_seconds,
            metadata=metadata or {}
        )
        
        self._feedback_events.append(feedback)
        
        # Update aggregated stats
        self._update_activity_stats(feedback)
        self._update_user_preferences(feedback)
        
        logger.info(
            f"Recorded {feedback_type.value} feedback",
            extra={
                "user_id": user_id,
                "activity_id": activity_id,
                "feedback_type": feedback_type.value,
                "rating": rating
            }
        )
        
        # Clean old events periodically
        if len(self._feedback_events) % 100 == 0:
            self._cleanup_old_events()
        
        return feedback_id
    
    def _update_activity_stats(self, feedback: RecommendationFeedback):
        """Update aggregated activity statistics"""
        activity_id = feedback.activity_id
        feedback_type = feedback.feedback_type.value
        
        self._activity_stats[activity_id]["total"] += 1
        self._activity_stats[activity_id][feedback_type] += 1
        
        if feedback.rating is not None:
            current_rating = self._activity_stats[activity_id].get("avg_rating", 0)
            rating_count = self._activity_stats[activity_id].get("rating_count", 0)
            new_rating = (current_rating * rating_count + feedback.rating) / (rating_count + 1)
            self._activity_stats[activity_id]["avg_rating"] = new_rating
            self._activity_stats[activity_id]["rating_count"] = rating_count + 1
    
    def _update_user_preferences(self, feedback: RecommendationFeedback):
        """Update user preference profile"""
        user_id = feedback.user_id
        activity_id = feedback.activity_id
        
        if "activities" not in self._user_preferences[user_id]:
            self._user_preferences[user_id]["activities"] = defaultdict(int)
        
        # Weight different feedback types
        weights = {
            FeedbackType.COMPLETED: 10,
            FeedbackType.ACCEPTED: 5,
            FeedbackType.RATED: 8 if feedback.rating and feedback.rating > 0.7 else -2,
            FeedbackType.ABANDONED: -3,
            FeedbackType.REJECTED: -5,
            FeedbackType.SKIPPED: -1
        }
        
        weight = weights.get(feedback.feedback_type, 0)
        self._user_preferences[user_id]["activities"][activity_id] += weight
        
        # Track ratings
        if feedback.rating is not None:
            if "ratings" not in self._user_preferences[user_id]:
                self._user_preferences[user_id]["ratings"] = []
            self._user_preferences[user_id]["ratings"].append({
                "activity_id": activity_id,
                "rating": feedback.rating,
                "timestamp": feedback.timestamp.isoformat()
            })
    
    def get_activity_performance(
        self,
        activity_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance metrics for an activity.
        
        Args:
            activity_id: Activity identifier
            days: Look-back period in days
        
        Returns:
            Dict with acceptance rate, completion rate, avg rating
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        relevant_events = [
            e for e in self._feedback_events
            if e.activity_id == activity_id and e.timestamp > cutoff
        ]
        
        if not relevant_events:
            return {
                "activity_id": activity_id,
                "total_recommendations": 0,
                "no_data": True
            }
        
        total = len(relevant_events)
        accepted = sum(1 for e in relevant_events if e.feedback_type == FeedbackType.ACCEPTED)
        completed = sum(1 for e in relevant_events if e.feedback_type == FeedbackType.COMPLETED)
        rejected = sum(1 for e in relevant_events if e.feedback_type == FeedbackType.REJECTED)
        
        ratings = [e.rating for e in relevant_events if e.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        return {
            "activity_id": activity_id,
            "period_days": days,
            "total_recommendations": total,
            "acceptance_count": accepted,
            "acceptance_rate": (accepted / total * 100) if total > 0 else 0,
            "completion_count": completed,
            "completion_rate": (completed / accepted * 100) if accepted > 0 else 0,
            "rejection_count": rejected,
            "rejection_rate": (rejected / total * 100) if total > 0 else 0,
            "average_rating": round(avg_rating, 2) if avg_rating is not None else None,
            "rating_count": len(ratings)
        }
    
    def get_user_insights(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get insights about user's preferences and engagement.
        
        Args:
            user_id: User identifier
            days: Look-back period
        
        Returns:
            Dict with top activities, engagement patterns, preferences
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        user_events = [
            e for e in self._feedback_events
            if e.user_id == user_id and e.timestamp > cutoff
        ]
        
        if not user_events:
            return {
                "user_id": user_id,
                "no_data": True
            }
        
        # Top activities by positive feedback
        activity_scores = defaultdict(int)
        for event in user_events:
            if event.feedback_type in [FeedbackType.COMPLETED, FeedbackType.ACCEPTED]:
                activity_scores[event.activity_id] += 1
            elif event.feedback_type in [FeedbackType.REJECTED, FeedbackType.ABANDONED]:
                activity_scores[event.activity_id] -= 1
        
        top_activities = sorted(
            activity_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Engagement metrics
        total_recommendations = len(user_events)
        accepted = sum(1 for e in user_events if e.feedback_type == FeedbackType.ACCEPTED)
        completed = sum(1 for e in user_events if e.feedback_type == FeedbackType.COMPLETED)
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_recommendations": total_recommendations,
            "acceptance_rate": (accepted / total_recommendations * 100) if total_recommendations > 0 else 0,
            "completion_rate": (completed / accepted * 100) if accepted > 0 else 0,
            "top_activities": dict(top_activities),
            "engagement_level": self._calculate_engagement_level(user_events)
        }
    
    def _calculate_engagement_level(self, events: List[RecommendationFeedback]) -> str:
        """Calculate user engagement level from events"""
        if not events:
            return "none"
        
        # Calculate engagement score
        score = 0
        for event in events:
            if event.feedback_type == FeedbackType.COMPLETED:
                score += 10
            elif event.feedback_type == FeedbackType.ACCEPTED:
                score += 5
            elif event.feedback_type == FeedbackType.RATED and event.rating:
                score += 3
            elif event.feedback_type == FeedbackType.REJECTED:
                score -= 2
        
        avg_score = score / len(events)
        
        if avg_score >= 7:
            return "high"
        elif avg_score >= 4:
            return "medium"
        elif avg_score >= 1:
            return "low"
        else:
            return "very_low"
    
    def get_top_performing_activities(
        self,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get top performing activities across all users.
        
        Args:
            limit: Number of activities to return
            days: Look-back period
        
        Returns:
            List of activity performance dictionaries
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Aggregate by activity
        activity_metrics = defaultdict(lambda: {"accepted": 0, "total": 0, "ratings": []})
        
        for event in self._feedback_events:
            if event.timestamp > cutoff:
                activity_id = event.activity_id
                activity_metrics[activity_id]["total"] += 1
                if event.feedback_type in [FeedbackType.ACCEPTED, FeedbackType.COMPLETED]:
                    activity_metrics[activity_id]["accepted"] += 1
                if event.rating is not None:
                    activity_metrics[activity_id]["ratings"].append(event.rating)
        
        # Calculate scores
        activity_scores = []
        for activity_id, metrics in activity_metrics.items():
            if metrics["total"] >= 5:  # Minimum threshold
                acceptance_rate = metrics["accepted"] / metrics["total"]
                avg_rating = sum(metrics["ratings"]) / len(metrics["ratings"]) if metrics["ratings"] else 0.5
                
                # Weighted score
                score = (acceptance_rate * 0.6) + (avg_rating * 0.4)
                
                activity_scores.append({
                    "activity_id": activity_id,
                    "score": round(score, 3),
                    "acceptance_rate": round(acceptance_rate * 100, 1),
                    "average_rating": round(avg_rating, 2) if metrics["ratings"] else None,
                    "total_recommendations": metrics["total"]
                })
        
        # Sort by score and return top N
        activity_scores.sort(key=lambda x: x["score"], reverse=True)
        return activity_scores[:limit]
    
    def _cleanup_old_events(self):
        """Remove events older than retention period"""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        before_count = len(self._feedback_events)
        
        self._feedback_events = [
            e for e in self._feedback_events
            if e.timestamp > cutoff
        ]
        
        removed = before_count - len(self._feedback_events)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old feedback events")


# Global analytics instance
_analytics: Optional[RecommendationAnalytics] = None


def get_recommendation_analytics() -> RecommendationAnalytics:
    """Get the global recommendation analytics instance"""
    global _analytics
    if _analytics is None:
        _analytics = RecommendationAnalytics()
    return _analytics
