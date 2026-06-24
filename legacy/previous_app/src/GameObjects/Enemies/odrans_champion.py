from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class OdransChampion(BasicEnemy):
    """Level 2 finale boss for a level 1 party."""

    name: str = "Champion Odrana"
    level: int = 2
    hp: int = 36
    max_hp: int | None = 36
    ac: int = 17
    initiative_bonus: int = 6
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 10
    strength: int = 4
    dex_mod: int = 1
    fortitude_bonus: int = 8
    reflex_bonus: int = 5
    will_bonus: int = 7
    perception_bonus: int = 6
    athletics_bonus: int = 8
    intimidation_bonus: int = 7
    stealth_bonus: int = 3
    behavior_id: str | None = "goblin_commando_raider"
    enemy_type: EnemyType | str = EnemyType.HUMAN
    traits: tuple[str, ...] = ("human", "humanoid", "champion", "oathbreaker")
    languages: tuple[str, ...] = ("Common",)
    weapon_loadout: tuple[str, ...] = ("halberd", "longsword")
    armor_loadout: tuple[str, ...] = ("breastplate",)
    active_weapon: str | None = "halberd"
    special_actions: tuple[str, ...] = ("demoralize", "enemy_trip")
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = True

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "boss_controller", "demoralize_opening": True, "preferred_reach_feet": 10}
        if self.awareness_profile is None:
            self.awareness_profile = {
                "awareness_range_feet": 45,
                "move_trigger_threshold": 0.85,
                "interaction_trigger_threshold": 0.40,
                "spell_trigger_threshold": 0.60,
                "stealth_fail_trigger_threshold": 0.45,
            }
        super().__post_init__()


META = GameObjectMeta(
    object_id="odrans_champion",
    label="Champion Odrana",
    color="#4f3941",
    category="Enemies",
    placement="cell",
    description="Finałowy champion Odrana poziomu 2; kontrola zasięgiem i wysoka Wytrwałość.",
    logic_cls=OdransChampion,
    default_config={
        "name": "Champion Odrana",
        "level": 2,
        "hp": 36,
        "max_hp": 36,
        "ac": 17,
        "initiative_bonus": 6,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 10,
        "strength": 4,
        "dex_mod": 1,
        "fortitude_bonus": 8,
        "reflex_bonus": 5,
        "will_bonus": 7,
        "perception_bonus": 6,
        "athletics_bonus": 8,
        "intimidation_bonus": 7,
        "stealth_bonus": 3,
        "behavior_id": "goblin_commando_raider",
        "enemy_type": EnemyType.HUMAN.value,
        "traits": ["human", "humanoid", "champion", "oathbreaker"],
        "languages": ["Common"],
        "weapon_loadout": ["halberd", "longsword"],
        "armor_loadout": ["breastplate"],
        "active_weapon": "halberd",
        "special_actions": ["demoralize", "enemy_trip"],
        "auto_opportunity_attack": True,
        "ai_profile": {"role": "boss_controller", "demoralize_opening": True, "preferred_reach_feet": 10},
    },
)


__all__ = ["OdransChampion", "META"]
