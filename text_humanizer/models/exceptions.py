"""
Custom exceptions for model operations.
"""

class ModelError(Exception):
    """Base class for model-related errors."""
    pass

class ModelNotFoundError(ModelError):
    """Error when model is not found or unavailable."""
    pass

class ModelNotReadyError(ModelError):
    """Error when model is not ready for inference."""
    pass

class ModelConnectionError(ModelError):
    """Error connecting to model endpoint."""
    pass

class ModelResponseError(ModelError):
    """Error in model response format."""
    pass

class ModelValidationError(ModelError):
    """Error validating model input or output."""
    pass

class ChipError(Exception):
    """Base class for chip-related errors."""
    pass

class ChipParsingError(ChipError):
    """Error parsing smart chip syntax."""
    pass

class ChipHandlingError(ChipError):
    """Error during chip handling."""
    pass
