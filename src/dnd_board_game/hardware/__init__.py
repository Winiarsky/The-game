"""Adapters between game events and the low-level board package."""

from .led_feedback import BoardLedAdapter, DEFAULT_COLORS, LedFeedback, LedFrame, LedRole, movement_led_feedback
from .led_palette import LedColor, led_color_name_pl

__all__ = [
    "BoardLedAdapter",
    "DEFAULT_COLORS",
    "LedColor",
    "LedFeedback",
    "LedFrame",
    "LedRole",
    "led_color_name_pl",
    "movement_led_feedback",
]
