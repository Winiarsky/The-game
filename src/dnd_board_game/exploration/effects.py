from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, TYPE_CHECKING

from dnd_board_game.combat import SetupVisibility, scene_flag, set_scene_flag

from .models import (
    ExplorationChallenge,
    ExplorationChallengeState,
    ExplorationPoint,
    ExplorationResource,
    ExplorationState,
    challenge_state_for,
    grant_resource,
    remove_resource,
    reveal_exploration_points,
    set_party_zone,
)
from .traps import reveal_trap, trap_state_for

if TYPE_CHECKING:
    from dnd_board_game.llm.content_config import LlmPrimitiveCatalog


@dataclass(frozen=True, slots=True)
class ExplorationEffectResult:
    state: ExplorationState
    effect_type: str
    changed: bool
    message: str


def validate_exploration_effect(
    effect: dict[str, Any],
    state: ExplorationState,
    catalog: "LlmPrimitiveCatalog | None" = None,
) -> None:
    if catalog is None:
        from dnd_board_game.llm.content_config import load_llm_effect_catalog

        catalog = load_llm_effect_catalog()
    effect_type, parameters = _effect_parts(effect, catalog)
    if effect_type == "set_flag":
        _require_string(parameters, "key", effect_type)
        _require(parameters, "value", effect_type)
    elif effect_type == "grant_resource":
        resource_id = _require_string(parameters, "resource_id", effect_type)
        _require_resource(state, resource_id, effect_type)
    elif effect_type == "remove_resource":
        resource_id = _require_string(parameters, "resource_id", effect_type)
        _require_resource(state, resource_id, effect_type)
    elif effect_type == "unlock_option":
        _require_string(parameters, "option_id", effect_type)
    elif effect_type == "reveal_point":
        point_id = _require_string(parameters, "point_id", effect_type)
        _require_point(state, point_id, effect_type)
    elif effect_type == "add_noise":
        challenge_id = _require_string(parameters, "challenge_id", effect_type)
        _require_challenge(state, challenge_id, effect_type)
        _require_non_negative_int(parameters, "value", effect_type)
    elif effect_type == "add_complication":
        challenge_id = _require_string(parameters, "challenge_id", effect_type)
        _require_challenge(state, challenge_id, effect_type)
        _require_string(parameters, "value", effect_type)
    elif effect_type == "move_party":
        zone_id = _require_string(parameters, "zone_id", effect_type)
        _require_zone(state, zone_id, effect_type)
    elif effect_type == "reveal_trap":
        trap_id = _require_string(parameters, "trap_id", effect_type)
        _require_trap(state, trap_id, effect_type)
    else:
        raise ValueError(f"Unsupported exploration effect: {effect_type}.")


