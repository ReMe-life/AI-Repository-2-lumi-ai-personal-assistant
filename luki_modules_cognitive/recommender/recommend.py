"""
Activity Recommendation Engine

Core recommendation system that combines:
- ELR-based personalization
- LUKi personality framework integration
- ReMeLife activity catalog
- Cognitive level adaptation
- Engagement history learning
- LRU recommendation cache for repeated requests
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, date
import random
import math

from ..data.activity_catalog import ActivityCatalog, Activity, ActivityType, ActivityModule, CognitiveLevel
from ..data.elr_adapter import ELRAdapter, ELRProfile, ActivityEngagement
from ..config import get_config
from ..utils.recommendation_cache import get_recommendation_cache

logger = logging.getLogger(__name__)


@dataclass
class RecommendationContext:
    """Context for generating activity recommendations"""
    user_id: str
    current_mood: Optional[str] = None
    time_of_day: Optional[str] = None
    available_duration: Optional[int] = None  # minutes
    carer_available: bool = True
    group_setting: bool = False
    specific_request: Optional[str] = None
    cognitive_capacity_today: Optional[str] = None


@dataclass
class ActivityRecommendation:
    """A recommended activity with scoring and reasoning"""
    activity: Activity
    score: float  # 0.0 to 1.0
    reasoning: List[str]
    personalization_notes: List[str]
    estimated_engagement: float
    adaptation_suggestions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary"""
        return {
            'activity': self.activity.to_dict(),
            'score': self.score,
            'reasoning': self.reasoning,
            'personalization_notes': self.personalization_notes,
            'estimated_engagement': self.estimated_engagement,
            'adaptation_suggestions': self.adaptation_suggestions
        }


