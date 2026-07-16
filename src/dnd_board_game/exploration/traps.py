"""Deterministic state transitions for exploration traps."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .models import (
    ExplorationState,
    ExplorationTrap,
    ExplorationTrapAction,
    ExplorationTrapState,
    ExplorationTrapStatus,
)


@dataclass(frozen=True, slots=True)
class ExplorationTrapActionResult:
    state: ExplorationState
    trap: ExplorationTrap
    action: ExplorationTrapAction
    success: bool
    triggered: bool
    message: str


def trap_state_for(state: ExplorationState, trap_id: str) -> ExplorationTrapState:
    return next(
        (item for item in state.trap_states if item.trap_id == trap_id),
        ExplorationTrapState(trap_id),
    )


def set_trap_status(
    state: ExplorationState,
    trap_id: str,
    status: ExplorationTrapStatus,
) -> ExplorationState:
    if trap_id not in {trap.id for trap in state.traps}:
        raise ValueError(f"Unknown exploration trap: {trap_id}.")
    current = trap_state_for(state, trap_id)
    updated = replace(current, status=status)
    remaining = tuple(item for item in state.trap_states if item.trap_id != trap_id)
    return replace(
        state,
        trap_states=tuple(sorted((*remaining, updated), key=lambda item: item.trap_id)),
    )


def reveal_trap(state: ExplorationState, trap_id: str) -> ExplorationState:
    current = trap_state_for(state, trap_id)
    if current.status != ExplorationTrapStatus.HIDDEN:
        return state
    return set_trap_status(state, trap_id, ExplorationTrapStatus.REVEALED)


def trigger_trap(state: ExplorationState, trap: ExplorationTrap) -> ExplorationState:
    current = trap_state_for(state, trap.id)
    if current.status in {
        ExplorationTrapStatus.DISARMED,
        ExplorationTrapStatus.BYPASSED,
        ExplorationTrapStatus.TRIGGERED,
    }:
        return state
    return set_trap_status(state, trap.id, ExplorationTrapStatus.TRIGGERED)


def resolve_trap_action(
    state: ExplorationState,
    trap: ExplorationTrap,
    action: ExplorationTrapAction,
    *,
    total: int | None = None,
) -> ExplorationTrapActionResult:
    status = trap_state_for(state, trap.id).status
    if status != ExplorationTrapStatus.REVEALED:
        raise ValueError("Pułapkę można obsłużyć dopiero po jej wykryciu.")
    if action == ExplorationTrapAction.TRIGGER:
        updated = trigger_trap(state, trap)
        return ExplorationTrapActionResult(updated, trap, action, True, True, "Celowo uruchamiacie pułapkę.")
    check = trap.disarm_check if action == ExplorationTrapAction.DISARM else trap.bypass_check
    if check is not None and total is None:
        raise ValueError("Ta akcja na pułapce wymaga wyniku testu.")
    success = check is None or int(total or 0) >= check.dc
    if success:
        target_status = (
            ExplorationTrapStatus.DISARMED
            if action == ExplorationTrapAction.DISARM
            else ExplorationTrapStatus.BYPASSED
        )
        message = (
            trap.disarm_success_message
            if action == ExplorationTrapAction.DISARM
            else trap.bypass_success_message
        )
        return ExplorationTrapActionResult(
            set_trap_status(state, trap.id, target_status),
            trap,
            action,
            True,
            False,
            message,
        )
    return ExplorationTrapActionResult(
        trigger_trap(state, trap),
        trap,
        action,
        False,
        True,
        "Próba nie udaje się i uruchamia mechanizm pułapki.",
    )


def match_revealed_trap_action(
    state: ExplorationState,
    player_action: str,
    *,
    zone_id: str,
) -> tuple[ExplorationTrap, ExplorationTrapAction] | None:
    candidates: list[tuple[int, ExplorationTrap, ExplorationTrapAction]] = []
    action_stems = _intent_stems(player_action)
    for trap in state.traps:
        if trap.zone_id != zone_id or trap_state_for(state, trap.id).status != ExplorationTrapStatus.REVEALED:
            continue
        for action, examples in (
            (ExplorationTrapAction.DISARM, trap.disarm_intent_examples),
            (ExplorationTrapAction.BYPASS, trap.bypass_intent_examples),
            (ExplorationTrapAction.TRIGGER, trap.trigger_intent_examples),
        ):
            score = max(
                (len(action_stems.intersection(_intent_stems(example))) for example in examples),
                default=0,
            )
            if score >= 1:
                candidates.append((score, trap, action))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        return None
    _, trap, action = candidates[0]
    return trap, action


def _intent_stems(value: str) -> frozenset[str]:
    translation = str.maketrans(
        {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"}
    )
    ignored = {"chce", "link", "pulap", "tego", "zeby"}
    return frozenset(
        token[:5]
        for token in value.lower().translate(translation).replace("?", " ").replace(",", " ").split()
        if len(token) >= 4 and token[:5] not in ignored
    )


__all__ = [
    "ExplorationTrapActionResult",
    "match_revealed_trap_action",
    "resolve_trap_action",
    "reveal_trap",
    "set_trap_status",
    "trap_state_for",
    "trigger_trap",
]
