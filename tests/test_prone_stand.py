import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bonuses import BonusEffect, BonusType  # noqa: E402
from GameObjects.events.prone_event import ProneEvent  # noqa: E402
from GameObjects.events.stand_event import StandEvent  # noqa: E402
from statuses import PRONE_STATUS  # noqa: E402


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class DummyHero:
    def __init__(self):
        self.statuses = []
        self.bonuses = []
        self.stealth_bonus = 0
        self.position = (0, 0)

    def has_status(self, status):
        sid = getattr(status, "id", status)
        return any(getattr(s, "id", s) == sid for s in self.statuses)

    def add_status(self, status):
        if self.has_status(status):
            return False
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        before = len(self.statuses)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]
        return len(self.statuses) != before

    def add_bonus(self, eff: BonusEffect):
        self.bonuses.append(eff)

    def remove_bonuses_by_source(self, source: str):
        self.bonuses = [b for b in self.bonuses if b.source != source]


class DummyCtx:
    def __init__(self, game, actor, in_combat=True, tags=None):
        self.game = game
        self.actor = actor
        self.in_combat = in_combat
        self.tags = tags


class DummyGame:
    def __init__(self):
        self.events = FakeEvents()
        self.ui_log_messages = []

    def ui_log(self, msg):
        self.ui_log_messages.append(msg)


def _bonus_for(hero, tag):
    return [b for b in hero.bonuses if b.tag == tag]


def test_prone_requires_combat():
    hero = DummyHero()
    game = DummyGame()
    ctx = DummyCtx(game, hero, in_combat=False)

    result = ProneEvent().execute(ctx)

    assert not result.success
    assert hero.has_status("prone") is False


def test_prone_applies_status_and_penalties():
    hero = DummyHero()
    game = DummyGame()
    ctx = DummyCtx(game, hero, in_combat=True)

    result = ProneEvent().execute(ctx)

    assert result.success
    assert hero.has_status(PRONE_STATUS)
    melee_pen = _bonus_for(hero, "attack_melee")[0]
    range_pen = _bonus_for(hero, "attack_ranged")[0]
    assert melee_pen.is_penalty and melee_pen.value == 2
    assert range_pen.is_penalty and range_pen.value == 2
    assert game.events.emitted[-1]["action_id"] == "prone"


def test_prone_second_time_is_cancelled():
    hero = DummyHero()
    hero.add_status(PRONE_STATUS)
    game = DummyGame()
    ctx = DummyCtx(game, hero, in_combat=True)

    result = ProneEvent().execute(ctx)

    assert not result.success
    assert hero.has_status(PRONE_STATUS)


def test_stand_removes_prone_and_penalties_and_has_move_tag():
    hero = DummyHero()
    # simulate prone already applied
    hero.add_status(PRONE_STATUS)
    hero.add_bonus(BonusEffect(type=BonusType.STATUS, value=2, tag="attack_melee", source="prone", is_penalty=True))
    hero.add_bonus(BonusEffect(type=BonusType.STATUS, value=2, tag="attack_ranged", source="prone", is_penalty=True))

    game = DummyGame()
    ctx = DummyCtx(game, hero, in_combat=True)

    result = StandEvent().execute(ctx)

    assert result.success
    assert not hero.has_status(PRONE_STATUS)
    assert not _bonus_for(hero, "attack_melee")
    assert not _bonus_for(hero, "attack_ranged")
    emitted = game.events.emitted[-1]
    assert "move" in emitted.get("action_tags", [])
