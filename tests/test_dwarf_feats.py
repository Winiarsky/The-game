import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Enemies.enemy_types import EnemyType  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources,
)
from skills import Skill  # noqa: E402
from statuses.race.dwarf import (  # noqa: E402
    DWARVEN_LORE_STATUS,
    DWARVEN_WEAPON_FAMILIARITY_STATUS,
    ROCK_RUNNER_STATUS,
    STONE_CUNNING_STATUS,
    UNBURDENED_IRON_STATUS,
    VENGEFUL_HATRED_STATUS,
    VengefulHatredStatus,
)


class DummyActor:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []


def test_dwarven_lore_contains_training_prompt():
    notes = DWARVEN_LORE_STATUS.data.get("prompt_notes")
    assert isinstance(notes, list)
    assert any("trained" in n.lower() for n in notes)


def test_dwarven_weapon_familiarity_prompt_exists():
    notes = DWARVEN_WEAPON_FAMILIARITY_STATUS.data.get("prompt_notes")
    assert notes and "uncommon dwarf weapons" in notes[0]


def test_rock_runner_promotes_success_to_critical(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 15)
    actor = DummyActor(statuses=[ROCK_RUNNER_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.ACROBATICS.value,
        dc=15,
        actor=actor,
        target=None,
        tags=["stone"],
        apply_modifiers=True,
    )
    assert res.outcome == "critical_success"
    assert any("Rock Runner" in note for note in res.notes)


def test_stone_cunning_adds_circumstance_bonus(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    actor = DummyActor(statuses=[STONE_CUNNING_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.PERCEPTION.value,
        dc=12,
        actor=actor,
        target=None,
        tags=["rock"],
        apply_modifiers=True,
    )
    assert res.modifier == 2  # +2 circumstance
    assert res.outcome == "success"


def test_unburdened_iron_mitigates_speed_reduction_in_data():
    data = UNBURDENED_IRON_STATUS.data
    assert data.get("speed_reduction_mitigate") == 1
    assert any("prędkości" in note or "prędkość" in note for note in data.get("prompt_notes", []))


def test_vengeful_hatred_stores_target_and_bonus_in_data():
    status = VengefulHatredStatus(EnemyType.ORC)
    assert status.data.get("vengeful_hatred_target") == EnemyType.ORC.value
    assert status.data.get("damage_bonus_vs_target") == 1
    assert "orc" in (status.label or "").lower()


def test_default_vengeful_hatred_label_mentions_human():
    assert "human" in (VENGEFUL_HATRED_STATUS.label or "").lower()
