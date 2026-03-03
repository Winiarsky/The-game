from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from statuses.classes.fighter.feats.snagging_strike import (
    apply_snagging_flat_footed,
    cleanup_snagging_flat_footed,
)


@dataclass(eq=False)
class _Actor:
    object_id: str
    position: tuple[int, int] | None
    statuses: list[object] = field(default_factory=list)

    def add_status(self, status) -> None:
        self.statuses.append(status)

    def has_status(self, status_id: str) -> bool:
        for status in self.statuses:
            if getattr(status, "id", status) == status_id:
                return True
        return False


def _snagging_flat_footed_count(actor: _Actor) -> int:
    count = 0
    for status in actor.statuses:
        if getattr(status, "id", status) != "flat_footed":
            continue
        data = getattr(status, "data", None) or {}
        if data.get("flat_footed_source") == "snagging_strike":
            count += 1
    return count


def test_apply_snagging_flat_footed_sets_source_metadata():
    fighter = _Actor(object_id="fighter-1", position=(0, 0))
    target = _Actor(object_id="enemy-1", position=(1, 0))

    ok = apply_snagging_flat_footed(target, source_actor=fighter, source_turns_left=1, reach=1)

    assert ok is True
    assert _snagging_flat_footed_count(target) == 1
    status = [s for s in target.statuses if getattr(s, "id", s) == "flat_footed"][0]
    data = getattr(status, "data", None) or {}
    assert data.get("flat_footed_source") == "snagging_strike"
    assert data.get("source_id") == "fighter-1"
    assert int(data.get("reach", 0) or 0) == 1


def test_cleanup_snagging_flat_footed_removes_when_target_leaves_reach():
    fighter = _Actor(object_id="fighter-1", position=(0, 0))
    target = _Actor(object_id="enemy-1", position=(1, 0))
    apply_snagging_flat_footed(target, source_actor=fighter, source_turns_left=1, reach=1)
    game = SimpleNamespace(heroes=[fighter], enemies=[target])

    removed = cleanup_snagging_flat_footed(game)
    assert removed == 0
    assert _snagging_flat_footed_count(target) == 1

    target.position = (2, 0)
    removed = cleanup_snagging_flat_footed(game)
    assert removed == 1
    assert _snagging_flat_footed_count(target) == 0
