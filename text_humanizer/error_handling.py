"""
Centralized error handling system for the Text Humanizer application.
Provides standardized error classes, error responses, and logging functionality.
"""

from typing import Dict, Any, Optional
import logging
from http import HTTPStatus
from dataclasses import dataclass
from functools import wraps
from flask import jsonify, Response, flash, current_app

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ErrorResponse:
    """Standardized error response structure"""
    error_code: str
    message: str
    http_status: int
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary format"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details or {}
            }
        }

class TextHumanizerError(Exception):
    """Base exception class for Text Humanizer application"""
    status_code = 500

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_response = ErrorResponse(
            error_code=error_code,
            message=message,
            http_status=http_status,
            details=details
        )

class ValidationError(TextHumanizerError):
    """Exception for input validation errors"""
    status_code = 400

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            http_status=HTTPStatus.BAD_REQUEST,
            details=details
        )

class FormatError(TextHumanizerError):
    """Exception for format parsing and processing errors"""
    status_code = 422

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="FORMAT_ERROR",
            http_status=HTTPStatus.UNPROCESSABLE_ENTITY,
            details=details
        )

class LLMServiceError(TextHumanizerError):
    """Exception for LLM service related errors"""
    status_code = 503

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="LLM_SERVICE_ERROR",
            http_status=HTTPStatus.SERVICE_UNAVAILABLE,
            details=details
        )

class ContextError(TextHumanizerError):
    """Exception for context management related errors"""
    status_code = 400

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONTEXT_ERROR",
            http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details
        )

def error_handler(f):
    """Decorator for handling errors in route functions."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except TextHumanizerError as e:
            logger.error(f"Application error: {str(e)}")
            response = jsonify(e.error_response.to_dict())
            response.status_code = e.error_response.http_status
            return response
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            error = ErrorResponse(
                error_code="INTERNAL_ERROR",
                message=str(e),
                http_status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
            response = jsonify(error.to_dict())
            response.status_code = error.http_status
            return response
    return wrapped

def register_error_handlers(app):
    """Register error handlers with the Flask application."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify(error="Resource not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify(error="Internal server error"), 500

    @app.errorhandler(ValidationError)
    def validation_error(error):
        return jsonify(error=str(error)), error.status_code

    @app.errorhandler(FormatError)
    def format_error(error):
        return jsonify(error=str(error)), error.status_code

    @app.errorhandler(LLMServiceError)
    def llm_service_error(error):
        return jsonify(error=str(error)), error.status_code

    @app.errorhandler(ContextError)
    def context_error(error):
        return jsonify(error=str(error)), error.status_code
