from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from skills import Skill
from statuses.race.human.feats.cooperative_nature import COOPERATIVE_NATURE_STATUS
from statuses.race.human.feats.haughty_obstinacy import HAUGHTY_OBSTINACY_STATUS
from statuses.race.human.feats.orc_sight import ORC_SIGHT_STATUS
from statuses.race.human.heritages.half_orc import HALF_ORC_STATUS


class DummyHero(StatusMixin):
    def __init__(self):
        self.statuses = []
        self.level = 1


def test_cooperative_nature_adds_plus_four_to_aid_checks():
    actor = DummyHero()
    actor.add_status(COOPERATIVE_NATURE_STATUS)

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.ATHLETICS.value,
        dc=15,
        actor=actor,
        tags=["aid", Skill.ATHLETICS.value],
        roll=10,
        apply_modifiers=True,
    )

    assert result.modifier == 4


def test_haughty_obstinacy_promotes_success_vs_mental_control():
    actor = DummyHero()
    actor.add_status(HAUGHTY_OBSTINACY_STATUS)

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=["mental", "control", Skill.WILL.value],
        roll=15,
        apply_modifiers=True,
    )

    assert result.outcome == "critical_success"


def test_haughty_obstinacy_demotes_failed_coerce_against_target():
    target = DummyHero()
    target.add_status(HAUGHTY_OBSTINACY_STATUS)

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.INTIMIDATION.value,
        dc=15,
        actor=DummyHero(),
        target=target,
        tags=["coerce", Skill.INTIMIDATION.value],
        roll=14,
        apply_modifiers=True,
    )

    assert result.outcome == "critical_failure"


def test_orc_sight_requires_low_light_vision_and_first_level():
    actor = DummyHero()
    assert actor.add_status(ORC_SIGHT_STATUS) is False

    assert actor.add_status(HALF_ORC_STATUS) is True
    assert actor.has_status("dim_light_vision") is True
    assert actor.add_status(ORC_SIGHT_STATUS) is True
    assert actor.has_status("darkvision") is True


def test_orc_sight_fails_above_first_level_even_with_low_light():
    actor = DummyHero()
    actor.level = 2
    actor.add_status(HALF_ORC_STATUS)

    added = actor.add_status(ORC_SIGHT_STATUS)

    assert added is False
    assert actor.has_status("orc_sight") is False
