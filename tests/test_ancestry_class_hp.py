from hero import Hero
from combat.hp_engine import computed_max_hp
import importlib.util
import sys
from pathlib import Path
from statuses import Status
from statuses.classes.fighter.fighter import FIGHTER_STATUS
from statuses.race.dwarf.dwarf import DWARF_STATUS
from statuses.race.elfs.elf import ELF_STATUS
from statuses.race.elfs.feats.nimble_elf import NIMBLE_ELF_STATUS
from statuses.race.gnome.gnome import GNOME_STATUS
from statuses.race.goblin.goblin import GOBLIN_STATUS
from statuses.race.halfling.halfling import HALFLING_STATUS
from statuses.race.human.human import HUMAN_STATUS


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


def test_elf_status_has_mechanical_ancestry_fields():
    data = ELF_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 6
    assert int(data.get("base_speed_feet", 0) or 0) == 30
    assert str(data.get("size", "")).lower() == "medium"
    assert "elf" in list(data.get("ancestry_traits") or [])
    assert "humanoid" in list(data.get("ancestry_traits") or [])


def test_elf_plus_fighter_uses_component_hp():
    hero = Hero()
    hero.add_status(ELF_STATUS)
    hero.add_status(FIGHTER_STATUS)
    assert computed_max_hp(hero) == 16


def test_nimble_elf_adds_5_to_base_speed():
    project_root = Path(__file__).resolve().parents[1]
    move_utils_path = project_root / "src" / "actions" / "move_utils.py"
    spec = importlib.util.spec_from_file_location("actions.move_utils", move_utils_path)
    move_utils = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(move_utils)  # type: ignore[arg-type]
    sys.modules["actions.move_utils"] = move_utils

    hero = Hero()
    hero.add_status(ELF_STATUS)
    hero.add_status(NIMBLE_ELF_STATUS)
    assert move_utils.base_speed_feet(hero) == 35


def test_gnome_status_has_mechanical_ancestry_fields():
    data = GNOME_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 8
    assert int(data.get("base_speed_feet", 0) or 0) == 25
    assert str(data.get("size", "")).lower() == "small"
    assert "gnome" in list(data.get("ancestry_traits") or [])
    assert "humanoid" in list(data.get("ancestry_traits") or [])


def test_gnome_plus_fighter_uses_component_hp():
    hero = Hero()
    hero.add_status(GNOME_STATUS)
    hero.add_status(FIGHTER_STATUS)
    assert computed_max_hp(hero) == 18


def test_goblin_status_has_mechanical_ancestry_fields():
    data = GOBLIN_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 6
    assert int(data.get("base_speed_feet", 0) or 0) == 25
    assert str(data.get("size", "")).lower() == "small"
    assert "goblin" in list(data.get("ancestry_traits") or [])
    assert "humanoid" in list(data.get("ancestry_traits") or [])


def test_goblin_plus_fighter_uses_component_hp():
    hero = Hero()
    hero.add_status(GOBLIN_STATUS)
    hero.add_status(FIGHTER_STATUS)
    assert computed_max_hp(hero) == 16


def test_halfling_status_has_mechanical_ancestry_fields():
    data = HALFLING_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 6
    assert int(data.get("base_speed_feet", 0) or 0) == 25
    assert str(data.get("size", "")).lower() == "small"
    assert "halfling" in list(data.get("ancestry_traits") or [])
    assert "humanoid" in list(data.get("ancestry_traits") or [])


def test_halfling_plus_fighter_uses_component_hp():
    hero = Hero()
    hero.add_status(HALFLING_STATUS)
    hero.add_status(FIGHTER_STATUS)
    assert computed_max_hp(hero) == 16


def test_human_status_has_mechanical_ancestry_fields():
    data = HUMAN_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 8
    assert int(data.get("base_speed_feet", 0) or 0) == 25
    assert str(data.get("size", "")).lower() == "medium"
    assert "human" in list(data.get("ancestry_traits") or [])
    assert "humanoid" in list(data.get("ancestry_traits") or [])


def test_human_plus_fighter_uses_component_hp():
    hero = Hero()
    hero.add_status(HUMAN_STATUS)
    hero.add_status(FIGHTER_STATUS)
    assert computed_max_hp(hero) == 18
