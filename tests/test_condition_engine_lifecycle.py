from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses import (
    Status,
    FrightenedStatus,
    SickenedStatus,
    DoomedStatus,
    DrainedStatus,
    ImmobilizedStatus,
    frightened_value,
    sickened_value,
    drained_value,
    doomed_value,
    normalize_condition_stacks,
    tick_condition_durations,
    decrement_end_of_turn_conditions,
    apply_daily_preparation_conditions,
    action_block_reason,
    skill_penalty_breakdown_label,
)


@dataclass
class DummyActor(StatusMixin):
    name: str = "Hero"
    statuses: list = field(default_factory=list)


def test_normalize_condition_stacks_keeps_strongest_scaled_status():
    actor = DummyActor()
    actor.add_status(FrightenedStatus(value=1, source="fear_a"))
    actor.add_status(FrightenedStatus(value=3, source="fear_b"))

    normalize_condition_stacks(actor)

    assert frightened_value(actor) == 3
    assert len([s for s in actor.statuses if getattr(s, "id", None) == "frightened"]) == 1


def test_tick_condition_durations_respects_phase_metadata():
    actor = DummyActor()
    actor.add_status(Status(id="test_start", label="Start", duration=2))
    actor.add_status(
        Status(
            id="test_end",
            label="End",
            duration=2,
            data={"duration_tick_phase": "turn_end"},
        )
    )

    tick_condition_durations(actor, phase="turn_start")
    start = actor.get_status("test_start")
    end = actor.get_status("test_end")
    assert start is not None and int(start.duration or 0) == 1
    assert end is not None and int(end.duration or 0) == 2

    tick_condition_durations(actor, phase="turn_end")
    end = actor.get_status("test_end")
    assert end is not None and int(end.duration or 0) == 1


def test_decrement_end_of_turn_conditions_reduces_frightened_but_not_sickened():
    actor = DummyActor()
    actor.add_status(FrightenedStatus(value=2))
    actor.add_status(SickenedStatus(value=2))

    decrement_end_of_turn_conditions(actor)

    assert frightened_value(actor) == 1
    assert sickened_value(actor) == 2


def test_apply_daily_preparation_conditions_reduces_doomed_and_drained():
    actor = DummyActor()
    actor.add_status(DoomedStatus(value=2, source="curse"))
    actor.add_status(DrainedStatus(value=3, source="drain"))
    actor.add_status(Status(id="fast_recovery", label="Fast Recovery", data={"drained_recovery_bonus": 1}))

    changed = apply_daily_preparation_conditions(actor)

    assert changed >= 2
    assert doomed_value(actor) == 1
    assert drained_value(actor) == 1


def test_normalize_condition_stacks_resolves_dying_conflict_with_stable():
    actor = DummyActor()
    actor.add_status(Status(id="stable", label="Stable"))
    actor.add_status(Status(id="dying_1", label="Dying 1", data={"value": 1}))

    normalize_condition_stacks(actor)

    assert actor.get_status("stable") is None
    assert actor.get_status("unconscious") is not None


def test_action_block_reason_immobilized_blocks_move_only():
    actor = DummyActor()
    actor.add_status(ImmobilizedStatus())

    move_block = action_block_reason(actor, action_tags=["move"], action_name="move")
    attack_block = action_block_reason(actor, action_tags=["attack"], action_name="attack")
    assert move_block is not None
    assert attack_block is None


def test_skill_penalty_breakdown_label_lists_condition_sources():
    actor = DummyActor()
    actor.add_status(FrightenedStatus(value=1))
    actor.add_status(SickenedStatus(value=2))

    label = skill_penalty_breakdown_label(actor, skill_id="diplomacy", tags=["diplomacy"])

    assert "frightened" in label
    assert "sickened" in label
