from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class AshenKnight(BasicEnemy):
    """Level 1 spirit soldier guarding the ruins before the crypt."""

    name: str = "Popielny Rycerz"
    level: int = 1
    hp: int = 21
    max_hp: int | None = 21
    ac: int = 16
    initiative_bonus: int = 5
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 9
    strength: int = 3
    dex_mod: int = 2
    fortitude_bonus: int = 6
    reflex_bonus: int = 5
    will_bonus: int = 6
    perception_bonus: int = 5
    athletics_bonus: int = 7
    intimidation_bonus: int = 6
    stealth_bonus: int = 4
    behavior_id: str | None = "goblin_commando_raider"
    enemy_type: EnemyType | str = EnemyType.UNDEAD
    traits: tuple[str, ...] = ("spirit", "undead", "oathbound", "soldier")
    languages: tuple[str, ...] = ("Common",)
    weapon_loadout: tuple[str, ...] = ("longsword", "shield_boss")
    armor_loadout: tuple[str, ...] = ("chain_mail",)
    active_weapon: str | None = "longsword"
    special_actions: tuple[str, ...] = ("demoralize", "enemy_trip")
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = True

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "elite_guardian", "demoralize_opening": True, "preferred_reach_feet": 5}
        if self.awareness_profile is None:
            self.awareness_profile = {
                "awareness_range_feet": 40,
                "move_trigger_threshold": 0.80,
                "interaction_trigger_threshold": 0.35,
                "spell_trigger_threshold": 0.55,
                "stealth_fail_trigger_threshold": 0.40,
            }
        super().__post_init__()


META = GameObjectMeta(
    object_id="ashen_knight",
    label="Popielny Rycerz",
    color="#706f68",
    category="Enemies",
    placement="cell",
    description="Nieumarły żołnierz przysięgi poziomu 1; umiarkowana presja bez roli bossa.",
    logic_cls=AshenKnight,
    default_config={
        "name": "Popielny Rycerz",
        "level": 1,
        "hp": 21,
        "max_hp": 21,
        "ac": 16,
        "initiative_bonus": 5,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 9,
        "strength": 3,
        "dex_mod": 2,
        "fortitude_bonus": 6,
        "reflex_bonus": 5,
        "will_bonus": 6,
        "perception_bonus": 5,
        "athletics_bonus": 7,
        "intimidation_bonus": 6,
        "stealth_bonus": 4,
        "behavior_id": "goblin_commando_raider",
        "enemy_type": EnemyType.UNDEAD.value,
        "traits": ["spirit", "undead", "oathbound", "soldier"],
        "languages": ["Common"],
        "weapon_loadout": ["longsword", "shield_boss"],
        "armor_loadout": ["chain_mail"],
        "active_weapon": "longsword",
        "special_actions": ["demoralize", "enemy_trip"],
        "auto_opportunity_attack": True,
        "ai_profile": {"role": "elite_guardian", "demoralize_opening": True, "preferred_reach_feet": 5},
    },
)


__all__ = ["AshenKnight", "META"]
