"""
Logging configuration for the application.
"""

import logging

# Create logger
logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    """Configure logging with a single handler to avoid duplicates."""
    # Remove any existing handlers
    logger.handlers.clear()
    logging.getLogger().handlers.clear()
    
    # Configure root logger
    logging.getLogger().setLevel(level)
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                datefmt='%Y-%m-%d %H:%M:%S,%f')[:-3]
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger
