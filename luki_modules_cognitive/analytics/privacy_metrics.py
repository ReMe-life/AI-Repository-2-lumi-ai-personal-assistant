"""
Privacy-aware analytics for cognitive module
Implements differential privacy for aggregate metrics collection
"""

import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime
import math

logger = logging.getLogger(__name__)


class DifferentialPrivacy:
    """Differential privacy mechanisms for analytics"""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        Initialize DP mechanism
        
        Args:
            epsilon: Privacy budget (smaller = more private)
            delta: Probability of privacy breach
        """
        self.epsilon = epsilon
        self.delta = delta
    
    def add_laplace_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """
        Add Laplace noise for differential privacy
        
        Args:
            value: True value
            sensitivity: Sensitivity of the query
        
        Returns:
            Noisy value
        """
        scale = sensitivity / self.epsilon
        noise = random.laplace(0, scale)
        return value + noise
    
    def add_gaussian_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """
        Add Gaussian noise for differential privacy
        
        Args:
            value: True value
            sensitivity: Sensitivity of the query
        
        Returns:
            Noisy value
        """
        sigma = (sensitivity * math.sqrt(2 * math.log(1.25 / self.delta))) / self.epsilon
        noise = random.gauss(0, sigma)
        return value + noise
    
    def clip_value(self, value: float, min_val: float, max_val: float) -> float:
        """Clip value to range for bounded sensitivity"""
        return max(min_val, min(value, max_val))


class PrivacyAwareMetrics:
    """Collects aggregate metrics with privacy guarantees"""
    
    def __init__(self, epsilon: float = 1.0):
        self.dp = DifferentialPrivacy(epsilon=epsilon)
        self.metrics_cache: Dict[str, Any] = {}
    
    def record_activity_completion(
        self,
        user_id: str,
        activity_id: str,
        completion_time_seconds: float,
        rating: Optional[float] = None
    ):
        """
        Record activity completion (stored privately)
        
        Args:
            user_id: User identifier (hashed before storage)
            activity_id: Activity identifier
            completion_time_seconds: Time taken
            rating: Optional user rating
        """
        # Hash user_id for privacy
        import hashlib
        user_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        
        # Store in cache (in production, use secure database)
        if activity_id not in self.metrics_cache:
            self.metrics_cache[activity_id] = {
                "completions": [],
                "ratings": [],
                "times": []
            }
        
        self.metrics_cache[activity_id]["completions"].append({
            "user_hash": user_hash,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if rating is not None:
            self.metrics_cache[activity_id]["ratings"].append(rating)
        
        self.metrics_cache[activity_id]["times"].append(completion_time_seconds)
    
    def get_activity_popularity(self, activity_id: str, apply_dp: bool = True) -> float:
        """
        Get activity popularity with differential privacy
        
        Args:
            activity_id: Activity identifier
            apply_dp: Whether to apply differential privacy
        
        Returns:
            Noisy popularity score (0-1)
        """
        if activity_id not in self.metrics_cache:
            return 0.0
        
        completions = len(self.metrics_cache[activity_id]["completions"])
        
        # Normalize to 0-1 range (assuming max 100 completions)
        popularity = min(completions / 100.0, 1.0)
        
        if apply_dp:
            # Add Laplace noise with sensitivity 0.01 (1 completion = 0.01 change)
            popularity = self.dp.add_laplace_noise(popularity, sensitivity=0.01)
            popularity = self.dp.clip_value(popularity, 0.0, 1.0)
        
        return popularity
    
    def get_average_rating(self, activity_id: str, apply_dp: bool = True) -> Optional[float]:
        """
        Get average rating with differential privacy
        
        Args:
            activity_id: Activity identifier
            apply_dp: Whether to apply differential privacy
        
        Returns:
            Noisy average rating or None if no ratings
        """
        if activity_id not in self.metrics_cache:
            return None
        
        ratings = self.metrics_cache[activity_id]["ratings"]
        
        if not ratings:
            return None
        
        avg_rating = sum(ratings) / len(ratings)
        
        if apply_dp:
            # Sensitivity is 1/n where n is number of ratings
            sensitivity = 1.0 / len(ratings) if len(ratings) > 0 else 1.0
            avg_rating = self.dp.add_laplace_noise(avg_rating, sensitivity=sensitivity)
            avg_rating = self.dp.clip_value(avg_rating, 0.0, 1.0)
        
        return avg_rating
    
    def get_aggregate_statistics(
        self,
        activity_ids: List[str],
        apply_dp: bool = True
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics across activities
        
        Args:
            activity_ids: List of activity identifiers
            apply_dp: Whether to apply differential privacy
        
        Returns:
            Dictionary of aggregate statistics
        """
        total_completions = 0
        total_ratings = []
        
        for activity_id in activity_ids:
            if activity_id in self.metrics_cache:
                total_completions += len(self.metrics_cache[activity_id]["completions"])
                total_ratings.extend(self.metrics_cache[activity_id]["ratings"])
        
        stats = {
            "total_completions": total_completions,
            "average_rating": sum(total_ratings) / len(total_ratings) if total_ratings else None,
            "activities_with_data": len([aid for aid in activity_ids if aid in self.metrics_cache])
        }
        
        if apply_dp:
            # Add noise to aggregates
            stats["total_completions"] = int(
                self.dp.add_laplace_noise(float(total_completions), sensitivity=1.0)
            )
            
            if stats["average_rating"] is not None:
                sensitivity = 1.0 / len(total_ratings) if len(total_ratings) > 0 else 1.0
                stats["average_rating"] = self.dp.add_laplace_noise(
                    stats["average_rating"],
                    sensitivity=sensitivity
                )
                stats["average_rating"] = self.dp.clip_value(stats["average_rating"], 0.0, 1.0)
        
        return stats
    
    def get_cohort_insights(
        self,
        cohort_filter: Dict[str, Any],
        apply_dp: bool = True
    ) -> Dict[str, Any]:
        """
        Get insights for a user cohort with privacy guarantees
        
        Args:
            cohort_filter: Filter criteria for cohort
            apply_dp: Whether to apply differential privacy
        
        Returns:
            Cohort insights with privacy guarantees
        """
        # In production, this would query a secure database with proper filtering
        # For now, return aggregated metrics
        
        insights = {
            "cohort_size": 0,
            "average_engagement": 0.0,
            "popular_activities": [],
            "privacy_applied": apply_dp
        }
        
        if apply_dp:
            # Add noise to protect cohort privacy
            insights["cohort_size"] = int(
                self.dp.add_laplace_noise(float(insights["cohort_size"]), sensitivity=1.0)
            )
            insights["average_engagement"] = self.dp.add_laplace_noise(
                insights["average_engagement"],
                sensitivity=0.1
            )
        
        logger.info(
            f"Generated cohort insights with DP={apply_dp}",
            extra={"epsilon": self.dp.epsilon, "apply_dp": apply_dp}
        )
        
        return insights


