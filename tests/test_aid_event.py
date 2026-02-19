from types import SimpleNamespace
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.aid_event import AidEvent
from GameObjects.events.base import EventContext
from GameObjects.interactions_mixin import BonusMixin, StatusMixin
from statuses.race.human.feats.cooperative_nature import COOPERATIVE_NATURE_STATUS
from states.combat import Combat


class DummyConn:
    def set_leds(self, *_a, **_k):
        return None

    def leds_off(self):
        return None

    def scan_board(self, positions):
        return positions[0] if positions else None


class DummyBoard:
    def __init__(self, occupants):
        self._occ = dict(occupants)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        x, y = pos
        res = [
            (x - 1, y),
            (x + 1, y),
            (x, y - 1),
            (x, y + 1),
        ]
        if diagonal:
            res += [(x - 1, y - 1), (x - 1, y + 1), (x + 1, y - 1), (x + 1, y + 1)]
        if include_position:
            res.append(pos)
        return res

    def occupant_at(self, pos):
        return self._occ.get(pos)


class DummyActor(StatusMixin, BonusMixin):
    def __init__(self, object_id, position):
        super().__init__()
        self.bonuses = []
        self.object_id = object_id
        self.position = position


def _game(hero, target, board):
    game = SimpleNamespace(
        heroes=[hero, target],
        enemies=[],
        board=board,
        conn=DummyConn(),
        ui=None,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
    )
    game.state = Combat(game)
    hero.game = game
    target.game = game
    return game


def _ctx(game, actor):
    return EventContext(game=game, actor=actor)


def test_aid_skill_success_adds_plus_one(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "skill:athletics")
    monkeypatch.setattr(
        "GameObjects.events.aid_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )

    res = event.execute(ctx)
    assert res.success is True
    status = target.get_status("aided")
    assert status is not None
    assert status.data.get("bonus") == 1
    assert status.data.get("skill_id") == "athletics"


def test_aid_skill_critical_success_with_coop_adds_plus_four(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    hero.add_status(COOPERATIVE_NATURE_STATUS)
    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "skill:athletics")
    monkeypatch.setattr(
        "GameObjects.events.aid_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="critical_success"),
    )

    res = event.execute(ctx)
    assert res.success is True
    status = target.get_status("aided")
    assert status is not None
    assert status.data.get("bonus") == 4


def test_aid_skill_critical_failure_adds_minus_one(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "skill:athletics")
    monkeypatch.setattr(
        "GameObjects.events.aid_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="critical_failure"),
    )

    res = event.execute(ctx)
    assert res.success is True
    status = target.get_status("aided")
    assert status is not None
    assert status.data.get("bonus") == -1


def test_aid_skill_failure_adds_nothing(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "skill:athletics")
    monkeypatch.setattr(
        "GameObjects.events.aid_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="failure"),
    )

    res = event.execute(ctx)
    assert res.success is True
    assert target.get_status("aided") is None


def test_aid_melee_attack_success_adds_bonus(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "attack:melee")
    monkeypatch.setattr("GameObjects.events.aid_event.prompt_for_roll", lambda *_a, **_k: 15)

    res = event.execute(ctx)
    assert res.success is True
    assert target.bonuses
    bonus = target.bonuses[-1]
    assert bonus.tag == "attack_melee"
    assert bonus.value == 1
    assert bonus.is_penalty is False


def test_aid_melee_attack_success_with_coop_adds_plus_two(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    hero.add_status(COOPERATIVE_NATURE_STATUS)
    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "attack:melee")
    monkeypatch.setattr("GameObjects.events.aid_event.prompt_for_roll", lambda *_a, **_k: 15)

    res = event.execute(ctx)
    assert res.success is True
    assert target.bonuses
    bonus = target.bonuses[-1]
    assert bonus.tag == "attack_melee"
    assert bonus.value == 2
    assert bonus.is_penalty is False


def test_aid_ranged_attack_critical_success_with_coop_adds_plus_four(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    hero.add_status(COOPERATIVE_NATURE_STATUS)
    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "attack:ranged")
    monkeypatch.setattr("GameObjects.events.aid_event.prompt_for_roll", lambda *_a, **_k: 25)

    res = event.execute(ctx)
    assert res.success is True
    assert target.bonuses
    bonus = target.bonuses[-1]
    assert bonus.tag == "attack_ranged"
    assert bonus.value == 4
    assert bonus.is_penalty is False


def test_aid_ranged_attack_critical_failure_adds_penalty(monkeypatch):
    hero = DummyActor("h1", (0, 0))
    target = DummyActor("h2", (1, 0))
    board = DummyBoard({hero.position: hero, target.position: target})
    game = _game(hero, target, board)
    ctx = _ctx(game, hero)
    event = AidEvent()

    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(event, "_pick_aid_test", lambda *_a, **_k: "attack:ranged")
    monkeypatch.setattr("GameObjects.events.aid_event.prompt_for_roll", lambda *_a, **_k: 5)

    res = event.execute(ctx)
    assert res.success is True
    assert target.bonuses
    bonus = target.bonuses[-1]
    assert bonus.tag == "attack_ranged"
    assert bonus.value == 1
    assert bonus.is_penalty is True
