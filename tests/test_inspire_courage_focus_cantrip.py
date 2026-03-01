from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext
from GameObjects.events.attack.attack_base import AttackEventBase
from GameObjects.events.magic.focus_spells.bard.inspire_courage_event import InspireCourageEvent
from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from skills import Skill
from states.combat import Combat
from statuses import inspire_courage_damage_bonus
from statuses.classes.bard.bard import BARD_STATUS
from statuses.inspire_courage import InspireCourageStatus


class DummyHero(StatusMixin, BonusMixin):
    def __init__(self, name: str, position: tuple[int, int]):
        super().__init__()
        self.name = name
        self.object_id = name
        self.position = position
        self.bonuses = []


def _game(heroes):
    logs: list[str] = []

    class DummyConn:
        def set_leds(self, *_a, **_k):
            return None

        def scan_board(self, _positions):
            return None

        def leds_off(self):
            return None

    return SimpleNamespace(
        heroes=list(heroes),
        enemies=[],
        conn=DummyConn(),
        ui=SimpleNamespace(prompt_info=lambda *_a, **_k: None),
        ui_log=lambda msg: logs.append(str(msg)),
        _logs=logs,
    )


def test_inspire_courage_applies_to_heroes_in_60_ft():
    bard = DummyHero("bard", (0, 0))
    bard.add_status(BARD_STATUS)
    near = DummyHero("near", (11, 0))   # 55 ft
    far = DummyHero("far", (13, 0))     # 65 ft
    game = _game([bard, near, far])
    game.state = Combat(game)

    result = InspireCourageEvent().execute(EventContext(game=game, actor=bard))

    assert result.success is True
    assert bard.has_status("inspire_courage")
    assert near.has_status("inspire_courage")
    assert not far.has_status("inspire_courage")


def test_inspire_courage_action_cost_only_in_combat():
    bard = DummyHero("bard", (0, 0))
    bard.add_status(BARD_STATUS)
    ally = DummyHero("ally", (1, 0))
    game = _game([bard, ally])

    class Exploration:
        pass

    game.state = Exploration()
    res_exploration = InspireCourageEvent().execute(EventContext(game=game, actor=bard))
    assert res_exploration.success is True
    assert res_exploration.consumed_action is False

    game.state = Combat(game)
    res_combat = InspireCourageEvent().execute(EventContext(game=game, actor=bard))
    assert res_combat.success is True
    assert res_combat.consumed_action is True
    assert res_combat.actions_spent == 1


def test_inspire_courage_adds_plus_one_attack_modifier():
    class DummyAttack(AttackEventBase):
        pass

    hero = DummyHero("hero", (0, 0))
    hero.add_status(InspireCourageStatus(source_id="bard"))
    modifier, _best, _log = DummyAttack()._attack_modifier_details(hero, "attack_melee", target=None, extra_effects=None)
    assert modifier == 1


def test_inspire_courage_adds_plus_one_damage_bonus():
    hero = DummyHero("hero", (0, 0))

    hero.add_status(InspireCourageStatus(source_id="bard"))
    assert inspire_courage_damage_bonus(hero) == 1


def test_inspire_courage_adds_plus_one_save_vs_fear():
    hero = DummyHero("hero", (0, 0))

    hero.add_status(InspireCourageStatus(source_id="bard"))
    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=hero,
        tags=["save", "fear", Skill.WILL.value],
        roll=14,
        apply_modifiers=True,
    )
    assert result.modifier == 1
    assert result.total == 15
    assert result.outcome == "success"
