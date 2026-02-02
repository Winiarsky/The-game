"""Attack-related events."""

from .basic_melee_attack_event import BasicMeleeAttackEvent  # noqa: F401
from .attack_sword_event import SwordAttackEvent  # noqa: F401
from .attack_dagger_event import DaggerAttackEvent  # noqa: F401

__all__ = [
    "BasicMeleeAttackEvent",
    "SwordAttackEvent",
    "DaggerAttackEvent",
    "attack_sword_event",
    "attack_dagger_event",
]

# re-export module name for compatibility
from . import attack_sword_event  # type: ignore  # noqa: F401,E402
from . import attack_dagger_event  # type: ignore  # noqa: F401,E402
