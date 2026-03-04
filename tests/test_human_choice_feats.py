from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.race.human.feats.adapted_cantrip import ADAPTED_CANTRIP_STATUS
from statuses.race.human.feats.general_training import GENERAL_TRAINING_STATUS
from statuses.race.human.feats.natural_ambition import NATURAL_AMBITION_STATUS
from statuses.race.human.heritages.versatile_heritage import VERSATILE_HERITAGE_STATUS


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


class DummyHero(StatusMixin):
    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_general_training_choice_grants_selected_general_feat(monkeypatch):
    ui = DummyUI(["Toughness"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(GENERAL_TRAINING_STATUS)

    assert hero.has_status("general_training")
    assert hero.get_status_data("general_training", "general_feat", None) == "toughness"
    assert hero.has_status("toughness")


def test_versatile_heritage_choice_grants_selected_general_feat(monkeypatch):
    ui = DummyUI(["Fleet"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(VERSATILE_HERITAGE_STATUS)

    assert hero.has_status("versatile_heritage")
    assert hero.get_status_data("versatile_heritage", "general_feat", None) == "fleet"
    assert hero.has_status("fleet")


def test_natural_ambition_uses_actor_class_and_grants_selected_class_feat(monkeypatch):
    ui = DummyUI(["Reach Spell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "bard"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.has_status("natural_ambition")
    assert hero.get_status_data("natural_ambition", "class_name", None) == "bard"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "reach_spell"
    assert hero.has_status("reach_spell")


def test_natural_ambition_without_supported_class_stops_cleanly(monkeypatch):
    ui = DummyUI(["Reach Spell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "wizard"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_feat", None) is None
    assert not hero.has_status("reach_spell")
    assert any("brak wspieranej klasy" in message.lower() for message in hero.messages)


def test_natural_ambition_for_cleric_grants_holy_castigation(monkeypatch):
    ui = DummyUI(["Holy Castigation"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "cleric"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "cleric"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "holy_castigation"
    assert hero.has_status("holy_castigation")


def test_natural_ambition_for_druid_grants_widen_spell(monkeypatch):
    ui = DummyUI(["Widen Spell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "druid"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "druid"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "widen_spell"
    assert hero.has_status("widen_spell")


def test_natural_ambition_for_sorcerer_grants_familiar(monkeypatch):
    ui = DummyUI(["Familiar"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "sorcerer"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "sorcerer"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "familiar"
    assert hero.has_status("familiar")
    assert hero.has_status("FamiliarOwner")


def test_adapted_cantrip_records_selected_choices(monkeypatch):
    ui = DummyUI(["Arcane", "Shield", "Detect Magic"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(ADAPTED_CANTRIP_STATUS)

    assert hero.has_status("adapted_cantrip")
    assert hero.get_status_data("adapted_cantrip", "adapted_tradition", None) == "arcane"
    assert hero.get_status_data("adapted_cantrip", "adapted_cantrip", None) == "shield"
    assert hero.get_status_data("adapted_cantrip", "replaced_cantrip", None) == "detect_magic"
