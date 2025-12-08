"""
Activity Catalog for ReMeLife Integration

Manages the catalog of activities from RemindMeCare system including:
- ReMeMades (World Days Calendar activities)
- Personal Module activities (image therapy, music reminiscence, My Story)
- Group Module activities (group video, group music sessions)
"""
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, date
from enum import Enum

from ..config import get_config


class ActivityType(Enum):
    """Types of activities in the ReMeLife system"""
    REMEMADE = "rememade"  # World Days Calendar activities
    PERSONAL_IMAGE = "personal_image"  # One-to-one image therapy
    PERSONAL_MUSIC = "personal_music"  # Music reminiscence
    PERSONAL_VIDEO = "personal_video"  # Family photos & videos
    PERSONAL_CALMING = "personal_calming"  # Calming strategies
    PERSONAL_RECORDED = "personal_recorded"  # Recorded activities (gardening, swimming)
    GROUP_VIDEO = "group_video"  # Group video entertainment
    GROUP_MUSIC = "group_music"  # Group music sessions
    MYSTORY = "mystory"  # My Story module interactions
    INSIGHTS = "insights"  # Insights recording
    CUSTOM = "custom"  # Custom created activities


class ActivityModule(Enum):
    """Activity modules from RemindMeCare"""
    GROUP = "group"
    PERSONAL = "personal"
    MYSTORY = "mystory"


class CognitiveLevel(Enum):
    """Cognitive capacity levels for activity adaptation"""
    HIGH = "high"
    MODERATE = "moderate"
    MILD = "mild"
    SEVERE = "severe"


@dataclass
class Activity:
    """Represents a single activity in the catalog"""
    id: str
    title: str
    description: str
    activity_type: ActivityType
    module: ActivityModule
    cognitive_level: List[CognitiveLevel]
    tags: List[str]
    duration_minutes: int
    requires_carer: bool
    supports_group: bool
    world_day_theme: Optional[str] = None
    content_type: Optional[str] = None  # video, music, image, text
    difficulty_adaptable: bool = True
    engagement_metrics: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.engagement_metrics is None:
            self.engagement_metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert activity to dictionary for storage/retrieval"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Activity':
        """Create activity from dictionary"""
        # Convert enum strings back to enums
        data['activity_type'] = ActivityType(data['activity_type'])
        data['module'] = ActivityModule(data['module'])
        data['cognitive_level'] = [CognitiveLevel(level) for level in data['cognitive_level']]
        return cls(**data)


