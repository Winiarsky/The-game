from __future__ import annotations

import pytest

from dnd_board_game.runtime import exploration_ui


def test_runtime_blanks_board_when_ctrl_c_stops_server(monkeypatch, capsys) -> None:
    events: list[str] = []

    class FakeSession:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def shutdown_board(self) -> bool:
            events.append("shutdown_board")
            return True

    class FakeApp:
        def run(self, **_kwargs) -> None:
            raise KeyboardInterrupt

    monkeypatch.setattr(exploration_ui, "ExplorationUiSession", FakeSession)
    monkeypatch.setattr(exploration_ui, "create_app", lambda _session: FakeApp())

    with pytest.raises(KeyboardInterrupt):
        exploration_ui.main(["--gm-classifier", "none"])

    assert events == ["shutdown_board"]
    assert "LED-y wygaszone" in capsys.readouterr().out
