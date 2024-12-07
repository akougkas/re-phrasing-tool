"""
Configuration management for the application.
Handles loading and accessing configuration settings.
"""

from typing import Dict, Any
import json
import os

class Config:
    """Configuration manager for the application."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.settings: Dict[str, Any] = {}
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Dict[str, Any]: Configuration settings
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.settings = json.load(f)
        return self.settings
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Any: Configuration value
        """
        return self.settings.get(key, default)
