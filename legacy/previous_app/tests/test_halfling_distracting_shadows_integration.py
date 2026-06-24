from types import SimpleNamespace
import importlib.util
import sys
import types
from pathlib import Path

from statuses import Status
from statuses.race.halfling.feats.distracting_shadows import DistractingShadowsStatus


class DummyHero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)

    def remove_status(self, status_id):
        for idx in range(len(self.statuses) - 1, -1, -1):
            if getattr(self.statuses[idx], "id", self.statuses[idx]) == status_id:
                del self.statuses[idx]
                return True
        return False

    def has_status(self, status_id):
        return any(getattr(s, "id", s) == status_id for s in self.statuses)


class DummyBoard:
    def __init__(self, hero_a, hero_b):
        self._a = hero_a
        self._b = hero_b

    def rooms_at(self, _pos):
        return {"r1"}

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        if pos == self._a.position:
            return [self._b.position]
        return []

    def occupant_at(self, pos):
        if pos == self._b.position:
            return self._b
        if pos == self._a.position:
            return self._a
        return None

    def cell_at(self, _pos):
        return SimpleNamespace(field=SimpleNamespace(stealth_impact=0))

    def interactables_at(self, _pos):
        return []


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


def test_distracting_shadows_allows_stealth_with_watchers(monkeypatch):
    hero = DummyHero((0, 0))
    hero.add_status(DistractingShadowsStatus())
    ally = DummyHero((1, 0))

    board = DummyBoard(hero, ally)
    game = SimpleNamespace(
        heroes=[hero, ally],
        board=board,
        conn=DummyConn(),
        events=DummyEvents(),
        ui_log=lambda *_a, **_k: None,
    )

    stealth_mod = _load_stealth_event()
    base_mod = sys.modules["GameObjects.events.base"]

    monkeypatch.setattr(stealth_mod, "iter_watchers_in_rooms", lambda *_a, **_k: [object()])
    monkeypatch.setattr(stealth_mod, "summarize_watchers", lambda *_a, **_k: (0, [(object(), (2, 2))]))
    monkeypatch.setattr(stealth_mod.StealthEvent, "_compute_modifier", lambda *_a, **_k: (0, []))
    monkeypatch.setattr(stealth_mod.StealthEvent, "_apply_success", lambda *_a, **_k: 0)
    monkeypatch.setattr(stealth_mod.StealthEvent, "_stealth_move", lambda *_a, **_k: None)

    result_ok = base_mod.EventResult(success=True, consumed_action=True, data={"outcome": "success", "total": 20})
    monkeypatch.setattr(stealth_mod, "dispatch_event", lambda *_a, **_k: result_ok)

    ctx = base_mod.EventContext(game=game, actor=hero)
    res = stealth_mod.StealthEvent().execute(ctx)

    assert res.success is True


def _load_stealth_event():
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
    stealth_path = root / "src" / "GameObjects" / "events" / "stealth_event.py"

    if "GameObjects.events.base" not in sys.modules:
        _load("GameObjects.events.base", base_path)
    if "GameObjects.events.registry" not in sys.modules:
        _load("GameObjects.events.registry", registry_path)

    return _load("GameObjects.events.stealth_event", stealth_path)
