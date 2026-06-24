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
from statuses.classes.monk.feats.ki_strike import KI_STRIKE_STATUS
from statuses.base import Status


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_monk_feats_require_monk_class():
    hero = DummyHero()

    added = hero.add_status(KI_STRIKE_STATUS)
    assert added is False
    assert any("wymaga klasy monk" in msg.lower() for msg in hero.messages)


def test_monk_feat_passes_for_monk_class():
    hero = DummyHero()
    hero.add_status(Status(id="monk", data={"monk_setup": {"key_ability": "strength", "class_feat": "ki_strike"}}))

    added = hero.add_status(KI_STRIKE_STATUS)
    assert added is True
    assert hero.has_status("ki_strike")
