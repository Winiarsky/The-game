"""Deterministic authored-world queries used by locating divinations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import copysign
from typing import Sequence

from dnd_board_game.world import Coordinate

from .models import ExplorationPoint


class DivinationTargetKind(StrEnum):
    ANIMAL = "animal"
    PLANT = "plant"
    OBJECT = "object"


@dataclass(frozen=True, slots=True)
class DivinationSearchResult:
    query: str
    point_id: str
    point_name: str
    kind: DivinationTargetKind
    position: Coordinate
    distance_feet: int
    direction: str


def locate_authored_target(
    points: Sequence[ExplorationPoint],
    *,
    query: str,
    allowed_kinds: frozenset[DivinationTargetKind],
    origin: Coordinate,
    maximum_distance_feet: int,
    blocked_by_lead: bool = False,
) -> DivinationSearchResult | None:
    """Locate the nearest matching authored target, including hidden points."""

    normalized = _normalize(query)
    if not normalized:
        raise ValueError("Podaj znany gatunek albo nazwę szukanego celu.")
    matches: list[tuple[int, ExplorationPoint, Coordinate]] = []
    for point in points:
        if point.divination_kind not in {kind.value for kind in allowed_kinds}:
            continue
        if blocked_by_lead and point.divination_lead_shielded:
            continue
        searchable = (_normalize(point.name), *(_normalize(tag) for tag in point.divination_tags))
        if normalized not in searchable:
            continue
        for position in point.positions:
            distance = max(
                abs(position.col - origin.col),
                abs(position.row - origin.row),
            ) * 5
            if distance <= maximum_distance_feet:
                matches.append((distance, point, position))
    if not matches:
        return None
    distance, point, position = min(
        matches,
        key=lambda entry: (entry[0], entry[1].id, entry[2]),
    )
    return DivinationSearchResult(
        query=query.strip(),
        point_id=point.id,
        point_name=point.name,
        kind=DivinationTargetKind(point.divination_kind),
        position=position,
        distance_feet=distance,
        direction=_direction(origin, position),
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _direction(origin: Coordinate, target: Coordinate) -> str:
    horizontal = int(copysign(1, target.col - origin.col)) if target.col != origin.col else 0
    vertical = int(copysign(1, target.row - origin.row)) if target.row != origin.row else 0
    labels = {
        (0, 0): "tutaj",
        (0, -1): "północ",
        (1, -1): "północny wschód",
        (1, 0): "wschód",
        (1, 1): "południowy wschód",
        (0, 1): "południe",
        (-1, 1): "południowy zachód",
        (-1, 0): "zachód",
        (-1, -1): "północny zachód",
    }
    return labels[(horizontal, vertical)]


__all__ = [
    "DivinationSearchResult",
    "DivinationTargetKind",
    "locate_authored_target",
]
