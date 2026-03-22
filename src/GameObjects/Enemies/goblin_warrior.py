from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass
class GoblinWarrior(BasicEnemy):
    name: str = "Goblin Warrior"
    hp: int = 6
    max_hp: int | None = 6
    ac: int = 16
    initiative_bonus: int = 2
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 8
    strength: int = 0
    dex_mod: int = 3
    fortitude_bonus: int = 5
    reflex_bonus: int = 7
    will_bonus: int = 3
    perception_bonus: int = 2
    athletics_bonus: int = 2
    stealth_bonus: int = 5
    behavior_id: str | None = "goblin_warrior_pack"
    enemy_type: EnemyType | str = EnemyType.GOBLIN
    traits: tuple[str, ...] = ("goblin", "humanoid", "small")
    languages: tuple[str, ...] = ("Goblin",)
    weapon_loadout: tuple[str, ...] = ("dogslicer", "shortbow")
    armor_loadout: tuple[str, ...] = ("leather_armor",)
    active_weapon: str | None = "dogslicer"
    special_reactions: tuple[str, ...] = ("goblin_scuttle",)
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = False

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "pack_melee", "cowardice_threshold": 0.4}
        super().__post_init__()


META = GameObjectMeta(
    object_id="goblin_warrior",
    label="Goblin Warrior",
    color="#8b2f17",
    category="Enemies",
    placement="cell",
    description="Goblinowy wojownik walczący stadnie, szukający przewagi liczebnej i flanki.",
    logic_cls=GoblinWarrior,
    default_config={
        "name": "Goblin Warrior",
        "hp": 6,
        "max_hp": 6,
        "ac": 16,
        "initiative_bonus": 2,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 8,
        "strength": 0,
        "dex_mod": 3,
        "fortitude_bonus": 5,
        "reflex_bonus": 7,
        "will_bonus": 3,
        "perception_bonus": 2,
        "athletics_bonus": 2,
        "stealth_bonus": 5,
        "behavior_id": "goblin_warrior_pack",
        "enemy_type": EnemyType.GOBLIN.value,
        "traits": ["goblin", "humanoid", "small"],
        "languages": ["Goblin"],
        "weapon_loadout": ["dogslicer", "shortbow"],
        "armor_loadout": ["leather_armor"],
        "active_weapon": "dogslicer",
        "special_reactions": ["goblin_scuttle"],
        "auto_opportunity_attack": False,
        "ai_profile": {"role": "pack_melee", "cowardice_threshold": 0.4},
    },
)


__all__ = ["GoblinWarrior", "META"]
