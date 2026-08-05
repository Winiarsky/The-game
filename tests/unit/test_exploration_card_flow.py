from __future__ import annotations

import pytest

from dnd_board_game.application.exploration_card_flow import (
    ExplorationCardFlowService,
    ExplorationCardFlowState,
)
from dnd_board_game.exploration.card_intents import (
    ExplorationPrompt,
    ExplorationPromptKind,
    exploration_card_handler,
)


def _prompt() -> ExplorationPrompt:
    return ExplorationPrompt(
        id="bren:payment",
        kind=ExplorationPromptKind.INTERACTION,
        tags=frozenset({"conversation", "negotiation"}),
        eligible_actor_ids=("brakka",),
        instance_id="village_square:bren",
    )


def test_accept_commits_attempt_and_clears_interrupt() -> None:
    service = ExplorationCardFlowService()
    handler = exploration_card_handler("intimidation")
    assert handler is not None
    declared = service.declare(
        state=ExplorationCardFlowState(),
        handler=handler,
        prompt=_prompt(),
        actor_id="brakka",
    )
    accepted = service.accept(declared.state)
    assert accepted.accepted
    assert accepted.state.pending is None
    assert accepted.pending is not None
    assert accepted.pending.attempt_key in accepted.state.spent_attempt_keys


def test_decline_does_not_commit_attempt() -> None:
    service = ExplorationCardFlowService()
    handler = exploration_card_handler("intimidation")
    assert handler is not None
    declared = service.declare(
        state=ExplorationCardFlowState(),
        handler=handler,
        prompt=_prompt(),
        actor_id="brakka",
    )
    declined = service.decline(declared.state)
    assert declined.declined
    assert not declined.state.spent_attempt_keys


def test_different_card_cannot_replace_open_interrupt() -> None:
    service = ExplorationCardFlowService()
    first = exploration_card_handler("intimidation")
    second = exploration_card_handler("charm_person")
    assert first is not None and second is not None
    declared = service.declare(
        state=ExplorationCardFlowState(),
        handler=first,
        prompt=_prompt(),
        actor_id="brakka",
    )
    with pytest.raises(ValueError, match="Najpierw rozstrzygnij"):
        service.declare(
            state=declared.state,
            handler=second,
            prompt=_prompt(),
            actor_id="brakka",
        )
