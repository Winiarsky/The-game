from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.registry import dispatch_event
from GameObjects.events.magic.focus_spells.monk import ki_spell_events
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status


@dataclass
class DummyHero(StatusMixin):
    name: str = "Hero"
    position: tuple[int, int] | None = (0, 0)

    def __post_init__(self):
        self.bonuses = []


def _game(actor):
    return SimpleNamespace(
        state=object(),
        heroes=[actor],
        enemies=[],
        conn=SimpleNamespace(set_leds=lambda *_a, **_k: None, scan_board=lambda *_a, **_k: None, leds_off=lambda: None),
        ui=None,
        board=None,
        ui_log=lambda *_a, **_k: None,
    )


def test_ki_strike_prompts_type_and_passes_metadata(monkeypatch):
    actor = DummyHero(name="Monk", position=(0, 0))
    actor.class_name = "monk"
    actor.focus_point = 1
    actor.add_status(Status(id="monk"))
    actor.add_status(Status(id="ki_strike", data={"ki_strike_damage_type_choices": ["force", "lawful", "negative", "positive"]}))

    picks = iter(["lawful", "Flurry of Blows"])
    monkeypatch.setattr(ki_spell_events, "_prompt_choice", lambda *_a, **_k: next(picks))

    captured = {}

    def _fake_dispatch(event_name: str, ctx: EventContext):
        captured["event_name"] = event_name
        captured["metadata"] = dict(ctx.metadata or {})
        return EventResult(success=True, consumed_action=True, message="ok", data={"hit": True})

    monkeypatch.setattr(ki_spell_events, "dispatch_event", _fake_dispatch)

    result = dispatch_event("ki_strike", EventContext(game=_game(actor), actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert captured.get("event_name") == "flurry_of_blows"
    metadata = captured.get("metadata") or {}
    assert metadata.get("ki_strike_attack_bonus") == 1
    assert metadata.get("ki_strike_extra_formula") == "1k6"
    assert metadata.get("ki_strike_extra_damage_type") == "lawful"


def test_ki_rush_executes_two_moves_and_adds_concealed(monkeypatch):
    actor = DummyHero(name="Monk", position=(0, 0))
    actor.class_name = "monk"
    actor.focus_point = 1
    actor.add_status(Status(id="monk"))
    actor.add_status(Status(id="ki_rush"))

    monkeypatch.setattr(ki_spell_events, "_prompt_choice", lambda *_a, **_k: "Stride + Step")

    calls = {"stride": 0, "step": 0}

    def _stride_execute(_self, _ctx):
        calls["stride"] += 1
        return EventResult(success=True, consumed_action=True, message="stride")

    def _step_execute(_self, _ctx):
        calls["step"] += 1
        return EventResult(success=True, consumed_action=True, message="step")

    monkeypatch.setattr(ki_spell_events.MoveEvent, "execute", _stride_execute)
    monkeypatch.setattr(ki_spell_events.StepEvent, "execute", _step_execute)

    result = dispatch_event("ki_rush", EventContext(game=_game(actor), actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert calls["stride"] == 1
    assert calls["step"] == 1
    assert actor.has_status("concealed")
