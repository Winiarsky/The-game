"""Action economy groups must reflect costs, not spell names or keyboard keys."""

from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.combat import ActionUse
from dnd_board_game.rules.physical_mana import mana_ability
from tests.unit.test_recruitment_arena import arena, begin


@pytest.mark.parametrize("hero_id", HERO_ORDER)
def test_current_hero_menu_groups_match_ability_costs(
    hero_id: str, tmp_path: Path
) -> None:
    session = arena(tmp_path)
    begin(session, hero_id)
    if hero_id == "brakka":
        session.use_combat_class_feature("rage")
    options = session._combat_turn_action_menu_payload()["options"]
    assert (
        next(o for o in options if o["action"] == "move")["action_economy"]
        == "movement"
    )
    assert (
        next(o for o in options if o["shortcut"] == "SPACE")["action_economy"]
        == "action"
    )
    assert (
        next(o for o in options if o["id"] == "turn:end")["action_economy"] == "control"
    )
    assert (
        next(o for o in options if o["id"] == "menu:weapons")["action_economy"]
        == "control"
    )
    for option in options:
        assert option["action_economy_label"]
        ability = mana_ability(
            hero_id, option["action_id"] or option["source_id"] or ""
        )
        if ability:
            assert (
                option["action_economy"]
                == {
                    "A": "action",
                    "D": "bonus_action",
                    "R": "reaction",
                    "MOD": "modifier",
                }[ability.timing]
            )


def test_garran_shield_remains_in_bonus_column_after_main_action(
    tmp_path: Path,
) -> None:
    session = arena(tmp_path)
    begin(session, "garran")
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action, action_use=ActionUse.ACTION_USED
        ),
    )
    menu = session._combat_turn_action_menu_payload()
    shield = next(o for o in menu["options"] if o["action_id"] == "shield_bash")
    assert (shield["action_economy"], shield["shortcut"], shield["mana_cost"]) == (
        "bonus_action",
        "E",
        ["C", "N"],
    )


def test_free_mark_transfer_does_not_claim_a_bonus_action(tmp_path: Path) -> None:
    from dnd_board_game.combat import current_actor
    from dnd_board_game.combat.context_menu import (
        CombatMenuAction,
        CombatMenuCategory,
        CombatMenuOption,
    )
    from dnd_board_game.ui.combat_menu_layout import menu_action_economy_payload

    session = arena(tmp_path)
    begin(session, "erynd")
    option = CombatMenuOption(
        "combat-action:hunters_mark:transfer",
        "Przenieś znak",
        "",
        CombatMenuCategory.MAGIC,
        CombatMenuAction.COMBAT_ACTION,
        action_id="hunters_mark",
    )
    assert (
        menu_action_economy_payload(option, current_actor(session.combat_state))[
            "action_economy"
        ]
        == "free"
    )
