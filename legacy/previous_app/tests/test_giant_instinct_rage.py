import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from hero import Hero
from GameObjects.events.base import EventContext
from GameObjects.events.rage_event import RageEvent
from statuses.base import Status
from statuses.classes.barbarian.barbarian import BARBARIAN_STATUS
from statuses.classes.barbarian.instincts.giant_instinct import GiantInstinctStatus
from statuses.clumsy import clumsy_ac_penalty, clumsy_ac_prompt_note
from statuses.rage import rage_damage_bonus
from states.combat import Combat


class DummyConn:
    def set_leds(self, *_a, **_k):
        return None

    def scan_board(self, *_a, **_k):
        return None

    def leds_off(self, *_a, **_k):
        return None

    def read_card(self, *_a, **_k):
        return ""


class DummyGame:
    def __init__(self):
        self.conn = DummyConn()
        self.ui_log = lambda *_a, **_k: None
        self.ui_event = lambda *_a, **_k: None
        self.heroes = []
        self.enemies = []
        self.state = None


def test_giant_instinct_rage_clumsy_and_bonus():
    game = DummyGame()
    combat = Combat(game)
    game.state = combat

    hero = Hero()
    game.heroes = [hero]

    assert not hero.has_status("clumsy")

    hero.add_status(BARBARIAN_STATUS)
    hero.add_status(GiantInstinctStatus())

    ctx = EventContext(game=game, actor=hero)
    result = RageEvent().execute(ctx)
    assert result.success

    assert hero.has_status("clumsy")
    assert int(getattr(hero, "temp_hp", 0) or 0) == 1
    status = hero.get_status("clumsy")
    assert getattr(status, "source", None) == "giant_instinct"
    assert clumsy_ac_penalty(hero) == 1
    note = clumsy_ac_prompt_note(hero)
    assert note is not None and "-1" in note

    assert rage_damage_bonus(hero, is_agile=False) == 6
    assert rage_damage_bonus(hero, is_agile=True) == 3

    combat.on_exit()
    assert not hero.has_status("clumsy")
    assert not hero.has_status("giant_instinct_active")
    assert not hero.has_status("rage")
    assert int(getattr(hero, "temp_hp", 0) or 0) == 0


def test_rage_requires_barbarian_class():
    game = DummyGame()
    combat = Combat(game)
    game.state = combat

    hero = Hero()
    game.heroes = [hero]

    result = RageEvent().execute(EventContext(game=game, actor=hero))

    assert result.success is False
    assert "tylko barbarian" in str(result.message or "").lower()


def test_rage_damage_bonus_is_zero_without_rage_even_with_instinct_active():
    hero = Hero()
    hero.add_status(GiantInstinctStatus())
    hero.add_status(Status(id="giant_instinct_active", data={"rage_damage_bonus_override": 6}))

    assert rage_damage_bonus(hero, is_agile=False) == 0
    assert rage_damage_bonus(hero, is_agile=True) == 0
