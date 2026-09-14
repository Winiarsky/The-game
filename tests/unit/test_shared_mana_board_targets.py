from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat import current_actor
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui.shared_mana import command, payload
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.world import Coordinate
from tests.unit.test_initiative_panel import Board
from tests.unit.test_recruitment_arena import arena, begin


def send(session, action: str, **values):
    return command(session, dict(command=action, revision=session.combat_state.shared_mana.revision, **values))


def support_session(tmp_path: Path, hero: str = "garran"):
    session = arena(tmp_path)
    begin(session, hero)
    owner = current_actor(session.combat_state)
    actors = tuple(replace(a, position=Coordinate(8, 8) if a.id == owner.id else Coordinate(2, 2))
                   for a in session.combat_state.actors)
    allies = tuple(replace(training_hero(name), position=pos) for name, pos in
                   (("mira", Coordinate(9, 8)), ("brakka", Coordinate(8, 9)),
                    ("erynd", Coordinate(9, 9)), ("lorian", Coordinate(16, 16))) if name != hero)
    session.combat_state = replace(session.combat_state, actors=(*actors, *allies))
    board = Board()
    session.attach_board_connection(board, backend="simulator")
    return session, board


def shield_bonus(tmp_path: Path, count: int = 2):
    session, board = support_session(tmp_path)
    session.use_combat_class_feature("garran_shield_wall")
    send(session, "boost", boost_id="ward", count=count)
    send(session, "pay")
    assert session.shared_mana_declaration.stage == "bonus"
    return session, board


def click(session, board: Board, position: Coordinate):
    board.selected = position.as_tuple()
    return session.scan_board_selection(automatic=True)


def test_legal_allies_light_dim_and_toggle_brighter_without_spending_again(tmp_path: Path) -> None:
    session, board = shield_bonus(tmp_path)
    fields = {Coordinate(9, 8), Coordinate(8, 9), Coordinate(9, 9)}
    assert set(session._current_board_scan_target().positions) == fields
    assert session.state_payload()["board_selection"]["auto_arm"]
    assert all(board.leds[p.as_tuple()] == LedColor.LEGAL_ABILITY_TARGET for p in fields)
    market = session.combat_state.shared_mana.market
    click(session, board, Coordinate(9, 8))
    assert board.leds[(9, 8)] == LedColor.SELECTED_ABILITY_TARGET
    assert board.leds[(8, 9)] == LedColor.LEGAL_ABILITY_TARGET
    assert panel_position(28) in session._current_board_scan_target().positions
    assert session.shared_mana_declaration.selected_target_ids == ("mira",)
    click(session, board, Coordinate(9, 8))
    assert board.leds[(9, 8)] == LedColor.LEGAL_ABILITY_TARGET
    assert panel_position(28) not in session._current_board_scan_target().positions
    assert session.combat_state.shared_mana.market == market
    assert all(a.temp_hp == 0 for a in session.combat_state.actors)


def test_two_allies_commit_together_with_one_board_accept(tmp_path: Path) -> None:
    session, board = shield_bonus(tmp_path)
    click(session, board, Coordinate(9, 8))
    click(session, board, Coordinate(8, 9))
    for pos in ((9, 8), (8, 9)):
        assert board.leds[pos] == LedColor.SELECTED_ABILITY_TARGET
    click(session, board, panel_position(28))
    assert session.shared_mana_declaration is None
    assert {str(a.id): a.temp_hp for a in session.combat_state.actors if a.temp_hp} == {"mira": 5, "brakka": 5}
    assert session.combat_state.shared_mana.market == 1


def test_back_clears_paid_selection_and_keeps_the_paid_action(tmp_path: Path) -> None:
    session, board = shield_bonus(tmp_path)
    click(session, board, Coordinate(9, 8))
    click(session, board, panel_position(29))
    assert session.shared_mana_declaration.stage == "bonus"
    assert session.shared_mana_declaration.selected_target_ids == ()
    assert session.combat_state.shared_mana.market == 1
    assert panel_position(28) not in session._current_board_scan_target().positions


def test_limits_illegal_targets_and_stale_scans_do_not_change_selection(tmp_path: Path) -> None:
    session, board = shield_bonus(tmp_path)
    revision = session._board_selection_payload()["revision"]
    click(session, board, Coordinate(9, 8))
    scans = board.scans
    session.scan_board_selection(expected_revision=revision, automatic=True)
    assert board.scans == scans
    click(session, board, Coordinate(8, 9))
    with pytest.raises(ValueError, match="limit"):
        send(session, "target", target_id="erynd")
    client = create_app(session).test_client()
    for key in ("garran", "lorian", "nonexistent"):
        response = client.post('/api/combat/shared-mana', json=dict(command="target", target_id=key,
            revision=session.combat_state.shared_mana.revision))
        assert response.status_code == 400
    assert session.shared_mana_declaration.selected_target_ids == ("mira", "brakka")
    assert all(a.temp_hp == 0 for a in session.combat_state.actors)


