"""Operations for persistent, movable spell zones."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.rules import ActiveEffect
from dnd_board_game.world import BoardState, Coordinate

from .session import CombatState, current_actor, use_bonus_action, use_turn_action
from .spells import grid_distance_feet


@dataclass(frozen=True, slots=True)
class SpellZoneMoveResult:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    effect_before: ActiveEffect
    effect_after: ActiveEffect


def move_moonbeam_zone(
    state: CombatState,
    active_effects: Sequence[ActiveEffect],
    *,
    effect_id: str,
    destination: Coordinate,
    board: BoardState,
) -> SpellZoneMoveResult:
    """Spend the spell's action cost to move a persistent damage zone."""

    effect = next(
        (
            candidate
            for candidate in active_effects
            if candidate.id == effect_id
            and candidate.kind.startswith("ongoing_damage_zone:")
        ),
        None,
    )
    if effect is None or effect.anchor_position is None:
        raise ValueError("Nie znaleziono aktywnej strefy Księżycowego promienia.")
    caster = current_actor(state)
    if effect.source_actor_id != str(caster.id):
        raise ValueError("Tylko rzucający może przesunąć Księżycowy promień w swojej turze.")
    flaming_sphere = effect.object_id == "combat_action:flaming_sphere"
    label = effect.label or (
        "Płonąca kula" if flaming_sphere else "Księżycowy promień"
    )
    maximum_distance = 30 if flaming_sphere else 60
    if not board.in_bounds(destination):
        raise ValueError(f"Nowy środek {label} leży poza planszą.")
    if grid_distance_feet(effect.anchor_position, destination) > maximum_distance:
        raise ValueError(
            f"{label} można przesunąć najwyżej o {maximum_distance} ft."
        )
    action = use_bonus_action(state) if flaming_sphere else use_turn_action(state)
    if not action.accepted:
        raise ValueError(action.message)
    moved = replace(effect, anchor_position=destination)
    updated_effects = tuple(
        moved if candidate.id == effect.id else candidate
        for candidate in active_effects
    )
    return SpellZoneMoveResult(action.state, updated_effects, effect, moved)


__all__ = ["SpellZoneMoveResult", "move_moonbeam_zone"]
