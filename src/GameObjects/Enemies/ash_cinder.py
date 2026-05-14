from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class AshCinder(BasicEnemy):
    """Kruchy popielny minion blokujący ruch i akcje rytuału."""

    name: str = "Popielna Iskra"
    level: int = -1
    hp: int = 1
    max_hp: int | None = 1
    ac: int = 13
    initiative_bonus: int = 4
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 5
    strength: int = 0
    dex_mod: int = 3
    fortitude_bonus: int = 2
    reflex_bonus: int = 5
    will_bonus: int = 3
    perception_bonus: int = 4
    athletics_bonus: int = 0
    intimidation_bonus: int = 2
    stealth_bonus: int = 6
    behavior_id: str | None = "basic_melee"
    enemy_type: EnemyType | str = EnemyType.UNDEAD
    traits: tuple[str, ...] = ("spirit", "undead", "minion", "ash")
    languages: tuple[str, ...] = ()
    weapon_loadout: tuple[str, ...] = ("unarmed",)
    armor_loadout: tuple[str, ...] = ()
    active_weapon: str | None = "unarmed"
    special_actions: tuple[str, ...] = ()
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = False
    encounter_role: str = "ash_cinder"

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {
                "role": "blocker_minion",
                "damage_cap": 1,
                "priorities": [
                    "marked_by_ash",
                    "active_statue",
                    "altar_access",
                    "nearest_hero",
                ],
            }
        if self.awareness_profile is None:
            self.awareness_profile = {
                "awareness_range_feet": 0,
                "move_trigger_threshold": 0.0,
                "interaction_trigger_threshold": 0.0,
                "spell_trigger_threshold": 0.0,
                "stealth_fail_trigger_threshold": 0.0,
            }
        super().__post_init__()

    def apply_damage(self, amount: int, damage_type: str = "normal", *, nonlethal: bool = False):
        return super().apply_damage(max(1, int(amount or 1)), damage_type, nonlethal=nonlethal)


META = GameObjectMeta(
    object_id="ash_cinder",
    label="Popielna Iskra",
    color="#3f3f46",
    category="Enemies",
    placement="cell",
    description="Popielny minion z 1 HP; słabe obrażenia, ale blokuje przejścia i punkty rytuału.",
    logic_cls=AshCinder,
    default_config={
        "name": "Popielna Iskra",
        "level": -1,
        "hp": 1,
        "max_hp": 1,
        "ac": 13,
        "initiative_bonus": 4,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 5,
        "dex_mod": 3,
        "reflex_bonus": 5,
        "will_bonus": 3,
        "perception_bonus": 4,
        "stealth_bonus": 6,
        "behavior_id": "basic_melee",
        "enemy_type": EnemyType.UNDEAD.value,
        "traits": ["spirit", "undead", "minion", "ash"],
        "weapon_loadout": ["unarmed"],
        "active_weapon": "unarmed",
        "auto_opportunity_attack": False,
    },
)


__all__ = ["AshCinder", "META"]
