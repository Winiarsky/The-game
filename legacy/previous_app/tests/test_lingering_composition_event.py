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
from GameObjects.events.lingering_composition_event import LingeringCompositionEvent
from GameObjects.events.magic.focus_spells.bard.counter_performance_event import CounterPerformanceEvent
from GameObjects.events.magic.focus_spells.bard.inspire_courage_event import InspireCourageEvent
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from states.combat import Combat
from statuses.classes.bard.bard import BARD_STATUS
from statuses.classes.bard.feats.lingering_composition import LINGERING_COMPOSITION_STATUS


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

    class DummyConn:
        def set_leds(self, *_a, **_k):
            return None

        def scan_board(self, _positions):
            return None

        def leds_off(self):
            return None

    return SimpleNamespace(
        heroes=list(heroes),
        enemies=[],
        conn=DummyConn(),
        ui=SimpleNamespace(prompt_info=lambda *_a, **_k: None),
        ui_log=lambda msg: logs.append(str(msg)),
        _logs=logs,
    )


def test_lingering_composition_spends_focus_and_sets_ready_status(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_a, **_k: 15,
    )

    bard = _hero("bard", (0, 0))
    bard.add_status(BARD_STATUS)
    bard.add_status(LINGERING_COMPOSITION_STATUS)
    game = _game([bard])
    game.state = Combat(game)

    result = LingeringCompositionEvent().execute(EventContext(game=game, actor=bard))

    assert result.success is True
    assert bard.focus_point == 1
    ready = bard.get_status("lingering_composition_ready")
    assert ready is not None
    assert (ready.data or {}).get("composition_rounds") == 3


def test_lingering_composition_extends_inspire_courage_duration(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_a, **_k: 15,
    )

    bard = _hero("bard", (0, 0))
    ally = _hero("ally", (1, 0))
    bard.add_status(BARD_STATUS)
    bard.add_status(LINGERING_COMPOSITION_STATUS)
    game = _game([bard, ally])
    game.state = Combat(game)

    ready = LingeringCompositionEvent().execute(EventContext(game=game, actor=bard))
    assert ready.success is True

    cast = InspireCourageEvent().execute(EventContext(game=game, actor=bard))
    assert cast.success is True

    bard_status = bard.get_status("inspire_courage")
    ally_status = ally.get_status("inspire_courage")
    assert bard_status is not None
    assert ally_status is not None
    assert (bard_status.data or {}).get("source_turns_left") == 3
    assert (ally_status.data or {}).get("source_turns_left") == 3
    assert not bard.has_status("lingering_composition_ready")


def test_lingering_composition_extends_counter_performance_duration(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_a, **_k: 25,
    )

    bard = _hero("bard", (0, 0))
    ally = _hero("ally", (1, 0))
    bard.add_status(BARD_STATUS)
    bard.add_status(LINGERING_COMPOSITION_STATUS)
    game = _game([bard, ally])
    game.state = Combat(game)

    ready = LingeringCompositionEvent().execute(EventContext(game=game, actor=bard))
    assert ready.success is True

    cast = CounterPerformanceEvent().execute(EventContext(game=game, actor=bard))
    assert cast.success is True

    status = ally.get_status("counter_performance")
    assert status is not None
    assert (status.data or {}).get("source_turns_left") == 4
    assert (status.data or {}).get("performance_total") == 25
    assert not bard.has_status("lingering_composition_ready")


def test_lingering_composition_critical_failure_blocks_other_compositions_this_turn(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_a, **_k: {"roll": 1, "raw_roll": 1, "natural_shift": -1},
    )

    bard = _hero("bard", (0, 0))
    ally = _hero("ally", (1, 0))
    bard.add_status(BARD_STATUS)
    bard.add_status(LINGERING_COMPOSITION_STATUS)
    game = _game([bard, ally])
    game.state = Combat(game)

    failed = LingeringCompositionEvent().execute(EventContext(game=game, actor=bard))
    blocked = InspireCourageEvent().execute(EventContext(game=game, actor=bard))

    assert failed.success is True
    assert bard.has_status("composition_locked")
    assert blocked.success is False
    assert "composition spells" in str(blocked.message or "").lower()
