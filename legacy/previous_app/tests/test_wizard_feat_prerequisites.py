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
from statuses.base import Status
from statuses.classes.wizard.feats.counterspell import COUNTERSPELL_STATUS
from statuses.classes.wizard.feats.eschew_materials import ESCHEW_MATERIALS_STATUS
from statuses.classes.wizard.feats.hand_of_the_apprentice import HAND_OF_THE_APPRENTICE_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_wizard_feats_require_wizard_class():
    hero = DummyHero()

    added = hero.add_status(ESCHEW_MATERIALS_STATUS)
    assert added is False
    assert any("wymaga klasy wizard" in msg.lower() for msg in hero.messages)


def test_counterspell_passes_for_wizard_class():
    hero = DummyHero()
    hero.add_status(Status(id="wizard", data={"wizard_setup": {"arcane_study": "evocation"}}))

    added = hero.add_status(COUNTERSPELL_STATUS)
    assert added is True
    assert hero.has_status("counterspell")


def test_hand_of_the_apprentice_requires_universalist_study():
    hero = DummyHero()
    hero.add_status(Status(id="wizard", data={"wizard_setup": {"arcane_study": "evocation"}}))

    added = hero.add_status(HAND_OF_THE_APPRENTICE_STATUS)
    assert added is False
    assert any("wymaga wizard study 'universalist'" in msg.lower() for msg in hero.messages)


def test_hand_of_the_apprentice_passes_for_universalist():
    hero = DummyHero()
    hero.add_status(Status(id="wizard", data={"wizard_setup": {"arcane_study": "universalist"}}))

    added = hero.add_status(HAND_OF_THE_APPRENTICE_STATUS)
    assert added is True
    assert hero.has_status("hand_of_the_apprentice")
