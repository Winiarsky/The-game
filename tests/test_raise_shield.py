import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from GameObjects.events.raise_shield_event import RaiseShieldEvent
from GameObjects.events.base import EventContext
from bonuses import BonusEffect, BonusType
from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from GameObjects.items.shield import StandardShield, create_shield
from states.combat import Combat
from statuses import RAISE_SHIELD_ALLOW_STATUS


class DummyGame:
    def __init__(self, round_idx=1):
        self.state = type("S", (), {"round_index": round_idx})()
        self.ui_log_messages = []

    def ui_log(self, msg):
        self.ui_log_messages.append(msg)


class DummyCtx(EventContext):
    @property
    def in_combat(self):
        return True

    @property
    def in_exploration(self):
        return False


class DummyHero(BonusMixin):
    def __init__(self):
        super().__init__()
        self.object_id = "hero1"
        self.statuses = []
        self.equipped_shield = StandardShield()

    def __hash__(self):
        return id(self)

    def has_status(self, status_id):
        return any(getattr(status, "id", status) == status_id for status in self.statuses)

    def add_status(self, status):
        if self.has_status(getattr(status, "id", status)):
            return False
        self.statuses.append(status)
        return True


def _find_shield_bonus(hero):
    return [b for b in hero.bonuses if b.tag == "ac" and b.label == "tarcza w górze"]


def test_raise_shield_adds_circumstance_bonus_and_clears_previous():
    hero = DummyHero()
    hero.add_status(RAISE_SHIELD_ALLOW_STATUS)
    game = DummyGame(round_idx=3)
    ctx = DummyCtx(game=game, actor=hero)
    event = RaiseShieldEvent()

    # pierwsze podniesienie
    res1 = event.execute(ctx)
    assert res1.success
    bonuses1 = _find_shield_bonus(hero)
    assert len(bonuses1) == 1
    assert bonuses1[0].type == BonusType.CIRCUMSTANCE
    assert bonuses1[0].value == 2
    assert "round3" in bonuses1[0].source

    # drugie podniesienie w tej samej turze – stary efekt usunięty, zostaje jeden
    res2 = event.execute(ctx)
    assert res2.success
    bonuses2 = _find_shield_bonus(hero)
    assert len(bonuses2) == 1


def test_raise_tower_shield_adds_temporary_speed_penalty():
    hero = DummyHero()
    hero.add_status(RAISE_SHIELD_ALLOW_STATUS)
    tower = create_shield("tower_shield")
    assert tower is not None
    hero.equipped_shield = tower
    game = DummyGame(round_idx=4)
    ctx = DummyCtx(game=game, actor=hero)

    res = RaiseShieldEvent().execute(ctx)

    assert res.success
    penalties = [s for s in hero.statuses if getattr(s, "id", "") == "speed_penalty" and str(getattr(s, "source", "")).startswith("raise_shield:")]
    assert penalties
    data = getattr(penalties[0], "data", {}) or {}
    assert int(data.get("speed_penalty_feet", 0) or 0) == 5


def test_raise_shield_works_without_raise_shield_allow_status():
    hero = DummyHero()
    game = DummyGame(round_idx=2)
    ctx = DummyCtx(game=game, actor=hero)
    event = RaiseShieldEvent()

    res = event.execute(ctx)
    assert res.success
    assert res.consumed_action is True


def test_raise_shield_requires_equipped_shield():
    hero = DummyHero()
    hero.add_status(RAISE_SHIELD_ALLOW_STATUS)
    hero.equipped_shield = None
    game = DummyGame(round_idx=2)
    ctx = DummyCtx(game=game, actor=hero)
    event = RaiseShieldEvent()

    res = event.execute(ctx)
    assert not res.success
    assert res.consumed_action is False
    assert "brak wyposazonej tarczy" in (res.message or "").lower()


def test_raise_shield_requires_combat():
    hero = DummyHero()

    class ExpCtx(EventContext):
        @property
        def in_combat(self):
            return False

        @property
        def in_exploration(self):
            return True

    ctx = ExpCtx(game=DummyGame(), actor=hero)
    event = RaiseShieldEvent()
    res = event.execute(ctx)
    assert not res.success
    assert res.consumed_action is False
    assert "walce" in (res.message or "").lower()


def test_raise_shield_lasts_until_heros_next_turn_not_enemy():
    hero = DummyHero()
    hero.position = (1, 0)

    class EnemyStub:
        def __init__(self):
            self.position = (0, 0)
            self.hp = 10

    enemy = EnemyStub()

    game = DummyGame(round_idx=1)
    game.heroes = [hero]
    game.enemies = [enemy]
    game.ui = None
    game.ui_log = lambda *_args, **_kwargs: None
    game.conn = None
    game.board = None

    combat = Combat(game)
    combat.base_order = [enemy, hero]
    combat.round_queue = [enemy, hero]
    combat.initiative_order = list(combat.round_queue)
    combat.actions_used = {}

    # hero raises shield during his turn in previous round -> bonus present
    hero.add_bonus(
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag="ac",
            source="raise_shield:round1",
            label="tarcza w górze",
        )
    )

    # start of round: current actor is enemy, bonus still active
    assert combat._current_actor() is enemy
    assert hero.compute_modifier("ac") == 2

    # enemy finishes turn -> advance to hero, bonus should clear
    combat._advance_turn()
    assert combat._current_actor() is hero
    assert hero.compute_modifier("ac") == 0