class ActivityCatalog:
    """Manages the catalog of ReMeLife activities"""
    
    def __init__(self):
        self.config = get_config()
        self.activities: Dict[str, Activity] = {}
        self._initialize_default_activities()
    
    def _initialize_default_activities(self):
        """Initialize catalog with default ReMeLife activities"""
        
        # ReMeMades (World Days Calendar)
        self.add_activity(Activity(
            id="rememade_easter",
            title="Easter Memories",
            description="Share Easter traditions, egg hunts, and spring celebrations",
            activity_type=ActivityType.REMEMADE,
            module=ActivityModule.GROUP,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE, CognitiveLevel.MILD],
            tags=["easter", "spring", "traditions", "family", "celebrations"],
            duration_minutes=30,
            requires_carer=True,
            supports_group=True,
            world_day_theme="Easter Sunday",
            content_type="mixed"
        ))
        
        self.add_activity(Activity(
            id="rememade_poets_day",
            title="World Poetry Day",
            description="Explore favorite poems, recite verses, and share literary memories",
            activity_type=ActivityType.REMEMADE,
            module=ActivityModule.PERSONAL,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE],
            tags=["poetry", "literature", "memory", "recitation", "culture"],
            duration_minutes=25,
            requires_carer=True,
            supports_group=True,
            world_day_theme="World Poetry Day",
            content_type="text"
        ))
        
        # Personal Module Activities
        self.add_activity(Activity(
            id="personal_image_therapy",
            title="Personal Photo Reminiscence",
            description="Use personal images and videos to stimulate memory recall",
            activity_type=ActivityType.PERSONAL_IMAGE,
            module=ActivityModule.PERSONAL,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE, CognitiveLevel.MILD, CognitiveLevel.SEVERE],
            tags=["photos", "memories", "family", "reminiscence", "therapy"],
            duration_minutes=20,
            requires_carer=True,
            supports_group=False,
            content_type="image"
        ))
        
        self.add_activity(Activity(
            id="personal_music_reminiscence",
            title="Personal Music Journey",
            description="Build personalized playlists to evoke memories and support therapy",
            activity_type=ActivityType.PERSONAL_MUSIC,
            module=ActivityModule.PERSONAL,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE, CognitiveLevel.MILD, CognitiveLevel.SEVERE],
            tags=["music", "memories", "therapy", "emotional", "personal"],
            duration_minutes=30,
            requires_carer=False,
            supports_group=False,
            content_type="music"
        ))
        
        self.add_activity(Activity(
            id="personal_calming_strategy",
            title="Calming Content Session",
            description="Use familiar content to soothe agitation and support emotional regulation",
            activity_type=ActivityType.PERSONAL_CALMING,
            module=ActivityModule.PERSONAL,
            cognitive_level=[CognitiveLevel.MODERATE, CognitiveLevel.MILD, CognitiveLevel.SEVERE],
            tags=["calming", "emotional", "regulation", "familiar", "comfort"],
            duration_minutes=15,
            requires_carer=True,
            supports_group=False,
            content_type="mixed"
        ))
        
        # Group Module Activities
        self.add_activity(Activity(
            id="group_video_entertainment",
            title="Group Video Session",
            description="Curated video content for group engagement around themes like travel or sports",
            activity_type=ActivityType.GROUP_VIDEO,
            module=ActivityModule.GROUP,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE, CognitiveLevel.MILD],
            tags=["group", "video", "entertainment", "social", "themes"],
            duration_minutes=45,
            requires_carer=True,
            supports_group=True,
            content_type="video"
        ))
        
        self.add_activity(Activity(
            id="group_music_session",
            title="Group Music Experience",
            description="Combine playlists from multiple profiles for communal enjoyment",
            activity_type=ActivityType.GROUP_MUSIC,
            module=ActivityModule.GROUP,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE, CognitiveLevel.MILD, CognitiveLevel.SEVERE],
            tags=["group", "music", "social", "community", "sharing"],
            duration_minutes=40,
            requires_carer=True,
            supports_group=True,
            content_type="music"
        ))
        
        # My Story Activities
        self.add_activity(Activity(
            id="mystory_recording",
            title="Life Story Recording",
            description="Record and capture life stories, memories, and personal insights",
            activity_type=ActivityType.MYSTORY,
            module=ActivityModule.MYSTORY,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE, CognitiveLevel.MILD],
            tags=["mystory", "recording", "memories", "personal", "legacy"],
            duration_minutes=25,
            requires_carer=True,
            supports_group=False,
            content_type="mixed"
        ))
        
        self.add_activity(Activity(
            id="insights_capture",
            title="Insights Discovery",
            description="Record discoveries learned about the person during activities",
            activity_type=ActivityType.INSIGHTS,
            module=ActivityModule.PERSONAL,
            cognitive_level=[CognitiveLevel.HIGH, CognitiveLevel.MODERATE, CognitiveLevel.MILD],
            tags=["insights", "discovery", "learning", "personal", "knowledge"],
            duration_minutes=10,
            requires_carer=True,
            supports_group=False,
            content_type="text"
        ))
    
    def add_activity(self, activity: Activity):
        """Add an activity to the catalog"""
        self.activities[activity.id] = activity
    
    def get_activity(self, activity_id: str) -> Optional[Activity]:
        """Get a specific activity by ID"""
        return self.activities.get(activity_id)
    
    def get_activities_by_type(self, activity_type: ActivityType) -> List[Activity]:
        """Get all activities of a specific type"""
        return [activity for activity in self.activities.values() 
                if activity.activity_type == activity_type]
    
    def get_activities_by_module(self, module: ActivityModule) -> List[Activity]:
        """Get all activities for a specific module"""
        return [activity for activity in self.activities.values() 
                if activity.module == module]
    
    def get_activities_by_cognitive_level(self, cognitive_level: CognitiveLevel) -> List[Activity]:
        """Get activities suitable for a specific cognitive level"""
        return [activity for activity in self.activities.values() 
                if cognitive_level in activity.cognitive_level]
    
    def get_activities_by_tags(self, tags: List[str]) -> List[Activity]:
        """Get activities that match any of the provided tags"""
        matching_activities = []
        for activity in self.activities.values():
            if any(tag in activity.tags for tag in tags):
                matching_activities.append(activity)
        return matching_activities
    
    def get_world_day_activities(self, world_day_theme: Optional[str] = None) -> List[Activity]:
        """Get ReMeMades activities, optionally filtered by theme"""
        rememades = self.get_activities_by_type(ActivityType.REMEMADE)
        if world_day_theme:
            return [activity for activity in rememades 
                    if activity.world_day_theme and world_day_theme.lower() in activity.world_day_theme.lower()]
        return rememades
    
    def get_group_activities(self) -> List[Activity]:
        """Get all activities that support group participation"""
        return [activity for activity in self.activities.values() 
                if activity.supports_group]
    
    def get_personal_activities(self) -> List[Activity]:
        """Get all personal (individual) activities"""
        return [activity for activity in self.activities.values() 
                if not activity.supports_group or activity.module == ActivityModule.PERSONAL]
    
    def search_activities(self, 
                         query: Optional[str] = None,
                         activity_type: Optional[ActivityType] = None,
                         module: Optional[ActivityModule] = None,
                         cognitive_level: Optional[CognitiveLevel] = None,
                         tags: Optional[List[str]] = None,
                         requires_carer: Optional[bool] = None,
                         supports_group: Optional[bool] = None) -> List[Activity]:
        """Search activities with multiple filters"""
        results = list(self.activities.values())
        
        if query:
            query_lower = query.lower()
            results = [activity for activity in results 
                      if query_lower in activity.title.lower() or 
                         query_lower in activity.description.lower() or
                         any(query_lower in tag.lower() for tag in activity.tags)]
        
        if activity_type:
            results = [activity for activity in results if activity.activity_type == activity_type]
        
        if module:
            results = [activity for activity in results if activity.module == module]
        
        if cognitive_level:
            results = [activity for activity in results if cognitive_level in activity.cognitive_level]
        
        if tags:
            results = [activity for activity in results 
                      if any(tag in activity.tags for tag in tags)]
        
        if requires_carer is not None:
            results = [activity for activity in results if activity.requires_carer == requires_carer]
        
        if supports_group is not None:
            results = [activity for activity in results if activity.supports_group == supports_group]
        
        return results
    
    def get_today_world_day_activities(self) -> List[Activity]:
        """Get activities for today's world events (placeholder for actual calendar integration)"""
        # This would integrate with actual world days calendar
        # For now, return a sample of ReMeMades
        today = date.today()
        # Placeholder logic - in real implementation, this would query actual world days API
        return self.get_activities_by_type(ActivityType.REMEMADE)[:3]
    
    def export_catalog(self) -> Dict[str, Any]:
        """Export the entire catalog to a dictionary"""
        return {
            "activities": {aid: activity.to_dict() for aid, activity in self.activities.items()},
            "metadata": {
                "total_activities": len(self.activities),
                "export_timestamp": datetime.utcnow().isoformat()
            }
        }
    
    def import_catalog(self, catalog_data: Dict[str, Any]):
        """Import activities from a dictionary"""
        if "activities" in catalog_data:
            for activity_id, activity_data in catalog_data["activities"].items():
                try:
                    activity = Activity.from_dict(activity_data)
                    self.add_activity(activity)
                except Exception as e:
                    print(f"Error importing activity {activity_id}: {e}")
