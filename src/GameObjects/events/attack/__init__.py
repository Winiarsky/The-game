"""Attack-related events."""

from .attack_sword_event import SwordAttackEvent  # noqa: F401

__all__ = [
    "SwordAttackEvent",
    "attack_sword_event",
]

# re-export module name for compatibility
from . import attack_sword_event  # type: ignore  # noqa: F401,E402
