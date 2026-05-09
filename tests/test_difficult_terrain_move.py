import sys
from pathlib import Path
import types
import importlib
import importlib.util

# ensure src on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# podmień stub z conftest na realny move_utils
MOVE_UTILS_PATH = SRC_ROOT / "actions" / "move_utils.py"
spec = importlib.util.spec_from_file_location("actions.move_utils", MOVE_UTILS_PATH)
move_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(move_utils)  # type: ignore[arg-type]
sys.modules["actions.move_utils"] = move_utils

import GameObjects.events.move_event as move_event  # noqa: E402

importlib.reload(move_event)

from board_grid import BoardGrid  # noqa: E402
from GameObjects.Terrains.rumble_terrain import RumbleTerrain  # noqa: E402
from GameObjects.Terrains.bushes_terrain import BushesTerrain  # noqa: E402
from GameObjects.events.base import EventContext  # noqa: E402
from statuses.race.dwarf.feats.rock_runner import ROCK_RUNNER_STATUS  # noqa: E402
from statuses.race.dwarf.dwarf import DWARF_STATUS  # noqa: E402
from statuses.race.elfs.heritages.woodland_elf import WOODLAND_ELF_STATUS  # noqa: E402

MoveEvent = move_event.MoveEvent


class DummyConn:
    def __init__(self, clicks):
        self.clicks = list(clicks)
        self.led_calls = []

    def set_leds(self, positions, colors, **_kwargs):
        self.led_calls.append((list(positions), colors))
        return None

    def scan_board(self, *_args, **_kwargs):
        if not self.clicks:
            raise RuntimeError("No more clicks queued")
        return self.clicks.pop(0)

    def leds_off(self):
        return None


class DummyEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class DummyUI:
    def __init__(self):
        self.prompts = []
        self.hints = []

    def prompt_info(self, title, *, prompt_long=None, source=None, image=None):
        self.prompts.append(
            {
                "title": title,
                "prompt_long": prompt_long,
                "source": source,
                "image": image,
            }
        )

    def idle_hint(self, title, text):
        self.hints.append({"title": title, "text": text})


class DummyHero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def set_position(self, position):
        self.position = position

    def has_status(self, s):
        return s in self.statuses

    def remove_status(self, s):
        if s in self.statuses:
            self.statuses.remove(s)


def test_path_cost_feet_includes_difficult_bonus():
    board = BoardGrid(rows=1, cols=3)
    board.set_field((1, 0), RumbleTerrain())
    path = [(0, 0), (1, 0), (2, 0)]
    assert move_utils.path_cost_feet(path, board) == 15


def test_move_initial_leds_exclude_current_field_as_destination():
    board = BoardGrid(rows=3, cols=3)
    start = (1, 1)
    hero = DummyHero(start)
    board.place(hero, start)

    target = (2, 1)
    conn = DummyConn(clicks=[target, target])
    ui = DummyUI()
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=ui,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
    )

    MoveEvent().execute(EventContext(game=game, actor=hero))

    first_positions, _colors = conn.led_calls[0]
    assert start not in first_positions
    assert target in first_positions


def test_trim_path_to_feet_respects_difficult_bonus():
    board = BoardGrid(rows=1, cols=3)
    board.set_field((1, 0), RumbleTerrain())
    path = [(0, 0), (1, 0), (2, 0)]
    assert move_utils.trim_path_to_feet(path, 10, board) == [(0, 0), (1, 0)]


def test_move_prompts_only_on_entering_difficult_terrain():
    board = BoardGrid(rows=1, cols=3)
    board.set_field((1, 0), RumbleTerrain())

    hero = DummyHero((0, 0))
    board.place(hero, (0, 0))

    target = (2, 0)
    conn = DummyConn(clicks=[target, target, target])
    ui = DummyUI()
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=ui,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
    )

    ctx = EventContext(game=game, actor=hero)
    MoveEvent().execute(ctx)

    assert len(ui.prompts) == 1
    assert ui.prompts[0]["title"] == "Trudny teren"


