"""
Feedback analytics for cognitive module
Analyzes user feedback to improve activity recommendations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Simple rule-based sentiment analysis for feedback"""
    
    def __init__(self):
        self.positive_words = {
            'love', 'loved', 'enjoy', 'enjoyed', 'great', 'excellent', 'wonderful',
            'amazing', 'fantastic', 'fun', 'happy', 'pleased', 'delighted',
            'perfect', 'brilliant', 'good', 'nice', 'beautiful', 'lovely'
        }
        
        self.negative_words = {
            'hate', 'hated', 'dislike', 'disliked', 'bad', 'terrible', 'awful',
            'boring', 'difficult', 'hard', 'frustrating', 'confused', 'sad',
            'disappointed', 'poor', 'worst', 'horrible', 'unpleasant'
        }
        
        self.intensifiers = {
            'very', 'really', 'extremely', 'absolutely', 'completely', 'totally'
        }
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of feedback text
        
        Args:
            text: Feedback text
        
        Returns:
            Dictionary with sentiment analysis results
        """
        if not text:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0
            }
        
        # Normalize text
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        # Count sentiment words
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        intensifier_count = sum(1 for word in words if word in self.intensifiers)
        
        # Calculate score
        score = positive_count - negative_count
        
        # Apply intensifier boost
        if intensifier_count > 0:
            score *= (1 + 0.2 * intensifier_count)
        
        # Normalize to -1 to 1 range
        max_words = max(len(words), 1)
        normalized_score = max(-1.0, min(1.0, score / max_words * 10))
        
        # Determine sentiment category
        if normalized_score > 0.2:
            sentiment = "positive"
        elif normalized_score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Calculate confidence
        confidence = min(abs(normalized_score), 1.0)
        
        return {
            "sentiment": sentiment,
            "score": normalized_score,
            "confidence": confidence,
            "positive_words": positive_count,
            "negative_words": negative_count
        }


class FeedbackAggregator:
    """Aggregates and analyzes feedback across activities"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.feedback_data: Dict[str, List[Dict]] = defaultdict(list)
    
    def add_feedback(
        self,
        activity_id: str,
        user_id: str,
        feedback_text: Optional[str],
        rating: Optional[float],
        completed: bool,
        timestamp: Optional[datetime] = None
    ):
        """
        Add feedback entry
        
        Args:
            activity_id: Activity identifier
            user_id: User identifier
            feedback_text: Optional text feedback
            rating: Optional numeric rating (0-1)
            completed: Whether activity was completed
            timestamp: Feedback timestamp
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Analyze sentiment if text provided
        sentiment_analysis = None
        if feedback_text:
            sentiment_analysis = self.sentiment_analyzer.analyze_sentiment(feedback_text)
        
        feedback_entry = {
            "user_id": user_id,
            "feedback_text": feedback_text,
            "rating": rating,
            "completed": completed,
            "timestamp": timestamp.isoformat(),
            "sentiment": sentiment_analysis
        }
        
        self.feedback_data[activity_id].append(feedback_entry)
        
        logger.info(
            f"Added feedback for activity {activity_id}",
            extra={
                "activity_id": activity_id,
                "has_text": bool(feedback_text),
                "rating": rating,
                "completed": completed
            }
        )
    
    def get_activity_insights(self, activity_id: str) -> Dict[str, Any]:
        """
        Get insights for specific activity
        
        Args:
            activity_id: Activity identifier
        
        Returns:
            Dictionary with activity insights
        """
        feedbacks = self.feedback_data.get(activity_id, [])
        
        if not feedbacks:
            return {
                "activity_id": activity_id,
                "total_feedback": 0,
                "insights": "No feedback available"
            }
        
        # Calculate metrics
        total = len(feedbacks)
        completed_count = sum(1 for f in feedbacks if f["completed"])
        ratings = [f["rating"] for f in feedbacks if f["rating"] is not None]
        
        # Sentiment analysis
        sentiments = [f["sentiment"] for f in feedbacks if f["sentiment"]]
        positive_count = sum(1 for s in sentiments if s["sentiment"] == "positive")
        negative_count = sum(1 for s in sentiments if s["sentiment"] == "negative")
        
        insights = {
            "activity_id": activity_id,
            "total_feedback": total,
            "completion_rate": completed_count / total if total > 0 else 0,
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "sentiment_distribution": {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": len(sentiments) - positive_count - negative_count
            },
            "recommendation": self._generate_recommendation(
                completed_count / total if total > 0 else 0,
                sum(ratings) / len(ratings) if ratings else None,
                positive_count,
                negative_count
            )
        }
        
        return insights
    
    def _generate_recommendation(
        self,
        completion_rate: float,
        avg_rating: Optional[float],
        positive_count: int,
        negative_count: int
    ) -> str:
        """Generate recommendation based on metrics"""
        if completion_rate > 0.8 and (avg_rating is None or avg_rating > 0.7):
            return "Highly recommended - users complete and enjoy this activity"
        elif completion_rate < 0.3:
            return "Consider reviewing - low completion rate"
        elif avg_rating is not None and avg_rating < 0.4:
            return "Needs improvement - low user satisfaction"
        elif negative_count > positive_count * 2:
            return "Review feedback - predominantly negative sentiment"
        else:
            return "Performing adequately - continue monitoring"
    
    def get_trending_activities(
        self,
        time_window_days: int = 7,
        min_feedback: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get trending activities based on recent feedback
        
        Args:
            time_window_days: Days to look back
            min_feedback: Minimum feedback count to consider
        
        Returns:
            List of trending activities
        """
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        trending = []
        
        for activity_id, feedbacks in self.feedback_data.items():
            # Filter to recent feedback
            recent_feedback = [
                f for f in feedbacks
                if datetime.fromisoformat(f["timestamp"]) > cutoff_date
            ]
            
            if len(recent_feedback) < min_feedback:
                continue
            
            # Calculate trend score
            ratings = [f["rating"] for f in recent_feedback if f["rating"] is not None]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.5
            
            completed = sum(1 for f in recent_feedback if f["completed"])
            completion_rate = completed / len(recent_feedback)
            
            # Trend score combines recency, rating, and completion
            trend_score = (
                len(recent_feedback) * 0.3 +  # Volume
                avg_rating * 0.4 +              # Quality
                completion_rate * 0.3           # Engagement
            )
            
            trending.append({
                "activity_id": activity_id,
                "trend_score": trend_score,
                "recent_feedback_count": len(recent_feedback),
                "average_rating": avg_rating,
                "completion_rate": completion_rate
            })
        
        # Sort by trend score
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        
        return trending[:10]  # Top 10
    
    def get_user_feedback_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get feedback history for specific user
        
        Args:
            user_id: User identifier
            limit: Maximum number of entries
        
        Returns:
            List of user's feedback entries
        """
        user_feedback = []
        
        for activity_id, feedbacks in self.feedback_data.items():
            for feedback in feedbacks:
                if feedback["user_id"] == user_id:
                    feedback_copy = feedback.copy()
                    feedback_copy["activity_id"] = activity_id
                    user_feedback.append(feedback_copy)
        
        # Sort by timestamp (most recent first)
        user_feedback.sort(
            key=lambda x: x["timestamp"],
            reverse=True
        )
        
        return user_feedback[:limit]


# Global instance
feedback_aggregator = FeedbackAggregator()
