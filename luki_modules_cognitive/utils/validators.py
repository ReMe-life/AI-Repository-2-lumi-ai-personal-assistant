"""
Input Validators for LUKi Cognitive Modules

Provides validation utilities for activity recommendations, life story sessions,
and cognitive engagement features.
"""

import re
import logging
from typing import Optional, Any, Dict, Tuple
from dataclasses import dataclass

from ..constants import (
    MoodCategories,
    ActivityTypes,
    CognitiveLevels,
    DurationLimits,
    RecommendationDefaults,
)
from ..exceptions import ValidationError

logger = logging.getLogger(__name__)

# =============================================================================
# REGEX PATTERNS
# =============================================================================

USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
ACTIVITY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,256}$")

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RecommendationParams:
    """Validated recommendation request parameters"""
    user_id: str
    mood: Optional[str]
    duration: Optional[int]
    activity_type: Optional[str]
    cognitive_level: Optional[str]
    max_recommendations: int
    carer_available: bool
    group_setting: bool


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_user_id(
    user_id: Any,
    field_name: str = "user_id",
    required: bool = True
) -> Optional[str]:
    """
    Validate user ID format.
    
    Args:
        user_id: User ID to validate
        field_name: Field name for error messages
        required: Whether the field is required
        
    Returns:
        Validated user ID string or None
        
    Raises:
        ValidationError: If validation fails
    """
    if user_id is None or (isinstance(user_id, str) and not user_id.strip()):
        if required:
            raise ValidationError(f"{field_name} is required", field=field_name)
        return None
    
    if not isinstance(user_id, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)
    
    user_id = user_id.strip()
    
    if len(user_id) > 128:
        raise ValidationError(
            f"{field_name} exceeds maximum length of 128 characters",
            field=field_name
        )
    
    if not USER_ID_PATTERN.match(user_id):
        raise ValidationError(
            f"{field_name} contains invalid characters",
            field=field_name
        )
    
    return user_id


def validate_activity_id(
    activity_id: Any,
    field_name: str = "activity_id",
    required: bool = True
) -> Optional[str]:
    """
    Validate activity ID format.
    
    Args:
        activity_id: Activity ID to validate
        field_name: Field name for error messages
        required: Whether the field is required
        
    Returns:
        Validated activity ID string or None
        
    Raises:
        ValidationError: If validation fails
    """
    if activity_id is None or (isinstance(activity_id, str) and not activity_id.strip()):
        if required:
            raise ValidationError(f"{field_name} is required", field=field_name)
        return None
    
    if not isinstance(activity_id, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)
    
    activity_id = activity_id.strip()
    
    if not ACTIVITY_ID_PATTERN.match(activity_id):
        raise ValidationError(
            f"{field_name} has invalid format",
            field=field_name
        )
    
    return activity_id


def validate_mood(
    mood: Any,
    field_name: str = "mood",
    required: bool = False
) -> Optional[str]:
    """
    Validate mood value.
    
    Args:
        mood: Mood to validate
        field_name: Field name for error messages
        required: Whether the field is required
        
    Returns:
        Validated mood string or None
        
    Raises:
        ValidationError: If validation fails
    """
    if mood is None or (isinstance(mood, str) and not mood.strip()):
        if required:
            raise ValidationError(f"{field_name} is required", field=field_name)
        return None
    
    if not isinstance(mood, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)
    
    mood = mood.strip().lower()
    
    if mood not in MoodCategories.ALL:
        logger.warning(f"Unknown mood value: {mood}")
        # Allow unknown moods but log them
    
    return mood


def validate_duration(
    duration: Any,
    field_name: str = "duration",
    required: bool = False,
    min_value: int = DurationLimits.MIN_DURATION,
    max_value: int = DurationLimits.MAX_DURATION
) -> Optional[int]:
    """
    Validate duration in minutes.
    
    Args:
        duration: Duration to validate
        field_name: Field name for error messages
        required: Whether the field is required
        min_value: Minimum allowed duration
        max_value: Maximum allowed duration
        
    Returns:
        Validated duration integer or None
        
    Raises:
        ValidationError: If validation fails
    """
    if duration is None:
        if required:
            raise ValidationError(f"{field_name} is required", field=field_name)
        return None
    
    try:
        duration_int = int(duration)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be an integer", field=field_name)
    
    if duration_int < min_value:
        raise ValidationError(
            f"{field_name} must be at least {min_value} minutes",
            field=field_name
        )
    
    if duration_int > max_value:
        raise ValidationError(
            f"{field_name} cannot exceed {max_value} minutes",
            field=field_name
        )
    
    return duration_int


