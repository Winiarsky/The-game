import sys
from pathlib import Path
import types


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext, EventResult, GameEvent
from GameObjects.events.registry import dispatch_event, register_event
from board_grid import BoardGrid


class FakeHero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def has_status(self, _status):
        return False


class FakeEnemy:
    def __init__(self, pos, hp=10, awareness_profile=None):
        self.position = pos
        self.hp = hp
        self.awareness_profile = dict(awareness_profile or {})

    def has_status(self, _status):
        return False


class FakeGame:
    def __init__(self, hero, enemies):
        self.board = BoardGrid(20, 20)
        self.heroes = [hero]
        self.enemies = list(enemies)
        self.state = types.SimpleNamespace()
        self.start_combat_calls = []

    def _is_enemy_combat_ready(self, enemy):
        return enemy is not None and getattr(enemy, "position", None) is not None and int(getattr(enemy, "hp", 0) or 0) > 0

    def start_combat(self, trigger=None, *, preinitiative_pause=False):
        self.start_combat_calls.append(
            {
                "trigger": trigger,
                "preinitiative_pause": preinitiative_pause,
            }
        )


@register_event
class _TestExplorationAttackEvent(GameEvent):
    name = "zz_test_exploration_attack"
    default_tags = ["attack_melee"]

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult(
            success=True,
            consumed_action=True,
            data={"target": ctx.game.enemies[0]},
        )


@register_event
class _TestExplorationMoveEvent(GameEvent):
    name = "zz_test_exploration_move"
    default_tags = ["move"]

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=True)


@register_event
class _TestExplorationSpellEvent(GameEvent):
    name = "zz_test_exploration_spell"
    default_tags = ["magic", "spell"]

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=True)


@register_event
class _TestExplorationStealthFailEvent(GameEvent):
    name = "zz_test_exploration_stealth_fail"
    default_tags = ["stealth", "move"]

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult.noop(message="fail",)

    def post(self, ctx: EventContext, result: EventResult) -> None:
        result.data["stealth_outcome"] = "failure"


@register_event
class _TestExplorationStealthSuccessEvent(GameEvent):
    name = "zz_test_exploration_stealth_success"
    default_tags = ["stealth", "move"]

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult(success=True, consumed_action=True, data={"stealth_outcome": "success"})


def test_attack_in_exploration_starts_combat_immediately():
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((8, 8))
    game = FakeGame(hero, [enemy])

    result = dispatch_event("zz_test_exploration_attack", EventContext(game=game, actor=hero))

    assert result.success
    assert len(game.start_combat_calls) == 1
    assert game.start_combat_calls[0]["trigger"] is enemy


def test_move_in_exploration_triggers_when_enemy_observes_and_roll_passes(monkeypatch):
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((1, 0))
    game = FakeGame(hero, [enemy])
    monkeypatch.setattr("GameObjects.events.exploration_combat_trigger.random.random", lambda: 0.05)

    result = dispatch_event("zz_test_exploration_move", EventContext(game=game, actor=hero))

    assert result.success
    assert len(game.start_combat_calls) == 1
    assert game.start_combat_calls[0]["trigger"] is enemy


def test_move_in_exploration_does_not_trigger_outside_awareness_range(monkeypatch):
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((10, 10), awareness_profile={"awareness_range_feet": 30})
    game = FakeGame(hero, [enemy])
    monkeypatch.setattr("GameObjects.events.exploration_combat_trigger.random.random", lambda: 0.01)

    dispatch_event("zz_test_exploration_move", EventContext(game=game, actor=hero))

    assert game.start_combat_calls == []


def test_non_hostile_spell_uses_observed_probability(monkeypatch):
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((2, 0), awareness_profile={"spell_trigger_threshold": 0.35})
    game = FakeGame(hero, [enemy])
    monkeypatch.setattr("GameObjects.events.exploration_combat_trigger.random.random", lambda: 0.30)

    dispatch_event("zz_test_exploration_spell", EventContext(game=game, actor=hero))

    assert len(game.start_combat_calls) == 1


def test_stealth_failure_can_trigger_combat(monkeypatch):
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((1, 1), awareness_profile={"stealth_failure_trigger_threshold": 0.25})
    game = FakeGame(hero, [enemy])
    monkeypatch.setattr("GameObjects.events.exploration_combat_trigger.random.random", lambda: 0.10)

    dispatch_event("zz_test_exploration_stealth_fail", EventContext(game=game, actor=hero))

    assert len(game.start_combat_calls) == 1


def test_stealth_success_does_not_trigger_combat(monkeypatch):
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((1, 1))
    game = FakeGame(hero, [enemy])
    monkeypatch.setattr("GameObjects.events.exploration_combat_trigger.random.random", lambda: 0.01)

    dispatch_event("zz_test_exploration_stealth_success", EventContext(game=game, actor=hero))

    assert game.start_combat_calls == []


def test_deaf_guard_like_enemy_uses_low_move_threshold(monkeypatch):
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((1, 0), awareness_profile={"move_trigger_threshold": 0.10})
    game = FakeGame(hero, [enemy])
    monkeypatch.setattr("GameObjects.events.exploration_combat_trigger.random.random", lambda: 0.30)

    dispatch_event("zz_test_exploration_move", EventContext(game=game, actor=hero))

    assert game.start_combat_calls == []


def test_sensitive_hunter_uses_high_move_threshold(monkeypatch):
    hero = FakeHero((0, 0))
    enemy = FakeEnemy((1, 0), awareness_profile={"move_trigger_threshold": 0.90})
    game = FakeGame(hero, [enemy])
    monkeypatch.setattr("GameObjects.events.exploration_combat_trigger.random.random", lambda: 0.30)

    dispatch_event("zz_test_exploration_move", EventContext(game=game, actor=hero))

    assert len(game.start_combat_calls) == 1
