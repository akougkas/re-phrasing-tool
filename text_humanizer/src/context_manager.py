"""
Context management system for handling conversation history and context selection.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from text_humanizer.src.logger_config import logger

# Global list to store selected segment IDs
selected_segment_ids = []

@dataclass
class ContextSegment:
    """Represents a segment of conversation context"""
    segment_id: str
    content: str
    role: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

class ContextManager:
    def __init__(self):
        """Initializes the ContextManager with empty chat history and selected segments."""
        self.chat_history = []
        self._selected_segments: List[str] = []  # List of selected segment IDs
        
        # Mock data for development
        self._mock_qa_pairs = [
            {"id": "qa1", "question": "What is the capital of France?", "answer": "Paris", "timestamp": 1234567890},
            {"id": "qa2", "question": "What is Python?", "answer": "A programming language", "timestamp": 1234567891},
            {"id": "qa3", "question": "How does context work?", "answer": "It maintains conversation history", "timestamp": 1234567892}
        ]

    def log_context_operation(self, operation: str, context_id: str):
        logger.info(f"Operation '{operation}' performed on context '{context_id}'")

    def add_message(self, message: str, role: str):
        """Adds a new message to the chat history.

        Args:
            message: The message content.
            role: The role of the sender ('user' or 'assistant').
        """
        self.chat_history.append({'role': role, 'content': message})
        logger.debug(f"Added message from {role}: {message[:50]}...")

    def get_history(self) -> List[Dict[str, str]]:
        """Returns the entire chat history."""
        return self.chat_history

    def clear_history(self):
        """Clears the chat history."""
        self.chat_history = []
        logger.info("Chat history cleared")

    def get_selected_context(self) -> List[Tuple[str, str]]:
        """Return currently selected context segments.
        
        Returns:
            List[Tuple[str, str]]: List of selected context segments as tuples
        """
        # Mock implementation - return segments based on selected IDs
        mock_segments = [
            ("What is Python?", "Python is a programming language."),
            ("How does context work?", "Context is retrieved from past queries.")
        ]
        
        logger.info(f"Retrieved {len(mock_segments)} selected context segments")
        return mock_segments

    def get_recent_context(self, n: int = 2) -> List[Tuple[str, str]]:
        """Return the most recent Q/A pairs.
        
        Args:
            n: Number of recent Q/A pairs to return
            
        Returns:
            List[Tuple[str, str]]: List of recent Q/A pairs as tuples
        """
        # Mock implementation - return last n pairs from mock data
        recent_pairs = [
            ("What is Python?", "Python is a programming language."),
            ("How does context work?", "Context is retrieved from past queries.")
        ]
        logger.info(f"Retrieved {len(recent_pairs)} recent Q/A pairs")
        return recent_pairs

    def select_context(self, segment_ids: List[str]) -> bool:
        global selected_segment_ids
        """Select specific context segments for use.
        
        Args:
            segment_ids: List of segment IDs to select
            
        Returns:
            bool: True if selection was successful
        """
        try:
            self._selected_segments = segment_ids
            selected_segment_ids = segment_ids  # Store in global list
            logger.info(f"Selected {len(segment_ids)} context segments: {segment_ids}")
            for segment_id in segment_ids:
                self.log_context_operation("select", segment_id)
            return True
        except Exception as e:
            logger.error(f"Error selecting context segments: {str(e)}")
            return False

    def clear_context(self):
        """Clear all stored context and selections."""
        self.chat_history = []
        self._selected_segments = []
        selected_segment_ids = []
        logger.info("Cleared all context and selections")