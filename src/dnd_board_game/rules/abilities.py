from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor


def ability_modifier(score: int) -> int:
    if score <= 0:
        raise ValueError("Ability score must be positive.")
    return (score - 10) // 2


def dexterity_modifier(actor: Actor) -> int:
    return ability_modifier(actor.ability_scores.dexterity)
