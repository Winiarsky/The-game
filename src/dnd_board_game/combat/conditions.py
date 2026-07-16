from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    RollMode,
    RollModifier,
    RollModifierType,
    SavingThrowRequest,
    SavingThrowResult,
    resolve_d20_roll,
    resolve_saving_throw_request,
)
from dnd_board_game.world import MovementRangeResult, PathResult

from .attack_flow import AttackSource


class CombatCondition(StrEnum):
    PRONE = "prone"
    GRAPPLED = "grappled"
    POISONED = "poisoned"
    RESTRAINED = "restrained"


class ConditionSaveTiming(StrEnum):
    TURN_START = "turn_start"
    TURN_END = "turn_end"


@dataclass(frozen=True, slots=True)
class ConditionDefinition:
    condition: CombatCondition
    label: str
    description: str
    speed_zero: bool = False
    attack_disadvantage: bool = False
    attacks_against_advantage: bool = False
    ability_check_disadvantage: bool = False
    dexterity_save_disadvantage: bool = False


CONDITION_DEFINITIONS: dict[CombatCondition, ConditionDefinition] = {
    CombatCondition.PRONE: ConditionDefinition(
        CombatCondition.PRONE,
        "Powalony",
        "Ataki aktora mają utrudnienie; wstawanie kosztuje połowę szybkości.",
    ),
    CombatCondition.GRAPPLED: ConditionDefinition(
        CombatCondition.GRAPPLED,
        "Chwytany",
        "Szybkość wynosi 0 do czasu zakończenia chwytu.",
        speed_zero=True,
    ),
    CombatCondition.POISONED: ConditionDefinition(
        CombatCondition.POISONED,
        "Zatruty",
        "Ataki i testy cech aktora mają utrudnienie.",
        attack_disadvantage=True,
        ability_check_disadvantage=True,
    ),
    CombatCondition.RESTRAINED: ConditionDefinition(
        CombatCondition.RESTRAINED,
        "Unieruchomiony",
        "Szybkość wynosi 0; ataki aktora i Dexterity saves mają utrudnienie, a ataki przeciw niemu przewagę.",
        speed_zero=True,
        attack_disadvantage=True,
        attacks_against_advantage=True,
        dexterity_save_disadvantage=True,
    ),
}


@dataclass(frozen=True, slots=True)
class ConditionState:
    actor_id: str
    condition: CombatCondition
    source_actor_id: str | None = None
    source_label: str = ""
    duration: EffectDuration = EffectDuration.PERMANENT
    expiration_actor_id: str | None = None
    save_ability: str | None = None
    save_dc: int | None = None
    save_timing: ConditionSaveTiming | None = None

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("Condition actor id cannot be empty.")
        if self.condition == CombatCondition.GRAPPLED and not self.source_actor_id:
            raise ValueError("Grappled condition requires a source actor id.")
        if self.source_actor_id == self.actor_id:
            raise ValueError("An actor cannot be the source of its own condition.")
        if self.expiration_actor_id is None:
            object.__setattr__(self, "expiration_actor_id", self.actor_id)
        save_fields = (self.save_ability, self.save_dc, self.save_timing)
        if any(value is not None for value in save_fields) and not all(
            value is not None for value in save_fields
        ):
            raise ValueError("Condition save requires ability, DC and timing.")
        if self.save_dc is not None and self.save_dc < 0:
            raise ValueError("Condition save DC cannot be negative.")


@dataclass(frozen=True, slots=True)
class ConditionApplicationResult:
    condition_states: tuple[ConditionState, ...]
    applied: bool
    state: ConditionState | None
    message: str


@dataclass(frozen=True, slots=True)
class ConditionSaveResolution:
    condition_states: tuple[ConditionState, ...]
    condition_state: ConditionState
    saving_throw: SavingThrowResult
    removed: bool


def has_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
) -> bool:
    return any(state.actor_id == actor_id and state.condition == condition for state in states)


def add_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
    *,
    source_actor_id: str | None = None,
    source_label: str = "",
    duration: EffectDuration = EffectDuration.PERMANENT,
    expiration_actor_id: str | None = None,
    save_ability: str | None = None,
    save_dc: int | None = None,
    save_timing: ConditionSaveTiming | None = None,
) -> tuple[ConditionState, ...]:
    candidate = ConditionState(
        actor_id,
        condition,
        source_actor_id,
        source_label,
        duration,
        expiration_actor_id,
        save_ability,
        save_dc,
        save_timing,
    )
    if candidate in states:
        return tuple(states)
    remaining = tuple(
        state
        for state in states
        if not (state.actor_id == actor_id and state.condition == condition)
    )
    return (*remaining, candidate)


