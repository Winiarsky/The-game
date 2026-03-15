from __future__ import annotations

import logging

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType

logger = logging.getLogger(__name__)


class SimpleEnemy(BasicEnemy):
    """Podstawowy przeciwnik do walki turowej."""


META = GameObjectMeta(
    object_id="simple_enemy",
    label="Wrogi NPC",
    color="#b00",
    category="Enemies",
    placement="cell",
    description="Podstawowy przeciwnik do walki turowej.",
    logic_cls=SimpleEnemy,
    default_config={
        "name": "Wrogi strażnik",
        "hp": 12,
        "ac": 14,
        "initiative_bonus": 2,
        "distance": 25,
        "attack_bonus": 5,
        "strength": 2,
        "behavior_id": "basic_melee",
        "enemy_type": EnemyType.ORC.value,
        "watch_disturbed": 0,
        "watch_disabled": False,
        "perception_bonus": 4,
        "loot_cp": 10,
        "magical": True,
        "magical_description": "Wyraźna, wroga aura magiczna.",
        "tags": ["magical"],
    },
)

# Alias dla kompatybilności z wcześniejszymi importami.
Enemy = SimpleEnemy
