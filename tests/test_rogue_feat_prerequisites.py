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
from statuses.classes.rogue.feats.nimble_dodge import NIMBLE_DODGE_STATUS
from statuses.classes.rogue.feats.youre_next import YOURE_NEXT_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_rogue_feats_require_rogue_class():
    hero = DummyHero()

    added = hero.add_status(NIMBLE_DODGE_STATUS)
    assert added is False
    assert any("wymaga klasy rogue" in msg.lower() for msg in hero.messages)


def test_youre_next_requires_trained_intimidation():
    hero = DummyHero()
    hero.add_status(Status(id="rogue", data={"rogue_setup": {"trained_skills": ["thievery"]}}))

    added = hero.add_status(YOURE_NEXT_STATUS)
    assert added is False
    assert any("wymaga trained" in msg.lower() for msg in hero.messages)


def test_youre_next_passes_for_rogue_with_intimidation_training():
    hero = DummyHero()
    hero.add_status(Status(id="rogue", data={"rogue_setup": {"trained_skills": ["intimidation"]}}))

    added = hero.add_status(YOURE_NEXT_STATUS)
    assert added is True
    assert hero.has_status("youre_next")

