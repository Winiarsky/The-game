from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.actors import Actor
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


def actor_as_combat_target(actor: Actor) -> CombatTarget:
    return CombatTarget(
        id=str(actor.id),
        name=actor.name,
        position=actor.position,
        ac=actor.ac,
        hp=actor.hp,
        target_type=CombatTargetType.ACTOR,
        visibility=CombatTargetVisibility.VISIBLE,
        attackable=not actor.is_defeated(),
    )


def target_is_defeated(target: CombatTarget) -> bool:
    return target.hp <= 0


def is_public_attack_target(target: CombatTarget) -> bool:
    return target.attackable and target.visibility == CombatTargetVisibility.VISIBLE and not target_is_defeated(target)
