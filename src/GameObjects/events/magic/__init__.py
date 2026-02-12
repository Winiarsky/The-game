"""Magic-related events and helpers."""

from .magic_event import MagicEvent, MagicEventResolver  # noqa: F401
from .acid_splash_event import AcidSplashEvent  # noqa: F401
from .magic_missile_event import MagicMissileEvent  # noqa: F401
from .magic_utils import grid_distance_feet, pick_target_in_range  # noqa: F401
from .spell_types import SpellTradition  # noqa: F401
from .base_attack_magic_event import BaseMagicAttackEvent  # noqa: F401

__all__ = [
    "MagicEvent",
    "MagicEventResolver",
    "AcidSplashEvent",
    "BaseMagicAttackEvent",
    "MagicMissileEvent",
    "grid_distance_feet",
    "pick_target_in_range",
    "SpellTradition",
    "magic_missile_event",
    "magic_event",
    "magic_utils",
    "spell_types",
]

from . import magic_event  # type: ignore  # noqa: F401,E402
from . import magic_missile_event  # type: ignore  # noqa: F401,E402
from . import magic_utils  # type: ignore  # noqa: F401,E402
from . import spell_types  # type: ignore  # noqa: F401,E402
