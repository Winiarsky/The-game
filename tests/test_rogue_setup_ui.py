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
from statuses.classes.rogue.rogue import ROGUE_STATUS


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


def test_rogue_setup_saves_racket_key_ability_and_feat(monkeypatch):
    ui = DummyUI(["Ruffian", "Strength", "Twin Feint"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    added = hero.add_status(ROGUE_STATUS)

    assert added is True
    assert hero.has_status("rogue")
    assert hero.get_status_data("rogue", "rogue_racket", None) == "ruffian"
    assert hero.get_status_data("rogue", "rogue_key_ability", None) == "strength"
    assert hero.get_status_data("rogue", "rogue_class_feat", None) == "twin_feint"
    assert hero.has_status("sneak_attack")
    assert hero.has_status("surprise_attack")
    assert hero.has_status("twin_feint")
    assert getattr(hero, "rogue_racket", None) == "ruffian"


def test_rogue_setup_nimble_dodge_adds_reaction(monkeypatch):
    ui = DummyUI(["Scoundrel", "Charisma", "Nimble Dodge"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(ROGUE_STATUS)

    reaction_ids = [getattr(item, "id", None) for item in getattr(hero, "reactions", [])]
    assert "nimble_dodge" in reaction_ids
