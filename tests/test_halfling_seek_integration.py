from types import SimpleNamespace
import importlib.util
import sys
import types
from pathlib import Path

import GameObjects.interactions_mixin.skill_check_resolver as check_resolver
from statuses.race.halfling.keen_eyes import KeenEyesStatus


class DummyHidden:
    def __init__(self, reveal_dc=12):
        self.hidden = True
        self.revealed = False
        self.seekable = True
        self.reveal_dc = reveal_dc
        self.reveal_tags = ()
        self.description_on_reveal = "hidden thing"

    def try_reveal(self, total):
        if total >= self.reveal_dc:
            self.revealed = True


class DummyBoard:
    def __init__(self, hero_pos, obj):
        self._hero_pos = hero_pos
        self._obj = obj
        self._locked = set()
        self._fails = {}

    def rooms_at(self, _pos):
        return {"r1"}

    def is_room_seek_locked(self, room_id):
        return room_id in self._locked

    def room_seek_failures(self, room_id):
        return self._fails.get(room_id, 0)

    def positions_in_rooms(self, _rooms):
        return {self._hero_pos}

    def interactables_at(self, _pos):
        return [self._obj]

    def lock_room_seek(self, room_id):
        self._locked.add(room_id)

    def increment_room_seek_fail(self, room_id):
        self._fails[room_id] = self._fails.get(room_id, 0) + 1


class DummyConn:
    def set_leds(self, *_a, **_k):
        return None

    def scan_board(self, *_a, **_k):
        return None

    def leds_off(self, *_a, **_k):
        return None


class DummyEvents:
    def safe_emit_action(self, *a, **k):
        return None


class DummyHero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, status_id):
        return any(getattr(s, "id", s) == status_id for s in self.statuses)


def _run_seek(actor, board, monkeypatch, roll):
    game = SimpleNamespace(
        heroes=[actor],
        board=board,
        conn=DummyConn(),
        events=DummyEvents(),
        ui_log=lambda *_a, **_k: None,
    )

    class DummyUI:
        enabled = False

        def prompt_info(self, *a, **k):
            return None

    seek_mod = _load_seek_event()
    monkeypatch.setattr(check_resolver, "prompt_for_roll", lambda *a, **k: roll)
    monkeypatch.setattr(seek_mod, "get_ui_client", lambda: DummyUI())

    base_mod = sys.modules["GameObjects.events.base"]
    ctx = base_mod.EventContext(game=game, actor=actor)
    SeekEvent = seek_mod.SeekEvent
    return SeekEvent().execute(ctx)


def test_seek_reveals_with_keen_eyes(monkeypatch):
    hero = DummyHero((0, 0))
    hero.add_status(KeenEyesStatus())
    obj = DummyHidden(reveal_dc=12)
    board = DummyBoard((0, 0), obj)

    _run_seek(hero, board, monkeypatch, roll=10)
    assert obj.revealed is True


def test_seek_fails_without_keen_eyes(monkeypatch):
    hero = DummyHero((0, 0))
    obj = DummyHidden(reveal_dc=12)
    board = DummyBoard((0, 0), obj)

    _run_seek(hero, board, monkeypatch, roll=10)
    assert obj.revealed is False


def _load_seek_event():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    sys.modules.setdefault("GameObjects", types.ModuleType("GameObjects"))
    events_pkg = sys.modules.setdefault("GameObjects.events", types.ModuleType("GameObjects.events"))
    setattr(events_pkg, "__path__", [str(root / "src" / "GameObjects" / "events")])

    def _load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    base_path = root / "src" / "GameObjects" / "events" / "base.py"
    registry_path = root / "src" / "GameObjects" / "events" / "registry.py"
    seek_path = root / "src" / "GameObjects" / "events" / "seek_event.py"

    if "GameObjects.events.base" not in sys.modules:
        _load("GameObjects.events.base", base_path)
    if "GameObjects.events.registry" not in sys.modules:
        _load("GameObjects.events.registry", registry_path)

    return _load("GameObjects.events.seek_event", seek_path)
