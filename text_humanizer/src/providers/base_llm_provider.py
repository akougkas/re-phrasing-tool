"""
Base class for LLM providers.
Defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    endpoint_url: str
    model_name: str
    timeout: int = 30
    max_tokens: int = 2048

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def infer(self, enhanced_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an inference request to the LLM provider.
        
        Args:
            enhanced_input: Dictionary containing the input prompt and any additional context
                          Expected format:
                          {
                              "prompt": str,
                              "context": Optional[Dict[str, Any]],
                              "system_prompt": Optional[str]
                          }
            
        Returns:
            Dict[str, Any]: The LLM's response containing at least:
                           {
                               "response": str,
                               "status": str,
                               "metadata": Dict[str, Any]
                           }
        """
        pass

    @abstractmethod
    def switch_model(self, endpoint: Optional[str] = None, model_name: Optional[str] = None) -> bool:
        """
        Switch to a different model or endpoint.
        
        Args:
            endpoint: New endpoint URL (optional)
            model_name: New model name (optional)
            
        Returns:
            bool: True if switch was successful, False otherwise
        """
        pass

    @property
    def current_config(self) -> LLMConfig:
        """Get current LLM configuration."""
        return self.config