def test_revalidate_all_targets_before_applying_any_effect(tmp_path: Path) -> None:
    session, _ = shield_bonus(tmp_path)
    send(session, "target", target_id="mira")
    send(session, "target", target_id="brakka")
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(a, position=Coordinate(16, 15)) if str(a.id) == "brakka" else a
        for a in session.combat_state.actors))
    with pytest.raises(ValueError, match="legalny cel"):
        send(session, "bonus")
    assert all(a.temp_hp == 0 for a in session.combat_state.actors)
    assert panel_position(28) not in session._current_board_scan_target().positions


def test_partial_confirmation_requires_different_ally_for_next_ward(tmp_path: Path) -> None:
    session, board = shield_bonus(tmp_path)
    send(session, "parameters", target_id="mira")
    click(session, board, panel_position(28))
    assert session.shared_mana_declaration.resume_arguments["remaining"] == 1
    assert Coordinate(9, 8) not in session._current_board_scan_target().positions
    assert board.leds[(9, 8)] == LedColor.SELECTED_ABILITY_TARGET
    with pytest.raises(ValueError, match="legalny cel"):
        send(session, "target", target_id="mira")
    click(session, board, Coordinate(8, 9))
    click(session, board, panel_position(28))
    assert session.shared_mana_declaration is None


def test_caring_gesture_target_before_payment_and_roll_after_payment_on_board(tmp_path: Path) -> None:
    session, board = support_session(tmp_path, "dagna")
    session.use_combat_class_feature("caring_gesture")
    assert panel_position(28) not in session._current_board_scan_target().positions
    click(session, board, Coordinate(9, 8))
    click(session, board, panel_position(28))
    assert session.shared_mana_declaration.stage == "effect_roll"
    assert board.leds[(9, 8)] == LedColor.SELECTED_ABILITY_TARGET
    click(session, board, panel_position(27))
    assert session.shared_mana_declaration.resume_arguments["natural_roll"] == 2
    click(session, board, panel_position(28))
    assert session.shared_mana_declaration is None
    assert next(a for a in session.combat_state.actors if str(a.id) == "mira").temp_hp > 0


def test_old_browser_dice_context_does_not_hide_targets_or_stream_repeated_clicks(tmp_path: Path) -> None:
    session, board = shield_bonus(tmp_path)
    session.board_panel_context = ("dice:old:0:false", (26, 27, 28), True)
    selection = session._board_selection_payload()
    assert selection["input_mode"] == "single"
    assert selection["auto_arm"] and selection["mode"] == "mana_targets"
    click(session, board, Coordinate(9, 8))
    assert payload(session)["declaration"]["target_selection"]["selected_ids"] == ["mira"]
    assert session.board_panel_context is None


@pytest.mark.parametrize("hero,ability", [("lorian", "mana_inspiration"), ("garran", "counterattack_command")])
def test_single_target_changes_selection_and_back_cancels_unpaid_action(tmp_path: Path, hero: str, ability: str) -> None:
    session, board = support_session(tmp_path, hero)
    session.use_combat_class_feature(ability)
    assert panel_position(28) not in session._current_board_scan_target().positions
    click(session, board, Coordinate(9, 8))
    click(session, board, Coordinate(8, 9))
    assert payload(session)["declaration"]["target_selection"]["selected_ids"] == ["brakka"]
    assert board.leds[(9, 8)] == LedColor.LEGAL_ABILITY_TARGET
    assert board.leds[(8, 9)] == LedColor.SELECTED_ABILITY_TARGET
    click(session, board, panel_position(29))
    assert session.shared_mana_declaration is None
    assert session.combat_state.shared_mana.market == 5


@pytest.mark.parametrize("roll", [0, 7, False])
def test_rally_still_rejects_invalid_dice_before_applying_healing(tmp_path: Path, roll: object) -> None:
    session, _ = support_session(tmp_path)
    session.use_combat_class_feature("garran_rally")
    send(session, "boost", boost_id="heal", count=1)
    send(session, "pay")
    send(session, "target", target_id="mira")
    send(session, "parameters", natural_roll=roll)
    before = session.combat_state
    with pytest.raises(ValueError, match="k6"):
        send(session, "bonus")
    assert session.combat_state == before
    assert session.shared_mana_declaration is not None
