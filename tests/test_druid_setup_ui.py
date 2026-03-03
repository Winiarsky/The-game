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
from statuses.classes.druid.druid import DRUID_STATUS


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


def test_animal_order_grants_companion_feat_and_order_spell(monkeypatch):
    ui = DummyUI(["Animal"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(DRUID_STATUS)

    assert hero.has_status("druid")
    assert hero.get_status_data("druid", "druid_order", None) == "animal"
    assert hero.get_status_data("druid", "druid_order_skill", None) == "athletics"
    assert hero.get_status_data("druid", "druid_order_spell", None) == "heal_animal"
    assert hero.has_status("animal_companion")
    assert getattr(hero, "focus_point", None) == 1
    assert "heal_animal" in list(getattr(hero, "druid_order_spells", []) or [])


def test_leaf_order_grants_leshy_familiar_and_extra_focus(monkeypatch):
    ui = DummyUI(["Leaf"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(DRUID_STATUS)

    assert hero.has_status("druid")
    assert hero.get_status_data("druid", "druid_order", None) == "leaf"
    assert hero.get_status_data("druid", "druid_order_skill", None) == "diplomacy"
    assert hero.get_status_data("druid", "druid_order_spell", None) == "goodberry"
    assert hero.has_status("leshy_familiar")
    assert hero.has_status("FamiliarOwner")
    assert getattr(hero, "focus_point", None) == 2
    assert "goodberry" in list(getattr(hero, "druid_order_spells", []) or [])


def test_storm_order_grants_storm_born_and_extra_focus(monkeypatch):
    ui = DummyUI(["Storm"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(DRUID_STATUS)

    assert hero.get_status_data("druid", "druid_order", None) == "storm"
    assert hero.get_status_data("druid", "druid_order_skill", None) == "acrobatics"
    assert hero.get_status_data("druid", "druid_order_spell", None) == "tempest_surge"
    assert hero.has_status("storm_born")
    assert getattr(hero, "focus_point", None) == 2
    assert "tempest_surge" in list(getattr(hero, "druid_order_spells", []) or [])


def test_wild_order_grants_wild_shape(monkeypatch):
    ui = DummyUI(["Wild"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(DRUID_STATUS)

    assert hero.get_status_data("druid", "druid_order", None) == "wild"
    assert hero.get_status_data("druid", "druid_order_skill", None) == "intimidation"
    assert hero.get_status_data("druid", "druid_order_spell", None) == "wild_morph"
    assert hero.has_status("wild_shape")
    assert getattr(hero, "focus_point", None) == 1
    assert "wild_morph" in list(getattr(hero, "druid_order_spells", []) or [])
