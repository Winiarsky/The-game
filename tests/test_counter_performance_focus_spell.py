from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext
from GameObjects.events.magic.focus_spells.bard.counter_performance_event import CounterPerformanceEvent
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.classes.bard.bard import BARD_STATUS
from statuses.counter_performance import CounterPerformanceStatus
from skills import Skill


class DummyHero(StatusMixin):
    pass


def _hero(name: str, position: tuple[int, int]):
    actor = DummyHero()
    actor.name = name
    actor.object_id = name
    actor.position = position
    actor.bonuses = []
    return actor


def _game(heroes):
    logs: list[str] = []
    return SimpleNamespace(
        heroes=list(heroes),
        enemies=[],
        ui=SimpleNamespace(prompt_info=lambda *_a, **_k: None),
        ui_log=lambda msg: logs.append(str(msg)),
        _logs=logs,
    )


def test_counter_performance_requires_bard():
    caster = _hero("caster", (0, 0))
    ally = _hero("ally", (1, 0))
    game = _game([caster, ally])

    result = CounterPerformanceEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is False
    assert "tylko bard" in (result.message or "").lower()


def test_counter_performance_is_focus_cantrip_and_does_not_spend_focus(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_a, **_k: 15)

    caster = _hero("bard", (0, 0))
    caster.add_status(BARD_STATUS)
    near = _hero("near", (5, 0))   # 25 ft
    far = _hero("far", (20, 0))    # 100 ft
    game = _game([caster, near, far])

    event = CounterPerformanceEvent()
    result = event.execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert getattr(caster, "focus_point", None) == 1
    assert not caster.has_status("counter_performance")
    assert near.has_status("counter_performance")
    assert not far.has_status("counter_performance")
    status = near.get_status("counter_performance")
    assert status is not None
    assert (status.data or {}).get("performance_total") == 15
    assert (status.data or {}).get("source_turns_left") == 1


def test_counter_performance_works_even_with_zero_focus_points(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_a, **_k: 12)

    caster = _hero("bard", (0, 0))
    caster.add_status(BARD_STATUS)
    caster.focus_point = 0
    near = _hero("near", (1, 0))
    game = _game([caster, near])

    result = CounterPerformanceEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert near.has_status("counter_performance")


def test_counter_performance_replaces_lower_save_result(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_a, **_k: 5)
    ally = _hero("ally", (1, 0))
    ally.add_status(
        CounterPerformanceStatus(
            performance_total=18,
            source_id="bard",
            source_turns_left=1,
            source="counter_performance",
        )
    )

    result = resolve_skill_check_with_sources(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=ally,
        target=None,
        tags=["save", Skill.WILL.value],
        apply_modifiers=True,
    )

    assert result.total == 18
    assert result.outcome == "success"
    assert any("Counter Performance" in note for note in result.notes)


def test_counter_performance_does_not_replace_higher_save_result(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_a, **_k: 19)
    ally = _hero("ally", (1, 0))
    ally.add_status(
        CounterPerformanceStatus(
            performance_total=18,
            source_id="bard",
            source_turns_left=1,
            source="counter_performance",
        )
    )

    result = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=15,
        actor=ally,
        target=None,
        tags=["save", Skill.FORTITUDE.value],
        apply_modifiers=True,
    )

    assert result.total == 19
    assert result.outcome == "success"
    assert not any("Counter Performance" in note for note in result.notes)
