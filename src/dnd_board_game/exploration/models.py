from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneAbilityCheck, SceneFlags, SetupVisibility, scene_flag, set_scene_flag
from dnd_board_game.hardware import LedColor, LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import D20RollInput, D20RollRequest, D20RollResult, resolve_ability_check, resolve_d20_roll
from dnd_board_game.world import Coordinate


class SceneMode(StrEnum):
    ENCOUNTER = "encounter"
    EXPLORATION = "exploration"


class ExplorationOptionKind(StrEnum):
    MESSAGE = "message"
    SEARCH = "search"
    CHECK = "check"


@dataclass(frozen=True, slots=True)
class ExplorationOption:
    id: str
    label: str
    kind: ExplorationOptionKind
    color: tuple[int, int, int]
    description: str = ""
    message: str = ""
    success_message: str = ""
    failure_message: str = ""
    ability_check: SceneAbilityCheck | None = None
    allow_help: bool = False
    success_flag: str | None = None
    failure_flag: str | None = None
    reveals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExplorationZone:
    id: str
    name: str
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    anchor_position: Coordinate | None = None
    description: str = ""
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    available_if_flag: str | None = None
    available_if_value: object = True
    options: tuple[ExplorationOption, ...] = ()
    adjacent_zone_ids: tuple[str, ...] = ()
    search_dc: int | None = None
    search_ability: str = "wisdom"
    search_skill: str | None = "perception"
    search_reveals: tuple[str, ...] = ()
    search_success_flag: str | None = None
    search_failure_flag: str | None = None

    @property
    def marker_position(self) -> Coordinate:
        if self.anchor_position is not None:
            return self.anchor_position
        if not self.positions:
            raise ValueError(f"Exploration zone {self.id} has no positions.")
        return self.positions[0]


@dataclass(frozen=True, slots=True)
class ExplorationPoint:
    id: str
    name: str
    zone_id: str
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    description: str = ""


@dataclass(frozen=True, slots=True)
class PartyPosition:
    zone_id: str
    marker_position: Coordinate | None = None


@dataclass(frozen=True, slots=True)
class ExplorationState:
    zones: tuple[ExplorationZone, ...]
    points: tuple[ExplorationPoint, ...]
    party_position: PartyPosition
    flags: SceneFlags = SceneFlags()
    exhausted_search_zones: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PartyCheckInput:
    actor: Actor
    natural_roll: int
    request: D20RollRequest


@dataclass(frozen=True, slots=True)
class PartyCheckResult:
    rolls: tuple[tuple[Actor, D20RollResult], ...]
    winner: Actor
    winning_roll: D20RollResult
    dc: int
    success: bool


@dataclass(frozen=True, slots=True)
class SearchResult:
    state: ExplorationState
    party_check: PartyCheckResult
    revealed_points: tuple[ExplorationPoint, ...]
    message: str


def visible_exploration_zones(zones: tuple[ExplorationZone, ...]) -> tuple[ExplorationZone, ...]:
    return tuple(zone for zone in zones if zone.visibility == SetupVisibility.VISIBLE and zone.positions)


def available_exploration_zones(state: ExplorationState) -> tuple[ExplorationZone, ...]:
    return tuple(zone for zone in visible_exploration_zones(state.zones) if zone_is_available(state, zone))


def zone_is_available(state: ExplorationState, zone: ExplorationZone) -> bool:
    if zone.available_if_flag is None:
        return True
    return scene_flag(state.flags, zone.available_if_flag) == zone.available_if_value


def visible_exploration_points(points: tuple[ExplorationPoint, ...]) -> tuple[ExplorationPoint, ...]:
    return tuple(point for point in points if point.visibility == SetupVisibility.VISIBLE and point.positions)


def zone_for_position(zones: tuple[ExplorationZone, ...], position: Coordinate) -> ExplorationZone | None:
    for zone in zones:
        if position in zone.positions:
            return zone
    return None


def set_party_zone(state: ExplorationState, zone: ExplorationZone) -> ExplorationState:
    return replace(state, party_position=PartyPosition(zone.id, zone.marker_position))


def resolve_party_check(inputs: tuple[PartyCheckInput, ...], dc: int) -> PartyCheckResult:
    if not inputs:
        raise ValueError("Party check requires at least one roll.")
    rolls = tuple((item.actor, resolve_d20_roll(D20RollInput(item.request, item.natural_roll))) for item in inputs)
    winner, winning_roll = max(rolls, key=lambda item: (item[1].total, item[1].natural_roll, item[0].name))
    return PartyCheckResult(rolls, winner, winning_roll, dc, resolve_ability_check(winning_roll, dc).success)


