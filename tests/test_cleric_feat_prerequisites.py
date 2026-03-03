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
from statuses.classes.cleric.feats.harming_hands import HARMING_HANDS_STATUS
from statuses.classes.cleric.feats.healing_hands import HEALING_HANDS_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_harming_hands_requires_cleric_and_harm_font():
    hero = DummyHero()

    added = hero.add_status(HARMING_HANDS_STATUS)
    assert added is False
    assert any("wymaga klasy cleric" in msg.lower() for msg in hero.messages)

    hero.add_status(
        Status(
            id="cleric",
            data={
                "cleric_setup": {
                    "font": "heal",
                    "favored_weapon_group": "simple",
                }
            },
        )
    )
    added = hero.add_status(HARMING_HANDS_STATUS)
    assert added is False
    assert any("wymaga divine font 'harm'" in msg.lower() for msg in hero.messages)


def test_healing_hands_passes_for_heal_font():
    hero = DummyHero()
    hero.add_status(
        Status(
            id="cleric",
            data={
                "cleric_setup": {
                    "font": "heal",
                    "favored_weapon_group": "simple",
                }
            },
        )
    )

    added = hero.add_status(HEALING_HANDS_STATUS)
    assert added is True
    assert hero.has_status("healing_hands")
