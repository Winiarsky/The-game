"""One-use Wisdom-save penalties, separate from source damage and expiry."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from dnd_board_game.rules import ActiveEffect, RollMode

MIND_BREAK_WISDOM = "nimra_mind_break_wisdom"


class CompletedSavingThrow(Protocol):
    actor_id: str
    ability: str


def has_wisdom_save_penalty(actor_id: str, ability: str, effects: Sequence[object]) -> bool:
    return ability == "wisdom" and any(
        getattr(effect, "actor_id", "") == actor_id
        and getattr(effect, "kind", "") == MIND_BREAK_WISDOM
        for effect in effects
    )


def saving_effect_roll_mode(
    actor_id: str, ability: str, effects: Sequence[object], mode: RollMode = RollMode.NORMAL,
) -> RollMode:
    if not has_wisdom_save_penalty(actor_id, ability, effects):
        return mode
    return RollMode.NORMAL if mode == RollMode.ADVANTAGE else RollMode.DISADVANTAGE


def consume_saving_effects(
    effects: tuple[ActiveEffect, ...], saving_throw: CompletedSavingThrow,
) -> tuple[ActiveEffect, ...]:
    """Call only after a real save, before applying its new on-failure effects."""
    if saving_throw.ability != "wisdom":
        return effects
    return tuple(effect for effect in effects if not (
        effect.actor_id == str(saving_throw.actor_id) and effect.kind == MIND_BREAK_WISDOM
    ))
