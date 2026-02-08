from __future__ import annotations

from ..registry import register_event
from .base_attack_range_event import BaseRangeAttackEvent


@register_event
class LongBowAttackEvent(BaseRangeAttackEvent):
    name = "longbow"
    weapon_label = "długim łukiem"
    damage_prompt = "1k8 + DEX"
    action_id_base = "attack_long_bow"
    damage_type = "piercing"
    range_increment_ft = 100
    default_tags = ["attack_ranged", "ranged_attack", "bow", "longbow"]
