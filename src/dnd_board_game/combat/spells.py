from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Iterable, Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollModifier,
    RollModifierType,
    ability_modifier,
    resolve_d20_roll,
    resolve_saving_throw,
)
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear


class SpellAreaShape(StrEnum):
    RADIUS = "radius"
    LINE = "line"
    CONE = "cone"


@dataclass(frozen=True, slots=True)
class SpellArea:
    shape: SpellAreaShape
    radius_feet: int = 0
    length_feet: int = 0
    width_feet: int = 5


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


@dataclass(frozen=True, slots=True)
class SpellSaveResult:
    actor_id: str
    actor_name: str
    ability: str
    dc: int
    natural_roll: int
    modifier: int
    total: int
    success: bool
    damage_multiplier: float

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "ability": self.ability,
            "ability_label": ability_label_pl(self.ability),
            "dc": self.dc,
            "natural_roll": self.natural_roll,
            "modifier": self.modifier,
            "total": self.total,
            "success": self.success,
            "damage_multiplier": self.damage_multiplier,
        }


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
        return _line_positions(board, origin, direction, max(0, area.length_feet // 5))
    if area.shape == SpellAreaShape.CONE:
        return _cone_positions(board, origin, direction, max(0, area.length_feet // 5))
    raise ValueError("Directional area requires a line or cone spell area.")


def actors_in_area(actors: Sequence[Actor], positions: Iterable[Coordinate], caster: Actor) -> tuple[Actor, ...]:
    area = frozenset(positions)
    return tuple(
        actor
        for actor in actors
        if actor.id != caster.id and not actor.is_defeated() and actor.faction != caster.faction and actor.position in area
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
) -> SpellSaveResult:
    modifier = ability_modifier_for_actor(actor, ability)
    request = D20RollRequest(
        modifiers=(
            RollModifier(
                f"Modyfikator {ability_label_pl(ability)}",
                modifier,
                RollModifierType.ABILITY,
                stacking_key=f"ability:{ability}",
            ),
        )
    )
    roll = resolve_d20_roll(D20RollInput(request, int(natural_roll)))
    check = resolve_saving_throw(roll, int(dc))
    return SpellSaveResult(
        actor_id=str(actor.id),
        actor_name=actor.name,
        ability=ability,
        dc=int(dc),
        natural_roll=roll.natural_roll,
        modifier=modifier,
        total=roll.total,
        success=check.success,
        damage_multiplier=spell_save_damage_multiplier(check.success, damage_on_success),
    )


def spell_save_damage_multiplier(success: bool, damage_on_success: str) -> float:
    if not success:
        return 1.0
    if damage_on_success == "half":
        return 0.5
    return 0.0


def apply_save_damage_amount(base_damage: int, save: SpellSaveResult | None) -> int:
    if save is None:
        return max(0, int(base_damage))
    return max(0, int(int(base_damage) * save.damage_multiplier))


def ability_modifier_for_actor(actor: Actor, ability: str) -> int:
    if not hasattr(actor.ability_scores, ability):
        raise ValueError(f"Nieznana cecha rzutu obronnego: {ability}.")
    return ability_modifier(int(getattr(actor.ability_scores, ability)))


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


def _line_positions(board: BoardState, origin: Coordinate, direction: tuple[int, int], steps: int) -> tuple[Coordinate, ...]:
    dx, dy = direction
    positions: list[Coordinate] = []
    for step in range(1, steps + 1):
        position = Coordinate(origin.col + dx * step, origin.row + dy * step)
        if not _in_bounds(board, position):
            break
        if not line_of_sight_clear(board, origin, position):
            break
        positions.append(position)
    return tuple(positions)


def _cone_positions(board: BoardState, origin: Coordinate, direction: tuple[int, int], steps: int) -> tuple[Coordinate, ...]:
    dx, dy = direction
    positions: set[Coordinate] = set()
    for step in range(1, steps + 1):
        width = step - 1
        for side in range(-width, width + 1):
            if dx == 0:
                position = Coordinate(origin.col + side, origin.row + dy * step)
            elif dy == 0:
                position = Coordinate(origin.col + dx * step, origin.row + side)
            else:
                position = Coordinate(origin.col + dx * step - dy * side, origin.row + dy * step + dx * side)
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
