import sys
from pathlib import Path
import types
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

from board_grid import BoardGrid  # noqa: E402
from GameObjects.Terrains.rumble_terrain import RumbleTerrain  # noqa: E402
from GameObjects.events.move_event import MoveEvent  # noqa: E402
from GameObjects.events.base import EventContext  # noqa: E402
from statuses.race.dwarf.feats.rock_runner import ROCK_RUNNER_STATUS  # noqa: E402


class DummyConn:
    def __init__(self, clicks):
        self.clicks = list(clicks)

    def set_leds(self, *_args, **_kwargs):
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
