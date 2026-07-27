from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Iterable, Sequence

from dnd_board_game.actors import (
    Actor,
    ExhaustionRollKind,
    Faction,
    apply_exhaustion_to_roll_request,
    saving_throw_roll_modifiers,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    SaveDamageOnSuccess,
    SavingThrowRequest,
    SavingThrowResult,
    SpellCastValidation,
    RollModifier,
    RollMode,
    resolve_d20_roll,
    resolve_saving_throw_request,
    save_damage_multiplier,
    available_spell_slot_levels,
    spell_is_accessible,
    validate_spell_cast,
)
from dnd_board_game.inventory import free_hand_count
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


def available_cast_levels(actor: Actor, spell_level: int) -> tuple[int, ...]:
    """Return legal slot levels, including higher-level slots used for upcasting."""
    return available_spell_slot_levels(actor.spell_slots, spell_level)


def actor_spell_cast_validation(
    actor: Actor,
    spell_id: str,
    *,
    cast_level: int | None = None,
    ritual: bool = False,
) -> SpellCastValidation | None:
    """Validate access, slot level, focus/material and somatic-hand requirements."""
    spell = next((candidate for candidate in actor.spells if candidate.id == spell_id), None)
    if spell is None:
        return None
    prepared = actor.spell_preparation
    accessible = spell_is_accessible(
        spell,
        actor.spell_access,
        prepared_spell_ids=prepared.prepared_spell_ids if prepared is not None else (),
        always_prepared_spell_ids=(
            prepared.always_prepared_spell_ids if prepared is not None else ()
        ),
    )
    if ritual and not accessible:
        accessible = any(
            profile.kind.value == "spellbook" and spell.id in profile.spell_ids
            for profile in actor.spell_access
        )
    if not accessible:
        return replace(
            validate_spell_cast(
                spell,
                slots=actor.spell_slots,
                inventory=actor.inventory,
                cast_level=cast_level,
                ritual=ritual,
            ),
            valid=False,
            errors=(f"Aktor nie ma dostępu do czaru {spell.name}.",),
        )
    allowed_focus_kinds = tuple(
        kind
        for profile in actor.spell_access
        if spell.id in profile.spell_ids
        for kind in profile.allowed_focus_kinds
    )
    return validate_spell_cast(
        spell,
        slots=actor.spell_slots,
        inventory=actor.inventory,
        cast_level=cast_level,
        allowed_focus_kinds=allowed_focus_kinds,
        has_free_hand=free_hand_count(actor.inventory) > 0,
        ritual=ritual,
    )


def can_consume_spell_resource(
    actor: Actor,
    spell_level: int,
    cast_level: int | None = None,
) -> bool:
    if spell_level <= 0:
        return True
    levels = available_cast_levels(actor, spell_level)
    return bool(levels) if cast_level is None else cast_level in levels


def consume_spell_resource(
    actor: Actor,
    spell_level: int,
    cast_level: int | None = None,
    spell_id: str | None = None,
    ritual: bool = False,
) -> SpellResourceUse:
    actor_after_components = actor
    if spell_id is not None:
        validation = actor_spell_cast_validation(
            actor,
            spell_id,
            cast_level=cast_level,
            ritual=ritual,
        )
        if validation is not None:
            if not validation.valid:
                raise ValueError(" ".join(validation.errors))
            inventory = list(actor.inventory)
            for use in validation.material_uses:
                if not use.consumed:
                    continue
                index = next(
                    (
                        index
                        for index, item in enumerate(inventory)
                        if item.id == use.item_id
                    ),
                    None,
                )
                if index is None:
                    raise ValueError(f"Brak komponentu materialnego {use.item_id}.")
                item = inventory[index]
                remaining = item.quantity - use.quantity
                if remaining < 0:
                    raise ValueError(f"Za mało komponentu materialnego {item.name}.")
                if remaining == 0:
                    inventory.pop(index)
                else:
                    inventory[index] = replace(item, quantity=remaining)
            actor_after_components = replace(actor, inventory=tuple(inventory))
    if ritual or spell_level <= 0:
        return SpellResourceUse(actor, actor_after_components, spell_level, False)
    levels = available_cast_levels(actor_after_components, spell_level)
    selected_level = levels[0] if cast_level is None and levels else cast_level
    if selected_level is None or selected_level not in levels:
        requested = spell_level if cast_level is None else cast_level
        raise ValueError(f"Brak slotów czaru poziomu {requested} lub wyższego.")
    slots = list(actor_after_components.spell_slots)
    for index, slot in enumerate(slots):
        if slot.level == selected_level:
            slots[index] = replace(slot, remaining=slot.remaining - 1)
            return SpellResourceUse(
                actor,
                replace(actor_after_components, spell_slots=tuple(slots)),
                selected_level,
                True,
            )
    raise ValueError(f"Aktor nie ma slotów czaru poziomu {selected_level}.")


def resolve_spell_save(
    actor: Actor,
    *,
    ability: str,
    dc: int,
    natural_roll: int,
    natural_roll_2: int | None = None,
    damage_on_success: str = "none",
    situational_modifiers: Sequence[RollModifier] = (),
    condition_states: Sequence = (),
    combat_actors: Sequence[Actor] = (),
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
        natural_roll_2=natural_roll_2,
        situational_modifiers=situational_modifiers,
        condition_states=condition_states,
        combat_actors=combat_actors,
    )


def resolve_actor_saving_throw(
    actor: Actor,
    saving_throw: SavingThrowRequest,
    *,
    natural_roll: int,
    natural_roll_2: int | None = None,
    situational_modifiers: Sequence[RollModifier] = (),
    condition_states: Sequence = (),
    combat_actors: Sequence[Actor] = (),
) -> SavingThrowResult:
    from .auras import saving_throw_aura_modifiers

    roll_request = D20RollRequest(
        modifiers=(
            *saving_throw_roll_modifiers(actor, saving_throw.ability),
            *saving_throw_aura_modifiers(combat_actors, actor),
            *situational_modifiers,
        )
    )
    if condition_states:
        from .conditions import condition_roll_request

        roll_request = condition_roll_request(
            roll_request,
            condition_states,
            actor,
            saving_throw_ability=saving_throw.ability,
        )
    roll_request = apply_exhaustion_to_roll_request(
        actor,
        roll_request,
        ExhaustionRollKind.SAVING_THROW,
    )
    if roll_request.mode != RollMode.NORMAL and natural_roll_2 is None:
        raise ValueError("Advantage or disadvantage saving throw requires two d20 rolls.")
    roll = resolve_d20_roll(
        D20RollInput(
            roll_request,
            int(natural_roll),
            int(natural_roll_2) if natural_roll_2 is not None else None,
        )
    )
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
