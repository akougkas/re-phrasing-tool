"""
Logging configuration and utilities.
Provides consistent logging across the application.
"""

import logging
import sys
from datetime import datetime

class Logger:
    def __init__(self):
        self.logger = logging.getLogger('text_humanizer')
        self.logger.setLevel(logging.INFO)
        
        # Create console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(f"[INFO] {message}")

    def error(self, message):
        self.logger.error(f"[ERROR] {message}")

# Create a singleton instance
logger = Logger()
