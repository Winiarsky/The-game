from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.combat import scene_flag

from .models import (
    ExplorationState,
    NpcAttemptPolicy,
    NpcInteractionStatus,
    NpcRelationshipEvent,
    NpcRuntimeState,
    NpcStateUpdate,
)


@dataclass(frozen=True, slots=True)
class NpcRuntimeResolution:
    state: ExplorationState
    npc_before: NpcRuntimeState
    npc_after: NpcRuntimeState
    event: NpcRelationshipEvent


@dataclass(frozen=True, slots=True)
class NpcAttemptPlan:
    attempt_id: str
    attempts_used: int
    max_attempts: int
    available: bool
    blocked_reason: str = ""
    retry_requires_any_flags: tuple[str, ...] = ()

    @property
    def attempts_remaining(self) -> int:
        return max(0, self.max_attempts - self.attempts_used)

    @property
    def is_retry(self) -> bool:
        return self.attempts_used > 0

    def as_payload(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "attempts_used": self.attempts_used,
            "max_attempts": self.max_attempts,
            "attempts_remaining": self.attempts_remaining,
            "is_retry": self.is_retry,
            "available": self.available,
            "blocked_reason": self.blocked_reason,
            "retry_requires_any_flags": list(self.retry_requires_any_flags),
        }


def npc_runtime_state_for(
    state: ExplorationState,
    npc_id: str,
) -> NpcRuntimeState | None:
    return next((item for item in state.npc_states if item.npc_id == npc_id), None)


def plan_npc_attempt(
    state: ExplorationState,
    *,
    npc_id: str,
    policy: NpcAttemptPolicy,
) -> NpcAttemptPlan:
    current = npc_runtime_state_for(state, npc_id)
    if current is None:
        raise ValueError(f"Unknown NPC runtime state: {npc_id}.")
    attempt_id = policy.attempt_id.strip().lower()
    attempts_used = sum(
        event.attempt_id is not None
        and event.attempt_id.strip().lower() == attempt_id
        for event in current.relationship_events
    )
    if attempts_used == 0 and attempt_id in current.used_attempt_ids:
        # Backwards-compatible snapshots recorded only unique used ids.
        attempts_used = 1
    if attempts_used >= policy.max_attempts:
        return NpcAttemptPlan(
            attempt_id,
            attempts_used,
            policy.max_attempts,
            False,
            policy.exhausted_message,
            policy.retry_requires_any_flags,
        )
    if attempts_used > 0 and policy.retry_requires_any_flags:
        retry_unlocked = any(
            bool(scene_flag(state.flags, flag, False))
            for flag in policy.retry_requires_any_flags
        )
        if not retry_unlocked:
            return NpcAttemptPlan(
                attempt_id,
                attempts_used,
                policy.max_attempts,
                False,
                policy.retry_locked_message,
                policy.retry_requires_any_flags,
            )
    return NpcAttemptPlan(
        attempt_id,
        attempts_used,
        policy.max_attempts,
        True,
        retry_requires_any_flags=policy.retry_requires_any_flags,
    )


def resolve_npc_runtime_interaction(
    state: ExplorationState,
    *,
    npc_id: str,
    intent: str,
    success: bool,
    summary: str,
    update: NpcStateUpdate | None = None,
    revealed_information_ids: tuple[str, ...] = (),
    attempt_id: str | None = None,
) -> NpcRuntimeResolution:
    current = npc_runtime_state_for(state, npc_id)
    if current is None:
        raise ValueError(f"Unknown NPC runtime state: {npc_id}.")
    normalized_intent = intent.strip().lower()
    if not normalized_intent:
        raise ValueError("NPC interaction intent cannot be empty.")
    normalized_summary = summary.strip() or (
        f"{normalized_intent}: {'sukces' if success else 'porażka'}"
    )
    event = NpcRelationshipEvent(
        sequence=len(current.relationship_events) + 1,
        intent=normalized_intent,
        outcome="success" if success else "failure",
        summary=normalized_summary,
        attempt_id=(attempt_id.strip().lower() if attempt_id and attempt_id.strip() else None),
    )
    revealed = tuple(
        dict.fromkeys((*current.revealed_information_ids, *revealed_information_ids))
    )
    attempts = current.used_attempt_ids
    if attempt_id is not None and attempt_id.strip():
        attempts = tuple(dict.fromkeys((*attempts, attempt_id.strip().lower())))
    updated = replace(
        current,
        attitude=(
            update.attitude
            if update is not None and update.attitude is not None
            else current.attitude
        ),
        physical_state=(
            update.physical_state
            if update is not None and update.physical_state is not None
            else current.physical_state
        ),
        emotional_state=(
            update.emotional_state
            if update is not None and update.emotional_state is not None
            else current.emotional_state
        ),
        revealed_information_ids=revealed,
        used_attempt_ids=attempts,
        relationship_events=(*current.relationship_events, event),
    )
    updated_state = replace(
        state,
        npc_states=tuple(updated if item.npc_id == npc_id else item for item in state.npc_states),
    )
    return NpcRuntimeResolution(updated_state, current, updated, event)


def set_npc_interaction_status(
    state: ExplorationState,
    *,
    npc_id: str,
    status: NpcInteractionStatus,
    closure_reason: str = "",
) -> ExplorationState:
    current = npc_runtime_state_for(state, npc_id)
    if current is None:
        raise ValueError(f"Unknown NPC runtime state: {npc_id}.")
    updated = replace(
        current,
        interaction_status=status,
        closure_reason=(closure_reason.strip() if status == NpcInteractionStatus.CLOSED else ""),
    )
    return replace(
        state,
        npc_states=tuple(updated if item.npc_id == npc_id else item for item in state.npc_states),
    )


__all__ = [
    "NpcAttemptPlan",
    "NpcRuntimeResolution",
    "npc_runtime_state_for",
    "plan_npc_attempt",
    "resolve_npc_runtime_interaction",
    "set_npc_interaction_status",
]
