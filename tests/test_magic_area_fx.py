from types import SimpleNamespace
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from board_grid import BoardGrid
from GameObjects.events.base import EventContext
from GameObjects.events.magic.level_1st import events as lvl1


class FakeConn:
    def __init__(self, responses):
        self.responses = list(responses)

    def set_leds(self, positions, colors):
        return None

    def scan_board(self, _positions=None):
        if not self.responses:
            return None
        return self.responses.pop(0)

    def leds_off(self):
        return None


def _game_with_board(board, responses):
    return SimpleNamespace(
        board=board,
        conn=FakeConn(responses),
        ui_log=lambda *_args, **_kwargs: None,
    )


def test_directional_area_confirmation_triggers_led_animation(monkeypatch):
    board = BoardGrid(rows=5, cols=5)
    origin = (2, 2)
    game = _game_with_board(board, responses=[(3, 2)])
    ctx = EventContext(game=game)

    calls = []
    monkeypatch.setattr(
        lvl1,
        "animate_area_wave",
        lambda conn, effect_origin, area_positions, **_kwargs: calls.append((effect_origin, list(area_positions))) or True,
    )

    direction, positions = lvl1._pick_line_from_caster(
        ctx,
        origin,
        steps=3,
        prompt_name="Test Line",
        source="test_line",
        vibe="air",
    )

    assert direction == "E"
    assert positions
    assert calls == [(origin, positions)]


def test_centered_area_confirmation_triggers_led_animation(monkeypatch):
    board = BoardGrid(rows=5, cols=5)
    origin = (2, 2)
    center = (3, 2)
    game = _game_with_board(board, responses=[center, center])
    ctx = EventContext(game=game)

    calls = []
    monkeypatch.setattr(
        lvl1,
        "animate_area_wave",
        lambda conn, effect_origin, area_positions, **_kwargs: calls.append((effect_origin, list(area_positions))) or True,
    )

    selected_center, area_positions = lvl1._pick_centered_area(
        ctx,
        origin,
        max_range_feet=30,
        radius_feet=10,
        prompt_name="Test Burst",
        vibe="fire",
    )

    assert selected_center == center
    assert area_positions
    assert calls == [(center, area_positions)]
