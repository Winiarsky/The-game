"""Adapters between game events and the low-level board package."""

from .led_feedback import BoardLedAdapter, DEFAULT_COLORS, LedFeedback, LedFrame, LedRole, movement_led_feedback
from .led_palette import LedColor

__all__ = [
    "BoardLedAdapter",
    "DEFAULT_COLORS",
    "LedColor",
    "LedFeedback",
    "LedFrame",
    "LedRole",
    "movement_led_feedback",
]
