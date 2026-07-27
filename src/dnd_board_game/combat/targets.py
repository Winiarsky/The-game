from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.actors import Actor
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.rules import ActiveEffect
from dnd_board_game.world import Coordinate


class CombatTargetType(StrEnum):
    ACTOR = "actor"
    OBJECT = "object"
    TERRAIN = "terrain"
    INTERACTABLE = "interactable"


class CombatTargetVisibility(StrEnum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    CONDITIONAL = "conditional"


@dataclass(frozen=True, slots=True)
class CombatTarget:
    id: str
    name: str
    position: Coordinate
    ac: int
    hp: int
    target_type: CombatTargetType
    visibility: CombatTargetVisibility = CombatTargetVisibility.VISIBLE
    attackable: bool = True
    max_hp: int = 0
    temp_hp: int = 0
    defeated: bool = False
    unconscious: bool = False

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            object.__setattr__(self, "max_hp", max(0, self.hp))


def combat_effect_armor_class_bonus(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> int:
    return sum(
        effect.value
        for effect in active_effects
        if effect.actor_id == str(actor.id)
        and effect.kind == "spell_ac_bonus"
    )


def combat_armor_class(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> int:
    return effective_armor_class(actor) + combat_effect_armor_class_bonus(
        actor,
        active_effects,
    )


def actor_as_combat_target(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> CombatTarget:
    return CombatTarget(
        id=str(actor.id),
        name=actor.name,
        position=actor.position,
        ac=combat_armor_class(actor, active_effects),
        hp=actor.hp,
        target_type=CombatTargetType.ACTOR,
        visibility=CombatTargetVisibility.VISIBLE,
        attackable=not actor.is_dead(),
        max_hp=actor.max_hp,
        temp_hp=actor.temp_hp,
        defeated=actor.is_defeated(),
        unconscious=actor.is_unconscious(),
    )


def target_is_defeated(target: CombatTarget) -> bool:
    return target.hp <= 0


def is_public_attack_target(target: CombatTarget) -> bool:
    return target.attackable and target.visibility == CombatTargetVisibility.VISIBLE