def apply_condition(
    states: Sequence[ConditionState],
    actor: Actor,
    condition: CombatCondition,
    *,
    source_actor_id: str | None = None,
    source_label: str = "",
    duration: EffectDuration = EffectDuration.PERMANENT,
    expiration_actor_id: str | None = None,
    save_ability: str | None = None,
    save_dc: int | None = None,
    save_timing: ConditionSaveTiming | None = None,
) -> ConditionApplicationResult:
    definition = condition_definition(condition)
    if condition.value in actor.condition_immunities:
        return ConditionApplicationResult(
            tuple(states),
            False,
            None,
            f"{actor.name} ma odporność na stan {definition.label}.",
        )
    updated = add_condition(
        states,
        str(actor.id),
        condition,
        source_actor_id=source_actor_id,
        source_label=source_label,
        duration=duration,
        expiration_actor_id=expiration_actor_id,
        save_ability=save_ability,
        save_dc=save_dc,
        save_timing=save_timing,
    )
    applied_state = next(
        state
        for state in updated
        if state.actor_id == str(actor.id) and state.condition == condition
    )
    return ConditionApplicationResult(
        updated,
        updated != tuple(states),
        applied_state,
        f"Nałożono stan {definition.label} na {actor.name}.",
    )


def condition_definition(condition: CombatCondition) -> ConditionDefinition:
    return CONDITION_DEFINITIONS[condition]


def condition_label(condition: CombatCondition) -> str:
    return condition_definition(condition).label


def expire_condition_states(
    states: Sequence[ConditionState],
    event: EffectEvent,
) -> tuple[tuple[ConditionState, ...], tuple[ConditionState, ...]]:
    expired = tuple(state for state in states if _condition_expires_on(state, event))
    expired_ids = {id(state) for state in expired}
    return tuple(state for state in states if id(state) not in expired_ids), expired


def pending_condition_saves(
    states: Sequence[ConditionState],
    actor_id: str,
    timing: ConditionSaveTiming,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if state.actor_id == actor_id and state.save_timing == timing
    )


def resolve_condition_save(
    states: Sequence[ConditionState],
    actor: Actor,
    condition_state: ConditionState,
    *,
    natural_roll: int,
    natural_roll_2: int | None = None,
    combat_actors: Sequence[Actor] = (),
) -> ConditionSaveResolution:
    from dnd_board_game.actors import saving_throw_roll_modifiers
    from .auras import saving_throw_aura_modifiers

    if condition_state.actor_id != str(actor.id):
        raise ValueError("Condition save does not belong to this actor.")
    if condition_state.save_ability is None or condition_state.save_dc is None:
        raise ValueError("Condition does not define a saving throw.")
    request = condition_roll_request(
        D20RollRequest(
            modifiers=(
                *saving_throw_roll_modifiers(actor, condition_state.save_ability),
                *saving_throw_aura_modifiers(combat_actors, actor),
            )
        ),
        states,
        actor,
        saving_throw_ability=condition_state.save_ability,
    )
    if request.mode != RollMode.NORMAL and natural_roll_2 is None:
        raise ValueError("Condition save with advantage or disadvantage requires two d20 rolls.")
    roll = resolve_d20_roll(D20RollInput(request, int(natural_roll), natural_roll_2))
    saving_throw = resolve_saving_throw_request(
        SavingThrowRequest(
            ability=condition_state.save_ability,
            dc=condition_state.save_dc,
            source_label=condition_state.source_label or condition_label(condition_state.condition),
            failure_effect_label=f"stan {condition_label(condition_state.condition)} pozostaje",
            success_effect_label=f"stan {condition_label(condition_state.condition)} usunięty",
        ),
        actor_id=str(actor.id),
        actor_name=actor.name,
        roll=roll,
    )
    updated = (
        remove_condition(states, str(actor.id), condition_state.condition)
        if saving_throw.success
        else tuple(states)
    )
    return ConditionSaveResolution(updated, condition_state, saving_throw, saving_throw.success)


def remove_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if not (state.actor_id == actor_id and state.condition == condition)
    )


def grappled_by(
    states: Sequence[ConditionState],
    actor_id: str,
) -> str | None:
    state = next(
        (
            state
            for state in states
            if state.actor_id == actor_id
            and state.condition == CombatCondition.GRAPPLED
        ),
        None,
    )
    return state.source_actor_id if state is not None else None


