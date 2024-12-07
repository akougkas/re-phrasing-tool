"""
Configuration module for text humanizer.
"""

from dataclasses import dataclass
from typing import List

@dataclass
class LLMProviderConfig:
    """Configuration for LLM provider settings."""
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAY: int = 1
    LLM_FALLBACK_MODELS: List[str] = None
    LLM_HEALTH_CHECK_INTERVAL: int = 60
    LLM_HEALTH_CHECK_TIMEOUT: int = 5

    def __post_init__(self):
        if self.LLM_FALLBACK_MODELS is None:
            self.LLM_FALLBACK_MODELS = ["gpt2", "gpt2-medium"]

class DefaultConfig(LLMProviderConfig):
    """Default configuration for LLM provider."""
    pass

class DevelopmentConfig(LLMProviderConfig):
    """Development configuration for LLM provider."""
    LLM_MAX_RETRIES = 2
    LLM_RETRY_DELAY = 0.5
    LLM_HEALTH_CHECK_INTERVAL = 30

class ProductionConfig(LLMProviderConfig):
    """Production configuration for LLM provider."""
    LLM_MAX_RETRIES = 5
    LLM_RETRY_DELAY = 2
    LLM_HEALTH_CHECK_INTERVAL = 120

class TestingConfig(LLMProviderConfig):
    """Testing configuration for LLM provider."""
    LLM_MAX_RETRIES = 1
    LLM_RETRY_DELAY = 0.1
    LLM_HEALTH_CHECK_INTERVAL = 10
    LLM_FALLBACK_MODELS = ["mock-model"]

# Configuration mapping
config = {
    "default": DefaultConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
