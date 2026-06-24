"""Attack-related events."""

from .attack_event import AttackEvent  # noqa: F401
from .swap_weapon_event import SwapWeaponEvent  # noqa: F401
from .basic_melee_attack_event import BasicMeleeAttackEvent  # noqa: F401
from .attack_sword_event import SwordAttackEvent  # noqa: F401
from .attack_dagger_event import DaggerAttackEvent  # noqa: F401
from .attack_razortooth_jaws_event import RazortoothJawsAttackEvent  # noqa: F401
from .attack_unarmed_event import UnarmedAttackEvent  # noqa: F401
from . import attack_additional_weapon_events  # noqa: F401

__all__ = [
    "AttackEvent",
    "SwapWeaponEvent",
    "BasicMeleeAttackEvent",
    "SwordAttackEvent",
    "DaggerAttackEvent",
    "RazortoothJawsAttackEvent",
    "UnarmedAttackEvent",
    "attack_event",
    "swap_weapon_event",
    "attack_sword_event",
    "attack_dagger_event",
    "attack_razortooth_jaws_event",
    "attack_unarmed_event",
    "attack_additional_weapon_events",
]

# re-export module name for compatibility
from . import attack_event  # type: ignore  # noqa: F401,E402
from . import swap_weapon_event  # type: ignore  # noqa: F401,E402
from . import attack_sword_event  # type: ignore  # noqa: F401,E402
from . import attack_dagger_event  # type: ignore  # noqa: F401,E402
from . import attack_razortooth_jaws_event  # type: ignore  # noqa: F401,E402
from . import attack_unarmed_event  # type: ignore  # noqa: F401,E402
from . import attack_additional_weapon_events  # type: ignore  # noqa: F401,E402
