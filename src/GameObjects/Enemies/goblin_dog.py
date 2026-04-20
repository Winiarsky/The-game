from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy


@dataclass(eq=False)
class GoblinDog(BasicEnemy):
    name: str = "Goblin Dog"
    hp: int = 17
    max_hp: int | None = 17
    ac: int = 17
    initiative_bonus: int = 6
    distance: int = 40
    base_speed_feet: int | None = 40
    attack_bonus: int = 9
    strength: int = 3
    dex_mod: int = 2
    fortitude_bonus: int = 8
    reflex_bonus: int = 8
    will_bonus: int = 5
    perception_bonus: int = 6
    athletics_bonus: int = 6
    stealth_bonus: int = 7
    behavior_id: str | None = "goblin_dog_hunter"
    enemy_type: str = "animal"
    traits: tuple[str, ...] = ("goblin_dog", "animal", "medium")
    weapon_loadout: tuple[str, ...] = ("jaws",)
    active_weapon: str | None = "jaws"
    special_actions: tuple[str, ...] = ("goblin_dog_scratch",)
    special_reactions: tuple[str, ...] = ("buck", "juke")
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = False

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {"role": "hunter", "flee_threshold": 0.4}
        if self.awareness_profile is None:
            self.awareness_profile = {
                "awareness_range_feet": 40,
                "move_trigger_threshold": 0.90,
                "interaction_trigger_threshold": 0.55,
                "spell_trigger_threshold": 0.75,
                "stealth_fail_trigger_threshold": 0.85,
            }
        super().__post_init__()


META = GameObjectMeta(
    object_id="goblin_dog",
    label="Goblin Dog",
    color="#7a5d2a",
    category="Enemies",
    placement="cell",
    description="Gobliński pies polujący na osłabione i samotne cele, uciekający po zranieniu.",
    logic_cls=GoblinDog,
    default_config={
        "name": "Goblin Dog",
        "hp": 17,
        "max_hp": 17,
        "ac": 17,
        "initiative_bonus": 6,
        "distance": 40,
        "base_speed_feet": 40,
        "attack_bonus": 9,
        "strength": 3,
        "dex_mod": 2,
        "fortitude_bonus": 8,
        "reflex_bonus": 8,
        "will_bonus": 5,
        "perception_bonus": 6,
        "athletics_bonus": 6,
        "stealth_bonus": 7,
        "behavior_id": "goblin_dog_hunter",
        "enemy_type": "animal",
        "traits": ["goblin_dog", "animal", "medium"],
        "weapon_loadout": ["jaws"],
        "active_weapon": "jaws",
        "special_actions": ["goblin_dog_scratch"],
        "special_reactions": ["buck", "juke"],
        "auto_opportunity_attack": False,
        "ai_profile": {"role": "hunter", "flee_threshold": 0.4},
        "awareness_profile": {
            "awareness_range_feet": 40,
            "move_trigger_threshold": 0.9,
            "interaction_trigger_threshold": 0.55,
            "spell_trigger_threshold": 0.75,
            "stealth_fail_trigger_threshold": 0.85
        },
    },
)


__all__ = ["GoblinDog", "META"]
