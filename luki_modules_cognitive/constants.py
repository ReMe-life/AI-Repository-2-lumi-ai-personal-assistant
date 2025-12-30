"""
Constants for LUKi Cognitive Modules

Centralized configuration for activity types, mood categories, 
recommendation parameters, and cognitive module defaults.
"""

from typing import Final, Tuple

# =============================================================================
# SERVICE IDENTIFICATION
# =============================================================================

SERVICE_NAME: Final[str] = "luki-modules-cognitive"
SERVICE_VERSION: Final[str] = "1.0.0"

# =============================================================================
# ACTIVITY TYPES
# =============================================================================

class ActivityTypes:
    """Activity type identifiers"""
    REMINISCENCE: Final[str] = "reminiscence"
    MUSIC_THERAPY: Final[str] = "music_therapy"
    COGNITIVE_GAMES: Final[str] = "cognitive_games"
    SOCIAL_ACTIVITY: Final[str] = "social_activity"
    PHYSICAL_EXERCISE: Final[str] = "physical_exercise"
    CREATIVE_ARTS: Final[str] = "creative_arts"
    RELAXATION: Final[str] = "relaxation"
    LIFE_STORY: Final[str] = "life_story"
    PHOTO_REMINISCENCE: Final[str] = "photo_reminiscence"
    WORLD_DAY: Final[str] = "world_day"
    
    ALL: Final[Tuple[str, ...]] = (
        REMINISCENCE, MUSIC_THERAPY, COGNITIVE_GAMES, SOCIAL_ACTIVITY,
        PHYSICAL_EXERCISE, CREATIVE_ARTS, RELAXATION, LIFE_STORY,
        PHOTO_REMINISCENCE, WORLD_DAY
    )


# =============================================================================
# MOOD CATEGORIES
# =============================================================================

class MoodCategories:
    """Recognized mood categories for activity recommendation"""
    # Positive moods
    HAPPY: Final[str] = "happy"
    EXCITED: Final[str] = "excited"
    CALM: Final[str] = "calm"
    CONTENT: Final[str] = "content"
    ENERGETIC: Final[str] = "energetic"
    
    # Negative moods
    SAD: Final[str] = "sad"
    ANXIOUS: Final[str] = "anxious"
    CONFUSED: Final[str] = "confused"
    AGITATED: Final[str] = "agitated"
    TIRED: Final[str] = "tired"
    FRUSTRATED: Final[str] = "frustrated"
    
    # Neutral
    NEUTRAL: Final[str] = "neutral"
    
    POSITIVE: Final[Tuple[str, ...]] = (HAPPY, EXCITED, CALM, CONTENT, ENERGETIC)
    NEGATIVE: Final[Tuple[str, ...]] = (SAD, ANXIOUS, CONFUSED, AGITATED, TIRED, FRUSTRATED)
    ALL: Final[Tuple[str, ...]] = POSITIVE + NEGATIVE + (NEUTRAL,)


# =============================================================================
# COGNITIVE LEVELS
# =============================================================================

class CognitiveLevels:
    """Cognitive ability level identifiers"""
    HIGH: Final[str] = "high"
    MEDIUM: Final[str] = "medium"
    LOW: Final[str] = "low"
    ADAPTIVE: Final[str] = "adaptive"
    
    ALL: Final[Tuple[str, ...]] = (HIGH, MEDIUM, LOW, ADAPTIVE)


# =============================================================================
# DURATION LIMITS (minutes)
# =============================================================================

class DurationLimits:
    """Activity duration limits in minutes"""
    MIN_DURATION: Final[int] = 5
    SHORT_DURATION: Final[int] = 15
    MEDIUM_DURATION: Final[int] = 30
    LONG_DURATION: Final[int] = 60
    MAX_DURATION: Final[int] = 120
    DEFAULT_DURATION: Final[int] = 30


# =============================================================================
# RECOMMENDATION CONFIGURATION
# =============================================================================

class RecommendationDefaults:
    """Default values for recommendation engine"""
    MAX_RECOMMENDATIONS: Final[int] = 5
    MIN_SCORE_THRESHOLD: Final[float] = 0.3
    DIVERSITY_WEIGHT: Final[float] = 0.2
    RECENCY_WEIGHT: Final[float] = 0.15
    PERSONALIZATION_WEIGHT: Final[float] = 0.4
    CONTEXT_WEIGHT: Final[float] = 0.25
    
    # Engagement score thresholds
    HIGH_ENGAGEMENT: Final[float] = 0.8
    MEDIUM_ENGAGEMENT: Final[float] = 0.5
    LOW_ENGAGEMENT: Final[float] = 0.3


# =============================================================================
# LIFE STORY CONFIGURATION
# =============================================================================

class LifeStoryDefaults:
    """Default values for life story recording"""
    MAX_CHUNK_LENGTH: Final[int] = 5000
    MIN_CHUNK_LENGTH: Final[int] = 50
    MAX_SESSIONS_PER_USER: Final[int] = 100
    SESSION_TIMEOUT_HOURS: Final[int] = 24
    MAX_PHASES: Final[int] = 10


# =============================================================================
# IMAGE GENERATION
# =============================================================================

class ImageGenerationDefaults:
    """Defaults for photo reminiscence image generation"""
    DEFAULT_STYLE: Final[str] = "nostalgic_photograph"
    MAX_PROMPT_LENGTH: Final[int] = 1000
    DEFAULT_ASPECT_RATIO: Final[str] = "1:1"
    
    # Rate limits by tier
    FREE_TIER_DAILY_LIMIT: Final[int] = 5
    BASIC_TIER_DAILY_LIMIT: Final[int] = 20
    PREMIUM_TIER_DAILY_LIMIT: Final[int] = 50


# =============================================================================
# TIME OF DAY
# =============================================================================

class TimeOfDay:
    """Time of day categories for contextual recommendations"""
    MORNING: Final[str] = "morning"
    AFTERNOON: Final[str] = "afternoon"
    EVENING: Final[str] = "evening"
    NIGHT: Final[str] = "night"
    
    # Hour ranges (24-hour format)
    MORNING_HOURS: Final[Tuple[int, int]] = (6, 12)
    AFTERNOON_HOURS: Final[Tuple[int, int]] = (12, 17)
    EVENING_HOURS: Final[Tuple[int, int]] = (17, 21)
    NIGHT_HOURS: Final[Tuple[int, int]] = (21, 6)


# =============================================================================
# ERROR CODES
# =============================================================================

class ErrorCodes:
    """Standardized error codes for cognitive module"""
    UNKNOWN_ERROR: Final[str] = "UNKNOWN_ERROR"
    VALIDATION_ERROR: Final[str] = "VALIDATION_ERROR"
    ACTIVITY_NOT_FOUND: Final[str] = "ACTIVITY_NOT_FOUND"
    SESSION_NOT_FOUND: Final[str] = "SESSION_NOT_FOUND"
    SESSION_EXPIRED: Final[str] = "SESSION_EXPIRED"
    RECOMMENDATION_ERROR: Final[str] = "RECOMMENDATION_ERROR"
    ELR_CONNECTION_ERROR: Final[str] = "ELR_CONNECTION_ERROR"
    IMAGE_GENERATION_ERROR: Final[str] = "IMAGE_GENERATION_ERROR"
    RATE_LIMIT_EXCEEDED: Final[str] = "RATE_LIMIT_EXCEEDED"
    CONSENT_REQUIRED: Final[str] = "CONSENT_REQUIRED"
