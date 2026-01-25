"""
Graceful Degradation for Cognitive Module

Provides fallback strategies when cognitive services fail or degrade,
ensuring users still receive value even during partial outages.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DegradationLevel(str, Enum):
    """Service degradation levels"""
    FULL = "full"  # All features available
    PARTIAL = "partial"  # Some features degraded
    MINIMAL = "minimal"  # Basic features only
    UNAVAILABLE = "unavailable"  # Service down


class FallbackStrategy:
    """
    Implements fallback strategies for cognitive module failures.
    """
    
    def __init__(self):
        self.degradation_level = DegradationLevel.FULL
        self.last_check = datetime.utcnow()
        self._fallback_cache: Dict[str, Any] = {}
    
    async def get_recommendations_with_fallback(
        self,
        primary_strategy: Callable,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get recommendations with fallback strategies.
        
        Attempts strategies in order:
        1. Primary recommendation engine (ML-based)
        2. Rule-based fallback (simpler algorithm)
        3. Cached popular recommendations
        4. Static default recommendations
        
        Args:
            primary_strategy: Primary recommendation function
            user_id: User identifier
            **kwargs: Additional parameters for recommendation
        
        Returns:
            Dict with recommendations and degradation metadata
        """
        try:
            # Try primary strategy
            result = await primary_strategy(user_id=user_id, **kwargs)
            self.degradation_level = DegradationLevel.FULL
            return self._wrap_result(result, DegradationLevel.FULL)
            
        except Exception as primary_error:
            logger.warning(
                f"Primary recommendation strategy failed, trying fallback",
                extra={"user_id": user_id, "error": str(primary_error)}
            )
            
            # Try rule-based fallback
            try:
                result = await self._rule_based_recommendations(user_id, **kwargs)
                self.degradation_level = DegradationLevel.PARTIAL
                return self._wrap_result(result, DegradationLevel.PARTIAL, warning="Using simplified recommendations")
                
            except Exception as fallback_error:
                logger.error(
                    f"Fallback strategy failed, using cached recommendations",
                    extra={"user_id": user_id, "error": str(fallback_error)}
                )
                
                # Try cached popular recommendations
                cached_result = self._get_cached_recommendations(user_id, **kwargs)
                if cached_result:
                    self.degradation_level = DegradationLevel.MINIMAL
                    return self._wrap_result(
                        cached_result,
                        DegradationLevel.MINIMAL,
                        warning="Using cached recommendations due to service issues"
                    )
                
                # Final fallback: static defaults
                logger.error("All recommendation strategies failed, using static defaults")
                self.degradation_level = DegradationLevel.UNAVAILABLE
                default_result = self._get_default_recommendations(**kwargs)
                return self._wrap_result(
                    default_result,
                    DegradationLevel.UNAVAILABLE,
                    error="Recommendation service temporarily unavailable"
                )
    
    async def _rule_based_recommendations(
        self,
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Simple rule-based recommendations as fallback.
        
        Uses basic heuristics instead of ML:
        - Time of day → activity type
        - Current mood → activity energy level
        - Available duration → activity length
        """
        current_hour = datetime.utcnow().hour
        current_mood = kwargs.get("current_mood", "neutral")
        available_duration = kwargs.get("available_duration", 30)
        
        # Simple rules
        recommendations = []
        
        # Morning activities (6-12)
        if 6 <= current_hour < 12:
            recommendations.extend([
                {
                    "id": "morning_walk",
                    "title": "Morning Walk",
                    "description": "A refreshing walk to start the day",
                    "duration_minutes": 20,
                    "fallback": True
                },
                {
                    "id": "breakfast_routine",
                    "title": "Breakfast Routine",
                    "description": "Prepare and enjoy a healthy breakfast",
                    "duration_minutes": 30,
                    "fallback": True
                }
            ])
        
        # Afternoon activities (12-17)
        elif 12 <= current_hour < 17:
            recommendations.extend([
                {
                    "id": "light_exercise",
                    "title": "Light Exercise",
                    "description": "Gentle stretching or chair exercises",
                    "duration_minutes": 15,
                    "fallback": True
                },
                {
                    "id": "social_activity",
                    "title": "Social Connection",
                    "description": "Call a friend or family member",
                    "duration_minutes": 20,
                    "fallback": True
                }
            ])
        
        # Evening activities (17-22)
        elif 17 <= current_hour < 22:
            recommendations.extend([
                {
                    "id": "evening_relaxation",
                    "title": "Evening Relaxation",
                    "description": "Calming activities like reading or music",
                    "duration_minutes": 25,
                    "fallback": True
                },
                {
                    "id": "reminiscence",
                    "title": "Photo Reminiscence",
                    "description": "Look through old photos and share memories",
                    "duration_minutes": 30,
                    "fallback": True
                }
            ])
        
        # Night activities (22-6)
        else:
            recommendations.extend([
                {
                    "id": "bedtime_routine",
                    "title": "Bedtime Routine",
                    "description": "Wind down with calming activities",
                    "duration_minutes": 20,
                    "fallback": True
                }
            ])
        
        # Filter by available duration
        recommendations = [
            r for r in recommendations
            if r["duration_minutes"] <= available_duration + 10  # 10 min buffer
        ]
        
        # Limit to max recommendations
        max_recs = kwargs.get("max_recommendations", 5)
        recommendations = recommendations[:max_recs]
        
        logger.info(
            f"Generated {len(recommendations)} rule-based recommendations",
            extra={"user_id": user_id, "count": len(recommendations)}
        )
        
        return {"recommendations": recommendations}
    
    def _get_cached_recommendations(
        self,
        user_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached popular recommendations.
        
        Returns previously successful recommendations
        from the cache if available.
        """
        cache_key = f"popular_recs_{user_id}"
        
        if cache_key in self._fallback_cache:
            logger.info(f"Using cached recommendations for user {user_id}")
            return self._fallback_cache[cache_key]
        
        # If no user-specific cache, try global popular
        if "popular_recs_global" in self._fallback_cache:
            logger.info("Using global popular recommendations")
            return self._fallback_cache["popular_recs_global"]
        
        return None
    
    def _get_default_recommendations(self, **kwargs) -> Dict[str, Any]:
        """
        Get static default recommendations.
        
        Last resort fallback with universally appropriate activities.
        """
        default_activities = [
            {
                "id": "conversation",
                "title": "Friendly Conversation",
                "description": "Share thoughts and stories",
                "duration_minutes": 20,
                "default": True
            },
            {
                "id": "music_listening",
                "title": "Listen to Music",
                "description": "Enjoy favorite songs",
                "duration_minutes": 15,
                "default": True
            },
            {
                "id": "gentle_movement",
                "title": "Gentle Movement",
                "description": "Light stretching or walking",
                "duration_minutes": 10,
                "default": True
            },
            {
                "id": "mindful_breathing",
                "title": "Mindful Breathing",
                "description": "Calming breathing exercises",
                "duration_minutes": 5,
                "default": True
            }
        ]
        
        max_recs = kwargs.get("max_recommendations", 5)
        return {"recommendations": default_activities[:max_recs]}
    
    def cache_recommendations(
        self,
        user_id: str,
        recommendations: List[Dict[str, Any]],
        is_global: bool = False
    ):
        """
        Cache recommendations for fallback use.
        
        Args:
            user_id: User identifier
            recommendations: Recommendations to cache
            is_global: Whether these are global popular recommendations
        """
        cache_key = "popular_recs_global" if is_global else f"popular_recs_{user_id}"
        self._fallback_cache[cache_key] = {"recommendations": recommendations}
        logger.debug(f"Cached {len(recommendations)} recommendations (global={is_global})")
    
    def _wrap_result(
        self,
        result: Dict[str, Any],
        level: DegradationLevel,
        warning: Optional[str] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Wrap result with degradation metadata.
        """
        wrapped = {
            **result,
            "_degradation": {
                "level": level.value,
                "timestamp": datetime.utcnow().isoformat(),
                "warning": warning,
                "error": error
            }
        }
        
        return wrapped
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current degradation status"""
        return {
            "degradation_level": self.degradation_level.value,
            "last_check": self.last_check.isoformat(),
            "cache_size": len(self._fallback_cache)
        }


# Global fallback strategy instance
_fallback_strategy: Optional[FallbackStrategy] = None


def get_fallback_strategy() -> FallbackStrategy:
    """Get the global fallback strategy instance"""
    global _fallback_strategy
    if _fallback_strategy is None:
        _fallback_strategy = FallbackStrategy()
    return _fallback_strategy
