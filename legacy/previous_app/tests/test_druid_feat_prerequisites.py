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
from statuses.classes.druid.feats.storm_born import STORM_BORN_STATUS
from statuses.classes.druid.feats.wild_shape import WILD_SHAPE_STATUS
from statuses.classes.druid.feats.widen_spell import WIDEN_SPELL_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def _druid_with_order(order: str) -> Status:
    normalized = str(order).strip().lower()
    return Status(
        id="druid",
        data={
            "druid_setup": {
                "order": normalized,
            }
        },
    )


def test_storm_born_requires_druid_class():
    hero = DummyHero()
    added = hero.add_status(STORM_BORN_STATUS)

    assert added is False
    assert any("wymaga klasy druid" in msg.lower() for msg in hero.messages)


def test_storm_born_requires_storm_order():
    hero = DummyHero()
    hero.add_status(_druid_with_order("leaf"))

    added = hero.add_status(STORM_BORN_STATUS)
    assert added is False
    assert any("wymaga druid order 'storm'" in msg.lower() for msg in hero.messages)


def test_wild_shape_passes_for_wild_order():
    hero = DummyHero()
    hero.add_status(_druid_with_order("wild"))

    added = hero.add_status(WILD_SHAPE_STATUS)
    assert added is True
    assert hero.has_status("wild_shape")


def test_widen_spell_requires_druid_but_not_specific_order():
    hero = DummyHero()
    hero.add_status(_druid_with_order("animal"))

    added = hero.add_status(WIDEN_SPELL_STATUS)
    assert added is True
    assert hero.has_status("widen_spell")
