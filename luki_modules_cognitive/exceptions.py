"""
Custom Exceptions for LUKi Cognitive Modules

Provides a structured exception hierarchy for activity recommendation,
life story recording, and cognitive engagement features.
"""

from typing import Optional, Dict, Any


class CognitiveModuleError(Exception):
    """
    Base exception for all cognitive module errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional context about the error
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "COGNITIVE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        result = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# =============================================================================
# ACTIVITY ERRORS
# =============================================================================

class ActivityError(CognitiveModuleError):
    """Base exception for activity-related errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "ACTIVITY_ERROR",
        activity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if activity_id:
            details["activity_id"] = activity_id
        super().__init__(message, error_code, details)


class ActivityNotFoundError(ActivityError):
    """Raised when an activity is not found"""
    
    def __init__(self, activity_id: str):
        super().__init__(
            message=f"Activity '{activity_id}' not found",
            error_code="ACTIVITY_NOT_FOUND",
            activity_id=activity_id
        )


class InvalidActivityTypeError(ActivityError):
    """Raised when activity type is invalid"""
    
    def __init__(self, activity_type: str, valid_types: Optional[list] = None):
        details = {}
        if valid_types:
            details["valid_types"] = valid_types
        super().__init__(
            message=f"Invalid activity type: '{activity_type}'",
            error_code="INVALID_ACTIVITY_TYPE",
            details=details
        )


# =============================================================================
# RECOMMENDATION ERRORS
# =============================================================================

class RecommendationError(CognitiveModuleError):
    """Base exception for recommendation errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "RECOMMENDATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class InsufficientDataError(RecommendationError):
    """Raised when there's insufficient data for recommendations"""
    
    def __init__(self, message: str = "Insufficient data to generate recommendations"):
        super().__init__(message, "INSUFFICIENT_DATA")


class NoRecommendationsError(RecommendationError):
    """Raised when no suitable recommendations are found"""
    
    def __init__(self, reason: Optional[str] = None):
        message = "No suitable recommendations found"
        details = {}
        if reason:
            message = f"{message}: {reason}"
            details["reason"] = reason
        super().__init__(message, "NO_RECOMMENDATIONS", details)


# =============================================================================
# LIFE STORY ERRORS
# =============================================================================

class LifeStoryError(CognitiveModuleError):
    """Base exception for life story recording errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "LIFE_STORY_ERROR",
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, error_code, details)


class SessionNotFoundError(LifeStoryError):
    """Raised when a life story session is not found"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Life story session '{session_id}' not found",
            error_code="SESSION_NOT_FOUND",
            session_id=session_id
        )


class SessionExpiredError(LifeStoryError):
    """Raised when a life story session has expired"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Life story session '{session_id}' has expired",
            error_code="SESSION_EXPIRED",
            session_id=session_id
        )


class SessionAlreadyCompleteError(LifeStoryError):
    """Raised when trying to modify a completed session"""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Life story session '{session_id}' is already complete",
            error_code="SESSION_ALREADY_COMPLETE",
            session_id=session_id
        )


class InvalidPhaseError(LifeStoryError):
    """Raised when life story phase is invalid"""
    
    def __init__(self, phase: str, valid_phases: Optional[list] = None):
        details = {"phase": phase}
        if valid_phases:
            details["valid_phases"] = valid_phases
        super().__init__(
            message=f"Invalid life story phase: '{phase}'",
            error_code="INVALID_PHASE",
            details=details
        )


# =============================================================================
# IMAGE GENERATION ERRORS
# =============================================================================

class ImageGenerationError(CognitiveModuleError):
    """Base exception for image generation errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "IMAGE_GENERATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class ImageRateLimitError(ImageGenerationError):
    """Raised when image generation rate limit is exceeded"""
    
    def __init__(
        self,
        user_id: str,
        limit: int,
        reset_time: Optional[str] = None
    ):
        details = {
            "user_id": user_id,
            "limit": limit
        }
        if reset_time:
            details["reset_time"] = reset_time
        super().__init__(
            message=f"Image generation rate limit exceeded ({limit} per day)",
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


# =============================================================================
# ELR CONNECTION ERRORS
# =============================================================================

class ELRConnectionError(CognitiveModuleError):
    """Raised when ELR/Memory service connection fails"""
    
    def __init__(
        self,
        message: str = "Failed to connect to ELR/Memory service",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "ELR_CONNECTION_ERROR", details)


class ELRDataError(CognitiveModuleError):
    """Raised when ELR data retrieval or parsing fails"""
    
    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if user_id:
            details["user_id"] = user_id
        super().__init__(message, "ELR_DATA_ERROR", details)


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(CognitiveModuleError):
    """Raised when input validation fails"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)
