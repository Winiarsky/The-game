from types import SimpleNamespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.magic.magic_utils import pick_target_in_range
from GameObjects.events.magic.base_attack_magic_event import BaseMagicAttackEvent


class FakeConn:
    def __init__(self, responses):
        self.responses = list(responses)
        self.leds_set = None
        self.leds_off_called = False

    def set_leds(self, positions, colors):
        self.leds_set = list(positions)

    def scan_board(self, _positions):
        if not self.responses:
            return None
        return self.responses.pop(0)

    def leds_off(self):
        self.leds_off_called = True


def test_pick_target_in_range_returns_choice():
    conn = FakeConn(responses=[(1, 0)])
    game = SimpleNamespace(conn=conn)
    ctx = EventContext(game=game)
    enemy = object()
    target, pos = pick_target_in_range(
        ctx,
        (0, 0),
        [(enemy, (1, 0), "enemy")],
        max_range_feet=15,
        allowed_kinds=("enemy",),
    )
    assert target is enemy
    assert pos == (1, 0)
    assert conn.leds_set == [(1, 0)]
    assert conn.leds_off_called


def test_pick_target_in_range_rejects_self_or_out_of_range():
    conn = FakeConn(responses=[(0, 0)])
    game = SimpleNamespace(conn=conn)
    ctx = EventContext(game=game)
    enemy = object()
    target, pos = pick_target_in_range(
        ctx,
        (0, 0),
        [(enemy, (3, 3), "enemy")],
        max_range_feet=15,
        allowed_kinds=("enemy",),
    )
    assert target is None
    assert pos is None


def test_pick_target_in_range_filters_by_kind():
    hero_target = object()
    enemy = object()
    conn = FakeConn(responses=[(2, 0)])
    game = SimpleNamespace(conn=conn)
    ctx = EventContext(game=game)
    target, pos = pick_target_in_range(
        ctx,
        (0, 0),
        [
            (enemy, (1, 0), "enemy"),
            (hero_target, (2, 0), "hero"),
        ],
        max_range_feet=15,
        allowed_kinds=("hero",),
    )
    assert target is hero_target
    assert pos == (2, 0)
    assert conn.leds_set == [(2, 0)]


class _DummyMagicAttack(BaseMagicAttackEvent):
    target_kind = "enemy"
    range_feet = 15

    def _resolve_on_target(self, target, pos, ctx, *, critical: bool = False):
        return EventResult(success=True, consumed_action=True, message="crit" if critical else f"hit {pos}")


def test_base_magic_attack_event_uses_helper(monkeypatch):
    from GameObjects.events.magic import base_attack_magic_event as bam
    monkeypatch.setattr(bam, "prompt_for_roll", lambda *_, **__: 15)

    hero = SimpleNamespace(position=(0, 0))
    enemy = SimpleNamespace(position=(1, 0))
    conn = FakeConn(responses=[(1, 0)])
    game = SimpleNamespace(conn=conn, heroes=[hero], enemies=[enemy])
    ctx = EventContext(game=game, actor=hero)
    event = _DummyMagicAttack()
    result = event.execute(ctx)
    assert result.success is True
    assert result.message == "hit (1, 0)"


def test_base_magic_attack_event_hits_on_roll(monkeypatch):
    from GameObjects.events.magic import base_attack_magic_event as bam
    monkeypatch.setattr(bam, "prompt_for_roll", lambda *_, **__: 15)

    hero = SimpleNamespace(position=(0, 0))
    enemy = SimpleNamespace(position=(1, 0), ac=15, bonuses=[])
    conn = FakeConn(responses=[(1, 0)])
    game = SimpleNamespace(conn=conn, heroes=[hero], enemies=[enemy])
    ctx = EventContext(game=game, actor=hero)

    class HitSpell(BaseMagicAttackEvent):
        target_kind = "enemy"
        range_feet = 30

        def _resolve_on_target(self, target, pos, ctx, *, critical: bool = False):
            return EventResult(success=True, consumed_action=True, message="crit" if critical else "hit")

    event = HitSpell()
    res = event.execute(ctx)
    assert res.success is True
    assert res.message == "hit"


def test_base_magic_attack_event_miss_does_not_resolve(monkeypatch):
    from GameObjects.events.magic import base_attack_magic_event as bam
    monkeypatch.setattr(bam, "prompt_for_roll", lambda *_, **__: 10)

    hero = SimpleNamespace(position=(0, 0))
    enemy = SimpleNamespace(position=(1, 0), ac=15, bonuses=[])
    conn = FakeConn(responses=[(1, 0)])
    game = SimpleNamespace(conn=conn, heroes=[hero], enemies=[enemy])
    ctx = EventContext(game=game, actor=hero)

    class MissSpell(BaseMagicAttackEvent):
        target_kind = "enemy"
        range_feet = 30
        called = False

        def _resolve_on_target(self, target, pos, ctx, *, critical: bool = False):
            self.called = True
            return EventResult(success=True, message="should not happen")

    event = MissSpell()
    res = event.execute(ctx)
    assert res.success is True
    assert res.message == "Czar chybia."
    assert event.called is False


def test_base_magic_attack_event_critical(monkeypatch):
    from GameObjects.events.magic import base_attack_magic_event as bam
    monkeypatch.setattr(bam, "prompt_for_roll", lambda *_, **__: 25)

    hero = SimpleNamespace(position=(0, 0))
    enemy = SimpleNamespace(position=(1, 0), ac=15, bonuses=[])
    conn = FakeConn(responses=[(1, 0)])
    game = SimpleNamespace(conn=conn, heroes=[hero], enemies=[enemy])
    ctx = EventContext(game=game, actor=hero)

    class CritSpell(BaseMagicAttackEvent):
        target_kind = "enemy"
        range_feet = 30

        def _resolve_on_target(self, target, pos, ctx, *, critical: bool = False):
            return EventResult(success=True, consumed_action=True, message="crit" if critical else "hit")

    event = CritSpell()
    res = event.execute(ctx)
    assert res.success is True
    assert res.message == "crit"
