from __future__ import annotations

from ..registry import register_event
from .basic_enemy_melee_attack_event import BasicEnemyMeleeAttackEvent


@register_event
class EnemyMeleeAttackEvent(BasicEnemyMeleeAttackEvent):
    """Domyślny atak wręcz wroga (1d6 + STR)."""

    name = "enemy_attack_melee"
    weapon_label = "atakuje bohatera"
    action_id_base = "enemy_attack_melee"
    damage_die_sides = 6
