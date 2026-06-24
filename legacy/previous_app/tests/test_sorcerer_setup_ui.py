from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.classes.sorcerer.sorcerer import SORCERER_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


class DummyUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True
        self.allow_cli_fallback = False

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None

    def prompt_info(self, *_args, **_kwargs):
        return None


def test_imperial_setup_sets_tradition_granted_spells_and_feat(monkeypatch):
    ui = DummyUI(["Imperial", "Dangerous Sorcery"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.reactions = []
    hero.add_status(SORCERER_STATUS)

    assert hero.has_status("sorcerer")
    assert hero.get_status_data("sorcerer", "sorcerer_bloodline", None) == "imperial"
    assert hero.get_status_data("sorcerer", "sorcerer_spell_tradition", None) == "arcane"
    assert hero.get_status_data("sorcerer", "sorcerer_class_feat", None) == "dangerous_sorcery"
    assert hero.get_status_data("sorcerer", "sorcerer_bloodline_initial_focus_spell", None) == "ancestral_memories"
    assert getattr(hero, "class_name", None) == "sorcerer"
    assert getattr(hero, "focus_point", None) == 1
    assert hero.has_status("dangerous_sorcery")
    assert "detect_magic" in list(getattr(hero, "sorcerer_known_cantrips", []) or [])
    assert "magic_missile" in list(getattr(hero, "sorcerer_known_rank_1_spells", []) or [])


def test_draconic_setup_prompts_for_dragon_type(monkeypatch):
    ui = DummyUI(["Draconic", "Red", "Reach Spell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(SORCERER_STATUS)

    setup = dict(hero.get_status_data("sorcerer", "sorcerer_setup", {}) or {})
    assert setup.get("bloodline") == "draconic"
    assert setup.get("dragon_type") == "red"
    assert setup.get("dragon_damage_type") == "fire"
    assert hero.get_status_data("sorcerer", "sorcerer_spell_tradition", None) == "arcane"
    assert hero.has_status("reach_spell")


def test_elemental_setup_prompts_for_element_type_and_can_grant_familiar(monkeypatch):
    ui = DummyUI(["Elemental", "Water", "Familiar"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(SORCERER_STATUS)

    setup = dict(hero.get_status_data("sorcerer", "sorcerer_setup", {}) or {})
    assert setup.get("bloodline") == "elemental"
    assert setup.get("elemental_type") == "water"
    assert setup.get("elemental_damage_type") == "bludgeoning"
    assert hero.has_status("familiar")
    assert hero.has_status("FamiliarOwner")


def test_elemental_type_prompt_uses_mechanical_choice_description(monkeypatch):
    class CapturingUI(DummyUI):
        def __init__(self, answers: list[str]):
            super().__init__(answers)
            self.elemental_choice_meta = None

        def prompt_choice(self, prompt: str, choices=None, **kwargs):
            if "elemental type" in str(prompt).lower():
                self.elemental_choice_meta = kwargs.get("choice_meta")
            return super().prompt_choice(prompt, choices=choices, **kwargs)

    ui = CapturingUI(["Elemental", "Water", "Familiar"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(SORCERER_STATUS)

    meta = ui.elemental_choice_meta
    assert isinstance(meta, list) and meta
    sample_desc = str(meta[0].get("desc", ""))
    assert "damage type efektow bloodline" in sample_desc.lower()
    assert "Brak dodatkowego opisu mechaniki." not in sample_desc


def test_counterspell_feat_adds_reaction(monkeypatch):
    ui = DummyUI(["Imperial", "Counterspell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.reactions = []
    hero.add_status(SORCERER_STATUS)

    assert hero.has_status("counterspell")
    reaction_ids = [getattr(item, "id", None) for item in getattr(hero, "reactions", [])]
    assert "counterspell_reaction" in reaction_ids


def test_sorcerer_setup_persists_slot_economy_and_repertoire_fields(monkeypatch):
    ui = DummyUI(["Imperial", "Dangerous Sorcery"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(SORCERER_STATUS)

    setup = dict(hero.get_status_data("sorcerer", "sorcerer_setup", {}) or {})
    assert setup.get("spell_tradition") == "arcane"
    assert int(setup.get("rank_1_slots_per_day", 0) or 0) == 3
    assert isinstance(setup.get("known_cantrips"), list) and len(list(setup.get("known_cantrips") or [])) >= 5
    assert isinstance(setup.get("known_rank_1_spells"), list) and len(list(setup.get("known_rank_1_spells") or [])) >= 3

    assert int(getattr(hero, "sorcerer_rank_1_slots_per_day", 0) or 0) == 3
    assert "detect_magic" in list(getattr(hero, "sorcerer_known_cantrips", []) or [])
    assert "magic_missile" in list(getattr(hero, "sorcerer_known_rank_1_spells", []) or [])


def test_sorcerer_level1_rank1_repertoire_has_two_picks_plus_bloodline_spell(monkeypatch):
    ui = DummyUI(["Imperial", "Dangerous Sorcery"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(SORCERER_STATUS)

    rank1_spells = list(getattr(hero, "sorcerer_known_rank_1_spells", []) or [])
    assert "magic_missile" in rank1_spells
    assert len(rank1_spells) >= 3
