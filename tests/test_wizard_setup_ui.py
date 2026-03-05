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
from statuses.classes.wizard.wizard import WIZARD_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)
    reactions: list[object] = field(default_factory=list)

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


def test_specialist_setup_saves_school_thesis_feat_and_bond(monkeypatch):
    ui = DummyUI(["Evocation", "Spell Substitution", "Eschew Materials", "Staff"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(WIZARD_STATUS)

    setup = dict(hero.get_status_data("wizard", "wizard_setup", {}) or {})
    assert setup.get("arcane_study") == "evocation"
    assert setup.get("school") == "evocation"
    assert setup.get("thesis") == "spell_substitution"
    assert setup.get("class_feat") == "eschew_materials"
    assert setup.get("bond_source") == "item"
    assert setup.get("bonded_item") == "staff"
    assert setup.get("school_bonus_spell") == "shocking_grasp"
    assert setup.get("school_focus_spell") == "force_bolt"
    assert setup.get("prepared_cantrips") == 6
    assert setup.get("prepared_rank1_slots") == 3

    assert hero.has_status("wizard")
    assert hero.has_status("eschew_materials")
    assert getattr(hero, "class_name", None) == "wizard"
    assert getattr(hero, "focus_point", None) == 1
    assert "force_bolt" in list(getattr(hero, "wizard_focus_spells", []) or [])


def test_universalist_setup_gets_bonus_feat_and_familiar_bond(monkeypatch):
    ui = DummyUI(
        [
            "Universalist",
            "Improved Familiar Attunement",
            "Counterspell",
            "Hand Of The Apprentice",
        ]
    )
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(WIZARD_STATUS)

    setup = dict(hero.get_status_data("wizard", "wizard_setup", {}) or {})
    assert setup.get("arcane_study") == "universalist"
    assert setup.get("school") is None
    assert setup.get("thesis") == "improved_familiar_attunement"
    assert setup.get("class_feat") == "counterspell"
    assert setup.get("bonus_class_feat") == "hand_of_the_apprentice"
    assert setup.get("bond_source") == "familiar"
    assert setup.get("drain_action") == "drain_familiar"

    assert hero.has_status("counterspell")
    assert hero.has_status("familiar")
    assert hero.has_status("FamiliarOwner")
    assert hero.has_status("hand_of_the_apprentice")
    assert "hand_of_the_apprentice" in list(getattr(hero, "wizard_focus_spells", []) or [])
    assert getattr(hero, "focus_point", 0) >= 1
    reaction_ids = [getattr(item, "id", None) for item in getattr(hero, "reactions", [])]
    assert "counterspell_reaction" in reaction_ids


def test_metamagical_thesis_grants_selected_metamagic_feat(monkeypatch):
    ui = DummyUI(
        [
            "Abjuration",
            "Metamagical Experimentation",
            "Widen Spell",
            "Reach Spell",
            "Wand",
        ]
    )
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(WIZARD_STATUS)

    setup = dict(hero.get_status_data("wizard", "wizard_setup", {}) or {})
    assert setup.get("thesis") == "metamagical_experimentation"
    assert setup.get("class_feat") == "widen_spell"
    assert setup.get("thesis_metamagic_feat") == "reach_spell"
    assert hero.has_status("widen_spell")
    assert hero.has_status("reach_spell")
