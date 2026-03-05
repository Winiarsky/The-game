from __future__ import annotations

from GameObjects.interactions_mixin import skill_check_resolver
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from skills import Skill
from statuses import Status
from statuses.race.halfling.feats.halfling_lore import HALFLING_LORE_STATUS
from statuses.race.halfling.feats.halfling_luck import HALFLING_LUCK_STATUS
from statuses.race.halfling.feats.halfling_weapon_familiarity import HALFLING_WEAPON_FAMILIARITY_STATUS
from statuses.race.halfling.feats.sure_feet import SURE_FEET_STATUS
from statuses.race.halfling.feats.titan_slinger import TITAN_SLINGER_STATUS
from statuses.race.halfling.feats.unfettered_halfling import UNFETTERED_HALFLING_STATUS
from statuses.race.halfling.feats.watchful_halfling import WATCHFUL_HALFLING_STATUS


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


def test_watchful_halfling_sense_motive_bonus():
    actor = DummyHero()
    actor.add_status(WATCHFUL_HALFLING_STATUS)
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=15,
        actor=actor,
        tags=["sense_motive", Skill.PERCEPTION.value],
        roll=13,
        apply_modifiers=True,
    )
    assert res.modifier == 2
    assert res.total == 15


def test_sure_feet_promotes_balance_success():
    actor = DummyHero()
    actor.add_status(SURE_FEET_STATUS)
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.ACROBATICS.value,
        dc=15,
        actor=actor,
        tags=["balance", Skill.ACROBATICS.value],
        roll=15,
        apply_modifiers=True,
    )
    assert res.outcome == "critical_success"


def test_halfling_luck_reroll_consumes_status(monkeypatch):
    actor = DummyHero()
    actor.add_status(HALFLING_LUCK_STATUS)

    class LuckUI:
        enabled = True

        def prompt_choice(self, *a, **k):
            return "tak"

    monkeypatch.setattr(skill_check_resolver, "get_ui_client", lambda: LuckUI())
    monkeypatch.setattr(skill_check_resolver, "prompt_for_roll", lambda *a, **k: 18)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=[Skill.WILL.value],
        roll=5,
        apply_modifiers=True,
    )
    assert res.outcome in ("success", "critical_success")
    assert actor.has_status("halfling_luck") is False


def test_halfling_lore_choice_replaces_overlapping_training(monkeypatch):
    dummy_ui = DummyUI(["Arcana"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    actor = DummyHero()
    actor.add_status(Status(id="trained_acrobatics", data={"trained_skills": ["acrobatics"]}))
    assert actor.add_status(HALFLING_LORE_STATUS) is True
    trained = actor.get_status_data("halfling_lore", "trained_skills", [])
    assert "stealth" in trained
    assert "arcana" in trained
    assert "acrobatics" not in trained


def test_halfling_weapon_familiarity_has_runtime_data():
    data = HALFLING_WEAPON_FAMILIARITY_STATUS.data
    overrides = data.get("weapon_proficiency_overrides") or {}
    assert overrides.get("sling") == "trained"
    assert overrides.get("halfling_sling_staff") == "trained"
    assert overrides.get("shortsword") == "trained"
    assert data.get("weapon_category_adjustments")


def test_titan_slinger_has_large_target_hook():
    data = TITAN_SLINGER_STATUS.data
    assert "sling" in list(data.get("titan_slinger_weapon_ids") or [])
    assert data.get("titan_slinger_min_target_size") == "large"
    assert int(data.get("titan_slinger_damage_die_step_increase", 0) or 0) == 1


def test_unfettered_halfling_promotes_escape_and_punishes_grapple_failure():
    actor = DummyHero()
    actor.add_status(UNFETTERED_HALFLING_STATUS)
    escape = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.ACROBATICS.value,
        dc=15,
        actor=actor,
        tags=["escape", Skill.ACROBATICS.value],
        roll=15,
        apply_modifiers=True,
    )
    assert escape.outcome == "critical_success"
    grapple = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.ATHLETICS.value,
        dc=15,
        actor=DummyHero(),
        target=actor,
        tags=["grapple", Skill.ATHLETICS.value],
        roll=14,
        apply_modifiers=True,
    )
    assert grapple.outcome == "critical_failure"