def validate_engagement_score(
    score: Any,
    field_name: str = "engagement_score",
    required: bool = True
) -> Optional[float]:
    """
    Validate engagement score (0.0 to 1.0).
    
    Args:
        score: Score to validate
        field_name: Field name for error messages
        required: Whether the field is required
        
    Returns:
        Validated score float or None
        
    Raises:
        ValidationError: If validation fails
    """
    if score is None:
        if required:
            raise ValidationError(f"{field_name} is required", field=field_name)
        return None
    
    try:
        score_float = float(score)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a number", field=field_name)
    
    if score_float < 0.0 or score_float > 1.0:
        raise ValidationError(
            f"{field_name} must be between 0.0 and 1.0",
            field=field_name
        )
    
    return score_float


def validate_activity_type(
    activity_type: Any,
    field_name: str = "activity_type",
    required: bool = False
) -> Optional[str]:
    """
    Validate activity type.
    
    Args:
        activity_type: Activity type to validate
        field_name: Field name for error messages
        required: Whether the field is required
        
    Returns:
        Validated activity type string or None
        
    Raises:
        ValidationError: If validation fails
    """
    if activity_type is None or (isinstance(activity_type, str) and not activity_type.strip()):
        if required:
            raise ValidationError(f"{field_name} is required", field=field_name)
        return None
    
    if not isinstance(activity_type, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)
    
    activity_type = activity_type.strip().lower()
    
    if activity_type not in ActivityTypes.ALL:
        raise ValidationError(
            f"Invalid {field_name}: '{activity_type}'",
            field=field_name,
            details={"valid_types": list(ActivityTypes.ALL)}
        )
    
    return activity_type


def validate_cognitive_level(
    level: Any,
    field_name: str = "cognitive_level",
    required: bool = False
) -> Optional[str]:
    """
    Validate cognitive level.
    
    Args:
        level: Cognitive level to validate
        field_name: Field name for error messages
        required: Whether the field is required
        
    Returns:
        Validated cognitive level string or None
        
    Raises:
        ValidationError: If validation fails
    """
    if level is None or (isinstance(level, str) and not level.strip()):
        if required:
            raise ValidationError(f"{field_name} is required", field=field_name)
        return None
    
    if not isinstance(level, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)
    
    level = level.strip().lower()
    
    if level not in CognitiveLevels.ALL:
        raise ValidationError(
            f"Invalid {field_name}: '{level}'",
            field=field_name,
            details={"valid_levels": list(CognitiveLevels.ALL)}
        )
    
    return level


def validate_recommendation_request(
    user_id: Any,
    mood: Any = None,
    duration: Any = None,
    activity_type: Any = None,
    cognitive_level: Any = None,
    max_recommendations: Any = None,
    carer_available: Any = True,
    group_setting: Any = False
) -> RecommendationParams:
    """
    Validate a complete recommendation request.
    
    Args:
        user_id: User identifier
        mood: Optional current mood
        duration: Optional available duration in minutes
        activity_type: Optional activity type filter
        cognitive_level: Optional cognitive level
        max_recommendations: Maximum recommendations to return
        carer_available: Whether carer is available
        group_setting: Whether this is a group setting
        
    Returns:
        RecommendationParams with validated values
        
    Raises:
        ValidationError: If validation fails
    """
    validated_user_id = validate_user_id(user_id)
    validated_mood = validate_mood(mood)
    validated_duration = validate_duration(duration)
    validated_type = validate_activity_type(activity_type)
    validated_level = validate_cognitive_level(cognitive_level)
    
    # Validate max_recommendations
    validated_max = RecommendationDefaults.MAX_RECOMMENDATIONS
    if max_recommendations is not None:
        try:
            validated_max = int(max_recommendations)
            if validated_max < 1:
                validated_max = 1
            elif validated_max > 10:
                validated_max = 10
        except (TypeError, ValueError):
            pass
    
    # Validate boolean fields
    validated_carer = bool(carer_available) if carer_available is not None else True
    validated_group = bool(group_setting) if group_setting is not None else False
    
    # validated_user_id is guaranteed to be str since required=True
    assert validated_user_id is not None
    
    return RecommendationParams(
        user_id=validated_user_id,
        mood=validated_mood,
        duration=validated_duration,
        activity_type=validated_type,
        cognitive_level=validated_level,
        max_recommendations=validated_max,
        carer_available=validated_carer,
        group_setting=validated_group
    )
