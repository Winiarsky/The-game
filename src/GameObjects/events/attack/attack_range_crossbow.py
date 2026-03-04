from __future__ import annotations

from damage_types import DamageType

from ..registry import register_event
from .base_attack_range_event import BaseRangeAttackEvent


@register_event
class CrossbowAttackEvent(BaseRangeAttackEvent):
    name = "crossbow"
    weapon_label = "kuszą"
    damage_prompt = "1k8"
    action_id_base = "attack_crossbow"
    damage_type = DamageType.PIERCING.value
    range_increment_ft = 120
    default_tags = ["attack_ranged", "ranged_attack", "crossbow", "simple_crossbow"]

