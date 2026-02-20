from types import SimpleNamespace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.bombs.bottled_lightning_event import BottledLightningEvent
from GameObjects.events.bombs.frost_vial_event import FrostVialEvent
from GameObjects.events.bombs.tanglefoot_bag_event import TanglefootBagEvent
from GameObjects.events.bombs.thunderstone_event import ThunderstoneEvent
from GameObjects.events.bombs.alchemists_fire_event import AlchemistsFireEvent
from states.combat import Combat
from statuses import PERSISTENT_DAMAGE_STATUS, Status


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
    def __init__(self, pos, name="Hero", object_id="hero"):
        self.position = pos
        self.name = name
        self.object_id = object_id
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)
        return True


def _dummy_ui(monkeypatch):
    class DummyUI:
        def __init__(self):
            self.messages = []

        def prompt_info(self, title, *, prompt_long=None, **_kwargs):
            self.messages.append((title, prompt_long))
            return "ok"

    ui = DummyUI()
    monkeypatch.setattr("combat.damage_utils.get_ui_client", lambda: ui)
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)
    return ui


def test_bottled_lightning_applies_flat_footed(monkeypatch):
    event = BottledLightningEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 5)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    target = DummyEnemy((1, 0), object_id="enemy-1")
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
    assert any(s.id == "flat_footed" for s in target.statuses)


def test_frost_vial_applies_speed_penalty_to_enemy(monkeypatch):
    event = FrostVialEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "moderate")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 6)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    target = DummyEnemy((1, 0), object_id="enemy-1")
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
    assert any(s.id == "speed_penalty" for s in target.statuses)


def test_tanglefoot_bag_critical_immobilizes(monkeypatch):
    event = TanglefootBagEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 30)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    target = DummyEnemy((1, 0), object_id="enemy-1")
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
    assert any(s.id == "speed_penalty" for s in target.statuses)
    assert any(s.id == "immobilized" for s in target.statuses)


def test_thunderstone_applies_deafened_on_failed_save(monkeypatch):
    event = ThunderstoneEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 4)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)

    def _fail_save(**_kwargs):
        return SimpleNamespace(outcome="failure", total=0, modifier=0)

    monkeypatch.setattr("GameObjects.events.bombs.thunderstone_event.resolve_skill_check_with_sources", _fail_save)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    enemy = DummyEnemy((1, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(1, 0)]),
        board=BoardStub(),
        heroes=[hero],
        enemies=[enemy],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert res.success
    assert any(s.id == "deafened" for s in enemy.statuses)


def test_alchemists_fire_adds_persistent_damage(monkeypatch):
    event = AlchemistsFireEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 6)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    target = DummyEnemy((1, 0), object_id="enemy-1")
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
    assert any(s.id == PERSISTENT_DAMAGE_STATUS.id for s in target.statuses)


def test_far_lobber_extends_bomb_range(monkeypatch):
    event = BottledLightningEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")
    monkeypatch.setattr(event, "_prompt_damage", lambda *_args, **_kwargs: 4)
    monkeypatch.setattr("GameObjects.events.bombs.base_alchemical_bomb_event.prompt_for_roll", lambda *_, **__: 15)
    _dummy_ui(monkeypatch)

    hero = DummyHero((0, 0), object_id="hero-1")
    target = DummyEnemy((5, 0), object_id="enemy-1")
    game = SimpleNamespace(
        conn=FakeConn(responses=[(5, 0)]),
        board=BoardStub(width=10, height=5),
        heroes=[hero],
        enemies=[target],
        ui_log=lambda _msg=None: None,
    )
    ctx = EventContext(game=game, actor=hero)

    res = event.execute(ctx)
    assert not res.success
    assert res.message == "Brak celu w zasięgu."

    hero.add_status(Status(id="far_lobber", data={"bomb_range_bonus": 10}))
    game.conn = FakeConn(responses=[(5, 0)])
    res = event.execute(ctx)
    assert res.success


def test_quick_bomber_reduces_bomb_action_cost(monkeypatch):
    event = BottledLightningEvent()
    monkeypatch.setattr(event, "execute", lambda _ctx: EventResult(success=True, consumed_action=True))

    hero = DummyHero((0, 0), object_id="hero-1")
    hero.add_status(Status(id="quick_bomber", data={"bomb_action_cost_reduction": 1}))

    game = SimpleNamespace()
    state = Combat(game)
    game.state = state
    state.actions_used[hero] = 2

    ctx = EventContext(game=game, actor=hero)
    res = event.run(ctx)
    assert res.success
