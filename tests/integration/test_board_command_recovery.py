"""Rejected game commands can re-arm; hardware errors require an explicit retry."""
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from tests.unit.test_initiative_panel import Board
from tests.unit.test_mission_zero import session, start_battle


def test_rejected_received_command_is_marked_logged_and_leaves_reader_unlocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = start_battle(session(tmp_path, legacy_combat=False))
    board = Board()
    board.selected = panel_position(12).as_tuple()
    game.attach_board_connection(board, backend="simulator")
    client = create_app(game).test_client()
    before = deepcopy(game.combat_state.resonance.as_payload())
    revision = game._board_selection_payload()["revision"]
    events: list[tuple[str, dict[str, Any]]] = []
    handle = game._handle_board_position

    def reject(position: Coordinate) -> dict[str, object]:
        raise ValueError("Nieaktualny wybór celu.")

    monkeypatch.setattr(game, "_record", lambda name, payload: events.append((name, payload)))
    monkeypatch.setattr(game, "_handle_board_position", reject)
    result = client.post("/api/board/scan", json=dict(revision=revision, automatic=True))
    assert result.status_code == 400
    assert result.json["error_kind"] == "command_rejected"
    assert result.json["state"]["board_selection"]["revision"] == revision
    assert game.combat_state.resonance.as_payload() == before
    assert game._board_scan_lock.acquire(blocking=False)
    game._board_scan_lock.release()
    rejected = [payload for name, payload in events if name == "ui_board_command_rejected"]
    assert len(rejected) == 1
    assert rejected[0]["position"] == list(board.selected)
    assert rejected[0]["error"] == "Nieaktualny wybór celu."
    monkeypatch.setattr(game, "_handle_board_position", handle)
    retried = client.post("/api/board/scan", json=dict(revision=revision, automatic=True))
    assert retried.status_code == 200
    assert game.combat_state.resonance.preview["id"] == "second_wind"


@pytest.mark.parametrize("failure", ["prepare", "receive"])
def test_hardware_value_errors_do_not_get_the_command_retry_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    game = start_battle(session(tmp_path, legacy_combat=False))
    board = Board()
    board.selected = panel_position(12).as_tuple()
    game.attach_board_connection(board, backend="simulator")

    def broken_hardware(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("Nieprawidłowa odpowiedź kontrolera.")

    if failure == "prepare":
        monkeypatch.setattr(game.board_adapter, "prepare_scan", broken_hardware)
    else:
        monkeypatch.setattr(board, "scan_board", broken_hardware)
    result = create_app(game).test_client().post("/api/board/scan", json=dict(automatic=True))
    assert result.status_code == 400
    assert "error_kind" not in result.json
    assert result.json["error"] == "Nieprawidłowa odpowiedź kontrolera."
    assert game._board_scan_lock.acquire(blocking=False)
    game._board_scan_lock.release()
