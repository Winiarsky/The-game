import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from skills import Skill  # noqa: E402
from damage_types import DamageType  # noqa: E402
from combat.damage_utils import apply_damage_resistance  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources,
)
from statuses.race.goblin import (  # noqa: E402
    CHARHIDE_GOBLIN_STATUS,
    IRONGUT_GOBLIN_STATUS,
    RAZORTOOTH_GOBLIN_STATUS,
    SNOW_GOBLIN_STATUS,
    UNBREAKABLE_GOBLIN_STATUS,
)


class DummyActor:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []


def test_charhide_reduces_fire_damage():
    target = DummyActor(statuses=[CHARHIDE_GOBLIN_STATUS])
    effective, reduced = apply_damage_resistance(target, 4, DamageType.FIRE.value)
    assert reduced == 1
    assert effective == 3


def test_snow_goblin_reduces_cold_damage():
    target = DummyActor(statuses=[SNOW_GOBLIN_STATUS])
    effective, reduced = apply_damage_resistance(target, 2, DamageType.COLD.value)
    assert reduced == 1
    assert effective == 1


def test_irongut_bonus_and_promote(monkeypatch):
    """Rzut Fortitude przeciw fire dostaje +2 i podbicie sukcesu."""
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 13)
    actor = DummyActor()
    target = DummyActor(statuses=[IRONGUT_GOBLIN_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=15,
        actor=actor,
        target=target,
        tags=["saving_throw", "fire"],
        apply_modifiers=True,
    )
    assert res.modifier == 2  # +2 circumstance vs fire
    assert res.outcome == "critical_success"  # success (15) -> promoted to crit


def test_razortooth_has_prompt_note():
    notes = RAZORTOOTH_GOBLIN_STATUS.data.get("prompt_notes", [])
    assert any("Ostre Zęby" in note for note in notes)


def test_unbreakable_hp_note():
    notes = UNBREAKABLE_GOBLIN_STATUS.data.get("prompt_notes", [])
    text = " ".join(notes)
    assert "10" in text and "8" in text