def grappled_actor_ids(
    states: Sequence[ConditionState],
    source_actor_id: str,
) -> tuple[str, ...]:
    return tuple(
        state.actor_id
        for state in states
        if state.condition == CombatCondition.GRAPPLED
        and state.source_actor_id == source_actor_id
    )


def remove_grapple(
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    source_actor_id: str | None = None,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if not (
            state.actor_id == actor_id
            and state.condition == CombatCondition.GRAPPLED
            and (source_actor_id is None or state.source_actor_id == source_actor_id)
        )
    )


def normalize_grapple_conditions(
    states: Sequence[ConditionState],
    actors: Sequence[Actor],
) -> tuple[ConditionState, ...]:
    """Remove grapples whose source/target cannot maintain a 5 ft hold."""

    actors_by_id = {str(actor.id): actor for actor in actors}
    normalized: list[ConditionState] = []
    for state in states:
        if state.condition != CombatCondition.GRAPPLED:
            normalized.append(state)
            continue
        target = actors_by_id.get(state.actor_id)
        source = actors_by_id.get(state.source_actor_id or "")
        if target is None or source is None or target.is_defeated() or source.is_defeated():
            continue
        distance = max(
            abs(source.position.col - target.position.col),
            abs(source.position.row - target.position.row),
        )
        if distance <= 1:
            normalized.append(state)
    return tuple(normalized)


def standing_movement_cost(actor: Actor) -> int:
    return actor.speed_feet // 2


def path_with_condition_cost(
    path: PathResult,
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    movement_budget_feet: int | None = None,
) -> PathResult:
    cost = path.cost_feet
    if (
        path.valid
        and path.destination != path.origin
        and any(
            condition_definition(state.condition).speed_zero
            for state in states
            if state.actor_id == actor_id
        )
    ):
        return replace(path, valid=False)
    if path.valid and has_condition(states, actor_id, CombatCondition.PRONE):
        cost += _base_path_distance(path.path)
    valid = path.valid and (
        movement_budget_feet is None or cost <= movement_budget_feet
    )
    return replace(path, cost_feet=cost, valid=valid)


def effective_movement_speed(
    actor: Actor,
    states: Sequence[ConditionState],
) -> int:
    if any(
        condition_definition(state.condition).speed_zero
        for state in states
        if state.actor_id == str(actor.id)
    ):
        return 0
    if grappled_actor_ids(states, str(actor.id)):
        return actor.speed_feet // 2
    return actor.speed_feet


def movement_range_with_condition_cost(
    movement: MovementRangeResult,
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    movement_budget_feet: int,
) -> MovementRangeResult:
    costs: dict = {}
    paths: dict = {}
    for tile, path_positions in movement.paths_by_tile.items():
        path = PathResult(
            movement.origin,
            tile,
            path_positions,
            movement.costs_by_tile[tile],
            tile in movement.reachable_tiles,
        )
        adjusted = path_with_condition_cost(
            path,
            states,
            actor_id,
            movement_budget_feet=movement_budget_feet,
        )
        if adjusted.valid:
            costs[tile] = adjusted.cost_feet
            paths[tile] = adjusted.path
    return MovementRangeResult(
        origin=movement.origin,
        reachable_tiles=frozenset(costs),
        costs_by_tile=costs,
        paths_by_tile=paths,
    )


