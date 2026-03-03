from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses import Status
import statuses.death_dying as dd


@dataclass
class DummyActor(StatusMixin):
    name: str = "Hero"
    max_hp: int = 20
    wounds: int = 0



def test_on_reduced_to_zero_sets_dying_and_unconscious():
    actor = DummyActor(max_hp=20, wounds=20)

    result = dd.on_reduced_to_zero(actor, source="test")

    assert result["dead"] is False
    assert dd.dying_value(actor) == 1
    assert actor.has_status("unconscious")



def test_on_heal_clears_dying_and_removes_unconscious_when_hp_positive():
    actor = DummyActor(max_hp=20, wounds=19)
    actor.add_status(Status(id="dying_2", label="Dying 2"))
    actor.add_status(Status(id="unconscious", label="Unconscious"))

    result = dd.on_heal(actor, source="heal")

    assert result["changed"] is True
    assert dd.dying_value(actor) == 0
    assert dd.wounded_value(actor) == 1
    assert not actor.has_status("unconscious")



def test_recovery_check_nat20_stabilizes(monkeypatch):
    actor = DummyActor(max_hp=20, wounds=20)
    actor.add_status(Status(id="dying_2", label="Dying 2", data={"value": 2}))
    actor.add_status(Status(id="unconscious", label="Unconscious"))

    monkeypatch.setattr(dd, "prompt_for_roll", lambda *_a, **_k: 20)

    result = dd.run_recovery_check(actor, source="test")

    assert result["processed"] is True
    assert dd.dying_value(actor) == 0
    assert actor.has_status("stable")
    assert actor.has_status("unconscious")
    assert dd.wounded_value(actor) == 1



def test_recovery_check_critical_failure_can_kill(monkeypatch):
    actor = DummyActor(max_hp=20, wounds=20)
    actor.add_status(Status(id="dying_3", label="Dying 3", data={"value": 3}))
    actor.add_status(Status(id="unconscious", label="Unconscious"))

    monkeypatch.setattr(dd, "prompt_for_roll", lambda *_a, **_k: 1)

    result = dd.run_recovery_check(actor, source="test")

    assert result["processed"] is True
    assert actor.has_status("dead")
