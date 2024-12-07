"""
LLM Client module for handling interactions with language models.
"""

from typing import Dict, Any, Optional
from text_humanizer.providers.local_llm_provider import LocalLLMProvider

class LLMClient:
    """Client for interacting with language models."""
    
    def __init__(self, provider: Optional[LocalLLMProvider] = None):
        """Initialize LLM client with optional provider."""
        self.provider = provider or LocalLLMProvider()
    
    def process_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process text using the LLM provider.
        
        Args:
            text: Input text to process
            context: Optional context for processing
            
        Returns:
            Processed text from the LLM
        """
        return self.provider.process_text(text, context)
