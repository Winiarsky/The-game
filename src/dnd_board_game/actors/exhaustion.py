"""D&D 5e 2014 exhaustion consequences shared by travel and combat."""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum

from dnd_board_game.rules.dice import (
    D20RollRequest,
    RollMode,
    RollModifier,
    RollModifierType,
)

from .models import Actor, DeathSaveState


class ExhaustionRollKind(StrEnum):
    ABILITY_CHECK = "ability_check"
    ATTACK = "attack"
    SAVING_THROW = "saving_throw"


def increase_exhaustion(actor: Actor, levels: int = 1) -> Actor:
    if levels < 0:
        raise ValueError("Exhaustion increase cannot be negative.")
    level = min(6, actor.exhaustion_level + levels)
    if level < 6:
        return replace(actor, exhaustion_level=level)
    return replace(
        actor,
        exhaustion_level=6,
        hp=0,
        death_saves=(
            DeathSaveState(dead=True)
            if actor.uses_death_saves
            else actor.death_saves
        ),
    )


def reduce_exhaustion(actor: Actor, levels: int = 1) -> Actor:
    if levels < 0:
        raise ValueError("Exhaustion reduction cannot be negative.")
    return replace(
        actor,
        exhaustion_level=max(0, actor.exhaustion_level - levels),
    )


def effective_max_hit_points(actor: Actor) -> int:
    if actor.exhaustion_level >= 4:
        return actor.max_hp // 2
    return actor.max_hp


def exhaustion_disadvantages(
    actor: Actor,
    kind: ExhaustionRollKind,
) -> bool:
    if kind == ExhaustionRollKind.ABILITY_CHECK:
        return actor.exhaustion_level >= 1
    return actor.exhaustion_level >= 3


def apply_exhaustion_to_roll_request(
    actor: Actor,
    request: D20RollRequest,
    kind: ExhaustionRollKind,
) -> D20RollRequest:
    if not exhaustion_disadvantages(actor, kind):
        return request
    stacking_key = f"exhaustion:{kind.value}"
    if any(modifier.stacking_key == stacking_key for modifier in request.modifiers):
        return request
    mode = (
        RollMode.NORMAL
        if request.mode == RollMode.ADVANTAGE
        else RollMode.DISADVANTAGE
    )
    return D20RollRequest(
        mode=mode,
        modifiers=(
            *request.modifiers,
            RollModifier(
                "Exhaustion",
                0,
                RollModifierType.SITUATIONAL,
                stacking_key=stacking_key,
            ),
        ),
    )


__all__ = [
    "ExhaustionRollKind",
    "apply_exhaustion_to_roll_request",
    "effective_max_hit_points",
    "exhaustion_disadvantages",
    "increase_exhaustion",
    "reduce_exhaustion",
]