class ConsentAwareAnalytics:
    """Analytics that respect user consent preferences"""
    
    def __init__(self):
        self.consent_cache: Dict[str, Dict[str, bool]] = {}
    
    def set_user_consent(
        self,
        user_id: str,
        analytics_consent: bool,
        research_consent: bool,
        personalization_consent: bool
    ):
        """
        Set user consent preferences
        
        Args:
            user_id: User identifier
            analytics_consent: Consent for analytics
            research_consent: Consent for research
            personalization_consent: Consent for personalization
        """
        self.consent_cache[user_id] = {
            "analytics": analytics_consent,
            "research": research_consent,
            "personalization": personalization_consent,
            "updated_at": datetime.utcnow().isoformat()
        }
    
    def can_collect_analytics(self, user_id: str) -> bool:
        """Check if user consented to analytics"""
        consent = self.consent_cache.get(user_id, {})
        return consent.get("analytics", False)
    
    def can_use_for_research(self, user_id: str) -> bool:
        """Check if user consented to research"""
        consent = self.consent_cache.get(user_id, {})
        return consent.get("research", False)
    
    def can_personalize(self, user_id: str) -> bool:
        """Check if user consented to personalization"""
        consent = self.consent_cache.get(user_id, {})
        return consent.get("personalization", False)
    
    def filter_data_by_consent(
        self,
        data: List[Dict[str, Any]],
        required_consent: str
    ) -> List[Dict[str, Any]]:
        """
        Filter data based on consent requirements
        
        Args:
            data: List of data items with user_id
            required_consent: Type of consent required
        
        Returns:
            Filtered data list
        """
        filtered = []
        
        for item in data:
            user_id = item.get("user_id")
            if not user_id:
                continue
            
            consent = self.consent_cache.get(user_id, {})
            if consent.get(required_consent, False):
                filtered.append(item)
        
        logger.debug(
            f"Filtered {len(data)} items to {len(filtered)} based on {required_consent} consent"
        )
        
        return filtered


# Global instances
privacy_metrics = PrivacyAwareMetrics(epsilon=1.0)
consent_analytics = ConsentAwareAnalytics()
