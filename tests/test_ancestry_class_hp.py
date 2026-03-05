from hero import Hero
from combat.hp_engine import computed_max_hp
from statuses import Status
from statuses.classes.fighter.fighter import FIGHTER_STATUS
from statuses.race.dwarf.dwarf import DWARF_STATUS


def test_dwarf_status_has_mechanical_ancestry_fields():
    data = DWARF_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 10
    assert int(data.get("base_speed_feet", 0) or 0) == 20
    assert str(data.get("size", "")).lower() == "medium"


def test_computed_hp_uses_ancestry_plus_class_components():
    hero = Hero()
    hero.add_status(DWARF_STATUS)
    hero.add_status(FIGHTER_STATUS)

    assert computed_max_hp(hero) == 20


def test_component_hp_still_adds_flat_status_bonuses():
    hero = Hero()
    hero.add_status(DWARF_STATUS)
    hero.add_status(FIGHTER_STATUS)
    hero.add_status(Status(id="hp_bonus_test", data={"max_hp_flat": 3}))

    assert computed_max_hp(hero) == 23


def test_fallback_to_actor_max_hp_when_components_missing():
    hero = Hero()
    hero.max_hp = 33
    assert computed_max_hp(hero) == 33
