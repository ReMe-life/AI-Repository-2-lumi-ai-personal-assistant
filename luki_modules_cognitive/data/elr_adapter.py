"""
ELR (Electronic Life Record) Adapter

Integrates with LUKi Memory Service to retrieve and process ELR data
for activity recommendations and personalization.
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx

from ..config import get_config


@dataclass
class ELRProfile:
    """User's ELR profile for activity recommendations"""
    user_id: str
    preferences: Dict[str, Any]
    interests: List[str]
    cognitive_level: str
    mobility_level: str
    communication_style: str
    favorite_activities: List[str]
    music_preferences: Dict[str, Any]
    photo_themes: List[str]
    family_context: Dict[str, Any]
    care_goals: List[str]
    recent_engagement: Dict[str, Any]
    mood_patterns: Dict[str, Any]
    memory_triggers: List[str]
    
    @classmethod
    def from_elr_data(cls, user_id: str, elr_data: Dict[str, Any]) -> 'ELRProfile':
        """Create ELR profile from raw ELR data"""
        return cls(
            user_id=user_id,
            preferences=elr_data.get('preferences', {}),
            interests=elr_data.get('interests', []),
            cognitive_level=elr_data.get('cognitive_level', 'moderate'),
            mobility_level=elr_data.get('mobility_level', 'moderate'),
            communication_style=elr_data.get('communication_style', 'conversational'),
            favorite_activities=elr_data.get('favorite_activities', []),
            music_preferences=elr_data.get('music_preferences', {}),
            photo_themes=elr_data.get('photo_themes', []),
            family_context=elr_data.get('family_context', {}),
            care_goals=elr_data.get('care_goals', []),
            recent_engagement=elr_data.get('recent_engagement', {}),
            mood_patterns=elr_data.get('mood_patterns', {}),
            memory_triggers=elr_data.get('memory_triggers', [])
        )


@dataclass
class ActivityEngagement:
    """Records user engagement with activities"""
    user_id: str
    activity_id: str
    activity_type: str
    engagement_score: float  # 0.0 to 1.0
    duration_minutes: int
    completion_status: str  # completed, partial, abandoned
    feedback: Optional[str]
    mood_before: Optional[str]
    mood_after: Optional[str]
    carer_notes: Optional[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'activity_id': self.activity_id,
            'activity_type': self.activity_type,
            'engagement_score': self.engagement_score,
            'duration_minutes': self.duration_minutes,
            'completion_status': self.completion_status,
            'feedback': self.feedback,
            'mood_before': self.mood_before,
            'mood_after': self.mood_after,
            'carer_notes': self.carer_notes,
            'timestamp': self.timestamp.isoformat()
        }


