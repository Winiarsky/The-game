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
from statuses.classes.fighter.feats.power_attack import POWER_ATTACK_STATUS
from statuses.classes.fighter.feats.double_slice import DOUBLE_SLICE_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_fighter_feats_require_fighter_class():
    hero = DummyHero()

    added = hero.add_status(POWER_ATTACK_STATUS)
    assert added is False
    assert any("wymaga klasy fighter" in msg.lower() for msg in hero.messages)


def test_fighter_feat_passes_for_fighter_status():
    hero = DummyHero()
    hero.add_status(Status(id="fighter", data={"fighter_setup": {"key_ability": "strength"}}))

    added = hero.add_status(DOUBLE_SLICE_STATUS)
    assert added is True
    assert hero.has_status("double_slice")
