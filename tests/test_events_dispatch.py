import types
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401  # rejestruje eventy
from GameObjects.events.registry import dispatch_event
from GameObjects.events.base import EventContext
from GameObjects.events import attack_sword_event


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeBoard:
    def __init__(self, hero_pos, enemy_pos, enemy):
        self.hero_pos = hero_pos
        self.enemy_pos = enemy_pos
        self.enemy = enemy

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        return [self.enemy_pos]

    def occupant_at(self, pos):
        if pos == self.enemy_pos:
            return self.enemy
        if pos == self.hero_pos:
            return None
        return None

    def in_bounds(self, pos):
        return True

    def is_blocked(self, a, b):
        return False

    def edge_interactables_between(self, a, b):
        return []

    def remove(self, pos):
        return None


class FakeEnemy:
    def __init__(self, hp=10, ac=10):
        self.hp = hp
        self.ac = ac
        self.position = (1, 0)

    def apply_damage(self, amount, dmg_type):
        self.hp -= amount
        return amount, self.hp <= 0


class FakeGame:
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.conn = types.SimpleNamespace(set_leds=lambda *a, **k: None, scan_board=lambda allowed=None: None, leds_off=lambda: None)


class CombatCtx(EventContext):
    @property
    def in_combat(self) -> bool:  # type: ignore[override]
        return True

    @property
    def in_exploration(self) -> bool:  # type: ignore[override]
        return False


def test_delay_blocked_in_exploration():
    game = FakeGame()
    ctx = EventContext(game=game, actor=None)
    result = dispatch_event("delay", ctx)
    assert not result.success
    assert result.message


def test_end_turn_calls_advance(monkeypatch):
    game = FakeGame()

    class FakeState:
        def __init__(self):
            self.called = False

        def _advance_turn(self):
            self.called = True

    fake_state = FakeState()
    game.state = fake_state

    ctx = CombatCtx(game=game)
    result = dispatch_event("end_turn", ctx)
    assert result.success
    assert getattr(fake_state, "called", False)


def test_attack_sword_applies_damage(monkeypatch):
    hero = types.SimpleNamespace(position=(0, 0), statuses=[])
    enemy = FakeEnemy(hp=10, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board = FakeBoard(hero.position, enemy.position, enemy)

    # zapewnij trafienie i 5 obrażeń
    from GameObjects.events.attack import basic_melee_attack_event as bmae

    rolls = iter([20, 5])
    monkeypatch.setattr(bmae, "prompt_for_roll", lambda prompt: next(rolls))
    # wyłącz kosztowny refresh flankowania
    monkeypatch.setattr(bmae, "refresh_flanking_statuses", lambda *a, **k: None)

    ctx = EventContext(game=game, actor=hero)
    result = dispatch_event("attack_sword", ctx)
    assert result.success
    assert enemy.hp == 5
