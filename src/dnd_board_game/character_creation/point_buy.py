"""D&D 5e (2014) point-buy rules used by the character creator."""

from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.actors import AbilityScores

from .models import ABILITY_IDS


POINT_BUY_BUDGET = 27
POINT_BUY_MINIMUM = 8
POINT_BUY_MAXIMUM = 15
POINT_BUY_COSTS = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9,
}


@dataclass(frozen=True, slots=True)
class PointBuySummary:
    spent: int
    remaining: int
    scores_in_range: bool

    @property
    def complete(self) -> bool:
        return self.scores_in_range and self.remaining == 0


def summarize_point_buy(scores: AbilityScores) -> PointBuySummary:
    values = tuple(getattr(scores, ability_id) for ability_id in ABILITY_IDS)
    scores_in_range = all(value in POINT_BUY_COSTS for value in values)
    spent = (
        sum(POINT_BUY_COSTS[value] for value in values)
        if scores_in_range
        else 0
    )
    return PointBuySummary(
        spent=spent,
        remaining=POINT_BUY_BUDGET - spent,
        scores_in_range=scores_in_range,
    )


__all__ = [
    "POINT_BUY_BUDGET",
    "POINT_BUY_COSTS",
    "POINT_BUY_MAXIMUM",
    "POINT_BUY_MINIMUM",
    "PointBuySummary",
    "summarize_point_buy",
]
