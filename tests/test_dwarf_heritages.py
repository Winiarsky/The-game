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
from statuses.race.dwarf import (  # noqa: E402
    ANCIENT_BLOODED_DWARF_STATUS,
    DEATH_WARDEN_DWARF_STATUS,
    FORGE_DWARF_STATUS,
    ROCK_DWARF_STATUS,
    STRONG_BLOODED_DWARF_STATUS,
)


class DummyActor:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []


def test_ancient_blooded_adds_prompt_note(monkeypatch):
    """Magic saving throw powinien zawierać informację o reakcji +1."""
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 5)
    actor = DummyActor()
    target = DummyActor(statuses=[ANCIENT_BLOODED_DWARF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.REFLEX.value,
        dc=20,
        actor=actor,
        target=target,
        tags=["saving_throw", "magic"],
        apply_modifiers=True,
    )
    notes_text = " ".join(res.notes)
    assert "Możesz wydać reakcję" in notes_text


def test_death_warden_promotes_success_to_crit(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 15)
    actor = DummyActor()
    target = DummyActor(statuses=[DEATH_WARDEN_DWARF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=15,
        actor=actor,
        target=target,
        tags=["saving_throw", "necromancy"],
        apply_modifiers=True,
    )
    assert res.outcome == "critical_success"


def test_rock_dwarf_grants_circumstance_bonus(monkeypatch):
    # gracz podaje wynik końcowy (uwzględnia +2 w rzucie): wpisze 12 vs DC 12
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 12)
    actor = DummyActor()
    target = DummyActor(statuses=[ROCK_DWARF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=12,
        actor=actor,
        target=target,
        tags=["trip"],
        apply_modifiers=False,  # gracz sam dolicza premię; modyfikator ma trafić do promptu
    )
    assert res.modifier == 2  # pokazuje się w prompt/breakdown
    assert res.outcome == "success"


def test_strong_blooded_promotes_poison_save_and_reduces_poison_damage(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 12)
    actor = DummyActor()
    target = DummyActor(statuses=[STRONG_BLOODED_DWARF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.WILL.value,
        dc=12,
        actor=actor,
        target=target,
        tags=["saving_throw", "poison"],
        apply_modifiers=True,
    )
    assert res.outcome == "critical_success"  # success -> critical success

    effective, reduced = apply_damage_resistance(target, 5, DamageType.POISON.value)
    assert reduced == 1
    assert effective == 4


def test_forge_dwarf_reduces_fire_damage():
    target = DummyActor(statuses=[FORGE_DWARF_STATUS])
    effective, reduced = apply_damage_resistance(target, 3, DamageType.FIRE.value)
    assert reduced == 1
    assert effective == 2
