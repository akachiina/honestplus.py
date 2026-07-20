"""
Custom exceptions for honestplus.py
"""


class HonestException(Exception):
    """Base exception for all honestplus errors"""
    pass


class AuthenticationError(HonestException):
    """Raised when authentication fails (invalid token, expired session, etc)"""
    pass


class NotFoundError(HonestException):
    """Raised when a resource is not found (404)"""
    pass


class RateLimitError(HonestException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str, retry_after: float = None):
        super().__init__(message)
        self.retry_after = retry_after


class APIError(HonestException):
    """Raised when the API returns an error response"""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ValidationError(HonestException):
    """Raised when input validation fails"""
    pass


class MediaProcessingError(HonestException):
    """Raised when media upload/processing fails"""
    pass