def apply_exploration_effect(
    state: ExplorationState,
    effect: dict[str, Any],
    catalog: "LlmPrimitiveCatalog | None" = None,
) -> ExplorationEffectResult:
    if catalog is None:
        from dnd_board_game.llm.content_config import load_llm_effect_catalog

        catalog = load_llm_effect_catalog()
    validate_exploration_effect(effect, state, catalog)
    effect_type, parameters = _effect_parts(effect, catalog)
    if effect_type == "set_flag":
        key = _require_string(parameters, "key", effect_type)
        value = _require(parameters, "value", effect_type)
        previous = scene_flag(state.flags, key, None)
        updated = replace(state, flags=set_scene_flag(state.flags, key, value))
        return ExplorationEffectResult(updated, effect_type, previous != value, f"Flaga ustawiona: {key}.")
    if effect_type == "grant_resource":
        resource_id = _require_string(parameters, "resource_id", effect_type)
        updated = grant_resource(state, resource_id)
        changed = resource_id not in state.inventory_resource_ids
        return ExplorationEffectResult(updated, effect_type, changed, f"Zasób dodany: {resource_id}.")
    if effect_type == "remove_resource":
        resource_id = _require_string(parameters, "resource_id", effect_type)
        updated = remove_resource(state, resource_id)
        changed = resource_id in state.inventory_resource_ids
        return ExplorationEffectResult(updated, effect_type, changed, f"Zasób zużyty: {resource_id}.")
    if effect_type == "unlock_option":
        option_id = _require_string(parameters, "option_id", effect_type)
        flag = f"llm_unlocked_option:{option_id}"
        changed = not scene_flag(state.flags, flag, False)
        updated = replace(state, flags=set_scene_flag(state.flags, flag, True))
        return ExplorationEffectResult(updated, effect_type, changed, f"Opcja odblokowana: {option_id}.")
    if effect_type == "reveal_point":
        point_id = _require_string(parameters, "point_id", effect_type)
        updated, revealed = reveal_exploration_points(state, (point_id,))
        return ExplorationEffectResult(updated, effect_type, bool(revealed), f"Punkt ujawniony: {point_id}.")
    if effect_type == "add_noise":
        challenge_id = _require_string(parameters, "challenge_id", effect_type)
        value = _require_non_negative_int(parameters, "value", effect_type)
        updated = _add_challenge_noise(state, challenge_id, value)
        return ExplorationEffectResult(updated, effect_type, value > 0, f"Hałas dodany: {challenge_id} +{value}.")
    if effect_type == "add_complication":
        challenge_id = _require_string(parameters, "challenge_id", effect_type)
        value = _require_string(parameters, "value", effect_type)
        updated = _add_challenge_complication(state, challenge_id, value)
        changed = updated != state
        return ExplorationEffectResult(updated, effect_type, changed, f"Komplikacja dodana: {value}.")
    if effect_type == "move_party":
        zone_id = _require_string(parameters, "zone_id", effect_type)
        zone = _require_zone(state, zone_id, effect_type)
        updated = set_party_zone(state, zone)
        return ExplorationEffectResult(updated, effect_type, updated != state, f"Drużyna przesunięta: {zone.name}.")
    if effect_type == "reveal_trap":
        trap_id = _require_string(parameters, "trap_id", effect_type)
        trap = _require_trap(state, trap_id, effect_type)
        before = trap_state_for(state, trap_id)
        updated = reveal_trap(state, trap_id)
        return ExplorationEffectResult(
            updated,
            effect_type,
            updated != state,
            f"Wykryto pułapkę: {trap.name}." if updated != state else f"Pułapka już była znana: {before.trap_id}.",
        )
    raise ValueError(f"Unsupported exploration effect: {effect_type}.")


def exploration_condition_matches(
    state: ExplorationState,
    condition: dict[str, Any],
    catalog: "LlmPrimitiveCatalog | None" = None,
) -> bool:
    if catalog is None:
        from dnd_board_game.llm.content_config import load_llm_condition_catalog

        catalog = load_llm_condition_catalog()
    condition_type, parameters = _effect_parts(condition, catalog)
    if condition_type == "flag_equals":
        key = _require_string(parameters, "key", condition_type)
        value = _require(parameters, "value", condition_type)
        return scene_flag(state.flags, key, None) == value
    if condition_type == "has_resource":
        resource_id = _require_string(parameters, "resource_id", condition_type)
        return resource_id in state.inventory_resource_ids
    if condition_type == "point_revealed":
        point_id = _require_string(parameters, "point_id", condition_type)
        point = _require_point(state, point_id, condition_type)
        return point.visibility == SetupVisibility.VISIBLE
    if condition_type == "challenge_noise_at_least":
        challenge_id = _require_string(parameters, "challenge_id", condition_type)
        value = _require_non_negative_int(parameters, "value", condition_type)
        return challenge_state_for(state, challenge_id).noise >= value
    if condition_type == "challenge_completed":
        challenge_id = _require_string(parameters, "challenge_id", condition_type)
        return challenge_state_for(state, challenge_id).completed
    raise ValueError(f"Unsupported exploration condition: {condition_type}.")


