"""Utility module for input validation."""

from typing import Set, Optional, Dict, Any
from text_humanizer.error_handling import ValidationError

class InputValidator:
    """Centralized input validation utilities."""

    @staticmethod
    def validate_length(text: str, min_length: int, max_length: int) -> None:
        """Validate input text length.
        
        Args:
            text: Input text to validate
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            
        Raises:
            ValidationError: If text length is outside allowed range
        """
        if len(text) < min_length:
            raise ValidationError(
                f"Input must be at least {min_length} characters long",
                details={"input_length": len(text)}
            )
        if len(text) > max_length:
            raise ValidationError(
                f"Input cannot exceed {max_length} characters",
                details={"input_length": len(text)}
            )

    @staticmethod
    def validate_characters(
        text: str,
        disallowed_chars: Optional[Set[str]] = None,
        allowed_chars: Optional[Set[str]] = None
    ) -> None:
        """Validate input text characters.
        
        Args:
            text: Input text to validate
            disallowed_chars: Set of characters that are not allowed
            allowed_chars: Set of characters that are allowed (if specified, only these are allowed)
            
        Raises:
            ValidationError: If text contains invalid characters
        """
        if disallowed_chars:
            found_dangerous = [c for c in text if c in disallowed_chars]
            if found_dangerous:
                raise ValidationError(
                    "Input contains invalid characters",
                    details={"invalid_chars": found_dangerous}
                )
        
        if allowed_chars:
            invalid_chars = [c for c in text if c not in allowed_chars]
            if invalid_chars:
                raise ValidationError(
                    "Input contains characters outside allowed set",
                    details={"invalid_chars": invalid_chars}
                )

    @staticmethod
    def validate_rate_limit(
        request_times: list,
        max_requests: int,
        window_seconds: int,
        current_time: float
    ) -> None:
        """Validate rate limiting.
        
        Args:
            request_times: List of timestamps of previous requests
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds
            current_time: Current timestamp
            
        Raises:
            ValidationError: If rate limit is exceeded
        """
        # Remove old requests outside the window
        active_requests = [
            ts for ts in request_times 
            if current_time - ts < window_seconds
        ]
        
        if len(active_requests) >= max_requests:
            raise ValidationError(
                "Rate limit exceeded. Please try again later.",
                details={
                    "retry_after": int(active_requests[0] + window_seconds - current_time)
                }
            )
