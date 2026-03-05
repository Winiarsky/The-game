from hero import Hero
from actions.move_utils import movement_budget_feet
from statuses import SpeedPenaltyStatus
from statuses.race.dwarf.dwarf import DWARF_STATUS
from statuses.race.dwarf.feats.unburdened_iron import UNBURDENED_IRON_STATUS


def test_dwarf_base_speed_is_used_in_budget():
    hero = Hero()
    hero.add_status(DWARF_STATUS)
    assert movement_budget_feet(hero, default_feet=25) == 20


def test_unburdened_iron_reduces_speed_penalty_by_5():
    hero = Hero()
    hero.add_status(DWARF_STATUS)
    hero.add_status(SpeedPenaltyStatus(penalty_feet=10))
    assert movement_budget_feet(hero, default_feet=25) == 10

    hero.add_status(UNBURDENED_IRON_STATUS)
    assert movement_budget_feet(hero, default_feet=25) == 15
