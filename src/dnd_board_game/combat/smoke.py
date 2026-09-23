"""Stationary smoke: a square hiding area with no automatic hidden state."""
from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from dnd_board_game.rules import ActiveEffect, D20RollRequest, RollMode
from dnd_board_game.world import BoardState, Coordinate


SMOKE_AREA_KIND = "smoke_screen_area"


def smoke_contains(position: Coordinate, active_effects: Sequence[ActiveEffect]) -> bool:
    """Concealment applies to any figure, regardless of the smoke owner's side."""
    return any(
        effect.kind == SMOKE_AREA_KIND
        and effect.anchor_position is not None
        and max(abs(position.col - effect.anchor_position.col),
                abs(position.row - effect.anchor_position.row)) <= 1
        for effect in active_effects
    )


def smoke_positions(board: BoardState, center: Coordinate) -> tuple[Coordinate, ...]:
    return tuple(
        Coordinate(col, row)
        for row in range(max(0, center.row - 1), min(board.dimensions.rows, center.row + 2))
        for col in range(max(0, center.col - 1), min(board.dimensions.cols, center.col + 2))
    )


def smoke_hide_request(request: D20RollRequest, position: Coordinate,
                       active_effects: Sequence[ActiveEffect]) -> D20RollRequest:
    if not smoke_contains(position, active_effects):
        return request
    return replace(request, mode=(RollMode.NORMAL if request.mode == RollMode.DISADVANTAGE
                                  else RollMode.ADVANTAGE))
