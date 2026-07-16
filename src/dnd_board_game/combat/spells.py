from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Iterable, Sequence

from dnd_board_game.actors import Actor, Faction, saving_throw_roll_modifiers
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    SaveDamageOnSuccess,
    SavingThrowRequest,
    SavingThrowResult,
    RollModifier,
    resolve_d20_roll,
    resolve_saving_throw_request,
    save_damage_multiplier,
)
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear


class SpellAreaShape(StrEnum):
    RADIUS = "radius"
    LINE = "line"
    CONE = "cone"


class SpellAreaTargetMode(StrEnum):
    ALL_CREATURES = "all_creatures"
    ENEMIES = "enemies"
    ALLIES = "allies"


@dataclass(frozen=True, slots=True)
class SpellArea:
    shape: SpellAreaShape
    radius_feet: int = 0
    length_feet: int = 0
    width_feet: int = 5
    target_mode: SpellAreaTargetMode = SpellAreaTargetMode.ALL_CREATURES

    def __post_init__(self) -> None:
        if self.shape == SpellAreaShape.RADIUS:
            _require_positive_grid_measure(self.radius_feet, "radius_feet")
        else:
            _require_positive_grid_measure(self.length_feet, "length_feet")
        _require_positive_grid_measure(self.width_feet, "width_feet")


@dataclass(frozen=True, slots=True)
class SpellSlotState:
    level: int
    remaining: int
    maximum: int


@dataclass(frozen=True, slots=True)
class SpellResourceUse:
    actor_before: Actor
    actor_after: Actor
    spell_level: int
    consumed: bool


SpellSaveResult = SavingThrowResult


