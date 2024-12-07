"""
Smart chip detection and handling system.
"""

import re
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from functools import wraps

from text_humanizer.utils.logger import logger

@dataclass
class ChipMatch:
    """Represents a matched smart chip in text."""
    chip_type: str
    content: str
    start_index: int
    end_index: int
    parameters: Dict[str, str]

class ChipHandler:
    """Base class for chip handlers."""
    
    def __init__(self, chip_type: str, description: str):
        self.chip_type = chip_type
        self.description = description
        
    def handle(self, content: str, parameters: Dict[str, str]) -> Dict[str, Any]:
        """Handle the chip content."""
        raise NotImplementedError

class ChipRegistry:
    """Registry for smart chip handlers."""
    
    def __init__(self):
        self._handlers: Dict[str, ChipHandler] = {}
        
    def register(self, handler: ChipHandler) -> None:
        """Register a new chip handler."""
        self._handlers[handler.chip_type] = handler
        
    def get_handler(self, chip_type: str) -> Optional[ChipHandler]:
        """Get a handler for a chip type."""
        return self._handlers.get(chip_type)
        
    def list_handlers(self) -> List[Dict[str, str]]:
        """List all registered handlers."""
        return [
            {"type": h.chip_type, "description": h.description}
            for h in self._handlers.values()
        ]

class ChipDetector:
    """Detects and processes smart chips in text."""
    
    def __init__(self, registry: ChipRegistry):
        self.registry = registry
        self.chip_pattern = re.compile(
            r'@(\w+)(?:\[([\w=,]+)\])?\s*\{([^}]+)\}',
            re.MULTILINE | re.DOTALL
        )
        
    def find_chips(self, text: str) -> List[ChipMatch]:
        """Find all smart chips in the text.
        
        Args:
            text: Input text to search
            
        Returns:
            List of ChipMatch objects
        """
        matches = []
        for match in self.chip_pattern.finditer(text):
            chip_type = match.group(1)
            param_str = match.group(2) or ""
            content = match.group(3).strip()
            
            # Parse parameters
            parameters = {}
            if param_str:
                for param in param_str.split(','):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        parameters[key.strip()] = value.strip()
                    else:
                        parameters[param.strip()] = "true"
            
            matches.append(ChipMatch(
                chip_type=chip_type,
                content=content,
                start_index=match.start(),
                end_index=match.end(),
                parameters=parameters
            ))
            
        return matches
        
    def process_chips(self, text: str) -> Dict[str, Any]:
        """Process all chips in the text.
        
        Args:
            text: Input text with smart chips
            
        Returns:
            Dictionary containing:
            - processed_text: Text with chips replaced by their results
            - chip_results: List of individual chip processing results
        """
        matches = self.find_chips(text)
        results = []
        processed_text = text
        
        # Process each chip from end to start to maintain correct indices
        for match in reversed(matches):
            handler = self.registry.get_handler(match.chip_type)
            if handler:
                try:
                    result = handler.handle(match.content, match.parameters)
                    results.append({
                        "type": match.chip_type,
                        "result": result,
                        "success": True
                    })
                    # Replace the chip with its result in the text
                    processed_text = (
                        processed_text[:match.start_index] +
                        str(result.get("display_text", "")) +
                        processed_text[match.end_index:]
                    )
                except Exception as e:
                    logger.error(f"Error processing chip {match.chip_type}: {str(e)}")
                    results.append({
                        "type": match.chip_type,
                        "error": str(e),
                        "success": False
                    })
            else:
                logger.warning(f"No handler found for chip type: {match.chip_type}")
                results.append({
                    "type": match.chip_type,
                    "error": "Handler not found",
                    "success": False
                })
                
        return {
            "processed_text": processed_text,
            "chip_results": results
        }

def register_chip_handler(chip_type: str, description: str):
    """Decorator to register a chip handler class."""
    def decorator(cls):
        @wraps(cls)
        def wrapper(*args, **kwargs):
            instance = cls(*args, **kwargs)
            instance.chip_type = chip_type
            instance.description = description
            return instance
        return wrapper
    return decorator