def test_move_no_prompt_when_already_on_difficult_terrain():
    board = BoardGrid(rows=1, cols=3)
    board.set_field((0, 0), RumbleTerrain())
    board.set_field((1, 0), RumbleTerrain())

    hero = DummyHero((0, 0))
    board.place(hero, (0, 0))

    target = (2, 0)
    conn = DummyConn(clicks=[target, target, target])
    ui = DummyUI()
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=ui,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
    )

    ctx = EventContext(game=game, actor=hero)
    MoveEvent().execute(ctx)

    assert ui.prompts == []


def test_rock_runner_ignores_difficult_prompt_and_hint():
    board = BoardGrid(rows=1, cols=3)
    board.set_field((1, 0), RumbleTerrain())

    hero = DummyHero((0, 0))
    hero.statuses.append(ROCK_RUNNER_STATUS)
    board.place(hero, (0, 0))

    target = (2, 0)
    conn = DummyConn(clicks=[target, target, target])
    ui = DummyUI()
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=ui,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
        ui_idle_hint=ui.idle_hint,
    )

    ctx = EventContext(game=game, actor=hero)
    MoveEvent().execute(ctx)

    assert ui.prompts == []
    assert ui.hints
    assert "trudny teren" not in ui.hints[-1]["text"].lower()


def test_rock_runner_path_cost_ignores_rumble():
    board = BoardGrid(rows=1, cols=3)
    board.set_field((1, 0), RumbleTerrain())
    path = [(0, 0), (1, 0), (2, 0)]

    hero = DummyHero((0, 0))
    hero.statuses.append(ROCK_RUNNER_STATUS)

    assert move_utils.path_cost_feet(path, board, mover=hero) == 10


def test_woodland_elf_does_not_ignore_bushes_move_cost():
    board = BoardGrid(rows=1, cols=3)
    board.set_field((1, 0), BushesTerrain())

    hero = DummyHero((0, 0))
    hero.statuses.append(WOODLAND_ELF_STATUS)
    board.place(hero, (0, 0))

    target = (2, 0)
    conn = DummyConn(clicks=[target, target, target])
    ui = DummyUI()
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=ui,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
        ui_idle_hint=ui.idle_hint,
    )

    ctx = EventContext(game=game, actor=hero)
    MoveEvent().execute(ctx)

    assert ui.prompts
    assert "trudny teren" in ui.prompts[-1]["title"].lower()
    assert move_utils.path_cost_feet([(0, 0), (1, 0), (2, 0)], board, mover=hero) == 15


def test_move_builds_full_path_then_trims_to_speed_budget():
    board = BoardGrid(rows=1, cols=8)
    hero = DummyHero((0, 0))
    hero.statuses.append(DWARF_STATUS)  # base speed 20 ft
    board.place(hero, (0, 0))

    requested_target = (6, 0)  # 30 ft
    confirm_trimmed_target = (4, 0)  # 20 ft
    conn = DummyConn(clicks=[requested_target, confirm_trimmed_target])
    events = DummyEvents()
    ui_events = []
    game = types.SimpleNamespace(
        board=board,
        conn=conn,
        heroes=[hero],
        enemies=[],
        events=events,
        ui=DummyUI(),
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda name, payload: ui_events.append((name, payload)),
        state=types.SimpleNamespace(__class__=type("Exploration", (), {})),
    )

    ctx = EventContext(game=game, actor=hero)
    result = MoveEvent().execute(ctx)

    assert result.success
    assert hero.position == confirm_trimmed_target
    previews = [payload for name, payload in ui_events if name == "path_preview"]
    assert previews
    assert previews[-1].get("target") == confirm_trimmed_target
    assert previews[-1].get("requested_target") == requested_target
    assert previews[-1].get("trimmed") is True
