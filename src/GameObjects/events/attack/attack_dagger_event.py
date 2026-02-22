from __future__ import annotations

from ..registry import register_event
from .basic_melee_attack_event import BasicMeleeAttackEvent
from damage_types import DamageType


@register_event
class DaggerAttackEvent(BasicMeleeAttackEvent):
    name = "dagger"
    weapon_label = "sztyletem"
    damage_prompt = "1k4 + STR"
    action_id_base = "attack_dagger"
    default_tags = ["attack_melee", "finesse", "dagger"]
    damage_type = DamageType.SLASHING.value
