"""Application orchestration for exploration cards interrupting prompts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.exploration.card_intents import (
    ExplorationCardHandler,
    ExplorationPrompt,
    PendingExplorationCard,
    declare_exploration_card,
)


@dataclass(frozen=True, slots=True)
class ExplorationCardFlowState:
    pending: PendingExplorationCard | None = None
    spent_attempt_keys: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ExplorationCardFlowTransition:
    state: ExplorationCardFlowState
    pending: PendingExplorationCard | None
    accepted: bool = False
    declined: bool = False


class ExplorationCardFlowService:
    def declare(
        self,
        *,
        state: ExplorationCardFlowState,
        handler: ExplorationCardHandler,
        prompt: ExplorationPrompt,
        actor_id: str,
    ) -> ExplorationCardFlowTransition:
        if state.pending is not None:
            if (
                state.pending.card_action_id == handler.card_action_id
                and state.pending.actor_id == actor_id
                and state.pending.prompt_id == prompt.id
            ):
                return ExplorationCardFlowTransition(state, state.pending)
            raise ValueError("Najpierw rozstrzygnij oczekującą kartę eksploracji.")
        pending = declare_exploration_card(
            handler=handler,
            prompt=prompt,
            actor_id=actor_id,
            spent_attempt_keys=state.spent_attempt_keys,
        )
        updated = replace(state, pending=pending)
        return ExplorationCardFlowTransition(updated, pending)

    def accept(
        self,
        state: ExplorationCardFlowState,
    ) -> ExplorationCardFlowTransition:
        if state.pending is None:
            raise ValueError("Nie ma karty eksploracji oczekującej na akceptację.")
        pending = state.pending
        updated = ExplorationCardFlowState(
            pending=None,
            spent_attempt_keys=state.spent_attempt_keys | {pending.attempt_key},
        )
        return ExplorationCardFlowTransition(updated, pending, accepted=True)

    def decline(
        self,
        state: ExplorationCardFlowState,
    ) -> ExplorationCardFlowTransition:
        if state.pending is None:
            raise ValueError("Nie ma karty eksploracji oczekującej na odrzucenie.")
        pending = state.pending
        updated = replace(state, pending=None)
        return ExplorationCardFlowTransition(updated, pending, declined=True)


__all__ = [
    "ExplorationCardFlowService",
    "ExplorationCardFlowState",
    "ExplorationCardFlowTransition",
]
