"""Module for handling input text and context processing."""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import logging
from text_humanizer.src.logger_config import logger

from text_humanizer.src.context_manager import ContextManager

class InputProcessor:
    """Class for processing input text and managing context."""
    
    def __init__(self, context_manager: Optional[ContextManager] = None):
        """Initialize with optional context manager."""
        self.context_manager = context_manager or ContextManager()

    def read_text_from_file(self, file_path: str) -> str:
        """Reads text from a file and returns it as a string."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            return text
        except FileNotFoundError as e:
            logger.error(f"Error: File not found at path: {file_path}")
            logger.error(f"Details: {e}")
            return ""

    def process(self, query_string: str) -> Dict[str, Any]:
        """
        Process a query string by combining it with relevant context.
        
        Args:
            query_string: The user's query to process
            
        Returns:
            Dict[str, Any]: Structured input containing query, context, and metadata
        """
        # Get selected context or fall back to recent context
        selected_context = self.context_manager.get_selected_context()
        if not selected_context:
            logger.info("No context explicitly selected, falling back to recent context")
            recent_qa = self.context_manager.get_recent_context(n=2)
            context_list = [
                f"Q: {qa[0]} A: {qa[1]}"
                for qa in recent_qa
            ]
        else:
            context_list = [
                f"Q: {segment[0]} A: {segment[1]}"
                for segment in selected_context
            ]
        
        # Build the structured input
        structured_input = {
            "query": query_string,
            "prompt": query_string,  # Ensure 'prompt' is included for inference
            "context": context_list,
            "metadata": {}
        }
        
        # Debug output
        logger.debug("Processed input structure:")
        logger.debug(f"Merged Input: {structured_input}")
        
        return structured_input

    def format_debug_output(self, structured_input: Dict[str, Any]) -> str:
        """
        Format the structured input for debug display.
        
        Args:
            structured_input: The processed input structure
            
        Returns:
            str: Formatted debug string
        """
        return json.dumps(structured_input, indent=2)

    def handle_multiline_text(self, text: str) -> str:
        """Handles multiline text input."""
        # For now, simply returns the input text.
        # Future enhancements could include parsing and handling line breaks,
        # paragraphs, etc.
        return text