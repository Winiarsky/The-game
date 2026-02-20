from __future__ import annotations

from statuses import FLAT_FOOTED_STATUS

from .base_poison_event import BasePoisonEvent
from ..registry import register_event


@register_event
class GiantCentipedeVenomEvent(BasePoisonEvent):
    name = "giant_centipede_venom"
    dc = 17
    onset_turns = None
    duration_turns = 6  # 6 rounds
    stages = [
        {"dice": "1d6", "condition": FLAT_FOOTED_STATUS},
        {"dice": "1d8", "condition": FLAT_FOOTED_STATUS},
        {"dice": "1d12", "condition": FLAT_FOOTED_STATUS},
    ]
