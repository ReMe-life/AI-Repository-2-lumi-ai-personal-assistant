"""
Structured error handling for LUKi Cognitive Module
Provides categorized exceptions and error handling utilities
"""

from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error category types"""
    VALIDATION = "validation"
    CONSENT = "consent"
    RESOURCE_NOT_FOUND = "resource_not_found"
    EXTERNAL_SERVICE = "external_service"
    COMPUTATION = "computation"
    DATA_QUALITY = "data_quality"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"          # Minor issue, functionality not impacted
    MEDIUM = "medium"    # Some functionality impacted
    HIGH = "high"        # Major functionality impacted
    CRITICAL = "critical"  # System failure


class CognitiveModuleError(Exception):
    """Base exception for cognitive module"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """
        Initialize cognitive module error
        
        Args:
            message: Error message
            category: Error category
            severity: Error severity
            details: Additional error details
            recoverable: Whether error is recoverable
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "details": self.details
        }
    
    def log(self):
        """Log the error with appropriate level"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(self.severity, logging.ERROR)
        
        logger.log(
            log_level,
            self.message,
            extra={
                "error_class": self.__class__.__name__,
                "category": self.category.value,
                "severity": self.severity.value,
                "recoverable": self.recoverable,
                "details": self.details
            },
            exc_info=True
        )


class ValidationError(CognitiveModuleError):
    """Input validation error"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details={"field": field} if field else {},
            **kwargs
        )


class ConsentError(CognitiveModuleError):
    """Consent-related error"""
    
    def __init__(self, message: str, user_id: str, required_scope: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.CONSENT,
            severity=ErrorSeverity.HIGH,
            details={"user_id": user_id, "required_scope": required_scope},
            recoverable=False,
            **kwargs
        )


class ResourceNotFoundError(CognitiveModuleError):
    """Resource not found error"""
    
    def __init__(self, message: str, resource_type: str, resource_id: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.RESOURCE_NOT_FOUND,
            severity=ErrorSeverity.MEDIUM,
            details={"resource_type": resource_type, "resource_id": resource_id},
            **kwargs
        )


class ExternalServiceError(CognitiveModuleError):
    """External service error"""
    
    def __init__(self, message: str, service: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            details={"service": service, "status_code": status_code},
            **kwargs
        )


class ComputationError(CognitiveModuleError):
    """Computation/algorithm error"""
    
    def __init__(self, message: str, operation: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.COMPUTATION,
            severity=ErrorSeverity.MEDIUM,
            details={"operation": operation},
            **kwargs
        )


class DataQualityError(CognitiveModuleError):
    """Data quality/integrity error"""
    
    def __init__(self, message: str, data_type: str, issue: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.DATA_QUALITY,
            severity=ErrorSeverity.MEDIUM,
            details={"data_type": data_type, "issue": issue},
            **kwargs
        )


class CognitivePermissionError(CognitiveModuleError):
    """Permission denied error"""
    
    def __init__(self, message: str, user_id: str, action: str, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.HIGH,
            details={"user_id": user_id, "action": action},
            recoverable=False,
            **kwargs
        )


class RateLimitError(CognitiveModuleError):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str, limit: int, window: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.LOW,
            details={"limit": limit, "window": window, "retry_after": retry_after},
            **kwargs
        )


class ErrorHandler:
    """Error handling utility"""
    
    @staticmethod
    def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle and format error
        
        Args:
            error: Exception to handle
            context: Additional context
        
        Returns:
            Formatted error dictionary
        """
        if isinstance(error, CognitiveModuleError):
            error.log()
            response = error.to_dict()
        else:
            # Handle unexpected errors
            logger.error(
                f"Unexpected error: {str(error)}",
                extra={"error_type": type(error).__name__, "context": context},
                exc_info=True
            )
            response = {
                "error": "InternalError",
                "message": "An unexpected error occurred",
                "category": ErrorCategory.INTERNAL.value,
                "severity": ErrorSeverity.HIGH.value,
                "recoverable": False,
                "details": {"error_type": type(error).__name__}
            }
        
        if context:
            response["context"] = context
        
        return response
    
    @staticmethod
    def is_recoverable(error: Exception) -> bool:
        """Check if error is recoverable"""
        if isinstance(error, CognitiveModuleError):
            return error.recoverable
        return False
    
    @staticmethod
    def get_retry_strategy(error: Exception) -> Optional[Dict[str, Any]]:
        """
        Get retry strategy for error
        
        Args:
            error: Exception
        
        Returns:
            Retry strategy dict or None
        """
        if isinstance(error, RateLimitError):
            return {
                "should_retry": True,
                "retry_after": error.details.get("retry_after", 60),
                "strategy": "exponential_backoff"
            }
        
        if isinstance(error, ExternalServiceError):
            return {
                "should_retry": True,
                "retry_after": 5,
                "strategy": "exponential_backoff",
                "max_attempts": 3
            }
        
        if isinstance(error, ComputationError) and error.recoverable:
            return {
                "should_retry": True,
                "retry_after": 1,
                "strategy": "immediate",
                "max_attempts": 2
            }
        
        return None
    
    @staticmethod
    def format_for_client(error: Exception) -> Dict[str, Any]:
        """
        Format error for client response
        
        Args:
            error: Exception
        
        Returns:
            Client-safe error dictionary
        """
        if isinstance(error, CognitiveModuleError):
            # Don't expose internal details to client
            safe_details = {}
            
            # Include only safe details
            if error.category == ErrorCategory.VALIDATION:
                safe_details = error.details
            elif error.category == ErrorCategory.RATE_LIMIT:
                safe_details = {
                    "retry_after": error.details.get("retry_after")
                }
            
            return {
                "error": {
                    "message": error.message,
                    "category": error.category.value,
                    "recoverable": error.recoverable,
                    **safe_details
                }
            }
        
        # Generic error for client
        return {
            "error": {
                "message": "An error occurred processing your request",
                "category": "internal",
                "recoverable": False
            }
        }


class ErrorAggregator:
    """Aggregate multiple errors"""
    
    def __init__(self):
        self.errors: List[CognitiveModuleError] = []
    
    def add(self, error: CognitiveModuleError):
        """Add error to aggregator"""
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """Check if any errors exist"""
        return len(self.errors) > 0
    
    def has_critical(self) -> bool:
        """Check if any critical errors exist"""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def has_high_severity(self) -> bool:
        """Check if any high severity errors exist"""
        return any(e.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] for e in self.errors)
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[CognitiveModuleError]:
        """Get errors by category"""
        return [e for e in self.errors if e.category == category]
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[CognitiveModuleError]:
        """Get errors by severity"""
        return [e for e in self.errors if e.severity == severity]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "error_count": len(self.errors),
            "has_critical": self.has_critical(),
            "errors": [e.to_dict() for e in self.errors]
        }
    
    def clear(self):
        """Clear all errors"""
        self.errors.clear()
