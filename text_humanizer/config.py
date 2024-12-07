"""Configuration settings for the Text Humanizer application."""
import os
from typing import Dict, Any, List

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    CHROMA_PERSIST_DIRECTORY = "text_humanizer/data/chroma_db"
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    
    # LLM Provider Configuration
    LLM_MAX_RETRIES = 3
    LLM_RETRY_DELAY = 1.0  # Base delay in seconds
    LLM_HEALTH_CHECK_INTERVAL = 60  # Health check cache duration in seconds
    LLM_FALLBACK_MODELS: List[str] = [
        "internlm2_5-20b-chat",  # Primary model
        "qwen2.5-14b-instruct",  # Fallback 1
        "mistral-nemo-instruct-2407", # Fallback 2 (smaller model)
    ]
    LLM_HEALTH_CHECK_TIMEOUT = 3  # Timeout for health check requests in seconds

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    # More lenient settings for development
    LLM_MAX_RETRIES = 2
    LLM_RETRY_DELAY = 0.5

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # In production, ensure all security-related configs are properly set
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    # More conservative settings for production
    LLM_MAX_RETRIES = 3
    LLM_RETRY_DELAY = 2.0
    LLM_HEALTH_CHECK_INTERVAL = 300  # 5 minutes in production

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    # Faster settings for testing
    LLM_MAX_RETRIES = 1
    LLM_RETRY_DELAY = 0.1
    LLM_HEALTH_CHECK_INTERVAL = 1
    LLM_HEALTH_CHECK_TIMEOUT = 1

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig  # Use development config as default
}

# Set default configuration
default_config = config['default']
