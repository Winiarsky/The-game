"""Adapters between game events and the low-level board package."""

from .led_feedback import BoardLedAdapter, LedFeedback, LedFrame, LedRole, movement_led_feedback

__all__ = [
    "BoardLedAdapter",
    "LedFeedback",
    "LedFrame",
    "LedRole",
    "movement_led_feedback",
]
