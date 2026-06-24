from statuses import Status
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from damage_types import DamageType


class Dummy:
    def __init__(self, level=1):
        self.level = level
        self.statuses = [Status(id="burn_it")]


def test_burn_it_bonus_fire_minimum():
    actor = Dummy(level=1)
    assert burn_it_bonus(actor, DamageType.FIRE.value, source_kind="spell", spell_rank=1) == 1


def test_burn_it_bonus_spell_scales_with_rank():
    actor = Dummy(level=5)
    assert burn_it_bonus(actor, DamageType.FIRE.value, source_kind="spell", spell_rank=6) == 3


def test_burn_it_bonus_alchemical_scales_with_item_level():
    actor = Dummy(level=5)
    assert burn_it_bonus(actor, DamageType.FIRE.value, source_kind="alchemical", item_level=11) == 2


def test_burn_it_bonus_non_fire():
    actor = Dummy(level=5)
    assert burn_it_bonus(actor, DamageType.COLD.value, source_kind="spell", spell_rank=5) == 0


def test_burn_it_bonus_ignores_non_spell_non_alchemical_sources():
    actor = Dummy(level=5)
    assert burn_it_bonus(actor, DamageType.FIRE.value) == 0
    assert burn_it_bonus(actor, DamageType.FIRE.value, source_kind="weapon") == 0


def test_burn_it_bonus_persistent():
    actor = Dummy(level=10)
    assert burn_it_bonus(actor, DamageType.FIRE.value, persistent=True, source_kind="spell", spell_rank=5) == 1


def test_burn_it_prompt_persistent_note():
    actor = Dummy(level=10)
    note = burn_it_prompt_note(actor, DamageType.FIRE.value, persistent=True, source_kind="spell", spell_rank=5)
    assert note and "persistent fire" in note
