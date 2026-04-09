from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class GoblinCommando(BasicEnemy):
    name: str = "Goblin Commando"
    hp: int = 18
    max_hp: int | None = 18
    ac: int = 17
    initiative_bonus: int = 5
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 8
    strength: int = 3
    dex_mod: int = 3
    fortitude_bonus: int = 7
    reflex_bonus: int = 8
    will_bonus: int = 5
    perception_bonus: int = 5
    athletics_bonus: int = 6
    intimidation_bonus: int = 5
    stealth_bonus: int = 6
    behavior_id: str | None = "goblin_commando_raider"
    enemy_type: EnemyType | str = EnemyType.GOBLIN
    traits: tuple[str, ...] = ("goblin", "humanoid", "small")
    languages: tuple[str, ...] = ("Common", "Goblin")
    weapon_loadout: tuple[str, ...] = ("horsechopper", "shortbow")
    armor_loadout: tuple[str, ...] = ("leather_armor",)
    active_weapon: str | None = "horsechopper"
    special_actions: tuple[str, ...] = ("demoralize", "enemy_trip")
    special_reactions: tuple[str, ...] = ("goblin_scuttle",)
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = False

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "raider", "demoralize_opening": True, "preferred_reach_feet": 10}
        super().__post_init__()


META = GameObjectMeta(
    object_id="goblin_commando",
    label="Goblin Commando",
    color="#a33b12",
    category="Enemies",
    placement="cell",
    description="Gobliński komandos: agresywny rajder z Demoralize, reach i Trip.",
    logic_cls=GoblinCommando,
    default_config={
        "name": "Goblin Commando",
        "hp": 18,
        "max_hp": 18,
        "ac": 17,
        "initiative_bonus": 5,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 8,
        "strength": 3,
        "dex_mod": 3,
        "fortitude_bonus": 7,
        "reflex_bonus": 8,
        "will_bonus": 5,
        "perception_bonus": 5,
        "athletics_bonus": 6,
        "intimidation_bonus": 5,
        "stealth_bonus": 6,
        "behavior_id": "goblin_commando_raider",
        "enemy_type": EnemyType.GOBLIN.value,
        "traits": ["goblin", "humanoid", "small"],
        "languages": ["Common", "Goblin"],
        "weapon_loadout": ["horsechopper", "shortbow"],
        "armor_loadout": ["leather_armor"],
        "active_weapon": "horsechopper",
        "special_actions": ["demoralize", "enemy_trip"],
        "special_reactions": ["goblin_scuttle"],
        "auto_opportunity_attack": False,
        "ai_profile": {"role": "raider", "demoralize_opening": True, "preferred_reach_feet": 10},
    },
)


__all__ = ["GoblinCommando", "META"]
