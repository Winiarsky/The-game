from __future__ import annotations

from combat.hp_engine import computed_max_hp
from hero import Hero
from statuses.base import Status
from statuses.classes.fighter.fighter import FIGHTER_STATUS
from statuses.darkvision import DARKVISION_STATUS
from statuses.race.goblin.goblin import GOBLIN_STATUS
from statuses.race.goblin.heritages.charhide_goblin import CHARHIDE_GOBLIN_STATUS
from statuses.race.goblin.heritages.irongut_goblin import IRONGUT_GOBLIN_STATUS
from statuses.race.goblin.heritages.razortooth_goblin import RAZORTOOTH_GOBLIN_STATUS
from statuses.race.goblin.heritages.snow_goblin import SNOW_GOBLIN_STATUS
from statuses.race.goblin.heritages.unbreakable_goblin import UNBREAKABLE_GOBLIN_STATUS


def test_goblin_base_status_has_mechanical_fields():
    data = GOBLIN_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 6
    assert int(data.get("base_speed_feet", 0) or 0) == 25
    assert str(data.get("size", "")).lower() == "small"
    assert "goblin" in list(data.get("ancestry_traits") or [])
    assert "humanoid" in list(data.get("ancestry_traits") or [])


def test_goblin_base_grants_darkvision():
    hero = Hero()
    hero.add_status(GOBLIN_STATUS)
    assert hero.has_status(DARKVISION_STATUS)


def test_charhide_has_fire_resistance_and_persistent_dc_hook():
    data = CHARHIDE_GOBLIN_STATUS.data
    resist = data.get("damage_resistance") or {}
    fire = resist.get("fire") or {}
    assert fire.get("per_2_levels") == 1
    assert fire.get("minimum") == 1
    dc_overrides = data.get("persistent_damage_flat_check_dc_overrides") or {}
    assert int(dc_overrides.get("fire", 0) or 0) == 10


def test_irongut_has_ingested_fortitude_bonus():
    effects = list(IRONGUT_GOBLIN_STATUS.check_effects or [])
    assert effects
    assert any("ingested" in list(effect.tags_required or []) for effect in effects)


def test_razortooth_has_unarmed_attack_profile():
    data = RAZORTOOTH_GOBLIN_STATUS.data
    attacks = list(data.get("granted_unarmed_attacks") or [])
    assert attacks
    jaws = attacks[0]
    assert jaws.get("id") == "razortooth_jaws"
    assert jaws.get("damage_dice") == "1d6"
    assert "finesse" in list(jaws.get("traits") or [])


def test_snow_has_cold_resistance_and_environment_hook():
    data = SNOW_GOBLIN_STATUS.data
    resist = data.get("damage_resistance") or {}
    cold = resist.get("cold") or {}
    assert cold.get("per_2_levels") == 1
    assert cold.get("minimum") == 1
    assert int(data.get("cold_environment_step_reduction", 0) or 0) == 1


def test_unbreakable_adds_effective_plus_four_max_hp():
    hero = Hero()
    hero.add_status(GOBLIN_STATUS)
    hero.add_status(FIGHTER_STATUS)
    hero.add_status(UNBREAKABLE_GOBLIN_STATUS)
    assert computed_max_hp(hero) == 20
    assert int(UNBREAKABLE_GOBLIN_STATUS.data.get("max_hp_flat", 0) or 0) == 4


def test_inventory_default_loadout_can_use_razortooth_jaws():
    from GameObjects.items.inventory import default_weapon_ids_for_actor

    hero = Hero()
    hero.add_status(RAZORTOOTH_GOBLIN_STATUS)
    weapons = default_weapon_ids_for_actor(hero)
    assert "razortooth_jaws" in weapons


def test_charhide_override_works_from_status_data_path():
    # smoke test: data-based override key is present and parseable by persistent damage system.
    actor = Hero()
    actor.add_status(Status(id="persistent_damage", data={"amount": 1, "damage_type": "fire"}))
    actor.add_status(CHARHIDE_GOBLIN_STATUS)
    override = (actor.get_status_data("charhide_goblin", "persistent_damage_flat_check_dc_overrides", {}) or {}).get("fire")
    assert int(override or 0) == 10
