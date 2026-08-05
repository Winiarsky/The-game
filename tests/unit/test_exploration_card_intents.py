from __future__ import annotations

import pytest

from dnd_board_game.exploration.card_intents import (
    ExplorationPrompt,
    ExplorationPromptKind,
    declare_exploration_card,
    exploration_card_handler,
)


def _prompt(
    kind: ExplorationPromptKind,
    *tags: str,
    actor_ids: tuple[str, ...] = ("brakka", "lorian"),
) -> ExplorationPrompt:
    return ExplorationPrompt(
        id="bren:payment:decision",
        kind=kind,
        tags=frozenset(tags),
        eligible_actor_ids=actor_ids,
        instance_id="village_square:bren",
        interaction_id="bren_payment",
    )


def test_intimidation_interrupts_matching_conversation_prompt() -> None:
    handler = exploration_card_handler("intimidation")
    assert handler is not None
    pending = declare_exploration_card(
        handler=handler,
        prompt=_prompt(ExplorationPromptKind.INTERACTION, "conversation", "negotiation"),
        actor_id="brakka",
    )
    assert pending.actor_id == "brakka"
    assert pending.handler.result_flag == "intimidation_attempt"


def test_card_rejects_wrong_prompt_without_spending_attempt() -> None:
    handler = exploration_card_handler("intimidation")
    assert handler is not None
    with pytest.raises(ValueError, match="nie pasuje"):
        declare_exploration_card(
            handler=handler,
            prompt=_prompt(ExplorationPromptKind.FREE_ACTION, "location"),
            actor_id="brakka",
        )


def test_prompt_rejects_actor_who_does_not_participate() -> None:
    handler = exploration_card_handler("guidance")
    assert handler is not None
    with pytest.raises(ValueError, match="nie uczestniczy"):
        declare_exploration_card(
            handler=handler,
            prompt=_prompt(ExplorationPromptKind.BEFORE_ROLL, actor_ids=("lorian",)),
            actor_id="dagna",
        )


def test_once_per_prompt_card_cannot_be_redeclared() -> None:
    handler = exploration_card_handler("break_in")
    assert handler is not None
    prompt = _prompt(ExplorationPromptKind.INTERACTION, "lock")
    pending = declare_exploration_card(
        handler=handler,
        prompt=prompt,
        actor_id="brakka",
    )
    with pytest.raises(ValueError, match="już wykorzystana"):
        declare_exploration_card(
            handler=handler,
            prompt=prompt,
            actor_id="brakka",
            spent_attempt_keys=frozenset({pending.attempt_key}),
        )


def test_repeatable_modifier_is_not_blocked_by_attempt_ledger() -> None:
    handler = exploration_card_handler("guidance")
    assert handler is not None
    prompt = _prompt(ExplorationPromptKind.BEFORE_ROLL, actor_ids=("dagna",))
    pending = declare_exploration_card(
        handler=handler,
        prompt=prompt,
        actor_id="dagna",
    )
    repeated = declare_exploration_card(
        handler=handler,
        prompt=prompt,
        actor_id="dagna",
        spent_attempt_keys=frozenset({pending.attempt_key}),
    )
    assert repeated.attempt_key == pending.attempt_key


def test_content_handler_allowlist_rejects_unimplemented_card_without_cost() -> None:
    handler = exploration_card_handler("intimidation")
    assert handler is not None
    prompt = ExplorationPrompt(
        id="locked-door",
        kind=ExplorationPromptKind.INTERACTION,
        tags=frozenset({"conversation", "npc"}),
        eligible_actor_ids=("brakka",),
        instance_id="village:door",
        handler_ids=frozenset({"break_in"}),
    )
    with pytest.raises(ValueError, match="nie pasuje"):
        declare_exploration_card(handler=handler, prompt=prompt, actor_id="brakka")