def attack_source_with_prone(
    source: AttackSource,
    states: Sequence[ConditionState],
    attacker: Actor,
    target: Actor,
) -> AttackSource:
    if source.save_ability is not None or source.area is not None:
        return source
    attacker_prone = has_condition(states, str(attacker.id), CombatCondition.PRONE)
    target_prone = has_condition(states, str(target.id), CombatCondition.PRONE)
    target_within_five_feet = max(
        abs(attacker.position.col - target.position.col),
        abs(attacker.position.row - target.position.row),
    ) <= 1
    attacker_conditions = tuple(
        condition_definition(state.condition)
        for state in states
        if state.actor_id == str(attacker.id)
    )
    target_conditions = tuple(
        condition_definition(state.condition)
        for state in states
        if state.actor_id == str(target.id)
    )
    condition_advantage = any(item.attacks_against_advantage for item in target_conditions)
    condition_disadvantage = any(item.attack_disadvantage for item in attacker_conditions)
    advantage = (target_prone and target_within_five_feet) or condition_advantage
    disadvantage = attacker_prone or (target_prone and not target_within_five_feet) or condition_disadvantage
    if not advantage and not disadvantage:
        return source

    request = source.attack_roll_request
    mode = _mode_with_factors(request.mode, advantage=advantage, disadvantage=disadvantage)
    modifiers = list(request.modifiers)
    if attacker_prone:
        modifiers.append(_factor("Atak w pozycji powalonej", "prone_attacker"))
    if target_prone:
        modifiers.append(
            _factor(
                "Powalony cel w zasięgu 5 ft" if target_within_five_feet else "Powalony cel dalej niż 5 ft",
                "prone_target_close" if target_within_five_feet else "prone_target_far",
            )
        )
    for definition in attacker_conditions:
        if definition.attack_disadvantage:
            modifiers.append(
                _factor(f"{definition.label}: utrudnienie ataku", f"condition:{definition.condition}:attack")
            )
    for definition in target_conditions:
        if definition.attacks_against_advantage:
            modifiers.append(
                _factor(f"{definition.label}: przewaga przeciw celowi", f"condition:{definition.condition}:target")
            )
    return replace(
        source,
        attack_roll_request=D20RollRequest(mode=mode, modifiers=tuple(modifiers)),
    )


def condition_roll_request(
    request: D20RollRequest,
    states: Sequence[ConditionState],
    actor: Actor,
    *,
    ability_check: bool = False,
    saving_throw_ability: str | None = None,
) -> D20RollRequest:
    """Apply condition-driven advantage/disadvantage to a non-attack d20 roll."""
    definitions = tuple(
        condition_definition(state.condition)
        for state in states
        if state.actor_id == str(actor.id)
    )
    disadvantage_definitions = tuple(
        definition
        for definition in definitions
        if (ability_check and definition.ability_check_disadvantage)
        or (
            saving_throw_ability == "dexterity"
            and definition.dexterity_save_disadvantage
        )
    )
    if not disadvantage_definitions:
        return request
    mode = _mode_with_factors(request.mode, advantage=False, disadvantage=True)
    modifiers = (
        *request.modifiers,
        *(
            _factor(
                f"{definition.label}: utrudnienie",
                f"condition:{definition.condition}:roll",
            )
            for definition in disadvantage_definitions
        ),
    )
    return D20RollRequest(mode=mode, modifiers=modifiers)


def _condition_expires_on(state: ConditionState, event: EffectEvent) -> bool:
    if state.save_timing is not None:
        return False
    if state.duration == EffectDuration.UNTIL_ENCOUNTER_END:
        return event.event_type == EffectEventType.ENCOUNTER_ENDED
    if state.duration == EffectDuration.UNTIL_SCENARIO_END:
        return event.event_type == EffectEventType.SCENARIO_ENDED
    if state.duration == EffectDuration.UNTIL_LONG_REST:
        return event.event_type == EffectEventType.LONG_REST_COMPLETED
    if state.duration == EffectDuration.UNTIL_SHORT_REST:
        return event.event_type == EffectEventType.SHORT_REST_COMPLETED
    if state.duration == EffectDuration.UNTIL_TURN_START:
        return (
            event.event_type == EffectEventType.TURN_START
            and event.actor_id == state.expiration_actor_id
        )
    if state.duration == EffectDuration.UNTIL_TURN_END:
        return (
            event.event_type == EffectEventType.TURN_END
            and event.actor_id == state.expiration_actor_id
        )
    return False


def _base_path_distance(path: Sequence) -> int:
    distance = 0
    diagonal_parity = 0
    for origin, destination in zip(path, path[1:]):
        diagonal = origin.col != destination.col and origin.row != destination.row
        if diagonal:
            distance += 10 if diagonal_parity else 5
            diagonal_parity = 1 - diagonal_parity
        else:
            distance += 5
    return distance


def _mode_with_factors(
    current: RollMode,
    *,
    advantage: bool,
    disadvantage: bool,
) -> RollMode:
    if advantage and disadvantage:
        return RollMode.NORMAL
    if advantage:
        return RollMode.NORMAL if current == RollMode.DISADVANTAGE else RollMode.ADVANTAGE
    if disadvantage:
        return RollMode.NORMAL if current == RollMode.ADVANTAGE else RollMode.DISADVANTAGE
    return current


def _factor(label: str, stacking_key: str) -> RollModifier:
    return RollModifier(
        label,
        0,
        RollModifierType.SITUATIONAL,
        stacking_key=stacking_key,
    )
