from .base import EventContext, EventResult, GameEvent  # noqa: F401
from .registry import register_event, dispatch_event, list_events, get_event_cls  # noqa: F401

# Lekkie aliasy zgodnosciowe (bez eager importow modulow magic/NPC).
from .attack import attack_event, swap_weapon_event  # noqa: F401
from .attack import attack_sword_event  # noqa: F401
from . import equip_event  # noqa: F401
from . import quick_alchemy_event  # noqa: F401

__all__ = [
    "EventContext",
    "EventResult",
    "GameEvent",
    "register_event",
    "dispatch_event",
    "list_events",
    "get_event_cls",
    "equip_event",
    "quick_alchemy_event",
    "attack_event",
    "swap_weapon_event",
    "attack_sword_event",
]
