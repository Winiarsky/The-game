from __future__ import annotations

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from skills import Skill
from statuses.race.gnome.feats.burrow_elocutionist import BURROW_ELOCUTIONIST_STATUS
from statuses.race.gnome.feats.fey_fellowship import FEY_FELLOWSHIP_STATUS
from statuses.race.gnome.feats.first_world_magic import FIRST_WORLD_MAGIC_STATUS
from statuses.race.gnome.feats.gnome_obsession import GNOME_OBSESSION_STATUS
from statuses.race.gnome.feats.gnome_weapon_familiarity import GNOME_WEAPON_FAMILIARITY_STATUS
from statuses.race.gnome.feats.illusion_sense import ILLUSION_SENSE_STATUS
from statuses.race.gnome.heritages.fey_touched_gnome import FEY_TOUCHED_GNOME_STATUS
from statuses.race.gnome.heritages.wellspring_gnome import WELLSPRING_GNOME_STATUS


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


def test_gnome_weapon_familiarity_has_runtime_data():
    data = GNOME_WEAPON_FAMILIARITY_STATUS.data
    overrides = data.get("weapon_proficiency_overrides") or {}
    assert overrides.get("glaive") == "trained"
    assert overrides.get("kukri") == "trained"
    assert data.get("weapon_category_adjustments")


def test_illusion_sense_has_plus_one_without_promote():
    actor = DummyHero()
    actor.add_status(ILLUSION_SENSE_STATUS)
    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=["illusion", Skill.WILL.value],
        roll=14,
        apply_modifiers=True,
    )
    assert result.modifier == 1
    assert result.outcome == "success"


def test_fey_fellowship_bonus_applies_vs_fey():
    actor = DummyHero()
    actor.add_status(FEY_FELLOWSHIP_STATUS)
    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=15,
        actor=actor,
        tags=["fey", Skill.PERCEPTION.value],
        roll=10,
        apply_modifiers=True,
    )
    assert result.modifier == 2


def test_burrow_elocutionist_has_capability_flags():
    data = BURROW_ELOCUTIONIST_STATUS.data
    assert data.get("can_talk_to_burrow_animals") is True
    assert data.get("burrow_elocutionist_uses_diplomacy") is True


def test_gnome_obsession_records_selected_lore(monkeypatch):
    dummy_ui = DummyUI(["Fey Lore"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    hero = DummyHero()
    added = hero.add_status(GNOME_OBSESSION_STATUS)
    assert added is True
    assert hero.get_status_data("gnome_obsession", "gnome_obsession_lore", None) == "fey_lore"
    assert hero.get_status_data("gnome_obsession", "trained_lore", []) == ["fey_lore"]


def test_wellspring_overrides_existing_first_world_magic_tradition(monkeypatch):
    dummy_ui = DummyUI(["Light", "Occult", "Daze"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    hero = DummyHero()
    assert hero.add_status(FIRST_WORLD_MAGIC_STATUS) is True
    assert hero.get_status_data("first_world_magic", "innate_magic_tradition", None) == "primal"
    assert hero.add_status(WELLSPRING_GNOME_STATUS) is True
    assert hero.get_status_data("first_world_magic", "innate_magic_tradition", None) == "occult"


def test_wellspring_overrides_fey_touched_added_later(monkeypatch):
    dummy_ui = DummyUI(["Occult", "Daze", "Guidance"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)
    hero = DummyHero()
    assert hero.add_status(WELLSPRING_GNOME_STATUS) is True
    assert hero.add_status(FEY_TOUCHED_GNOME_STATUS) is True
    assert hero.get_status_data("fey_touched_gnome", "innate_magic_tradition", None) == "occult"
