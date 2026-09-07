"""Spent turn budgets remove choices from both payloads and command dispatch."""

from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.combat import ActionUse, current_actor
from dnd_board_game.combat.session import TurnActionState
from dnd_board_game.combat.physical_mana import effect
from tests.unit.test_recruitment_arena import arena, begin


@pytest.mark.parametrize("hero_id", HERO_ORDER)
def test_spent_budgets_remove_every_choice_and_reject_stale_selection(
    hero_id: str, tmp_path: Path
) -> None:
    s = arena(tmp_path)
    begin(s, hero_id)
    before = s.combat_state
    original = s._combat_turn_action_menu_payload()["options"]
    for changes, missing in [
        ({"action_use": ActionUse.ACTION_USED}, {"action", "modifier"}),
        ({"bonus_action_use": ActionUse.ACTION_USED}, {"bonus_action"}),
        ({"movement_used_feet": 100}, {"movement"}),
        (
            {
                "action_use": ActionUse.ACTION_USED,
                "bonus_action_use": ActionUse.ACTION_USED,
                "movement_action_used": True,
            },
            {"action", "modifier", "bonus_action", "movement"},
        ),
    ]:
        s.combat_state = replace(
            before, turn_action=replace(before.turn_action, **changes)
        )
        options = s._combat_turn_action_menu_payload()["options"]
        assert not any(o["action_economy"] in missing for o in options)
        assert any(o["id"] == "turn:end" for o in options)
        stale = [o for o in original if o["action_economy"] in missing]
        for option in stale:
            state = s.combat_state
            with pytest.raises(ValueError, match="aktualnej listy"):
                s.confirm_combat_turn_action(option["id"])
            assert s.combat_state == state
    # A fresh turn restores all choices governed only by the turn budgets.
    s.combat_state = replace(before, turn_action=TurnActionState())
    assert {o["id"] for o in s._combat_turn_action_menu_payload()["options"]} == {
        o["id"] for o in original
    }


def test_partial_movement_stays_available_until_exhausted(tmp_path: Path) -> None:
    s = arena(tmp_path)
    begin(s, "garran")
    for used, expected in [(5, True), (25, True), (26, False), (30, False)]:
        s.combat_state = replace(
            s.combat_state,
            turn_action=replace(s.combat_state.turn_action, movement_used_feet=used),
        )
        assert (
            any(o.id == "turn:move" for o in s._combat_turn_action_options())
            == expected
        )


@pytest.mark.parametrize(
    "hero_id,source_id",
    [("lorian", "basic"), ("lorian", "optical_scope"), ("erynd", "double_shot")],
)
def test_only_started_attack_can_continue_after_spending_main_action(
    hero_id: str, source_id: str, tmp_path: Path
) -> None:
    s = arena(tmp_path)
    begin(s, hero_id)
    actor = current_actor(s.combat_state)
    if source_id != "basic":
        from dnd_board_game.combat.erynd_features import prepare_erynd_arrow
        from dnd_board_game.combat.lorian_features import prepare_lorian_shot

        prepare = prepare_erynd_arrow if hero_id == "erynd" else prepare_lorian_shot
        s.active_combat_effects = prepare(
            s.combat_state, (), action_id=source_id
        ).active_effects
        source = next(
            a for a in s._attack_sources_for_actor(actor) if a.id == source_id
        )
    else:
        selected = next(
            o
            for o in s._combat_turn_action_menu_payload()["options"]
            if o["shortcut"] == "SPACE"
        )
        source = next(
            a
            for a in s._attack_sources_for_actor(actor)
            if a.id == selected["source_id"]
        )
    s.active_combat_effects += (
        replace(
            effect(hero_id, "mana_series_source", "Rodzaj serii"), object_id=source_id
        ),
    )
    if source_id == "basic":
        s.active_combat_effects += (effect(hero_id, "mana_attack_series", "Seria", 2),)
    s.combat_state = replace(
        s.combat_state,
        turn_action=replace(
            s.combat_state.turn_action,
            action_use=ActionUse.ACTION_USED,
            attack_action_active=True,
            attacks_used=1,
            attacks_maximum=2,
        ),
    )
    options = s._combat_turn_action_menu_payload()["options"]
    attacks = [o for o in options if o["action_economy"] == "action"]
    assert attacks and any(o["source_id"] == source.id for o in attacks)
    assert all(o["action"] == "select_attack_source" for o in attacks)
    if source_id != "basic":
        assert all(o["source_id"] == source_id for o in attacks)
    s.combat_state = replace(
        s.combat_state, turn_action=replace(s.combat_state.turn_action, attacks_used=2)
    )
    assert not any(
        o["action_economy"] == "action"
        for o in s._combat_turn_action_menu_payload()["options"]
    )
