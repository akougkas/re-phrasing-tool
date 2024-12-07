"""
Application configuration management.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import os
from pathlib import Path
import json

from text_humanizer.config.model_config import ModelConfig
from text_humanizer.utils.logger import logger

@dataclass
class AppConfig:
    """Application configuration."""
    # Server settings
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    
    # Security
    secret_key: str = os.urandom(24).hex()
    csrf_enabled: bool = True
    
    # Model settings
    chat_model_config: Dict[str, Any] = None
    humanizer_model_config: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize model configurations."""
        self.chat_model_config = {
            "endpoint_url": os.getenv("CHAT_MODEL_URL", "http://localhost:1234"),
            "model_name": os.getenv("CHAT_MODEL_NAME", "gpt-3.5-turbo"),
            "max_tokens": 2048,
            "timeout": 30,
            "temperature": 0.7,
            "system_prompt": "You are a helpful AI assistant."
        }
        
        self.humanizer_model_config = {
            "endpoint_url": os.getenv("HUMANIZER_MODEL_URL", "http://localhost:1234"),
            "model_name": os.getenv("HUMANIZER_MODEL_NAME", "gpt-3.5-turbo"),
            "max_tokens": 2048,
            "timeout": 30,
            "temperature": 0.7,
            "system_prompt": "You are a text improvement assistant. Your goal is to enhance text while preserving its core meaning."
        }
        
    def load_config(self, config_path: Optional[str] = None) -> None:
        """Load configuration from a JSON file."""
        if not config_path:
            config_path = os.getenv("APP_CONFIG_PATH")
            
        if not config_path:
            logger.warning("No config path provided, using defaults")
            return
            
        config_path = Path(config_path)
        if not config_path.exists():
            logger.warning(f"Config file {config_path} not found, using defaults")
            return
            
        try:
            with open(config_path) as f:
                config = json.load(f)
                
            # Update configurations
            for key, value in config.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
