"""
World Day integration for ReMeMades activities
Provides context-aware activity suggestions based on international observances
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WorldDay:
    """Represents a World Day observance"""
    date: date
    name: str
    description: str
    category: str
    activity_tags: List[str]
    cultural_significance: str


class WorldDayCalendar:
    """Calendar of World Days and international observances"""
    
    def __init__(self):
        self.world_days = self._initialize_calendar()
    
    def _initialize_calendar(self) -> Dict[Tuple[int, int], List[WorldDay]]:
        """Initialize calendar with World Days"""
        calendar = {}
        
        # Format: (month, day): [WorldDay, ...]
        world_days_data = [
            # January
            ((1, 1), WorldDay(
                date=date(2025, 1, 1),
                name="New Year's Day",
                description="Celebration of the new year",
                category="celebration",
                activity_tags=["reflection", "goals", "celebration"],
                cultural_significance="Universal celebration marking fresh starts"
            )),
            ((1, 4), WorldDay(
                date=date(2025, 1, 4),
                name="World Braille Day",
                description="Awareness of importance of Braille for blind and visually impaired",
                category="awareness",
                activity_tags=["accessibility", "education", "inclusion"],
                cultural_significance="Promotes accessibility and inclusion"
            )),
            
            # February
            ((2, 14), WorldDay(
                date=date(2025, 2, 14),
                name="Valentine's Day",
                description="Day of love and affection",
                category="celebration",
                activity_tags=["love", "relationships", "creativity"],
                cultural_significance="Celebrates love and relationships"
            )),
            ((2, 20), WorldDay(
                date=date(2025, 2, 20),
                name="World Day of Social Justice",
                description="Promoting social justice and fair globalization",
                category="awareness",
                activity_tags=["justice", "equality", "community"],
                cultural_significance="UN observance promoting fairness"
            )),
            
            # March
            ((3, 8), WorldDay(
                date=date(2025, 3, 8),
                name="International Women's Day",
                description="Celebrating women's achievements",
                category="celebration",
                activity_tags=["women", "equality", "empowerment"],
                cultural_significance="Global celebration of women's contributions"
            )),
            ((3, 20), WorldDay(
                date=date(2025, 3, 20),
                name="International Day of Happiness",
                description="Recognizing happiness as a fundamental human goal",
                category="wellbeing",
                activity_tags=["happiness", "wellbeing", "positivity"],
                cultural_significance="UN observance promoting wellbeing"
            )),
            
            # April
            ((4, 7), WorldDay(
                date=date(2025, 4, 7),
                name="World Health Day",
                description="Global health awareness",
                category="health",
                activity_tags=["health", "wellness", "exercise"],
                cultural_significance="WHO observance promoting health"
            )),
            ((4, 22), WorldDay(
                date=date(2025, 4, 22),
                name="Earth Day",
                description="Environmental protection awareness",
                category="environment",
                activity_tags=["nature", "environment", "sustainability"],
                cultural_significance="Global environmental movement"
            )),
            
            # May
            ((5, 15), WorldDay(
                date=date(2025, 5, 15),
                name="International Day of Families",
                description="Celebrating families and their importance",
                category="family",
                activity_tags=["family", "relationships", "togetherness"],
                cultural_significance="UN observance celebrating families"
            )),
            
            # June
            ((6, 5), WorldDay(
                date=date(2025, 6, 5),
                name="World Environment Day",
                description="Encouraging awareness and action for environmental protection",
                category="environment",
                activity_tags=["nature", "conservation", "outdoor"],
                cultural_significance="UN's principal vehicle for environmental awareness"
            )),
            ((6, 21), WorldDay(
                date=date(2025, 6, 21),
                name="International Day of Yoga",
                description="Promoting yoga for health and wellbeing",
                category="wellbeing",
                activity_tags=["yoga", "mindfulness", "exercise"],
                cultural_significance="UN observance promoting holistic health"
            )),
            
            # September
            ((9, 21), WorldDay(
                date=date(2025, 9, 21),
                name="International Day of Peace",
                description="Strengthening ideals of peace",
                category="peace",
                activity_tags=["peace", "meditation", "reflection"],
                cultural_significance="UN observance promoting peace"
            )),
            
            # October
            ((10, 1), WorldDay(
                date=date(2025, 10, 1),
                name="International Day of Older Persons",
                description="Recognizing contributions of older persons",
                category="celebration",
                activity_tags=["aging", "wisdom", "community"],
                cultural_significance="UN observance honoring older adults"
            )),
            ((10, 10), WorldDay(
                date=date(2025, 10, 10),
                name="World Mental Health Day",
                description="Mental health awareness and support",
                category="health",
                activity_tags=["mental_health", "wellbeing", "support"],
                cultural_significance="WHO observance promoting mental health"
            )),
            
            # December
            ((12, 3), WorldDay(
                date=date(2025, 12, 3),
                name="International Day of Persons with Disabilities",
                description="Promoting rights and wellbeing of persons with disabilities",
                category="awareness",
                activity_tags=["inclusion", "accessibility", "rights"],
                cultural_significance="UN observance promoting inclusion"
            )),
        ]
        
        for date_key, world_day in world_days_data:
            if date_key not in calendar:
                calendar[date_key] = []
            calendar[date_key].append(world_day)
        
        return calendar
    
    def get_today_world_days(self) -> List[WorldDay]:
        """Get World Days for today"""
        today = datetime.now().date()
        return self.get_world_days_for_date(today)
    
    def get_world_days_for_date(self, target_date: date) -> List[WorldDay]:
        """Get World Days for specific date"""
        date_key = (target_date.month, target_date.day)
        return self.world_days.get(date_key, [])
    
    def get_upcoming_world_days(self, days_ahead: int = 7) -> List[WorldDay]:
        """Get World Days in the next N days"""
        today = datetime.now().date()
        upcoming = []
        
        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            world_days = self.get_world_days_for_date(check_date)
            upcoming.extend(world_days)
        
        return upcoming
    
    def get_world_day_context(self) -> Dict[str, any]:
        """
        Get context about today's World Days for activity recommendations
        
        Returns:
            Dictionary with World Day context
        """
        today_world_days = self.get_today_world_days()
        
        if not today_world_days:
            return {
                "has_world_day": False,
                "world_days": [],
                "activity_tags": [],
                "suggested_themes": []
            }
        
        # Aggregate tags and themes
        all_tags = []
        themes = []
        
        for wd in today_world_days:
            all_tags.extend(wd.activity_tags)
            themes.append(wd.name)
        
        return {
            "has_world_day": True,
            "world_days": [
                {
                    "name": wd.name,
                    "description": wd.description,
                    "category": wd.category,
                    "cultural_significance": wd.cultural_significance
                }
                for wd in today_world_days
            ],
            "activity_tags": list(set(all_tags)),
            "suggested_themes": themes
        }


class WorldDayActivityMatcher:
    """Matches activities to World Days"""
    
    def __init__(self, calendar: WorldDayCalendar):
        self.calendar = calendar
    
    def get_relevant_activities(
        self,
        activities: List[Dict],
        target_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Filter activities relevant to World Days
        
        Args:
            activities: List of all activities
            target_date: Date to check (default: today)
        
        Returns:
            List of relevant activities with World Day context
        """
        if target_date is None:
            target_date = datetime.now().date()
        
        world_days = self.calendar.get_world_days_for_date(target_date)
        
        if not world_days:
            return []
        
        # Get all relevant tags
        relevant_tags = set()
        for wd in world_days:
            relevant_tags.update(wd.activity_tags)
        
        # Filter activities
        matched_activities = []
        for activity in activities:
            activity_tags = set(activity.get("tags", []))
            
            # Check for tag overlap
            if activity_tags & relevant_tags:
                # Add World Day context
                activity_with_context = activity.copy()
                activity_with_context["world_day_context"] = {
                    "world_days": [wd.name for wd in world_days],
                    "relevance_reason": f"Related to {world_days[0].name}"
                }
                matched_activities.append(activity_with_context)
        
        logger.info(
            f"Found {len(matched_activities)} activities relevant to {len(world_days)} World Day(s)",
            extra={"date": target_date.isoformat(), "world_days": [wd.name for wd in world_days]}
        )
        
        return matched_activities


# Global instances
from datetime import timedelta
world_day_calendar = WorldDayCalendar()
world_day_matcher = WorldDayActivityMatcher(world_day_calendar)
