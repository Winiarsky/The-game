from __future__ import annotations

from .base_poison_event import BasePoisonEvent
from ..registry import register_event


@register_event
class ArsenicEvent(BasePoisonEvent):
    name = "arsenic"
    dc = 18
    onset_turns = 100  # 10 minutes
    duration_turns = 50  # max 5 minutes
    stages = [
        {"dice": "1d4", "note": "sickened 1 (opisowo)"},
        {"dice": "1d6", "note": "sickened 2 (opisowo)"},
        {"dice": "2d6", "note": "sickened 3 (opisowo)"},
    ]
