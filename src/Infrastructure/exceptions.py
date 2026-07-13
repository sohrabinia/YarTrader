class RGException(Exception):
    """Base exception for all RG_V3 Platform errors."""
    pass


class ValidationException(RGException):
    """Exception raised when a data entity or model fails structural validation."""
    pass


class ConfigurationException(RGException):
    """Exception raised when config parameters are missing or corrupted."""
    pass


class StorageException(RGException):
    """Exception raised when local database or file storage operations fail."""
    pass


class AssessmentException(RGException):
    """Exception raised when risk or strategy evaluations fail structural boundaries."""
    pass
