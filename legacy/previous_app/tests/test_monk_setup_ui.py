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
from statuses.classes.monk.monk import MONK_STATUS


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


def test_monk_setup_saves_key_ability_and_selected_feat(monkeypatch):
    ui = DummyUI(["Dexterity", "Tiger Stance"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(MONK_STATUS)

    assert hero.has_status("monk")
    assert hero.get_status_data("monk", "monk_key_ability", None) == "dexterity"
    assert hero.get_status_data("monk", "monk_class_feat", None) == "tiger_stance"
    assert getattr(hero, "monk_key_ability", None) == "dexterity"
    assert hero.has_status("tiger_stance")


def test_monk_setup_ki_feat_grants_focus_point(monkeypatch):
    ui = DummyUI(["Strength", "Ki Strike"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(MONK_STATUS)

    assert hero.has_status("ki_strike")
    assert getattr(hero, "focus_point", None) == 1