class ELRAdapter:
    """Adapter for integrating with LUKi Memory Service ELR data.
    
    Uses in-memory storage for profiles and activity history since
    the Memory Service KV store is not available.
    """
    
    # In-memory storage for user profiles and activity history
    _profiles: Dict[str, 'ELRProfile'] = {}
    _activity_history: Dict[str, List['ActivityEngagement']] = {}
    
    def __init__(self):
        self.config = get_config()
        self.memory_service_url = self.config.memory_service_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def get_user_elr_profile(self, user_id: str) -> Optional[ELRProfile]:
        """Retrieve user's ELR profile from in-memory storage"""
        if user_id in self._profiles:
            return self._profiles[user_id]
        
        # No profile exists, create a basic one
        return await self._create_basic_profile(user_id)
    
    async def _create_basic_profile(self, user_id: str) -> ELRProfile:
        """Create a basic ELR profile for new users"""
        basic_profile = ELRProfile(
            user_id=user_id,
            preferences={},
            interests=[],
            cognitive_level="moderate",
            mobility_level="moderate", 
            communication_style="conversational",
            favorite_activities=[],
            music_preferences={},
            photo_themes=[],
            family_context={},
            care_goals=[],
            recent_engagement={},
            mood_patterns={},
            memory_triggers=[]
        )
        
        # Store the basic profile in memory
        await self.update_elr_profile(basic_profile)
        return basic_profile
    
    async def update_elr_profile(self, profile: ELRProfile) -> bool:
        """Update user's ELR profile in in-memory storage"""
        try:
            self._profiles[profile.user_id] = profile
            return True
        except Exception as e:
            print(f"Error updating ELR profile: {e}")
            return False
    
    async def get_user_activity_history(self, user_id: str, days: int = 30) -> List[ActivityEngagement]:
        """Get user's recent activity engagement history from in-memory storage"""
        try:
            history = self._activity_history.get(user_id, [])
            
            if not history:
                return []
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Filter by date range
            recent = [eng for eng in history if eng.timestamp >= cutoff_date]
            
            return sorted(recent, key=lambda x: x.timestamp, reverse=True)
            
        except Exception as e:
            print(f"Error retrieving activity history: {e}")
            return []
    
    async def record_activity_engagement(self, engagement: ActivityEngagement) -> bool:
        """Record a new activity engagement in in-memory storage"""
        try:
            user_id = engagement.user_id
            
            if user_id not in self._activity_history:
                self._activity_history[user_id] = []
            
            # Add new engagement
            self._activity_history[user_id].append(engagement)
            
            # Keep only last 100 engagements to prevent unlimited growth
            self._activity_history[user_id] = sorted(
                self._activity_history[user_id],
                key=lambda x: x.timestamp,
                reverse=True
            )[:100]
            
            return True
            
        except Exception as e:
            print(f"Error recording activity engagement: {e}")
            return False
    
    async def get_user_preferences_for_activity_type(self, user_id: str, activity_type: str) -> Dict[str, Any]:
        """Get user preferences specific to an activity type"""
        profile = await self.get_user_elr_profile(user_id)
        if not profile:
            return {}
        
        # Extract relevant preferences based on activity type
        if activity_type == "music":
            return profile.music_preferences
        elif activity_type == "image" or activity_type == "photo":
            return {"themes": profile.photo_themes}
        elif activity_type == "group":
            return {"communication_style": profile.communication_style}
        else:
            return profile.preferences
    
    async def update_user_preferences_from_engagement(self, user_id: str, engagement: ActivityEngagement):
        """Update user preferences based on activity engagement"""
        if engagement.engagement_score < 0.3:
            return  # Don't learn from poor engagements
        
        profile = await self.get_user_elr_profile(user_id)
        if not profile:
            return
        
        # Update favorite activities if engagement was high
        if engagement.engagement_score > 0.7 and engagement.activity_id not in profile.favorite_activities:
            profile.favorite_activities.append(engagement.activity_id)
            
        # Update recent engagement patterns
        profile.recent_engagement[engagement.activity_type] = {
            "last_engagement": engagement.timestamp.isoformat(),
            "average_score": engagement.engagement_score,
            "preferred_duration": engagement.duration_minutes
        }
        
        # Update mood patterns if available
        if engagement.mood_before and engagement.mood_after:
            mood_key = f"{engagement.activity_type}_mood_impact"
            profile.mood_patterns[mood_key] = {
                "before": engagement.mood_before,
                "after": engagement.mood_after,
                "improvement": engagement.mood_after != engagement.mood_before
            }
        
        await self.update_elr_profile(profile)
    
    async def search_elr_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search user's ELR memories using semantic search"""
        try:
            response = await self.client.post(
                f"{self.memory_service_url}/v1/search",
                json={
                    "user_id": user_id,
                    "query": query,
                    "limit": limit,
                    "filter": {"content_type": "memory"}
                }
            )
            
            if response.status_code == 200:
                return response.json().get('results', [])
            
            return []
            
        except Exception as e:
            print(f"Error searching ELR memories: {e}")
            return []
    
    async def get_family_context(self, user_id: str) -> Dict[str, Any]:
        """Get family context and care circle information"""
        profile = await self.get_user_elr_profile(user_id)
        if profile:
            return profile.family_context
        return {}
    
    async def get_current_mood_context(self, user_id: str) -> Optional[str]:
        """Get user's current mood context from recent interactions"""
        history = await self.get_user_activity_history(user_id, days=1)
        
        if history and history[0].mood_after:
            return history[0].mood_after
        
        # Fallback to mood patterns
        profile = await self.get_user_elr_profile(user_id)
        if profile and profile.mood_patterns:
            # Return most common recent mood
            recent_moods = [pattern.get('after') for pattern in profile.mood_patterns.values() 
                          if pattern.get('after')]
            if recent_moods:
                return max(set(recent_moods), key=recent_moods.count)
        
        return None
