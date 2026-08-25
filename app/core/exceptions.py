from typing import Optional, Any, Dict


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationException(AppException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401,
        )


class AuthorizationException(AppException):
    """Raised when user is not authorized to access a resource."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            code="ACCESS_DENIED",
            message=message,
            status_code=403,
        )


class NotFoundException(AppException):
    """Raised when a resource is not found."""
    
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=message,
            status_code=404,
        )


class ValidationException(AppException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class ConflictException(AppException):
    """Raised when there's a conflict (e.g., duplicate entry)."""
    
    def __init__(self, message: str):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
        )


class RateLimitException(AppException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
        )


class InternalServerException(AppException):
    """Raised when an internal server error occurs."""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            code="INTERNAL_SERVER_ERROR",
            message=message,
            status_code=500,
        )


class ServiceUnavailableException(AppException):
    """Raised when an external service is unavailable."""
    
    def __init__(self, service: str):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=f"{service} is currently unavailable",
            status_code=503,
        )
