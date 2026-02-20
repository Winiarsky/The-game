from types import SimpleNamespace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from GameObjects.events.acid_flask_event import AcidFlaskEvent
from GameObjects.events.base import EventContext
from statuses import PERSISTENT_DAMAGE_STATUS


class FakeConn:
    def __init__(self, responses):
        self.responses = list(responses)

    def set_leds(self, positions, colors):
        pass

    def scan_board(self, _positions):
        return self.responses.pop(0)

    def leds_off(self):
        pass


class BoardStub:
    def __init__(self, width=5, height=5):
        self.width = width
        self.height = height

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        if not self.in_bounds(pos):
            return []
        x, y = pos
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if not diagonal and abs(dx) + abs(dy) != 1:
                    continue
                candidate = (x + dx, y + dy)
                if self.in_bounds(candidate):
                    neighbors.append(candidate)
        if include_position:
            neighbors.append(pos)
        return neighbors

    def remove(self, _pos):
        pass


class DummyEnemy:
    def __init__(self, pos, hp=20, ac=10, object_id="enemy"):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.object_id = object_id
        self.statuses = []

    def apply_damage(self, amount, damage_type):
        self.hp -= amount
        return self.hp, self.hp <= 0

    def add_status(self, status):
        self.statuses.append(status)
        return True


class DummyHero:
    def __init__(self, pos, hp=20, name="Hero", object_id="hero"):
        self.position = pos
        self.hp = hp
        self.name = name
        self.object_id = object_id
        self.statuses = []


def test_acid_flask_moderate_hit_persistent_and_splash(monkeypatch):
    event = AcidFlaskEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "moderate")
    monkeypatch.setattr(event, "_prompt_persistent", lambda *_args, **_kwargs: 7)
    monkeypatch.setattr("GameObjects.events.acid_flask_event.prompt_for_roll", lambda *_, **__: 12)

    class DummyUI:
        def __init__(self):
            self.messages = []

        def prompt_info(self, title, *, prompt_long=None, **_kwargs):
            self.messages.append((title, prompt_long))
            return "ok"

    dummy_ui = DummyUI()
    monkeypatch.setattr("combat.damage_utils.get_ui_client", lambda: dummy_ui)

    hero = DummyHero((0, 0), object_id="hero-1")
    hero_adj = DummyHero((0, 1), object_id="hero-2")
    target = DummyEnemy((1, 0), object_id="enemy-1")
    enemy_adj = DummyEnemy((1, 1), object_id="enemy-2")

    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero, hero_adj],
        enemies=[target, enemy_adj],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert any(s.id == PERSISTENT_DAMAGE_STATUS.id for s in target.statuses)
    assert enemy_adj.hp == 18  # splash 2
    assert any("hero-2" in (msg or "") and "2" in (msg or "") for _title, msg in dummy_ui.messages)


@pytest.mark.parametrize(
    "tier,item_bonus",
    [
        ("lesser", 0),
        ("moderate", 1),
        ("greater", 2),
        ("major", 3),
    ],
)
def test_acid_flask_item_bonus_in_modifiers(monkeypatch, tier, item_bonus):
    event = AcidFlaskEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: tier)
    monkeypatch.setattr(event, "_prompt_persistent", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(event, "_apply_splash_damage", lambda *_args, **_kwargs: None)

    captured = {}

    def _prompt(*_args, **kwargs):
        captured.update(kwargs)
        return 20

    monkeypatch.setattr("GameObjects.events.acid_flask_event.prompt_for_roll", _prompt)

    hero = DummyHero((0, 0))
    target = DummyEnemy((1, 0), ac=10)
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    modifiers = captured.get("modifiers", {})
    bon_item = modifiers.get("bonItem", [])
    if item_bonus:
        assert any(item.get("value") == item_bonus for item in bon_item)
    else:
        assert not bon_item
