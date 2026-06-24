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
from statuses.classes.cleric.cleric import CLERIC_STATUS


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


def test_warpriest_gets_shield_block_and_deadly_simplicity(monkeypatch):
    ui = DummyUI(["Irori", "Warpriest", "Heal"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(CLERIC_STATUS)

    assert hero.has_status("cleric")
    assert hero.get_status_data("cleric", "cleric_doctrine", None) == "warpriest"
    assert hero.get_status_data("cleric", "cleric_font", None) == "heal"
    assert hero.has_status("shield_block")
    assert hero.has_status("deadly_simplicity")


def test_cloistered_gets_domain_initiate_and_focus_point(monkeypatch):
    ui = DummyUI(["Iomedae", "Cloistered Cleric", "Truth"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(CLERIC_STATUS)

    assert hero.has_status("cleric")
    assert hero.get_status_data("cleric", "cleric_doctrine", None) == "cloistered_cleric"
    assert hero.has_status("domain_initiate")
    assert getattr(hero, "focus_point", None) == 1
    assert "truth" in list(getattr(hero, "cleric_known_domains", []) or [])
    assert "word_of_truth" in list(getattr(hero, "cleric_domain_spells", []) or [])


def test_cleric_iomedae_records_divine_skill_and_trained_skills(monkeypatch):
    ui = DummyUI(["Iomedae", "Warpriest", "Heal"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(CLERIC_STATUS)

    setup = dict(hero.get_status_data("cleric", "cleric_setup", {}) or {})
    trained_skills = [str(item or "").strip().lower() for item in list(setup.get("trained_skills") or [])]
    assert setup.get("deity_skill") == "intimidation"
    assert "religion" in trained_skills
    assert "intimidation" in trained_skills


def test_cleric_shelyn_prompts_for_divine_skill_choice(monkeypatch):
    ui = DummyUI(["Shelyn", "Warpriest", "Crafting", "Heal"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(CLERIC_STATUS)

    setup = dict(hero.get_status_data("cleric", "cleric_setup", {}) or {})
    assert setup.get("deity_skill") == "crafting"


def test_cleric_setup_persists_spell_tradition_and_prepare_budgets(monkeypatch):
    ui = DummyUI(["Iomedae", "Cloistered Cleric", "Truth"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(CLERIC_STATUS)

    setup = dict(hero.get_status_data("cleric", "cleric_setup", {}) or {})
    assert setup.get("spell_tradition") == "divine"
    assert int(setup.get("prepared_cantrips_at_level1", 0) or 0) == 5
    assert int(setup.get("prepared_rank_1_slots_at_level1", 0) or 0) == 2

    assert hero.get_status_data("cleric", "cleric_spell_tradition", None) == "divine"
    assert int(hero.get_status_data("cleric", "cleric_prepared_cantrips_at_level1", 0) or 0) == 5
    assert int(hero.get_status_data("cleric", "cleric_prepared_rank_1_slots_at_level1", 0) or 0) == 2
