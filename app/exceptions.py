# ============================================================================
# PRITHU BACKEND - CUSTOM EXCEPTIONS
# ============================================================================
# Defines all custom exceptions with proper error codes and messages
# ============================================================================

from typing import Optional, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    DATABASE_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DATABASE_QUERY_FAILED = "DB_QUERY_FAILED"
    DATABASE_NOT_FOUND = "DB_NOT_FOUND"
    
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_USER_ID = "INVALID_USER_ID"
    INVALID_CATEGORY_ID = "INVALID_CATEGORY_ID"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    CATEGORY_NOT_FOUND = "CATEGORY_NOT_FOUND"
    FEED_NOT_FOUND = "FEED_NOT_FOUND"
    
    OPTIMIZER_ERROR = "OPTIMIZER_ERROR"
    SCORING_ERROR = "SCORING_ERROR"
    CLASSIFICATION_ERROR = "CLASSIFICATION_ERROR"
    
    CACHE_ERROR = "CACHE_ERROR"
    
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"


class PrithuException(Exception):
    """Base exception class for all Prithu errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary response format."""
        return {
            "success": False,
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "details": self.details
            },
            "data": None
        }


class DatabaseException(PrithuException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DATABASE_QUERY_FAILED,
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details
        )


class DatabaseConnectionException(DatabaseException):
    """Raised when database connection fails."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED,
            details=details
        )


class ResourceNotFoundException(PrithuException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Any] = None
    ):
        message = f"{resource_type} not found: {resource_id}"
        
        if resource_type == "User":
            error_code = ErrorCode.USER_NOT_FOUND
        elif resource_type == "Category":
            error_code = ErrorCode.CATEGORY_NOT_FOUND
        elif resource_type == "Feed":
            error_code = ErrorCode.FEED_NOT_FOUND
        else:
            error_code = ErrorCode.RESOURCE_NOT_FOUND

        super().__init__(
            message=message,
            error_code=error_code,
            status_code=404,
            details=details
        )


class ValidationException(PrithuException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Any] = None
    ):
        if field:
            message = f"Validation error in field '{field}': {message}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details or {"field": field}
        )


class OptimizerException(PrithuException):
    """Raised when recommendation engine fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.OPTIMIZER_ERROR,
            status_code=500,
            details=details
        )


class ScoringException(OptimizerException):
    """Raised when scoring calculation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            details=details
        )
        self.error_code = ErrorCode.SCORING_ERROR


class CacheException(PrithuException):
    """Raised when cache operations fail."""

    def __init__(
        self,
        message: str,
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.CACHE_ERROR,
            status_code=500,
            details=details
        )


class ExternalServiceException(PrithuException):
    """Raised when external service fails."""

    def __init__(
        self,
        service_name: str,
        message: str,
        details: Optional[Any] = None
    ):
        full_message = f"{service_name} service error: {message}"
        super().__init__(
            message=full_message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=503,
            details=details
        )
