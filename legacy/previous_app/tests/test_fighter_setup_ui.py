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
from statuses.classes.fighter.fighter import FIGHTER_STATUS


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


def test_fighter_setup_saves_key_ability_and_grants_core_statuses(monkeypatch):
    ui = DummyUI(["Dexterity"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    added = hero.add_status(FIGHTER_STATUS)

    assert added is True
    assert hero.has_status("fighter")
    assert hero.get_status_data("fighter", "fighter_key_ability", None) == "dexterity"
    assert getattr(hero, "fighter_key_ability", None) == "dexterity"
    assert hero.has_status("opportunity_attack")
    assert hero.has_status("shield_block")
