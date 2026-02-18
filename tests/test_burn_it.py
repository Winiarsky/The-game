from statuses import Status
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from damage_types import DamageType


class Dummy:
    def __init__(self, level=1):
        self.level = level
        self.statuses = [Status(id="burn_it")]


def test_burn_it_bonus_fire_minimum():
    actor = Dummy(level=1)
    assert burn_it_bonus(actor, DamageType.FIRE.value) == 1


def test_burn_it_bonus_fire_scales():
    actor = Dummy(level=5)
    assert burn_it_bonus(actor, DamageType.FIRE.value) == 2


def test_burn_it_bonus_non_fire():
    actor = Dummy(level=5)
    assert burn_it_bonus(actor, DamageType.COLD.value) == 0


def test_burn_it_bonus_persistent():
    actor = Dummy(level=10)
    assert burn_it_bonus(actor, DamageType.FIRE.value, persistent=True) == 1


def test_burn_it_prompt_persistent_note():
    actor = Dummy(level=10)
    note = burn_it_prompt_note(actor, DamageType.FIRE.value, persistent=True)
    assert note and "-1" in note
