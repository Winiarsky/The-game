from __future__ import annotations

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from hero import Hero
from skills import Skill
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS
from statuses.race.halfling.halfling import HALFLING_STATUS
from statuses.race.halfling.heritages.gutsy_halfling import GUTSY_HALFLING_STATUS
from statuses.race.halfling.heritages.hillock_halfling import HILLOCK_HALFLING_STATUS
from statuses.race.halfling.heritages.nomadic_halfling import NOMADIC_HALFLING_STATUS
from statuses.race.halfling.heritages.twilight_halfling import TWILIGHT_HALFLING_STATUS
from statuses.race.halfling.heritages.wildwood_halfling import WILDWOOD_HALFLING_STATUS


def test_halfling_base_has_mechanical_fields_and_keen_eyes():
    data = HALFLING_STATUS.data
    assert int(data.get("ancestry_hp", 0) or 0) == 6
    assert int(data.get("base_speed_feet", 0) or 0) == 25
    assert str(data.get("size", "")).lower() == "small"
    assert "halfling" in list(data.get("ancestry_traits") or [])
    assert "humanoid" in list(data.get("ancestry_traits") or [])
    hero = Hero()
    hero.add_status(HALFLING_STATUS)
    assert hero.has_status("keen_eyes")


def test_gutsy_halfling_promotes_emotion_success():
    actor = Hero()
    actor.add_status(GUTSY_HALFLING_STATUS)
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=["emotion", Skill.WILL.value],
        roll=15,
        apply_modifiers=True,
    )
    assert res.outcome == "critical_success"


def test_hillock_halfling_has_healing_hooks():
    data = HILLOCK_HALFLING_STATUS.data
    assert int(data.get("overnight_healing_bonus_per_level", 0) or 0) == 1
    assert int(data.get("treat_wounds_healing_bonus_per_level", 0) or 0) == 1
    assert data.get("treat_wounds_requires_snack") is True


def test_nomadic_halfling_language_hooks():
    data = NOMADIC_HALFLING_STATUS.data
    assert int(data.get("additional_languages", 0) or 0) == 2
    assert int(data.get("multilingual_bonus_languages", 0) or 0) == 1


def test_twilight_halfling_grants_dim_light_vision_status():
    grants = list(TWILIGHT_HALFLING_STATUS.data.get("grants_statuses") or [])
    assert any(getattr(s, "id", None) == DIM_LIGHT_VISION_STATUS.id for s in grants)


def test_wildwood_halfling_ignores_foliage_like_terrain():
    tags = list(WILDWOOD_HALFLING_STATUS.data.get("ignore_move_cost_terrain_tags") or [])
    assert "trees" in tags
    assert "foliage" in tags
    assert "undergrowth" in tags
