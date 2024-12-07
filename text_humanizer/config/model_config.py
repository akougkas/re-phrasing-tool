"""
Model configuration management.
Defines configurations for different model types and tasks.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class ModelType(Enum):
    """Supported model types."""
    CHAT = "chat"
    HUMANIZE = "humanize"
    SEARCH = "search"  # For future use


@dataclass
class ModelConfig:
    """Base configuration for all models."""
    endpoint_url: str
    model_name: str
    max_tokens: int = 2048
    timeout: int = 30
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


class ModelConfigs:
    """Central configuration for all model types."""
    
    # Default configurations for each model type
    DEFAULTS = {
        ModelType.CHAT: ModelConfig(
            endpoint_url="http://localhost:1234",
            model_name="mistral-nemo-instruct-2407",  # Fast and efficient chat model
            temperature=0.7,
            max_tokens=2048,
            timeout=30
        ),
        ModelType.HUMANIZE: ModelConfig(
            endpoint_url="http://localhost:1234",
            model_name="internlm2_5-20b-chat",  # Larger model for better text improvement
            temperature=0.3,  # Lower temperature for more focused output
            max_tokens=2048,
            timeout=30
        ),
        ModelType.SEARCH: ModelConfig(
            endpoint_url="http://localhost:1234",
            model_name="llama-3.2-3b-instruct",  # Fast model for search queries
            temperature=0.0,  # Zero temperature for consistent search
            max_tokens=1024,
            timeout=20
        )
    }

    # System prompts for each model type
    SYSTEM_PROMPTS = {
        ModelType.CHAT: """You are a helpful assistant. Respond clearly and concisely to user queries. 
You can help with various tasks including writing, analysis, and general questions. 
If you encounter a command starting with '@', inform the user that special commands 
should be handled by the appropriate model.""",

        ModelType.HUMANIZE: """You are a text humanizer specialized in improving text quality.
Your task is to enhance the given text while preserving its core meaning.
Always return your response in the following JSON format:
{
    "humanized_text": "The improved version of the text",
    "changes_made": ["List of specific improvements made"],
    "confidence_score": 0.95,
    "tone": "professional/casual/academic",
    "metadata": {
        "original_length": 123,
        "new_length": 128,
        "complexity_score": 0.7
    }
}""",

        ModelType.SEARCH: """You are a search assistant specialized in understanding and processing search queries.
Focus on extracting key information and intent from the user's query.
Maintain objectivity and prioritize relevance in your responses."""
    }

    # Fallback model configurations
    FALLBACK_MODELS = {
        ModelType.CHAT: [
            "mistral-nemo-instruct-2407",
            "llama-3.2-3b-instruct",
            "qwen2.5-14b-instruct"
        ],
        ModelType.HUMANIZE: [
            "internlm2_5-20b-chat",
            "qwen2.5-14b-instruct",
            "mistral-nemo-instruct-2407"
        ],
        ModelType.SEARCH: [
            "llama-3.2-3b-instruct",
            "mistral-nemo-instruct-2407",
            "qwen2.5-14b-instruct"
        ]
    }

    @classmethod
    def get_config(cls, model_type: ModelType) -> ModelConfig:
        """Get configuration for a specific model type."""
        return cls.DEFAULTS[model_type]

    @classmethod
    def get_system_prompt(cls, model_type: ModelType) -> str:
        """Get system prompt for a specific model type."""
        return cls.SYSTEM_PROMPTS[model_type]

    @classmethod
    def get_fallback_models(cls, model_type: ModelType) -> List[str]:
        """Get list of fallback models for a specific model type."""
        return cls.FALLBACK_MODELS[model_type]

    @classmethod
    def update_config(cls, model_type: ModelType, **kwargs) -> None:
        """Update configuration for a specific model type."""
        config = cls.DEFAULTS[model_type]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)


# Output format specifications
OUTPUT_FORMATS = {
    ModelType.HUMANIZE: {
        "type": "json",
        "schema": {
            "humanized_text": str,
            "changes_made": List[str],
            "confidence_score": float,
            "tone": str,
            "metadata": Dict[str, Any]
        }
    },
    ModelType.CHAT: {
        "type": "text",
        "format": "markdown"
    },
    ModelType.SEARCH: {
        "type": "json",
        "schema": {
            "query": str,
            "intent": str,
            "keywords": List[str],
            "filters": Dict[str, Any]
        }
    }
}
