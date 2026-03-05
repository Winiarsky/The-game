from __future__ import annotations

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from skills import Skill
from statuses import Status
from statuses.race.goblin.feats.city_scavenger import CITY_SCAVENGER_STATUS
from statuses.race.goblin.feats.goblin_lore import GOBLIN_LORE_STATUS
from statuses.race.goblin.feats.goblin_scuttle import GoblinScuttleStatus
from statuses.race.goblin.feats.goblin_song import GOBLIN_SONG_STATUS
from statuses.race.goblin.feats.goblin_weapon_familiarity import GOBLIN_WEAPON_FAMILIARITY_STATUS
from statuses.race.goblin.feats.junk_tinker import JUNK_TINKER_STATUS
from statuses.race.goblin.feats.rough_rider import ROUGH_RIDER_STATUS
from statuses.race.goblin.feats.very_sneaky import VERY_SNEAKY_STATUS
from statuses.race.goblin.heritages.irongut_goblin import IRONGUT_GOBLIN_STATUS


class DummyHero(StatusMixin):
    def __init__(self):
        self.statuses = []


class DummyUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None


def test_city_scavenger_has_tagged_subsist_bonus():
    actor = DummyHero()
    actor.add_status(CITY_SCAVENGER_STATUS)
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.SOCIETY.value,
        dc=15,
        actor=actor,
        tags=[Skill.SOCIETY.value, "subsist", "settlement"],
        roll=14,
        apply_modifiers=True,
    )
    assert res.modifier == 1
    assert res.outcome == "success"


def test_city_scavenger_gets_plus_two_with_irongut_if_added_after():
    actor = DummyHero()
    actor.add_status(IRONGUT_GOBLIN_STATUS)
    actor.add_status(CITY_SCAVENGER_STATUS)
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.SURVIVAL.value,
        dc=15,
        actor=actor,
        tags=[Skill.SURVIVAL.value, "subsist", "settlement"],
        roll=13,
        apply_modifiers=True,
    )
    assert res.modifier == 2
    assert res.outcome == "success"


def test_city_scavenger_gets_plus_two_with_irongut_if_added_before():
    actor = DummyHero()
    actor.add_status(CITY_SCAVENGER_STATUS)
    actor.add_status(IRONGUT_GOBLIN_STATUS)
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.SURVIVAL.value,
        dc=15,
        actor=actor,
        tags=[Skill.SURVIVAL.value, "subsist", "settlement"],
        roll=13,
        apply_modifiers=True,
    )
    assert res.modifier == 2


def test_goblin_scuttle_duration_default():
    status = GoblinScuttleStatus()
    assert status.duration == 1


def test_goblin_weapon_familiarity_has_runtime_data():
    data = GOBLIN_WEAPON_FAMILIARITY_STATUS.data
    overrides = data.get("weapon_proficiency_overrides") or {}
    assert overrides.get("dogslicer") == "trained"
    assert overrides.get("horsechopper") == "trained"
    assert data.get("weapon_category_adjustments")


def test_goblin_lore_choice_replaces_overlapping_training(monkeypatch):
    dummy_ui = DummyUI(["Arcana"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    actor = DummyHero()
    actor.add_status(Status(id="trained_arcana", data={"trained_skills": ["nature"]}))
    added = actor.add_status(GOBLIN_LORE_STATUS)
    assert added is True
    trained = actor.get_status_data("goblin_lore", "trained_skills", [])
    assert "stealth" in trained
    assert "arcana" in trained
    assert "nature" not in trained


def test_goblin_song_has_runtime_scaling_data():
    data = GOBLIN_SONG_STATUS.data
    assert int(data.get("goblin_song_range_feet", 0) or 0) == 30
    by_rank = data.get("goblin_song_max_targets_by_rank") or {}
    assert by_rank.get("expert") == 2
    assert by_rank.get("master") == 4
    assert by_rank.get("legendary") == 8


def test_very_sneaky_has_sneak_bonus_hook():
    data = VERY_SNEAKY_STATUS.data
    assert int(data.get("sneak_bonus_feet", 0) or 0) == 5


def test_junk_tinker_and_rough_rider_have_capability_data():
    junk = JUNK_TINKER_STATUS.data
    rough = ROUGH_RIDER_STATUS.data
    assert junk.get("junk_tinker_can_craft_level0_from_junk") is True
    assert junk.get("junk_tinker_ignore_selfmade_shoddy_penalty") is True
    assert "ride" in list(rough.get("granted_feat_ids") or [])
