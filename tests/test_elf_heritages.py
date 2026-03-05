from __future__ import annotations

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from hero import Hero
from skills import Skill
from statuses import BLINDED_STATUS
from statuses.darkvision import DARKVISION_STATUS
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS
from statuses.race.elfs.elf import ELF_STATUS
from statuses.race.elfs.heritages.arctic_elf import ARCTIC_ELF_STATUS
from statuses.race.elfs.heritages.cavern_elf import CAVERN_ELF_STATUS
from statuses.race.elfs.heritages.seer_elf import SEER_ELF_STATUS
from statuses.race.elfs.heritages.whisper_elf import WHISPER_ELF_STATUS
from statuses.race.elfs.heritages.woodland_elf import WOODLAND_ELF_STATUS


def test_arctic_elf_has_resistance_and_environment_hook():
    data = ARCTIC_ELF_STATUS.data
    resist = data.get("damage_resistance") or {}
    cold = resist.get("cold") or {}
    assert cold.get("per_2_levels") == 1
    assert cold.get("minimum") == 1
    assert int(data.get("cold_environment_step_reduction", 0) or 0) == 1


def test_cavern_elf_replaces_dim_light_with_darkvision():
    hero = Hero()
    hero.add_status(ELF_STATUS)
    assert hero.has_status(DIM_LIGHT_VISION_STATUS)
    hero.add_status(CAVERN_ELF_STATUS)
    assert not hero.has_status(DIM_LIGHT_VISION_STATUS)
    assert hero.has_status(DARKVISION_STATUS)


def test_seer_elf_bonus_applies_to_identify_magic_checks():
    hero = Hero()
    hero.add_status(SEER_ELF_STATUS)
    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.NATURE.value,
        dc=15,
        actor=hero,
        tags=["identify_magic", "nature"],
        roll=10,
        apply_modifiers=True,
    )
    assert result.modifier == 1


def test_whisper_elf_has_seek_radius_and_no_blind_immunity():
    data = WHISPER_ELF_STATUS.data
    assert int(data.get("seek_sense_radius_feet", 0) or 0) == 60
    assert int(data.get("seek_audio_locate_bonus_within_feet", 0) or 0) == 30

    hero = Hero()
    hero.add_status(WHISPER_ELF_STATUS)
    added = hero.add_status(BLINDED_STATUS)
    assert added is True


def test_woodland_elf_take_cover_and_climb_hooks_present():
    data = WOODLAND_ELF_STATUS.data
    assert "forest" in list(data.get("allow_take_cover_terrain_tags") or [])
    effects = list(WOODLAND_ELF_STATUS.check_effects or [])
    assert effects
    assert any("climb" in list(effect.tags_required or []) for effect in effects)