def resolve_zone_search(
    state: ExplorationState,
    zone: ExplorationZone,
    inputs: tuple[PartyCheckInput, ...],
) -> SearchResult:
    if zone.id in state.exhausted_search_zones:
        raise ValueError(f"Zone {zone.id} has already been searched.")
    if zone.search_dc is None:
        raise ValueError(f"Zone {zone.id} has no search configured.")
    party_check = resolve_party_check(inputs, zone.search_dc)
    exhausted = tuple(sorted((*state.exhausted_search_zones, zone.id)))
    flags = state.flags
    revealed: tuple[ExplorationPoint, ...] = ()
    points = state.points
    if party_check.success:
        if zone.search_success_flag:
            flags = set_scene_flag(flags, zone.search_success_flag, True)
        revealed_ids = set(zone.search_reveals)
        points = tuple(
            replace(point, visibility=SetupVisibility.VISIBLE) if point.id in revealed_ids else point
            for point in state.points
        )
        revealed = tuple(point for point in points if point.id in revealed_ids)
        if revealed:
            message = f"Sukces. {party_check.winner.name} osiąga wynik {party_check.winning_roll.total}. Odkrywacie ukryty element w strefie: {zone.name}."
        else:
            message = f"Sukces. {party_check.winner.name} osiąga wynik {party_check.winning_roll.total}. Uważnie sprawdzacie strefę: {zone.name}."
    else:
        if zone.search_failure_flag:
            flags = set_scene_flag(flags, zone.search_failure_flag, True)
        message = f"Porażka. Najwyższy wynik to {party_check.winning_roll.total}. Nie znajdujecie nic nowego w strefie: {zone.name}."
    return SearchResult(replace(state, points=points, flags=flags, exhausted_search_zones=exhausted), party_check, revealed, message)


def dim_color(color: tuple[int, int, int], factor: float = 0.3) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(round(component * factor)))) for component in color)


def exploration_setup_feedback(
    positions: tuple[Coordinate, ...],
    color: tuple[int, int, int],
    anchor_position: Coordinate | None = None,
) -> LedFeedback:
    if not positions:
        return LedFeedback()
    anchor = anchor_position if anchor_position in positions else None
    area_positions = tuple(position for position in positions if position != anchor)
    frames: list[LedFrame] = []
    if area_positions:
        frames.append(LedFrame(area_positions, dim_color(color), LedRole.DESTINATION))
    if anchor is not None:
        frames.append(LedFrame((anchor,), color, LedRole.DESTINATION))
    if anchor is None:
        frames.append(LedFrame(positions, dim_color(color), LedRole.DESTINATION))
    return LedFeedback(tuple(frames))


def exploration_zone_feedback(state: ExplorationState) -> LedFeedback:
    frames: list[LedFrame] = []
    for zone in available_exploration_zones(state):
        area_positions = tuple(position for position in zone.positions if position != zone.marker_position)
        if area_positions:
            frames.append(LedFrame(area_positions, dim_color(zone.color), LedRole.DESTINATION))
        frames.append(LedFrame((zone.marker_position,), zone.color, LedRole.DESTINATION))
    current = next((zone for zone in state.zones if zone.id == state.party_position.zone_id), None)
    if current is not None:
        frames.append(LedFrame((current.marker_position,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR))
    for point in visible_exploration_points(state.points):
        frames.append(LedFrame(point.positions, point.color, LedRole.DESTINATION))
    return LedFeedback(tuple(frames))


def party_position_feedback(state: ExplorationState) -> LedFeedback:
    current = next((zone for zone in state.zones if zone.id == state.party_position.zone_id), None)
    if current is None:
        return LedFeedback()
    return LedFeedback((LedFrame((current.marker_position,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),))


def option_feedback(zone: ExplorationZone, option: ExplorationOption) -> LedFeedback:
    area_positions = tuple(position for position in zone.positions if position != zone.marker_position)
    frames: list[LedFrame] = []
    if area_positions:
        frames.append(LedFrame(area_positions, dim_color(zone.color), LedRole.DESTINATION))
    frames.append(LedFrame((zone.marker_position,), option.color, LedRole.DESTINATION))
    return LedFeedback(tuple(frames))
