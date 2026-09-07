"""Each completed movement segment returns to the current action choices."""

from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.actors import Actor
from dnd_board_game.combat import current_actor
from dnd_board_game.world import Coordinate
from tests.unit.test_garran_mana_movement import positioned_session
from tests.unit.test_hero_rules_consistency import heroes


@pytest.mark.parametrize(
    "hero_id", ["garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"]
)
def test_split_movement_returns_to_updated_menu_without_spending_action(
    heroes: dict[str, Actor], tmp_path: Path, hero_id: str
) -> None:
    session = positioned_session(heroes[hero_id], tmp_path, Coordinate(4, 4))
    initial = session.state_payload()["combat"]
    remaining = initial["movement"]["remaining_feet"]
    for step, row in enumerate((4, 3), start=1):
        preview = session.confirm_combat_turn_action("turn:move")["combat"]
        assert preview["turn_action_menu"]["stage"] == "preview"
        session.preview_combat_movement(col=3, row=row)
        combat = session.confirm_combat_turn_action("turn:move")["combat"]
        menu = combat["turn_action_menu"]
        assert menu["stage"] == "list"
        assert menu["preview_option_id"] is None
        assert combat["movement_preview"] is None
        assert current_actor(session.combat_state).position == Coordinate(3, row)
        assert combat["movement"]["remaining_feet"] == remaining - 5 * step
        assert session.combat_state.turn_action.action_use.value == "action_available"
        move = next(o for o in menu["options"] if o["id"] == "turn:move")
        assert move["mana_cost"] == []
        assert "bez kolejnej dopłaty" in move["mana_cost_note"]
    # A different choice opens directly; no cancellation of movement is needed.
    option = next(o for o in menu["options"] if o["shortcut"] == "SPACE")
    session.confirm_combat_turn_action(option["id"])
    assert session.combat_turn_preview_option_id == option["id"]


def test_exhausted_movement_returns_to_menu_without_move_option(
    heroes: dict[str, Actor], tmp_path: Path
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, Coordinate(8, 8))
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(session.combat_state.turn_action, movement_used_feet=25),
    )
    session.confirm_combat_turn_action("turn:move")
    session.preview_combat_movement(col=3, row=4)
    combat = session.confirm_combat_turn_action("turn:move")["combat"]
    assert combat["movement"]["remaining_feet"] == 0
    assert combat["turn_action_menu"]["stage"] == "list"
    assert combat["turn_action_menu"]["preview_option_id"] is None
    assert all(o["id"] != "turn:move" for o in combat["turn_action_menu"]["options"])


def test_opportunity_confirmation_finishes_movement_preview(
    heroes: dict[str, Actor], tmp_path: Path
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, Coordinate(3, 4))
    session.confirm_combat_turn_action("turn:move")
    session.preview_combat_movement(col=3, row=2)
    combat = session.confirm_combat_turn_action("turn:move")["combat"]
    assert combat["pending_opportunity_movement"] is not None
    assert combat["turn_action_menu"] is None
    combat = session.confirm_opportunity_movement()["combat"]
    assert combat["pending_opportunity_movement"] is None
    assert combat["movement_preview"] is None
    assert combat["turn_action_menu"]["stage"] == "list"
    assert combat["turn_action_menu"]["preview_option_id"] is None


def test_invalid_movement_keeps_destination_selection_open(
    heroes: dict[str, Actor], tmp_path: Path
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, Coordinate(8, 8))
    session.confirm_combat_turn_action("turn:move")
    before = session.combat_state
    with pytest.raises(ValueError):
        session.submit_combat_movement(col=100, row=100)
    assert session.combat_state == before
    assert session.state_payload()["combat"]["turn_action_menu"]["stage"] == "preview"
