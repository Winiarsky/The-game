from __future__ import annotations

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from skills import Skill
from statuses import Status
from statuses.race.elfs.feats.ancestral_longevity import ANCESTRAL_LONGEVITY_STATUS
from statuses.race.elfs.feats.elven_lore import ELVEN_LORE_STATUS
from statuses.race.elfs.feats.elven_weapon_familiarity import ELVEN_WEAPON_FAMILIARITY_STATUS
from statuses.race.elfs.feats.forlorn import FORLORN_STATUS
from statuses.race.elfs.feats.nimble_elf import NIMBLE_ELF_STATUS
from statuses.race.elfs.feats.otherworldly_magic import OTHERWORLDLY_MAGIC_STATUS
from statuses.race.elfs.feats.unwavering_mien import UNWAVERING_MIEN_STATUS


class DummyHero(StatusMixin):
    def __init__(self, *, age_years: int | None = None):
        self.statuses = []
        self.age_years = age_years


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


def test_nimble_elf_has_runtime_speed_bonus_field():
    data = NIMBLE_ELF_STATUS.data
    assert int(data.get("base_speed_bonus_feet", 0) or 0) == 5


def test_elven_weapon_familiarity_has_runtime_data():
    data = ELVEN_WEAPON_FAMILIARITY_STATUS.data
    overrides = data.get("weapon_proficiency_overrides") or {}
    assert overrides.get("longbow") == "trained"
    assert overrides.get("shortbow") == "trained"
    assert data.get("weapon_category_adjustments")
    assert "Przykład" in str(data.get("ui_description", ""))


def test_elven_lore_has_runtime_trained_fields():
    data = ELVEN_LORE_STATUS.data
    assert data.get("ui_choice_kind") == "elven_lore"
    assert "arcana" in list(data.get("trained_skills") or [])
    assert "nature" in list(data.get("trained_skills") or [])
    assert "elven_lore" in list(data.get("trained_lore") or [])


def test_forlorn_grants_bonus_and_promote_vs_emotion():
    actor = DummyHero()
    actor.add_status(FORLORN_STATUS)
    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=["emotion", "will"],
        roll=14,
        apply_modifiers=True,
    )
    assert result.modifier == 1
    assert result.outcome == "critical_success"


def test_otherworldly_magic_records_selected_cantrip(monkeypatch):
    dummy_ui = DummyUI(["Shield"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    hero = DummyHero()
    added = hero.add_status(OTHERWORLDLY_MAGIC_STATUS)
    assert added is True
    assert hero.get_status_data("otherworldly_magic", "otherworldly_magic_cantrip", None) == "shield"
    assert hero.get_status_data("otherworldly_magic", "granted_cantrips", []) == ["shield"]


def test_ancestral_longevity_requires_age_when_age_is_present():
    hero = DummyHero(age_years=80)
    assert hero.add_status(ANCESTRAL_LONGEVITY_STATUS) is False


def test_ancestral_longevity_records_selected_skill(monkeypatch):
    dummy_ui = DummyUI(["Stealth"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    hero = DummyHero(age_years=180)
    added = hero.add_status(ANCESTRAL_LONGEVITY_STATUS)
    assert added is True
    assert hero.get_status_data("ancestral_longevity", "ancestral_longevity_skill", None) == "stealth"
    assert hero.get_status_data("ancestral_longevity", "trained_skills", []) == ["stealth"]


def test_unwavering_mien_reduces_duration_of_incoming_mental_effect():
    hero = DummyHero()
    hero.add_status(UNWAVERING_MIEN_STATUS)
    slowed_mind = Status(
        id="mental_test",
        duration=3,
        data={"effect_tags": ["mental"]},
    )
    hero.add_status(slowed_mind)
    reduced = hero.get_status("mental_test")
    assert reduced is not None
    assert int(getattr(reduced, "duration", 0) or 0) == 2
