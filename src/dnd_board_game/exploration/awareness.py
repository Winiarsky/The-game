"""Deterministic active/passive search and exploration hiding state."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from dnd_board_game.actors import Actor

from .models import (
    ExplorationCheckResult,
    ExplorationHiddenActorState,
    ExplorationState,
    ExplorationTrap,
    ExplorationTrapStatus,
    ExplorationZone,
    PartyCheckInput,
    SearchResult,
    resolve_zone_search,
)
from .traps import reveal_trap, trap_state_for


@dataclass(frozen=True, slots=True)
class ExplorationSearchResolution:
    search: SearchResult
    revealed_traps: tuple[ExplorationTrap, ...]


@dataclass(frozen=True, slots=True)
class PassiveTrapDetection:
    state: ExplorationState
    revealed_traps: tuple[ExplorationTrap, ...]
    detector_actor_id: str | None = None
    detector_total: int | None = None


def hide_exploration_actor(
    state: ExplorationState,
    actor: Actor,
    *,
    zone_id: str,
    check: ExplorationCheckResult,
) -> ExplorationState:
    if str(check.selected_actor.id) != str(actor.id):
        raise ValueError("Exploration Hide result belongs to a different actor.")
    hidden = ExplorationHiddenActorState(
        actor_id=str(actor.id),
        zone_id=zone_id,
        natural_roll=check.selected_roll.natural_roll,
        stealth_total=check.selected_roll.total,
    )
    remaining = tuple(
        item for item in state.hidden_actor_states if item.actor_id != str(actor.id)
    )
    return replace(
        state,
        hidden_actor_states=tuple(
            sorted((*remaining, hidden), key=lambda item: item.actor_id)
        ),
    )


def clear_exploration_hidden(
    state: ExplorationState,
    *,
    actor_id: str | None = None,
) -> ExplorationState:
    if actor_id is None:
        return replace(state, hidden_actor_states=())
    return replace(
        state,
        hidden_actor_states=tuple(
            item for item in state.hidden_actor_states if item.actor_id != actor_id
        ),
    )


def resolve_active_search(
    state: ExplorationState,
    zone: ExplorationZone,
    inputs: tuple[PartyCheckInput, ...],
) -> ExplorationSearchResolution:
    search = resolve_zone_search(state, zone, inputs)
    updated, revealed = _reveal_detected_traps(
        search.state,
        zone_id=zone.id,
        perception_total=search.party_check.winning_roll.total,
        passive_only=False,
    )
    return ExplorationSearchResolution(
        replace(search, state=updated),
        revealed,
    )


def detect_passive_traps(
    state: ExplorationState,
    *,
    zone_id: str,
    perception_totals: Mapping[str, int],
    trap_ids: tuple[str, ...] | None = None,
) -> PassiveTrapDetection:
    if not perception_totals:
        return PassiveTrapDetection(state, ())
    detector_actor_id, detector_total = max(
        perception_totals.items(),
        key=lambda item: (item[1], item[0]),
    )
    updated, revealed = _reveal_detected_traps(
        state,
        zone_id=zone_id,
        perception_total=detector_total,
        passive_only=True,
        trap_ids=None if trap_ids is None else frozenset(trap_ids),
    )
    return PassiveTrapDetection(
        updated,
        revealed,
        detector_actor_id if revealed else None,
        detector_total if revealed else None,
    )


def _reveal_detected_traps(
    state: ExplorationState,
    *,
    zone_id: str,
    perception_total: int,
    passive_only: bool,
    trap_ids: frozenset[str] | None = None,
) -> tuple[ExplorationState, tuple[ExplorationTrap, ...]]:
    current = state
    revealed: list[ExplorationTrap] = []
    for trap in state.traps:
        if (
            trap.zone_id != zone_id
            or (trap_ids is not None and trap.id not in trap_ids)
            or trap.detection_dc is None
            or perception_total < trap.detection_dc
            or (passive_only and not trap.passive_detection)
            or trap_state_for(current, trap.id).status
            != ExplorationTrapStatus.HIDDEN
        ):
            continue
        current = reveal_trap(current, trap.id)
        revealed.append(trap)
    return current, tuple(revealed)


__all__ = [
    "ExplorationSearchResolution",
    "PassiveTrapDetection",
    "clear_exploration_hidden",
    "detect_passive_traps",
    "hide_exploration_actor",
    "resolve_active_search",
]
