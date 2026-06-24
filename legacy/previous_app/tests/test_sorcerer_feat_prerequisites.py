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
from statuses.classes.sorcerer.feats.counterspell import COUNTERSPELL_STATUS
from statuses.classes.sorcerer.feats.dangerous_sorcery import DANGEROUS_SORCERY_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_sorcerer_feats_require_sorcerer_class():
    hero = DummyHero()

    added = hero.add_status(COUNTERSPELL_STATUS)
    assert added is False
    assert any("wymaga klasy sorcerer" in msg.lower() for msg in hero.messages)


def test_sorcerer_feat_passes_for_sorcerer_status():
    hero = DummyHero()
    hero.add_status(Status(id="sorcerer", data={"sorcerer_setup": {"bloodline": "imperial"}}))

    added = hero.add_status(DANGEROUS_SORCERY_STATUS)
    assert added is True
    assert hero.has_status("dangerous_sorcery")
