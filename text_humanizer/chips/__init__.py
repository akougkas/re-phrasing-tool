"""
Smart chip detection and handling package.
"""

from .chip_detector import ChipDetector, ChipRegistry, ChipHandler, register_chip_handler
from .handlers.humanize_handler import HumanizeHandler

__all__ = [
    'ChipDetector',
    'ChipRegistry',
    'ChipHandler',
    'register_chip_handler',
    'HumanizeHandler'
]
