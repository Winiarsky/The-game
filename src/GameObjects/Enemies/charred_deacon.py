from __future__ import annotations

from dataclasses import dataclass

from GameObjects.base import GameObjectMeta
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Enemies.enemy_types import EnemyType


@dataclass(eq=False)
class CharredDeacon(BasicEnemy):
    """Boss spalonej kaplicy; podtrzymywany przez oltarz do czasu sealu."""

    name: str = "Spalony Diakon"
    level: int = 2
    hp: int = 34
    max_hp: int | None = 34
    ac: int = 17
    initiative_bonus: int = 7
    distance: int = 25
    base_speed_feet: int | None = 25
    attack_bonus: int = 10
    strength: int = 3
    dex_mod: int = 2
    fortitude_bonus: int = 7
    reflex_bonus: int = 5
    will_bonus: int = 8
    perception_bonus: int = 7
    athletics_bonus: int = 6
    intimidation_bonus: int = 9
    stealth_bonus: int = 4
    behavior_id: str | None = "charred_deacon_guardian"
    enemy_type: EnemyType | str = EnemyType.UNDEAD
    traits: tuple[str, ...] = ("spirit", "undead", "oathbound", "divine", "boss")
    languages: tuple[str, ...] = ("Common",)
    weapon_loadout: tuple[str, ...] = ("staff",)
    armor_loadout: tuple[str, ...] = ()
    active_weapon: str | None = "staff"
    special_actions: tuple[str, ...] = ("demoralize",)
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = None  # type: ignore[assignment]
    awareness_profile: dict[str, object] = None  # type: ignore[assignment]
    auto_opportunity_attack: bool = True
    encounter_role: str = "charred_deacon"

    def __post_init__(self):
        if self.ai_profile is None:
            self.ai_profile = {
                "role": "altar_guardian_controller",
                "protects": "charred_altar",
                "tactics": [
                    "protect_altar",
                    "punish_seal_attempts",
                    "block_statues_with_cinders",
                    "return_to_inner_zone",
                ],
                "abilities": [
                    "Ashen Crozier",
                    "Sermon of Embers",
                    "Popielny Chwyt",
                    "Call from the Ashes",
                    "Return to the Altar",
                    "Ostatnie Kazanie",
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

    def before_defeated_cleanup(self, game, *, source: str = "damage") -> bool:
        from burned_chapel_encounter import handle_deacon_defeat

        return bool(handle_deacon_defeat(game, self, source=source))

    def on_combat_turn_start(self, game, _combat=None) -> None:
        from burned_chapel_encounter import deacon_turn_start

        deacon_turn_start(game, self)


META = GameObjectMeta(
    object_id="charred_deacon",
    label="Spalony Diakon",
    color="#7f1d1d",
    category="Enemies",
    placement="cell",
    description="Boss spalonej kaplicy; nie mozna go zniszczyc, dopoki oltarz nie zostanie zablokowany.",
    logic_cls=CharredDeacon,
    default_config={
        "name": "Spalony Diakon",
        "level": 2,
        "hp": 34,
        "max_hp": 34,
        "ac": 17,
        "initiative_bonus": 7,
        "distance": 25,
        "base_speed_feet": 25,
        "attack_bonus": 10,
        "strength": 3,
        "dex_mod": 2,
        "fortitude_bonus": 7,
        "reflex_bonus": 5,
        "will_bonus": 8,
        "perception_bonus": 7,
        "athletics_bonus": 6,
        "intimidation_bonus": 9,
        "stealth_bonus": 4,
        "behavior_id": "charred_deacon_guardian",
        "enemy_type": EnemyType.UNDEAD.value,
        "traits": ["spirit", "undead", "oathbound", "divine", "boss"],
        "languages": ["Common"],
        "weapon_loadout": ["staff"],
        "active_weapon": "staff",
        "special_actions": ["demoralize"],
        "auto_opportunity_attack": True,
    },
)


__all__ = ["CharredDeacon", "META"]
