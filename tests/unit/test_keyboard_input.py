"""Keyboard candidates are read-only and commits reuse the active game flow."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.rules.resonance import ResonanceChain, ResonanceEntry
from dnd_board_game.ui import input_context, resonance
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.input_commands import cursor_position, cursor_step
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.world import Coordinate
from tests.integration.test_combat_board_feedback import combat
from tests.unit.test_mission_zero import session, start_battle
from scripts.keyboard_playtest import prepare_session


def send(game: ExplorationUiSession, action: str, **data: Any) -> dict[str, Any]:
    view = input_context.payload(game)
    return input_context.command(game, dict(command=action, context=view["context"],
                                            revision=view["revision"], **data))


def test_cursor_crosses_obstacles_but_never_enters_panel_or_wraps() -> None:
    assert cursor_step(Coordinate(18, 0), 1, -1) == Coordinate(18, 0)
    assert cursor_step(Coordinate(0, 29), -1, 1) == Coordinate(0, 29)
    assert cursor_step(Coordinate(4, 3), 1, 0) == Coordinate(5, 3)
    for value in ([19, 1], [-1, 0], [0, 30], [True, 1], [1.5, 2]):
        with pytest.raises(ValueError):
            cursor_position(value)


def test_arrow_preview_and_cancel_do_not_change_combat_or_rng(tmp_path: Path) -> None:
    game, board, _, _ = combat(tmp_path)
    game.configure_input_mode("keyboard")
    send(game, "shortcut", id="move")
    before, rng = repr(game.combat_state), game.encounter_rng.getstate()
    context = input_context.payload(game)["context"]
    for position in ([3, 5], [1, 3]):
        result = send(game, "cursor", position=position)
        assert result["input"]["context"] == context
        assert result["input"]["preview"]["path"]
        assert repr(game.combat_state) == before
        assert game.encounter_rng.getstate() == rng
        assert board.leds[tuple(position)] == LedColor.MOVEMENT_DESTINATION
    send(game, "back")
    assert resonance.engine(game).active.position == Coordinate(3, 3)
    assert resonance.engine(game).fighter().base_spent == 0


def test_enter_commits_selected_movement_once_and_rejects_stale_request(tmp_path: Path) -> None:
    game, _, _, _ = combat(tmp_path)
    game.configure_input_mode("keyboard")
    send(game, "shortcut", id="move")
    send(game, "cursor", position=[3, 5])
    view = input_context.payload(game)
    data = dict(command="accept", context=view["context"], revision=view["revision"])
    client = create_app(game).test_client()
    response = client.post("/api/input/command", json=data)
    assert response.status_code == 200, response.json
    assert resonance.engine(game).active.position == Coordinate(3, 5)
    spent = resonance.engine(game).fighter().base_spent
    assert spent == 2
    response = client.post("/api/input/command", json=data)
    assert response.status_code == 400
    assert resonance.engine(game).fighter().base_spent == spent


def test_keyboard_preview_explains_confirmation_without_spending_movement(tmp_path: Path) -> None:
    game, _, _, _ = combat(tmp_path)
    game.configure_input_mode("keyboard")
    send(game, "shortcut", id="move")
    before = repr(game.combat_state)
    result = send(game, "cursor", position=[3, 5])
    assert result["input"]["can_accept"]
    assert result["input"]["accept_label"] == "Wykonaj ruch"
    assert result["input"]["preview"]["cost"] == 2
    assert "potwierdza ruch" in result["combat"]["resonance"]["decision"]["prompt"]
    assert repr(game.combat_state) == before
    result = send(game, "cursor", position=[5, 3])
    assert not result["input"]["can_accept"]
    assert result["combat"]["resonance"]["decision"]["prompt"] == result["input"]["notice"]
    assert repr(game.combat_state) == before


def test_end_turn_lists_unspent_turn_budgets_without_expiring_reaction(tmp_path: Path) -> None:
    game, _, _, _ = combat(tmp_path)
    game.configure_input_mode("keyboard")
    send(game, "shortcut", id="end")
    resources = resonance.payload(game)["decision"]["unused_resources"]
    assert "atak / przedmiot" in resources
    assert "akcja specjalna" in resources
    assert any(label.startswith("ruch:") for label in resources)
    assert not any("reakcja" in label for label in resources)
    send(game, "back")
    assert resonance.engine(game).fighter().reaction


def test_invalid_candidate_cannot_commit_previous_legal_destination(tmp_path: Path) -> None:
    game, board, _, _ = combat(tmp_path)
    game.configure_input_mode("keyboard")
    send(game, "shortcut", id="move")
    send(game, "cursor", position=[3, 5])
    result = send(game, "cursor", position=[5, 3])  # blocking terrain
    assert not result["input"]["can_accept"]
    assert board.leds[(5, 3)] == LedColor.ATTACK_MISS
    with pytest.raises(ValueError):
        send(game, "accept")
    assert resonance.engine(game).active.position == Coordinate(3, 3)


def test_enemy_target_preview_reads_rejection_and_does_not_change_target_queue(tmp_path: Path) -> None:
    game, _, blocked, legal = combat(tmp_path)
    game.configure_input_mode("keyboard")
    send(game, "shortcut", id="attack")
    before = repr(game.combat_state)
    for actor_id in (legal, blocked, legal):
        position = list(resonance.engine(game).actor(actor_id).position)
        result = send(game, "cursor", position=position)
        assert repr(game.combat_state) == before
        assert result["input"]["valid"] == (actor_id == legal)
        assert result["combat"]["resonance"]["decision"]["target_ids"] == [actor_id]
    send(game, "accept")
    assert resonance.engine(game).s.task["type"] == "roll"


def test_multi_target_arrows_do_not_add_or_toggle_targets(tmp_path: Path) -> None:
    game, _, _, legal = combat(tmp_path)
    e = resonance.engine(game)
    e.s.chain = ResonanceChain(1, [ResonanceEntry(r, "erynd", r) for r in ("Oko", "Węzeł")], ["erynd"])
    game.combat_state = e.combat_state()
    game.configure_input_mode("keyboard")
    send(game, "activate", id="double_shot")
    before = repr(game.combat_state)
    position = list(resonance.engine(game).actor(legal).position)
    for _ in range(3):
        send(game, "cursor", position=position)
        assert resonance.engine(game).s.preview["targets"] == []
        assert repr(game.combat_state) == before
    send(game, "select")
    assert resonance.engine(game).s.preview["targets"] == [legal]
    send(game, "cursor", position=position)
    send(game, "select")
    assert resonance.engine(game).s.preview["targets"] == [legal, legal]
    send(game, "accept")
    assert resonance.engine(game).s.phase != "preview"


def test_flame_area_selection_preserves_separate_exclusion_step(tmp_path: Path) -> None:
    game, _, _, _ = combat(tmp_path)
    e = resonance.engine(game)
    e.s.index = e.s.order.index("nimra")
    e.begin_turn()
    e.s.chain = ResonanceChain(1, [ResonanceEntry(r, "nimra", r) for r in ("Oko", "Węzeł")], ["nimra"])
    game.combat_state = e.combat_state()
    game.configure_input_mode("keyboard")
    initial = send(game, "activate", id="flame_fan")
    assert initial["input"]["can_accept"]
    assert initial["input"]["accept_label"] == "Wybierz obszar"
    fields = input_context.payload(game)["fields"]
    center = fields[0]
    before = repr(game.combat_state)
    preview = send(game, "cursor", position=center)
    assert preview["input"]["accept_label"] == "Wybierz obszar"
    assert "Precyzyjny splot" not in preview["combat"]["resonance"]["decision"]["prompt"]
    assert repr(game.combat_state) == before
    result = send(game, "accept")
    assert result["combat"]["resonance"]["phase"] == "preview"
    assert resonance.engine(game).s.preview["center"] == center
    assert not resonance.engine(game).s.preview["exclude_chosen"]
    assert any(control["command"] == "exclude" for control in result["combat"]["resonance"]["controls"])
    # Skipping the exclusion remains a separate choice and does not spend the power.
    before_skip = resonance.engine(game).fighter().charges
    result = send(game, "activate", id="control:28")
    assert resonance.engine(game).s.preview["exclude_chosen"]
    assert resonance.engine(game).fighter().charges == before_skip
    assert result["combat"]["resonance"]["phase"] == "preview"
    send(game, "accept")
    assert resonance.engine(game).s.phase != "preview"
    assert resonance.engine(game).fighter().charges < before_skip


def test_readonly_menu_owns_keyboard_and_cannot_confirm_combat_underneath(tmp_path: Path) -> None:
    game, _, _, legal = combat(tmp_path)
    game.configure_input_mode("keyboard")
    send(game, "shortcut", id="attack")
    resonance.command(game, dict(command="select", revision=game.combat_state.resonance.revision,
                                position=list(resonance.engine(game).actor(legal).position)))
    before = repr(game.combat_state)
    game.configure_board_panel("session-menu:keyboard-test", [26, 27, 28, 29], True)
    assert not input_context.payload(game)["controls"]
    result = send(game, "accept")
    assert result["panel_event"]["context"] == "session-menu:keyboard-test"
    assert result["input"]["revision"] == input_context.payload(game)["revision"]
    result = input_context.command(game, dict(command="adjust", delta=1,
        revision=result["input"]["revision"], context=result["input"]["context"]))
    assert result["panel_event"]["slot"] == 26
    assert repr(game.combat_state) == before
    with pytest.raises(ValueError):
        send(game, "shortcut", id="move")


@pytest.mark.parametrize("hero", ("garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"))
def test_keyboard_action_menu_uses_current_hero_catalog(tmp_path: Path, hero: str) -> None:
    game = session(tmp_path, legacy_combat=False)
    members = tuple(dict.fromkeys((hero, "garran", "nimra", "erynd")))[:3]
    game.configure_custom_party(tuple(training_hero(key) for key in members))
    start_battle(game)
    e = resonance.engine(game)
    e.s.index = e.s.order.index(hero)
    e.begin_turn()
    game.combat_state = e.combat_state()
    game.configure_input_mode("keyboard")
    controls = input_context.payload(game)["controls"]
    assert {c.id for c in resonance.engine(game).cards()} <= {c["id"] for c in controls}
    send(game, "shortcut", id="move")
    assert resonance.engine(game).s.preview["id"] == "move"


def test_keyboard_profile_survives_reset_load_and_disables_scans(tmp_path: Path) -> None:
    game, _, _, _ = combat(tmp_path)
    game.configure_input_mode("keyboard")
    view = game.state_payload()
    assert not view["board_selection"]["auto_arm"]
    with pytest.raises(ValueError, match="skaner"):
        game.scan_board_selection()
    game.save_snapshot()
    old_revision = input_context.payload(game)["revision"]
    game.load_snapshot()
    assert game.input_mode == "keyboard"
    assert input_context.payload(game)["revision"] != old_revision
    game.reset()
    assert game.input_mode == "keyboard"
    assert not game.state_payload()["board_selection"]["auto_arm"]


def test_keyboard_commit_matches_existing_board_command_path(tmp_path: Path) -> None:
    keyboard, _, _, _ = combat(tmp_path / "keyboard")
    reference, _, _, _ = combat(tmp_path / "reference")
    keyboard.configure_input_mode("keyboard")
    send(keyboard, "shortcut", id="move")
    send(keyboard, "cursor", position=[3, 5])
    send(keyboard, "accept")
    for action, extra in (("choose", dict(id="move")), ("select", dict(position=[3, 5])), ("accept", {})):
        resonance.command(reference, dict(command=action, revision=reference.combat_state.resonance.revision, **extra))
    assert keyboard.combat_state == reference.combat_state
    assert keyboard.encounter_rng.getstate() == reference.encounter_rng.getstate()


def test_keyboard_can_start_without_board_and_reset_preserves_readiness(tmp_path: Path) -> None:
    game = ExplorationUiSession("content/scenarios/abandoned_watchtower/scenario.json",
                                save_dir=tmp_path / "saves", observation_dir=tmp_path / "logs")
    game.configure_input_mode("keyboard")
    game.reset()
    assert game.board_adapter is None
    assert game.state_payload()["flow"]["can_start"]
    assert game.start_session()["flow"]["stage"] != "waiting_for_board"


def test_keyboard_full_battle_setup_and_initiative_without_scanner(tmp_path: Path) -> None:
    game = prepare_session(tmp_path, ("garran", "brakka", "nimra"), arena=True)
    setup = game.encounter_setup_flow
    for _ in range(100):
        if setup.completed:
            break
        if setup.is_player_start_step:
            actor = setup.current_player_start_actor
            candidate = list(setup.remaining_player_start_positions()[0])
            send(game, "cursor", position=candidate)
            send(game, "accept")
            assert setup.pending_start_position == Coordinate(*candidate)
            send(game, "accept")
            assert str(actor.id) in setup.player_start_assignments
        else:
            send(game, "accept")
    assert setup.completed
    send(game, "accept")  # Start initiative.
    for _ in range(40):
        if game.combat_state:
            break
        view = input_context.payload(game)
        if view["kind"] == "dice":
            send(game, "adjust", delta=1)
        send(game, "accept")
    assert game.combat_state and game.combat_state.resonance
    assert game.input_mode == "keyboard" and game.board_adapter is None
