from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class MillEnforcer(BasicEnemy):
    """Level 1 brute used as the old mill's main physical threat."""

    name: str = "Mill Enforcer"
    level: int = 1
    hp: int = 25
    max_hp: int | None = 25
    ac: int = 15
    initiative_bonus: int = 3
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 8
    strength: int = 4
    dex_mod: int = 0
    fortitude_bonus: int = 7
    reflex_bonus: int = 3
    will_bonus: int = 4
    perception_bonus: int = 4
    athletics_bonus: int = 7
    intimidation_bonus: int = 6
    stealth_bonus: int = 1
    behavior_id: str | None = "goblin_commando_raider"
    enemy_type: EnemyType | str = EnemyType.HUMAN
    traits: tuple[str, ...] = ("human", "humanoid", "brute")
    languages: tuple[str, ...] = ("Common",)
    weapon_loadout: tuple[str, ...] = ("war_flail",)
    armor_loadout: tuple[str, ...] = ("hide_armor",)
    active_weapon: str | None = "war_flail"
    special_actions: tuple[str, ...] = ("demoralize", "enemy_trip")
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = False

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "brute_controller", "demoralize_opening": True, "preferred_reach_feet": 10}
        if self.awareness_profile is None:
            self.awareness_profile = {
                "awareness_range_feet": 35,
                "move_trigger_threshold": 0.75,
                "interaction_trigger_threshold": 0.35,
                "spell_trigger_threshold": 0.50,
                "stealth_fail_trigger_threshold": 0.35,
            }
        super().__post_init__()


META = GameObjectMeta(
    object_id="mill_enforcer",
    label="Mill Enforcer",
    color="#7f4b2b",
    category="Enemies",
    placement="cell",
    description="Level 1 human brute for Ashen Oath; Trip and Demoralize pressure near the hostage.",
    logic_cls=MillEnforcer,
    default_config={
        "name": "Mill Enforcer",
        "level": 1,
        "hp": 25,
        "max_hp": 25,
        "ac": 15,
        "initiative_bonus": 3,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 8,
        "strength": 4,
        "dex_mod": 0,
        "fortitude_bonus": 7,
        "reflex_bonus": 3,
        "will_bonus": 4,
        "perception_bonus": 4,
        "athletics_bonus": 7,
        "intimidation_bonus": 6,
        "stealth_bonus": 1,
        "behavior_id": "goblin_commando_raider",
        "enemy_type": EnemyType.HUMAN.value,
        "traits": ["human", "humanoid", "brute"],
        "languages": ["Common"],
        "weapon_loadout": ["war_flail"],
        "armor_loadout": ["hide_armor"],
        "active_weapon": "war_flail",
        "special_actions": ["demoralize", "enemy_trip"],
        "auto_opportunity_attack": False,
        "ai_profile": {"role": "brute_controller", "demoralize_opening": True, "preferred_reach_feet": 10},
    },
)


__all__ = ["MillEnforcer", "META"]
