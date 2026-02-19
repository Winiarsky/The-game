from types import SimpleNamespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from GameObjects.events.magic.acid_splash_event import AcidSplashEvent
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


class DummyTarget:
    def __init__(self, pos):
        self.position = pos
        self.hp = 100
        self.statuses = []

    def apply_damage(self, amount, damage_type):
        self.hp -= amount
        return self.hp, self.hp <= 0

    def add_status(self, status):
        self.statuses.append(status)
        return True


def test_acid_splash_hit(monkeypatch):
    # roll: attack hits (handled in BaseMagicAttackEvent), damage=7
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_, **__: 15)
    monkeypatch.setattr("GameObjects.events.magic.acid_splash_event.AcidSplashEvent._prompt_damage", lambda self: 7)

    hero = SimpleNamespace(position=(0, 0))
    target = DummyTarget((1, 0))
    conn = FakeConn(responses=[(1, 0)])
    game = SimpleNamespace(conn=conn, heroes=[hero], enemies=[target], ui_log=lambda msg: None)
    ctx = EventContext(game=game, actor=hero)

    event = AcidSplashEvent()
    result = event.execute(ctx)
    assert result.success
    assert result.data["critical"] is False
    assert target.hp == 93


def test_acid_splash_critical_adds_persistent(monkeypatch):
    # attack roll = crit; damage=5, persistent=2
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_, **__: 30)

    def _prompt(prompt):
        if "persistent" in prompt.lower():
            return 2
        return 5

    monkeypatch.setattr("GameObjects.events.magic.acid_splash_event.AcidSplashEvent._prompt_damage", lambda self: 5)
    monkeypatch.setattr("GameObjects.events.magic.acid_splash_event.AcidSplashEvent._prompt_persistent", lambda *_, **__: 2)

    hero = SimpleNamespace(position=(0, 0))
    target = DummyTarget((1, 0))
    conn = FakeConn(responses=[(1, 0)])
    game = SimpleNamespace(conn=conn, heroes=[hero], enemies=[target], ui_log=lambda msg: None)
    ctx = EventContext(game=game, actor=hero)

    event = AcidSplashEvent()
    res = event.execute(ctx)
    assert res.success
    assert res.data["critical"] is True
    assert target.hp == 95
    assert any(s.id == PERSISTENT_DAMAGE_STATUS.id for s in target.statuses)