def grid_distance_feet(a: Coordinate, b: Coordinate) -> int:
    dx = abs(a.col - b.col)
    dy = abs(a.row - b.row)
    diagonal = min(dx, dy)
    straight = abs(dx - dy)
    return 5 * (diagonal + diagonal // 2) + straight * 5


def direction_from_adjacent(origin: Coordinate, target: Coordinate) -> tuple[int, int] | None:
    dx = target.col - origin.col
    dy = target.row - origin.row
    if dx == 0 and dy == 0:
        return None
    if abs(dx) > 1 or abs(dy) > 1:
        return None
    return (_sign(dx), _sign(dy))


def direction_anchor_positions(board: BoardState, origin: Coordinate) -> tuple[Coordinate, ...]:
    anchors: list[Coordinate] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            position = Coordinate(origin.col + dx, origin.row + dy)
            if _in_bounds(board, position):
                anchors.append(position)
    return tuple(sorted(anchors, key=lambda position: (position.row, position.col)))


def legal_area_centers(board: BoardState, origin: Coordinate, range_feet: int) -> tuple[Coordinate, ...]:
    centers: list[Coordinate] = []
    for position in _all_board_positions(board):
        if grid_distance_feet(origin, position) <= range_feet and line_of_sight_clear(board, origin, position):
            centers.append(position)
    return tuple(centers)


def area_positions_for_center(board: BoardState, center: Coordinate, area: SpellArea) -> tuple[Coordinate, ...]:
    if area.shape != SpellAreaShape.RADIUS:
        raise ValueError("Centered area requires a radius spell area.")
    positions = [
        position
        for position in _all_board_positions(board)
        if grid_distance_feet(center, position) <= max(0, area.radius_feet)
        and line_of_sight_clear(board, center, position)
    ]
    return tuple(sorted(positions, key=lambda position: (position.row, position.col)))


def area_positions_for_direction(
    board: BoardState,
    origin: Coordinate,
    direction_target: Coordinate,
    area: SpellArea,
) -> tuple[Coordinate, ...]:
    direction = direction_from_adjacent(origin, direction_target)
    if direction is None:
        raise ValueError("Kierunek czaru musi być wskazany sąsiednim polem.")
    if area.shape == SpellAreaShape.LINE:
        return _line_positions(
            board,
            origin,
            direction,
            max(0, area.length_feet // 5),
            max(1, area.width_feet // 5),
        )
    if area.shape == SpellAreaShape.CONE:
        return _cone_positions(board, origin, direction, max(0, area.length_feet // 5))
    raise ValueError("Directional area requires a line or cone spell area.")


def actors_in_area(
    actors: Sequence[Actor],
    positions: Iterable[Coordinate],
    caster: Actor,
    target_mode: SpellAreaTargetMode = SpellAreaTargetMode.ALL_CREATURES,
) -> tuple[Actor, ...]:
    area = frozenset(positions)
    return tuple(
        actor
        for actor in actors
        if not actor.is_defeated()
        and actor.position in area
        and _matches_area_target_mode(actor, caster, target_mode)
    )


def can_consume_spell_resource(actor: Actor, spell_level: int) -> bool:
    if spell_level <= 0:
        return True
    return any(slot.level == spell_level and slot.remaining > 0 for slot in actor.spell_slots)


def consume_spell_resource(actor: Actor, spell_level: int) -> SpellResourceUse:
    if spell_level <= 0:
        return SpellResourceUse(actor, actor, spell_level, False)
    slots = list(actor.spell_slots)
    for index, slot in enumerate(slots):
        if slot.level == spell_level:
            if slot.remaining <= 0:
                raise ValueError(f"Brak slotów czaru poziomu {spell_level}.")
            slots[index] = replace(slot, remaining=slot.remaining - 1)
            return SpellResourceUse(actor, replace(actor, spell_slots=tuple(slots)), spell_level, True)
    raise ValueError(f"Aktor nie ma slotów czaru poziomu {spell_level}.")


def resolve_spell_save(
    actor: Actor,
    *,
    ability: str,
    dc: int,
    natural_roll: int,
    damage_on_success: str = "none",
    situational_modifiers: Sequence[RollModifier] = (),
) -> SpellSaveResult:
    request = SavingThrowRequest(
        ability=ability,
        dc=int(dc),
        source_label="czar",
        dc_source_label="ST czaru",
        damage_on_success=SaveDamageOnSuccess(damage_on_success),
    )
    return resolve_actor_saving_throw(
        actor,
        request,
        natural_roll=natural_roll,
        situational_modifiers=situational_modifiers,
    )


def resolve_actor_saving_throw(
    actor: Actor,
    saving_throw: SavingThrowRequest,
    *,
    natural_roll: int,
    situational_modifiers: Sequence[RollModifier] = (),
) -> SavingThrowResult:
    roll_request = D20RollRequest(
        modifiers=(
            *saving_throw_roll_modifiers(actor, saving_throw.ability),
            *situational_modifiers,
        )
    )
    roll = resolve_d20_roll(D20RollInput(roll_request, int(natural_roll)))
    return resolve_saving_throw_request(
        saving_throw,
        actor_id=str(actor.id),
        actor_name=actor.name,
        roll=roll,
    )


def spell_save_damage_multiplier(success: bool, damage_on_success: str) -> float:
    return save_damage_multiplier(success, damage_on_success)


def apply_save_damage_amount(base_damage: int, save: SpellSaveResult | None) -> int:
    if save is None:
        return max(0, int(base_damage))
    return max(0, int(int(base_damage) * save.damage_multiplier))


def ability_label_pl(ability: str) -> str:
    labels = {
        "strength": "Siła",
        "dexterity": "Zręczność",
        "constitution": "Kondycja",
        "intelligence": "Inteligencja",
        "wisdom": "Mądrość",
        "charisma": "Charyzma",
    }
    return labels.get(ability, ability)


def _line_positions(
    board: BoardState,
    origin: Coordinate,
    direction: tuple[int, int],
    steps: int,
    width_tiles: int,
) -> tuple[Coordinate, ...]:
    dx, dy = direction
    perpendicular = (-dy, dx)
    positions: set[Coordinate] = set()
    for step in range(1, steps + 1):
        for offset in _centered_offsets(width_tiles):
            position = Coordinate(
                origin.col + dx * step + perpendicular[0] * offset,
                origin.row + dy * step + perpendicular[1] * offset,
            )
            if _in_bounds(board, position) and line_of_sight_clear(
                board,
                origin,
                position,
            ):
                positions.add(position)
    return tuple(sorted(positions, key=lambda position: (position.row, position.col)))


def _cone_positions(board: BoardState, origin: Coordinate, direction: tuple[int, int], steps: int) -> tuple[Coordinate, ...]:
    dx, dy = direction
    perpendicular = (-dy, dx)
    positions: set[Coordinate] = set()
    for step in range(1, steps + 1):
        for offset in _centered_offsets(step):
            position = Coordinate(
                origin.col + dx * step + perpendicular[0] * offset,
                origin.row + dy * step + perpendicular[1] * offset,
            )
            if _in_bounds(board, position) and line_of_sight_clear(board, origin, position):
                positions.add(position)
    return tuple(sorted(positions, key=lambda position: (position.row, position.col)))


def _all_board_positions(board: BoardState) -> tuple[Coordinate, ...]:
    return tuple(
        Coordinate(col, row)
        for row in range(board.dimensions.rows)
        for col in range(board.dimensions.cols)
    )


def _in_bounds(board: BoardState, position: Coordinate) -> bool:
    return 0 <= position.col < board.dimensions.cols and 0 <= position.row < board.dimensions.rows


def _sign(value: int) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def _centered_offsets(width_tiles: int) -> range:
    before = width_tiles // 2
    after = width_tiles - before
    return range(-before, after)


def _matches_area_target_mode(
    actor: Actor,
    caster: Actor,
    target_mode: SpellAreaTargetMode,
) -> bool:
    if target_mode == SpellAreaTargetMode.ALL_CREATURES:
        return True
    if target_mode == SpellAreaTargetMode.ENEMIES:
        return actor.faction not in {caster.faction, Faction.NEUTRAL}
    return actor.faction == caster.faction


def _require_positive_grid_measure(value: int, field: str) -> None:
    if value <= 0 or value % 5 != 0:
        raise ValueError(f"Spell area {field} must be a positive multiple of 5 feet.")
