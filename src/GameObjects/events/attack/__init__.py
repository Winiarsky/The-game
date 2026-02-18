"""Attack-related events."""

from .basic_melee_attack_event import BasicMeleeAttackEvent  # noqa: F401
from .attack_sword_event import SwordAttackEvent  # noqa: F401
from .attack_dagger_event import DaggerAttackEvent  # noqa: F401
from .attack_razortooth_jaws_event import RazortoothJawsAttackEvent  # noqa: F401

__all__ = [
    "BasicMeleeAttackEvent",
    "SwordAttackEvent",
    "DaggerAttackEvent",
    "RazortoothJawsAttackEvent",
    "attack_sword_event",
    "attack_dagger_event",
    "attack_razortooth_jaws_event",
]

# re-export module name for compatibility
from . import attack_sword_event  # type: ignore  # noqa: F401,E402
from . import attack_dagger_event  # type: ignore  # noqa: F401,E402
from . import attack_razortooth_jaws_event  # type: ignore  # noqa: F401,E402