def _add_challenge_noise(state: ExplorationState, challenge_id: str, value: int) -> ExplorationState:
    current = challenge_state_for(state, challenge_id)
    updated = replace(current, noise=current.noise + value)
    replaced = False
    challenge_states: list[ExplorationChallengeState] = []
    for entry in state.challenge_states:
        if entry.challenge_id == challenge_id:
            challenge_states.append(updated)
            replaced = True
        else:
            challenge_states.append(entry)
    if not replaced:
        challenge_states.append(updated)
    return replace(state, challenge_states=tuple(sorted(challenge_states, key=lambda item: item.challenge_id)))


def _add_challenge_complication(
    state: ExplorationState,
    challenge_id: str,
    value: str,
) -> ExplorationState:
    current = challenge_state_for(state, challenge_id)
    if value in current.complications:
        return state
    updated = replace(current, complications=(*current.complications, value))
    entries = tuple(item for item in state.challenge_states if item.challenge_id != challenge_id)
    return replace(
        state,
        challenge_states=tuple(sorted((*entries, updated), key=lambda item: item.challenge_id)),
    )


def _effect_parts(effect: dict[str, Any], catalog: "LlmPrimitiveCatalog") -> tuple[str, dict[str, Any]]:
    if not isinstance(effect, dict):
        raise ValueError("Exploration effect must be an object.")
    effect_type = str(effect.get("type", "")).strip().lower()
    if not effect_type:
        raise ValueError("Exploration effect type cannot be empty.")
    definition = catalog.definition(effect_type)
    if definition is None:
        raise ValueError(f"Unknown exploration primitive: {effect_type}.")
    parameters = effect.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError(f"{effect_type}.parameters must be an object.")
    missing = set(definition.parameters) - set(parameters)
    if missing:
        raise ValueError(f"{effect_type}.parameters missing: {', '.join(sorted(missing))}.")
    return effect_type, parameters


def _require(parameters: dict[str, Any], key: str, effect_type: str) -> Any:
    if key not in parameters:
        raise ValueError(f"{effect_type}.{key} is required.")
    return parameters[key]


def _require_string(parameters: dict[str, Any], key: str, effect_type: str) -> str:
    value = _require(parameters, key, effect_type)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{effect_type}.{key} must be a non-empty string.")
    return value.strip()


def _require_non_negative_int(parameters: dict[str, Any], key: str, effect_type: str) -> int:
    value = _require(parameters, key, effect_type)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{effect_type}.{key} must be a non-negative integer.")
    return value


def _require_resource(state: ExplorationState, resource_id: str, effect_type: str) -> ExplorationResource:
    resource = next((item for item in state.resources if item.id == resource_id), None)
    if resource is None:
        raise ValueError(f"{effect_type}.resource_id is unknown: {resource_id}.")
    return resource


def _require_point(state: ExplorationState, point_id: str, effect_type: str) -> ExplorationPoint:
    point = next((item for item in state.points if item.id == point_id), None)
    if point is None:
        raise ValueError(f"{effect_type}.point_id is unknown: {point_id}.")
    return point


def _require_challenge(state: ExplorationState, challenge_id: str, effect_type: str) -> ExplorationChallenge:
    challenge = next((item for item in state.challenges if item.id == challenge_id), None)
    if challenge is None:
        raise ValueError(f"{effect_type}.challenge_id is unknown: {challenge_id}.")
    return challenge


def _require_zone(state: ExplorationState, zone_id: str, effect_type: str):
    zone = next((item for item in state.zones if item.id == zone_id), None)
    if zone is None:
        raise ValueError(f"{effect_type}.zone_id is unknown: {zone_id}.")
    return zone


def _require_trap(state: ExplorationState, trap_id: str, effect_type: str):
    trap = next((item for item in state.traps if item.id == trap_id), None)
    if trap is None:
        raise ValueError(f"{effect_type}.trap_id is unknown: {trap_id}.")
    return trap
