from __future__ import annotations

from ..registry import register_event
from .basic_melee_attack_event import BasicMeleeAttackEvent
from damage_types import DamageType


@register_event
class RazortoothJawsAttackEvent(BasicMeleeAttackEvent):
    name = "razortooth_jaws"
    weapon_label = "szczekami"
    damage_prompt = "1k6 + STR"
    action_id_base = "attack_razortooth_jaws"
    default_tags = ["attack_melee", "jaws", "goblin"]
    damage_type = DamageType.PIERCING.value
