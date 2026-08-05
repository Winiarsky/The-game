from __future__ import annotations

from dnd_board_game.application.card_reminder_flow import (
    action_selection_card_reminders,
    reaction_card_reminder,
)
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards import (
    CardTriggerWindow,
    CHARACTER_DECKS,
    card_action_definition,
)
from dnd_board_game.physical_cards.character_card_sets import printable_action_cards


def test_every_printable_combat_card_has_a_generic_reminder_projection() -> None:
    for actor_id in PLAYABLE_HERO_IDS:
        cards = tuple(
            card
            for card in printable_action_cards(CHARACTER_DECKS[actor_id])
            if card.kind != "universal"
        )
        available_action_ids = {
            card_action_definition(card.source_id).action_id for card in cards
        }
        action_reminders = action_selection_card_reminders(
            owner_actor_id=actor_id,
            owner_actor_name=actor_id.title(),
            available_action_ids=available_action_ids,
            labels_by_action_id={
                card_action_definition(card.source_id).action_id: card.title
                for card in cards
            },
        )
        expected_actions = {
            card.source_id
            for card in cards
            if CardTriggerWindow.ACTION_SELECTION
            in card_action_definition(card.source_id).trigger_windows
        }
        assert {item.source_id for item in action_reminders} == expected_actions

        reaction_cards = tuple(
            card
            for card in cards
            if CardTriggerWindow.ACTION_SELECTION
            not in card_action_definition(card.source_id).trigger_windows
        )
        for card in reaction_cards:
            definition = card_action_definition(card.source_id)
            for trigger in definition.trigger_windows:
                reminder = reaction_card_reminder(
                    source_id=card.source_id,
                    owner_actor_id=actor_id,
                    owner_actor_name=actor_id.title(),
                    trigger_event=trigger.value,
                    label=card.title,
                )
                assert reminder is not None
                assert reminder.source_id == card.source_id
                assert reminder.label == card.title


def test_reaction_reminder_rejects_wrong_owner_or_wrong_timing() -> None:
    assert reaction_card_reminder(
        source_id="shield",
        owner_actor_id="garran",
        owner_actor_name="Garran",
        trigger_event=CardTriggerWindow.ATTACK_ROLL_REVEALED.value,
    ) is None
    assert reaction_card_reminder(
        source_id="shield",
        owner_actor_id="nimra",
        owner_actor_name="Nimra",
        trigger_event=CardTriggerWindow.DAMAGE_ROLL_REVEALED.value,
    ) is None

    legacy_owner = reaction_card_reminder(
        source_id="hellish_rebuke",
        owner_actor_id="warlock_hero",
        owner_actor_name="Czarownik",
        trigger_event=CardTriggerWindow.AFTER_DAMAGE_APPLIED.value,
        label="Piekielna riposta",
    )
    assert legacy_owner is not None
    assert legacy_owner.source_id == "hellish_rebuke"


def test_action_reminders_include_only_currently_legal_action_ids() -> None:
    reminders = action_selection_card_reminders(
        owner_actor_id="dagna",
        owner_actor_name="Dagna",
        available_action_ids={"sacred_flame", "healing_word"},
        labels_by_action_id={
            "sacred_flame": "Święty płomień",
            "healing_word": "Leczące słowo",
        },
    )

    assert {(item.source_id, item.label) for item in reminders} == {
        ("healing_word", "Leczące słowo"),
        ("sacred_flame", "Święty płomień"),
    }
