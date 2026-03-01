"""Magic-related events and helpers."""

from .magic_event import MagicEvent, MagicEventResolver  # noqa: F401
from .magic_utils import grid_distance_feet, pick_target_in_range  # noqa: F401
from .spell_types import SpellTradition  # noqa: F401
from .base_attack_magic_event import BaseMagicAttackEvent  # noqa: F401
from .cantrips.events import AcidSplashEvent, DetectMagicEvent  # noqa: F401
from .level_1st.events import MagicMissileEvent  # noqa: F401

__all__ = [
    "MagicEvent",
    "MagicEventResolver",
    "AcidSplashEvent",
    "DetectMagicEvent",
    "BaseMagicAttackEvent",
    "MagicMissileEvent",
    "grid_distance_feet",
    "pick_target_in_range",
    "SpellTradition",
    "magic_event",
    "magic_utils",
    "spell_types",
    "cantrips",
    "level_1st",
    "focus_spells",
]

from . import magic_event  # type: ignore  # noqa: F401,E402
from . import magic_utils  # type: ignore  # noqa: F401,E402
from . import spell_types  # type: ignore  # noqa: F401,E402
from . import cantrips  # type: ignore  # noqa: F401,E402
from . import level_1st  # type: ignore  # noqa: F401,E402
from . import focus_spells  # type: ignore  # noqa: F401,E402
