import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bonuses import BonusEffect, BonusType  # noqa: E402
from GameObjects.events.attack.attack_base import AttackEventBase  # noqa: E402


class DummyAttack(AttackEventBase):
    name = "dummy_attack"


class DummyAttacker:
    def __init__(self, object_id="hero-1", modifier=0, formatted=""):
        self.object_id = object_id
        self._modifier = modifier
        self._formatted = formatted

    def compute_modifier(self, tag, target=None):
        return self._modifier

    def format_prompt(self, tag, target=None):
        return self._formatted


class DummyTarget:
    def __init__(self, ac=15, bonuses=None):
        self.ac = ac
        self.bonuses = bonuses or []


def test_ac_with_bonuses_applies_extra_and_target_filters_target_id():
    attacker = DummyAttacker(object_id="hero-1")
    matching = BonusEffect(
        type=BonusType.STATUS,
        value=1,
        tag="ac",
        source="buff",
        target_id="hero-1",
    )
    mismatching = BonusEffect(
        type=BonusType.STATUS,
        value=2,
        tag="ac",
        source="other",
        target_id="enemy-xyz",
    )
    extra_cover = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag="ac",
        source="cover:greater",
        target_id="hero-1",
    )
    target = DummyTarget(ac=15, bonuses=[matching, mismatching])

    attack = DummyAttack()
    target_ac, base_ac, modifier = attack._ac_with_bonuses(target, attacker=attacker, extra_bonuses=[extra_cover])

    assert base_ac == 15
    # only matching STATUS + extra_cover (circumstance) should count: 1 + 2 = 3
    assert modifier == 3
    assert target_ac == 18


def test_attacker_modifier_uses_compute_modifier():
    attacker = DummyAttacker(modifier=-2)
    attack = DummyAttack()

    mod = attack._attacker_modifier(attacker, "attack_melee")
    assert mod == -2


def test_format_bonus_info_uses_formatter_output():
    attacker = DummyAttacker(formatted="+1 flank")
    attack = DummyAttack()

    info = attack._format_bonus_info(attacker, "attack_melee")
    assert "+1 flank" in info
    assert "Modyfikatory" in info
