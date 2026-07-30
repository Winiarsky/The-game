"""Adapters between game events and the low-level board package."""

from .board_session import BoardSessionAdapter
from .led_feedback import BoardLedAdapter, DEFAULT_COLORS, LedFeedback, LedFrame, LedRole, movement_led_feedback
from .led_palette import PARTY_IDENTITY_COLORS, LedColor, led_color_name_pl

__all__ = [
    "BoardLedAdapter",
    "BoardSessionAdapter",
    "DEFAULT_COLORS",
    "LedColor",
    "PARTY_IDENTITY_COLORS",
    "LedFeedback",
    "LedFrame",
    "LedRole",
    "led_color_name_pl",
    "movement_led_feedback",
]
