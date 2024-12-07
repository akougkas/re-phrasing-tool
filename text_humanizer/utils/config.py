"""
Configuration management for the application.
Handles loading and accessing configuration settings with validation,
environment-specific configurations, and hot-reloading support.
"""

from typing import Dict, Any, Set
import json
import os
import time
from pathlib import Path
from threading import Thread, Lock
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class Environment(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

@dataclass
class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    message: str
    missing_keys: Set[str] = None

class Config:
    """Configuration manager for the application."""
    
    REQUIRED_SETTINGS = {
        'app_name',
        'log_level',
        'model_settings',
    }
    
    def __init__(self, config_dir: str = "config", env: str = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
            env: Environment to load (development/testing/production)
        """
        self.config_dir = Path(config_dir)
        self.env = env or os.getenv("APP_ENV", "development")
        logger.info(f"Initializing Config with directory: {self.config_dir} and environment: {self.env}")
        self.settings: Dict[str, Any] = {}
        self._last_load_time = 0
        self._lock = Lock()
        self._hot_reload_interval = 10  # seconds
        self._hot_reload_enabled = False
        self._hot_reload_thread = None
        
    def start_hot_reload(self) -> None:
        """Enable hot-reloading of configuration files."""
        if self._hot_reload_enabled:
            return
            
        self._hot_reload_enabled = True
        self._hot_reload_thread = Thread(
            target=self._hot_reload_worker,
            daemon=True
        )
        self._hot_reload_thread.start()
        logger.info("Configuration hot-reloading enabled")
        
    def stop_hot_reload(self) -> None:
        """Disable hot-reloading of configuration files."""
        self._hot_reload_enabled = False
        if self._hot_reload_thread:
            self._hot_reload_thread.join()
            self._hot_reload_thread = None
        logger.info("Configuration hot-reloading disabled")
        
    def _hot_reload_worker(self) -> None:
        """Worker thread for hot-reloading configuration."""
        while self._hot_reload_enabled:
            config_file = self._get_config_file()
            if config_file.exists():
                mtime = config_file.stat().st_mtime
                if mtime > self._last_load_time:
                    logger.info("Configuration file changed, reloading...")
                    self.load_config()
            time.sleep(self._hot_reload_interval)
            
    def _get_config_file(self) -> Path:
        """Get the appropriate config file path based on environment."""
        config_file = self.config_dir / f"config.{self.env}.json"
        logger.debug(f"Config file path: {config_file}")
        return config_file
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file with environment-specific overrides.
        
        Returns:
            Dict[str, Any]: Configuration settings
            
        Raises:
            ConfigValidationError: If required settings are missing
        """
        with self._lock:
            config_file = self._get_config_file()
            logger.info(f"Loading configuration from {config_file}")
            
            # Load base config
            base_config = {}
            base_file = self.config_dir / "config.base.json"
            logger.info(f"Loading base config from {base_file}")
            if base_file.exists():
                with open(base_file, 'r') as f:
                    base_config = json.load(f)
                logger.debug(f"Base config loaded: {base_config}")
            else:
                logger.warning(f"Base config file not found at {base_file}")
            
            # Load environment-specific config
            env_config = {}
            logger.info(f"Loading environment config from {config_file}")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    env_config = json.load(f)
                logger.debug(f"Environment config loaded: {env_config}")
            else:
                logger.warning(f"Environment config file not found at {config_file}")
                    
            # Merge configurations
            self.settings = {**base_config, **env_config}
            logger.debug(f"Final merged config: {self.settings}")
            self._last_load_time = time.time()
            
            # Validate required settings
            self._validate_config()
            
            logger.info(f"Successfully loaded configuration for environment: {self.env}")
            return self.settings
            
    def _validate_config(self) -> None:
        """
        Validate that all required settings are present.
        
        Raises:
            ConfigValidationError: If required settings are missing
        """
        missing_keys = self.REQUIRED_SETTINGS - set(self.settings.keys())
        if missing_keys:
            logger.error(f"Missing required configuration keys: {missing_keys}")
            logger.error(f"Available keys: {set(self.settings.keys())}")
            raise ConfigValidationError(
                f"Missing required configuration keys: {missing_keys}",
                missing_keys=missing_keys
            )
        logger.debug("All required settings are present")
    
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
    
    def get_required(self, key: str) -> Any:
        """
        Get required configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            Any: Configuration value
            
        Raises:
            KeyError: If key not found
        """
        if key not in self.settings:
            raise KeyError(f"Required configuration key not found: {key}")
        return self.settings[key]
