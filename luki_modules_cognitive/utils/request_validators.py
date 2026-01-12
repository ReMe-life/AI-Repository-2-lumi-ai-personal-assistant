"""
Request validation utilities for LUKi Cognitive Module
Provides input validation for cognitive module endpoints
"""

import re
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

logger = logging.getLogger(__name__)


class ActivityRecommendationRequest(BaseModel):
    """Request for activity recommendations"""
    user_id: str = Field(..., min_length=3, max_length=128)
    interests: Optional[List[str]] = Field(None, max_items=20)
    difficulty_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k: int = Field(3, ge=1, le=20)
    exclude_completed: bool = Field(True)
    
    @field_validator("interests")
    @classmethod
    def validate_interests(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v:
            # Clean and validate interests
            cleaned = []
            for interest in v:
                stripped = interest.strip()
                if len(stripped) > 0 and len(stripped) <= 100:
                    cleaned.append(stripped)
            return cleaned if cleaned else None
        return v
    
    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("user_id must be alphanumeric with optional _ or -")
        return v


class WorldDayActivityRequest(BaseModel):
    """Request for world day activities"""
    user_id: str = Field(..., min_length=3, max_length=128)
    date: Optional[datetime] = Field(None)
    interests: Optional[List[str]] = Field(None, max_items=10)
    
    @field_validator("date")
    @classmethod
    def validate_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v > datetime.utcnow():
            # Allow future dates for planning
            pass
        return v


class LifeStoryRecordingRequest(BaseModel):
    """Request for life story recording suggestions"""
    user_id: str = Field(..., min_length=3, max_length=128)
    topics: Optional[List[str]] = Field(None, max_items=10)
    format_preference: Optional[str] = Field(None, pattern="^(text|audio|video)$")
    
    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v:
            cleaned = [t.strip() for t in v if t.strip()]
            return cleaned if cleaned else None
        return v


class FeedbackAnalysisRequest(BaseModel):
    """Request for feedback analysis"""
    user_id: str = Field(..., min_length=3, max_length=128)
    activity_id: str = Field(..., min_length=1, max_length=128)
    feedback_text: str = Field(..., min_length=1, max_length=5000)
    rating: Optional[float] = Field(None, ge=0.0, le=1.0)
    completion_time_seconds: Optional[float] = Field(None, ge=0)
    
    @field_validator("feedback_text")
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Feedback text cannot be empty")
        return stripped


class DifficultyAdjustmentRequest(BaseModel):
    """Request for difficulty adjustment"""
    user_id: str = Field(..., min_length=3, max_length=128)
    activity_id: str = Field(..., min_length=1, max_length=128)
    current_difficulty: float = Field(..., ge=0.0, le=1.0)
    performance_score: float = Field(..., ge=0.0, le=1.0)
    completion_time_seconds: Optional[float] = Field(None, ge=0)


class ActivityCatalogQueryRequest(BaseModel):
    """Request to query activity catalog"""
    query: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    difficulty_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    difficulty_max: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = Field(None, max_items=20)
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v:
            cleaned = [t.strip().lower() for t in v if t.strip()]
            return cleaned if cleaned else None
        return v


class RequestValidator:
    """Utility class for request validation"""
    
    # Dangerous patterns to reject
    DANGEROUS_PATTERNS = [
        r"(?i)<script[^>]*>.*?</script>",
        r"(?i)javascript:",
        r"(?i)on\w+\s*=",
    ]
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize text input
        
        Args:
            text: Input text
        
        Returns:
            Sanitized text
        """
        # Remove dangerous patterns
        sanitized = text
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized)
        
        # Normalize whitespace
        sanitized = " ".join(sanitized.split())
        
        return sanitized.strip()
    
    @classmethod
    def validate_user_consent(cls, user_id: str, required_scope: str) -> bool:
        """
        Validate user consent (placeholder - integrate with security service)
        
        Args:
            user_id: User identifier
            required_scope: Required consent scope
        
        Returns:
            Whether user has given consent
        """
        # TODO: Integrate with luki-security-privacy consent service
        logger.debug(
            f"Consent check: {user_id} for scope {required_scope}",
            extra={"user_id": user_id, "scope": required_scope}
        )
        return True  # Placeholder
    
    @classmethod
    def validate_activity_id(cls, activity_id: str) -> bool:
        """
        Validate activity ID format
        
        Args:
            activity_id: Activity identifier
        
        Returns:
            Whether activity ID is valid
        """
        # Activity IDs should be alphanumeric with optional _ or -
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, activity_id))
    
    @classmethod
    def validate_interests_list(cls, interests: List[str]) -> List[str]:
        """
        Validate and clean interests list
        
        Args:
            interests: List of interest strings
        
        Returns:
            Cleaned interests list
        """
        cleaned = []
        for interest in interests:
            # Sanitize each interest
            sanitized = cls.sanitize_text(interest)
            
            # Check length
            if 0 < len(sanitized) <= 100:
                cleaned.append(sanitized)
            else:
                logger.warning(
                    f"Skipping invalid interest: {interest}",
                    extra={"interest_length": len(sanitized)}
                )
        
        return cleaned
    
    @classmethod
    def validate_difficulty_range(cls, min_val: Optional[float], max_val: Optional[float]) -> bool:
        """
        Validate difficulty range
        
        Args:
            min_val: Minimum difficulty
            max_val: Maximum difficulty
        
        Returns:
            Whether range is valid
        """
        if min_val is not None and max_val is not None:
            if min_val > max_val:
                return False
        
        if min_val is not None and (min_val < 0.0 or min_val > 1.0):
            return False
        
        if max_val is not None and (max_val < 0.0 or max_val > 1.0):
            return False
        
        return True
    
    @classmethod
    def validate_pagination(cls, limit: int, offset: int) -> Dict[str, Any]:
        """
        Validate pagination parameters
        
        Args:
            limit: Page size
            offset: Page offset
        
        Returns:
            Validation result dict
        """
        errors = []
        
        if limit < 1 or limit > 100:
            errors.append({
                "field": "limit",
                "message": "Limit must be between 1 and 100"
            })
        
        if offset < 0:
            errors.append({
                "field": "offset",
                "message": "Offset must be non-negative"
            })
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    @classmethod
    def extract_safe_metadata(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract safe metadata fields for logging/storage
        
        Args:
            metadata: Raw metadata dict
        
        Returns:
            Safe metadata dict
        """
        # Allowlist of safe metadata fields
        safe_fields = [
            "source", "category", "difficulty", "tags",
            "duration_minutes", "format", "language"
        ]
        
        safe = {}
        for field in safe_fields:
            if field in metadata:
                value = metadata[field]
                
                # Convert to safe types
                if isinstance(value, (str, int, float, bool)):
                    safe[field] = value
                elif isinstance(value, list):
                    # Only include lists of primitives
                    if all(isinstance(item, (str, int, float, bool)) for item in value):
                        safe[field] = value
        
        return safe


def validate_request(request_model: BaseModel, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate request data against model
    
    Args:
        request_model: Pydantic model class
        data: Request data
    
    Returns:
        Dict with 'valid' flag and 'errors' or 'data'
    """
    try:
        validated = request_model(**data)
        return {
            "valid": True,
            "data": validated.model_dump()
        }
    except Exception as e:
        errors = []
        
        if hasattr(e, 'errors'):
            # Pydantic validation errors
            for error in e.errors():
                errors.append({
                    "field": ".".join(str(loc) for loc in error['loc']),
                    "message": error['msg'],
                    "type": error['type']
                })
        else:
            errors.append({
                "message": str(e)
            })
        
        logger.warning(
            "Request validation failed",
            extra={"errors": errors}
        )
        
        return {
            "valid": False,
            "errors": errors
        }
