from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class AshenWatcher(BasicEnemy):
    """Level -1 oath spirit tuned as a fragile early haunt-like enemy."""

    name: str = "Ashen Watcher"
    level: int = -1
    hp: int = 7
    max_hp: int | None = 7
    ac: int = 14
    initiative_bonus: int = 5
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 6
    strength: int = 1
    dex_mod: int = 3
    fortitude_bonus: int = 2
    reflex_bonus: int = 5
    will_bonus: int = 5
    perception_bonus: int = 5
    athletics_bonus: int = 1
    intimidation_bonus: int = 5
    stealth_bonus: int = 5
    behavior_id: str | None = "basic_melee"
    enemy_type: EnemyType | str = EnemyType.SPIRIT
    traits: tuple[str, ...] = ("spirit", "undead", "incorporeal", "oathbound")
    languages: tuple[str, ...] = ("Common",)
    weapon_loadout: tuple[str, ...] = ("unarmed",)
    armor_loadout: tuple[str, ...] = ()
    active_weapon: str | None = "unarmed"
    special_actions: tuple[str, ...] = ("demoralize",)
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = False

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "haunt_skirmisher", "demoralize_opening": True, "preferred_reach_feet": 5}
        if self.awareness_profile is None:
            self.awareness_profile = {
                "awareness_range_feet": 40,
                "move_trigger_threshold": 0.55,
                "interaction_trigger_threshold": 0.20,
                "spell_trigger_threshold": 0.30,
                "stealth_fail_trigger_threshold": 0.20,
            }
        super().__post_init__()


META = GameObjectMeta(
    object_id="ashen_watcher",
    label="Ashen Watcher",
    color="#9a8f86",
    category="Enemies",
    placement="cell",
    description="Level -1 oath spirit; a fragile clue encounter in the burned chapel.",
    logic_cls=AshenWatcher,
    default_config={
        "name": "Ashen Watcher",
        "level": -1,
        "hp": 7,
        "max_hp": 7,
        "ac": 14,
        "initiative_bonus": 5,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 6,
        "strength": 1,
        "dex_mod": 3,
        "fortitude_bonus": 2,
        "reflex_bonus": 5,
        "will_bonus": 5,
        "perception_bonus": 5,
        "athletics_bonus": 1,
        "intimidation_bonus": 5,
        "stealth_bonus": 5,
        "behavior_id": "basic_melee",
        "enemy_type": EnemyType.SPIRIT.value,
        "traits": ["spirit", "undead", "incorporeal", "oathbound"],
        "languages": ["Common"],
        "weapon_loadout": ["unarmed"],
        "active_weapon": "unarmed",
        "special_actions": ["demoralize"],
        "auto_opportunity_attack": False,
        "ai_profile": {"role": "haunt_skirmisher", "demoralize_opening": True, "preferred_reach_feet": 5},
    },
)


__all__ = ["AshenWatcher", "META"]
