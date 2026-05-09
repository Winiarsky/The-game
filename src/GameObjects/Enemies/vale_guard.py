from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class ValeGuard(BasicEnemy):
    """Level 0 guard built as a PF2e low-threat human soldier."""

    name: str = "Vale Guard"
    level: int = 0
    hp: int = 16
    max_hp: int | None = 16
    ac: int = 16
    initiative_bonus: int = 4
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 7
    strength: int = 2
    dex_mod: int = 1
    fortitude_bonus: int = 5
    reflex_bonus: int = 3
    will_bonus: int = 2
    perception_bonus: int = 4
    athletics_bonus: int = 5
    intimidation_bonus: int = 4
    stealth_bonus: int = 2
    behavior_id: str | None = "basic_melee"
    enemy_type: EnemyType | str = EnemyType.HUMAN
    traits: tuple[str, ...] = ("human", "humanoid", "guard")
    languages: tuple[str, ...] = ("Common",)
    weapon_loadout: tuple[str, ...] = ("spear", "shortbow")
    armor_loadout: tuple[str, ...] = ("chain_shirt",)
    active_weapon: str | None = "spear"
    special_actions: tuple[str, ...] = ()
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = False

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "line_guard", "hold_chokepoints": True, "protects": "mill_enforcer"}
        if self.awareness_profile is None:
            self.awareness_profile = {
                "awareness_range_feet": 35,
                "move_trigger_threshold": 0.70,
                "interaction_trigger_threshold": 0.25,
                "spell_trigger_threshold": 0.45,
                "stealth_fail_trigger_threshold": 0.30,
            }
        super().__post_init__()


META = GameObjectMeta(
    object_id="vale_guard",
    label="Vale Guard",
    color="#6c4a32",
    category="Enemies",
    placement="cell",
    description="Level 0 human guard for Ashen Oath; defensive spear line, PF2e low-threat numbers.",
    logic_cls=ValeGuard,
    default_config={
        "name": "Vale Guard",
        "level": 0,
        "hp": 16,
        "max_hp": 16,
        "ac": 16,
        "initiative_bonus": 4,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 7,
        "strength": 2,
        "dex_mod": 1,
        "fortitude_bonus": 5,
        "reflex_bonus": 3,
        "will_bonus": 2,
        "perception_bonus": 4,
        "athletics_bonus": 5,
        "intimidation_bonus": 4,
        "stealth_bonus": 2,
        "behavior_id": "basic_melee",
        "enemy_type": EnemyType.HUMAN.value,
        "traits": ["human", "humanoid", "guard"],
        "languages": ["Common"],
        "weapon_loadout": ["spear", "shortbow"],
        "armor_loadout": ["chain_shirt"],
        "active_weapon": "spear",
        "auto_opportunity_attack": False,
        "ai_profile": {"role": "line_guard", "hold_chokepoints": True, "protects": "mill_enforcer"},
    },
)


__all__ = ["ValeGuard", "META"]
