from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game import Game
from src.hero import Hero
from ui_client import DEBUG_UNDO_COMMAND, UIClient, UndoRequested, set_default_ui_client


class _DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return True

    def scan_board(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return True


class _UndoState:
    def __init__(self, game):
        self.game = game
        self.counter = 0

    def set_context(self, game):
        self.game = game
        return self

    def mutate(self):
        self.counter += 1
        hero = Hero()
        hero.name = "Temp"
        self.game.heroes.append(hero)
        return {"ok": True}

    def mutate_and_undo(self):
        self.counter += 1
        hero = Hero()
        hero.name = "Temp"
        self.game.heroes.append(hero)
        raise UndoRequested("undo")


def test_ui_client_raises_undo_requested_for_debug_command(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "answered", "answer": DEBUG_UNDO_COMMAND}

    monkeypatch.setattr("ui_client.requests.get", lambda *_a, **_k: _Resp())
    client = UIClient(base_url="http://127.0.0.1:5200")
    with pytest.raises(UndoRequested):
        client._wait_for_text_answer("1", max_wait=0.01)


def test_ui_client_maps_debug_undo_to_back_inside_character_creation(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "answered",
                "answer": DEBUG_UNDO_COMMAND,
                "source": "character_creation",
            }

    monkeypatch.setattr("ui_client.requests.get", lambda *_a, **_k: _Resp())
    client = UIClient(base_url="http://127.0.0.1:5200")
    answer = client._wait_for_text_answer("1", max_wait=0.01)
    assert answer == "/back"


def test_manual_undo_restores_previous_action_snapshot(monkeypatch):
    monkeypatch.setenv("GAME_DEBUG_TRACE", "0")
    monkeypatch.setenv("GAME_DEBUG_UNDO", "1")
    monkeypatch.delenv("PLAYER_UI_URL", raising=False)
    set_default_ui_client(UIClient(base_url=None))

    game = Game(conn=_DummyConnection(), scenario="test_chameleon_gnome")
    game.state = _UndoState(game)
    initial_heroes = len(game.heroes)

    game.run_action("mutate")
    assert len(game.heroes) == initial_heroes + 1
    assert int(getattr(game.state, "counter", 0)) == 1

    assert game.undo_last_action()
    assert len(game.heroes) == initial_heroes
    assert int(getattr(game.state, "counter", 0)) == 0


def test_run_action_undo_requested_restores_and_does_not_raise(monkeypatch):
    monkeypatch.setenv("GAME_DEBUG_TRACE", "0")
    monkeypatch.setenv("GAME_DEBUG_UNDO", "1")
    monkeypatch.delenv("PLAYER_UI_URL", raising=False)
    set_default_ui_client(UIClient(base_url=None))

    game = Game(conn=_DummyConnection(), scenario="test_chameleon_gnome")
    game.state = _UndoState(game)
    initial_heroes = len(game.heroes)

    result = game.run_action("mutate_and_undo")
    assert result is None
    assert len(game.heroes) == initial_heroes
    assert int(getattr(game.state, "counter", 0)) == 0
