from fastapi import status

class BaseCustomException(Exception):
    """Base class for all custom exceptions"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "An internal server error occurred."

    def __init__(self, detail: str = None):
        self.detail = detail
        super().__init__(self.detail)


class DocumentNotFoundException(BaseCustomException):
    """Raised when document not found"""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Document not found."


class AnalysisNotFoundException(BaseCustomException):
    """Raised when analysis not found"""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Analysis result not found."


class NotificationSettingNotFoundException(BaseCustomException):
    """Raised when notification setting not found"""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Notification setting not found."


class ValidationException(BaseCustomException):
    """Raised when validation fails"""
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Validation failed."


class DatabaseException(BaseCustomException):
    """Raised when database operation fails"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "A database error occurred."

class ConflictException(BaseCustomException):
    """Exception raised for conflicts (e.g., resource state prevents action)."""
    status_code = status.HTTP_409_CONFLICT
    detail = "Operation conflicts with the current state of the resource."

class FileNotFoundInGridFSException(BaseCustomException):
    """Exception thrown when a file with a given ID is not found in GridFS."""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "File not found in storage."