class ActivityRecommender:
    """Main activity recommendation engine"""
    
    def __init__(self):
        self.config = get_config()
        self.catalog = ActivityCatalog()
        self.elr_adapter = ELRAdapter()
        
        # Personality-based weights (from LUKi Personality Framework)
        self.personality_weights = {
            'memory_keeper': 0.9,  # Prioritize memory-stimulating activities
            'warmly_mischievous': 0.8,  # Include fun and engaging activities
            'adaptive_conversationalist': 0.85,  # Match communication style
            'family_inclusive': 0.9,  # Consider family context
            'dignity_preserving': 1.0  # Always respect user dignity
        }
    
    async def close(self):
        """Close resources"""
        await self.elr_adapter.close()
    
    async def get_recommendations(self,
                                context: RecommendationContext,
                                max_recommendations: Optional[int] = None) -> List[ActivityRecommendation]:
        """Get personalized activity recommendations.

        Results are cached per user+context using :class:`RecommendationCache`
        so rapid successive requests (e.g. page reloads, retries) avoid
        redundant scoring work.
        """
        if max_recommendations is None:
            max_recommendations = self.config.max_recommendations

        # Build cache-compatible parameters.  The cache keys on
        # (user_id, interests_list, difficulty) – we encode the context
        # parameters as "interests" so the existing cache key generation
        # produces a unique hash for each context combination.
        cache = get_recommendation_cache()
        cache_interests = [
            context.current_mood or "none",
            str(context.available_duration or 0),
            "group" if context.group_setting else "solo",
        ]
        cache_difficulty = float(max_recommendations)

        cached = cache.get(context.user_id, cache_interests, cache_difficulty)
        if cached is not None:
            logger.debug("Recommendation cache hit for user %s", context.user_id)
            # Cached data is a list of dicts; convert back to objects only if
            # they were stored as dicts.  If they're already recommendation
            # objects we can return directly.
            return cached  # type: ignore[return-value]

        # Get user's ELR profile and history
        elr_profile = await self.elr_adapter.get_user_elr_profile(context.user_id)
        activity_history = await self.elr_adapter.get_user_activity_history(context.user_id)

        if not elr_profile:
            defaults = await self._get_default_recommendations(context, max_recommendations)
            cache.set(context.user_id, cache_interests, defaults, cache_difficulty)
            return defaults

        # Get candidate activities based on context
        candidates = self._get_candidate_activities(context, elr_profile)

        # Score each candidate activity
        scored_recommendations = []
        for activity in candidates:
            recommendation = await self._score_activity(activity, context, elr_profile, activity_history)
            if recommendation.score >= self.config.recommendation_threshold:
                scored_recommendations.append(recommendation)

        # Sort by score and return top recommendations
        scored_recommendations.sort(key=lambda x: x.score, reverse=True)
        result = scored_recommendations[:max_recommendations]

        # Store in cache for subsequent identical requests
        cache.set(context.user_id, cache_interests, result, cache_difficulty)
        return result
    
    def _get_candidate_activities(self, context: RecommendationContext, profile: ELRProfile) -> List[Activity]:
        """Get candidate activities based on context and profile"""
        candidates = []
        
        # Filter by cognitive level
        cognitive_level = CognitiveLevel(profile.cognitive_level)
        cognitive_activities = self.catalog.get_activities_by_cognitive_level(cognitive_level)
        
        # Filter by group/personal preference
        if context.group_setting:
            candidates.extend([a for a in cognitive_activities if a.supports_group])
        else:
            candidates.extend([a for a in cognitive_activities if not a.supports_group or a.module == ActivityModule.PERSONAL])
        
        # Filter by carer availability
        if not context.carer_available:
            candidates = [a for a in candidates if not a.requires_carer]
        
        # Filter by duration if specified
        if context.available_duration:
            candidates = [a for a in candidates if a.duration_minutes <= context.available_duration]
        
        # Add today's world day activities if ReMeMades are enabled
        if self.config.rememades_enabled:
            world_day_activities = self.catalog.get_today_world_day_activities()
            candidates.extend(world_day_activities)
        
        # Remove duplicates
        seen_ids = set()
        unique_candidates = []
        for activity in candidates:
            if activity.id not in seen_ids:
                unique_candidates.append(activity)
                seen_ids.add(activity.id)
        
        return unique_candidates
    
    async def _score_activity(self, 
                             activity: Activity, 
                             context: RecommendationContext,
                             profile: ELRProfile,
                             history: List[ActivityEngagement]) -> ActivityRecommendation:
        """Score an activity for recommendation"""
        base_score = 0.5
        reasoning = []
        personalization_notes = []
        adaptation_suggestions = []
        
        # Interest matching
        interest_score = self._calculate_interest_score(activity, profile)
        base_score += interest_score * 0.3
        if interest_score > 0.7:
            reasoning.append(f"Matches your interests in {', '.join(activity.tags[:2])}")
        
        # Historical engagement
        history_score = self._calculate_history_score(activity, history)
        base_score += history_score * 0.25
        if history_score > 0.7:
            reasoning.append("You've enjoyed similar activities before")
        elif history_score < 0.3:
            reasoning.append("Trying something new based on your preferences")
        
        # Mood matching
        mood_score = self._calculate_mood_score(activity, context.current_mood, profile)
        base_score += mood_score * 0.2
        if mood_score > 0.7:
            reasoning.append(f"Well-suited for your current mood")
        
        # Time of day appropriateness
        time_score = self._calculate_time_score(activity, context.time_of_day)
        base_score += time_score * 0.1
        
        # Personality framework alignment
        personality_score = self._calculate_personality_score(activity, profile)
        base_score += personality_score * 0.15
        
        # Family context bonus
        family_score = self._calculate_family_score(activity, profile)
        if family_score > 0.5:
            base_score += 0.1
            reasoning.append("Connects with your family memories")
        
        # Generate personalization notes
        personalization_notes = self._generate_personalization_notes(activity, profile)
        
        # Generate adaptation suggestions
        adaptation_suggestions = self._generate_adaptation_suggestions(activity, profile, context)
        
        # Estimate engagement based on profile and activity match
        estimated_engagement = min(base_score + random.uniform(-0.1, 0.1), 1.0)
        
        # Ensure score is within bounds
        final_score = max(0.0, min(1.0, base_score))
        
        return ActivityRecommendation(
            activity=activity,
            score=final_score,
            reasoning=reasoning,
            personalization_notes=personalization_notes,
            estimated_engagement=estimated_engagement,
            adaptation_suggestions=adaptation_suggestions
        )
    
    def _calculate_interest_score(self, activity: Activity, profile: ELRProfile) -> float:
        """Calculate how well activity matches user interests"""
        if not profile.interests:
            return 0.5  # Neutral if no interests recorded
        
        # Check tag overlap with interests
        tag_matches = sum(1 for tag in activity.tags if tag.lower() in [i.lower() for i in profile.interests])
        tag_score = min(tag_matches / len(activity.tags), 1.0) if activity.tags else 0.0
        
        # Check if activity type matches preferences
        type_score = 0.0
        if activity.activity_type.value in profile.favorite_activities:
            type_score = 1.0
        elif activity.id in profile.favorite_activities:
            type_score = 1.0
        
        return (tag_score * 0.7) + (type_score * 0.3)
    
    def _calculate_history_score(self, activity: Activity, history: List[ActivityEngagement]) -> float:
        """Calculate score based on historical engagement"""
        if not history:
            return 0.5  # Neutral for new users
        
        # Find similar activities in history
        similar_engagements = [
            eng for eng in history 
            if eng.activity_type == activity.activity_type.value or eng.activity_id == activity.id
        ]
        
        if not similar_engagements:
            return 0.5  # No similar activities
        
        # Calculate average engagement for similar activities
        avg_engagement = sum(eng.engagement_score for eng in similar_engagements) / len(similar_engagements)
        
        # Boost score if user consistently engages well with this type
        if len(similar_engagements) >= 3 and avg_engagement > 0.7:
            return min(avg_engagement + 0.2, 1.0)
        
        return avg_engagement
    
    def _calculate_mood_score(self, activity: Activity, current_mood: Optional[str], profile: ELRProfile) -> float:
        """Calculate how well activity matches current mood"""
        if not current_mood:
            return 0.5
        
        # Mood-activity mapping based on care philosophy
        mood_activity_map = {
            'happy': ['group', 'social', 'music', 'celebration'],
            'sad': ['calming', 'comfort', 'familiar', 'music'],
            'anxious': ['calming', 'familiar', 'routine', 'gentle'],
            'energetic': ['active', 'group', 'engaging', 'challenging'],
            'tired': ['gentle', 'calming', 'low-energy', 'relaxing'],
            'confused': ['familiar', 'simple', 'routine', 'clear'],
            'agitated': ['calming', 'soothing', 'familiar', 'quiet']
        }
        
        mood_tags = mood_activity_map.get(current_mood.lower(), [])
        if not mood_tags:
            return 0.5
        
        # Check if activity tags match mood-appropriate activities
        matches = sum(1 for tag in activity.tags if tag.lower() in mood_tags)
        return min(matches / len(mood_tags), 1.0) if mood_tags else 0.5
    
    def _calculate_time_score(self, activity: Activity, time_of_day: Optional[str]) -> float:
        """Calculate time appropriateness score"""
        if not time_of_day:
            return 0.5
        
        # Time-based activity preferences
        time_preferences = {
            'morning': ['energetic', 'cognitive', 'planning', 'exercise'],
            'afternoon': ['social', 'group', 'active', 'engaging'],
            'evening': ['calming', 'relaxing', 'music', 'gentle'],
            'night': ['quiet', 'calming', 'soothing', 'bedtime']
        }
        
        preferred_tags = time_preferences.get(time_of_day.lower(), [])
        if not preferred_tags:
            return 0.5
        
        matches = sum(1 for tag in activity.tags if tag.lower() in preferred_tags)
        return min(matches / len(preferred_tags), 1.0) if preferred_tags else 0.5
    
    def _calculate_personality_score(self, activity: Activity, profile: ELRProfile) -> float:
        """Calculate score based on LUKi personality framework alignment"""
        score = 0.0
        
        # Memory keeper trait - prioritize memory-stimulating activities
        if any(tag in activity.tags for tag in ['memory', 'reminiscence', 'story', 'photos']):
            score += self.personality_weights['memory_keeper'] * 0.3
        
        # Warmly mischievous - include fun elements
        if any(tag in activity.tags for tag in ['fun', 'games', 'humor', 'playful']):
            score += self.personality_weights['warmly_mischievous'] * 0.2
        
        # Family inclusive - consider family context
        if activity.activity_type in [ActivityType.MYSTORY, ActivityType.PERSONAL_VIDEO] or 'family' in activity.tags:
            score += self.personality_weights['family_inclusive'] * 0.3
        
        # Dignity preserving - ensure appropriate cognitive level
        user_cognitive = CognitiveLevel(profile.cognitive_level)
        if user_cognitive in activity.cognitive_level:
            score += self.personality_weights['dignity_preserving'] * 0.2
        
        return min(score, 1.0)
    
    def _calculate_family_score(self, activity: Activity, profile: ELRProfile) -> float:
        """Calculate family context relevance score"""
        if not profile.family_context:
            return 0.0
        
        # Check if activity involves family elements
        family_activities = [ActivityType.MYSTORY, ActivityType.PERSONAL_VIDEO, ActivityType.PERSONAL_IMAGE]
        if activity.activity_type in family_activities:
            return 0.8
        
        # Check for family-related tags
        family_tags = ['family', 'relatives', 'children', 'grandchildren', 'spouse']
        matches = sum(1 for tag in activity.tags if tag.lower() in family_tags)
        return min(matches * 0.3, 1.0)
    
    def _generate_personalization_notes(self, activity: Activity, profile: ELRProfile) -> List[str]:
        """Generate personalization suggestions for the activity"""
        notes = []
        
        # Music personalization
        if activity.activity_type == ActivityType.PERSONAL_MUSIC and profile.music_preferences:
            if 'genres' in profile.music_preferences:
                notes.append(f"Focus on {', '.join(profile.music_preferences['genres'][:2])} music")
            if 'decades' in profile.music_preferences:
                notes.append(f"Include music from the {', '.join(profile.music_preferences['decades'])} era")
        
        # Photo personalization
        if activity.activity_type == ActivityType.PERSONAL_IMAGE and profile.photo_themes:
            notes.append(f"Use photos related to {', '.join(profile.photo_themes[:2])}")
        
        # Communication style adaptation
        if profile.communication_style:
            if profile.communication_style == 'simple':
                notes.append("Use clear, simple instructions and short sentences")
            elif profile.communication_style == 'detailed':
                notes.append("Provide rich context and detailed explanations")
        
        # Interest-based customization
        if profile.interests:
            relevant_interests = [interest for interest in profile.interests 
                                if any(interest.lower() in tag.lower() for tag in activity.tags)]
            if relevant_interests:
                notes.append(f"Connect to their interest in {', '.join(relevant_interests[:2])}")
        
        return notes
    
    def _generate_adaptation_suggestions(self, 
                                       activity: Activity, 
                                       profile: ELRProfile, 
                                       context: RecommendationContext) -> List[str]:
        """Generate suggestions for adapting the activity"""
        suggestions = []
        
        # Cognitive level adaptations
        cognitive_level = CognitiveLevel(profile.cognitive_level)
        
        if cognitive_level == CognitiveLevel.SEVERE:
            suggestions.append("Use very simple instructions and familiar content")
            suggestions.append("Focus on sensory engagement rather than complex tasks")
        elif cognitive_level == CognitiveLevel.MILD:
            suggestions.append("Break activity into smaller, manageable steps")
            suggestions.append("Provide gentle prompts and encouragement")
        
        # Duration adaptations
        if context.available_duration and context.available_duration < activity.duration_minutes:
            suggestions.append(f"Shorten to {context.available_duration} minutes by focusing on key elements")
        
        # Mood adaptations
        if context.current_mood:
            if context.current_mood.lower() == 'anxious':
                suggestions.append("Start slowly and provide extra reassurance")
            elif context.current_mood.lower() == 'energetic':
                suggestions.append("Include more interactive elements")
        
        # Group setting adaptations
        if context.group_setting and not activity.supports_group:
            suggestions.append("Adapt for group participation by having others share similar experiences")
        
        return suggestions
    
    async def _get_default_recommendations(self, 
                                         context: RecommendationContext,
                                         max_recommendations: int) -> List[ActivityRecommendation]:
        """Get default recommendations for new users"""
        # Safe, universally appealing activities for new users
        default_activity_ids = [
            "personal_music_reminiscence",
            "rememade_easter",  # or current world day
            "personal_image_therapy",
            "group_music_session",
            "mystory_recording"
        ]
        
        recommendations = []
        for activity_id in default_activity_ids[:max_recommendations]:
            activity = self.catalog.get_activity(activity_id)
            if activity:
                recommendation = ActivityRecommendation(
                    activity=activity,
                    score=0.6,  # Moderate confidence for new users
                    reasoning=["Great starting activity for new users"],
                    personalization_notes=["We'll learn your preferences as we go"],
                    estimated_engagement=0.6,
                    adaptation_suggestions=["Take your time and let us know what you enjoy"]
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    async def record_activity_feedback(self, engagement: ActivityEngagement):
        """Record activity engagement and update user preferences"""
        # Store the engagement
        await self.elr_adapter.record_activity_engagement(engagement)
        
        # Update user preferences based on engagement
        await self.elr_adapter.update_user_preferences_from_engagement(
            engagement.user_id, engagement
        )
    
    async def get_world_day_recommendations(self, user_id: str) -> List[ActivityRecommendation]:
        """Get recommendations specifically for today's world events"""
        context = RecommendationContext(user_id=user_id)
        
        # Get today's world day activities
        world_day_activities = self.catalog.get_today_world_day_activities()
        
        # Get user profile for personalization
        profile = await self.elr_adapter.get_user_elr_profile(user_id)
        history = await self.elr_adapter.get_user_activity_history(user_id)
        
        recommendations = []
        for activity in world_day_activities:
            if profile:
                recommendation = await self._score_activity(activity, context, profile, history)
            else:
                recommendation = ActivityRecommendation(
                    activity=activity,
                    score=0.7,
                    reasoning=["Special activity for today's world event"],
                    personalization_notes=["Perfect for celebrating today"],
                    estimated_engagement=0.7,
                    adaptation_suggestions=[]
                )
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x.score, reverse=True)
