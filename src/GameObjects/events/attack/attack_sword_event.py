from __future__ import annotations

from ..registry import register_event
from .basic_melee_attack_event import BasicMeleeAttackEvent
from damage_types import DamageType


@register_event
class SwordAttackEvent(BasicMeleeAttackEvent):
    name = "sword"
    weapon_label = "mieczem"
    damage_prompt = "1k8 + STR"
    action_id_base = "attack_sword"
    default_tags = ["attack_melee", "sword"]
    damage_type = DamageType.SLASHING.value
