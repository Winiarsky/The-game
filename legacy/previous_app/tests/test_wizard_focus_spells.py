from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401

from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event, list_events
from GameObjects.events.magic.focus_spells.wizard import wizard_school_spell_events as wizard_events
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status


@dataclass
class DummyActor(StatusMixin):
    name: str = "actor"
    object_id: str = "actor"
    position: tuple[int, int] | None = (0, 0)
    hp: int = 20
    statuses: list = field(default_factory=list)
    bonuses: list = field(default_factory=list)
    focus_point: int = 0

    def __hash__(self):
        return id(self)

    def add_bonus(self, effect):
        self.bonuses.append(effect)

    def apply_damage(self, amount: int, _damage_type: str = ""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


class DummyConn:
    def __init__(self, choice_pos: tuple[int, int] | None = None):
        self.choice_pos = choice_pos

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        if self.choice_pos in positions:
            return self.choice_pos
        return positions[0] if positions else None

    def leds_off(self):
        return None


def _wizard(*, known_spells: list[str], focus: int = 1, arcane_study: str = "evocation") -> DummyActor:
    actor = DummyActor(name="wizard", object_id="wizard", position=(0, 0), hp=20)
    actor.class_name = "wizard"
    actor.focus_point = int(focus)
    actor.wizard_focus_spells = list(known_spells)
    actor.statuses = [
        Status(
            id="wizard",
            data={
                "wizard_setup": {
                    "arcane_study": arcane_study,
                    "school_focus_spell": known_spells[0] if known_spells else "",
                }
            },
        )
    ]
    return actor


def _game(*, actor, enemies=None, heroes=None, board=None):
    return SimpleNamespace(
        state=object(),
        heroes=list(heroes or [actor]),
        enemies=list(enemies or []),
        conn=DummyConn(),
        ui=SimpleNamespace(enabled=False, allow_cli_fallback=False, prompt_choice=lambda *_a, **_k: None),
        board=board if board is not None else SimpleNamespace(rows=8, cols=8),
        ui_log=lambda *_a, **_k: None,
    )


def test_wizard_focus_spells_are_registered():
    events = list_events()
    for spell_name in (
        "augment_summoning",
        "call_of_the_grave",
        "charming_words",
        "diviners_sight",
        "force_bolt",
        "hand_of_the_apprentice",
        "physical_boost",
        "protective_ward",
        "warped_terrain",
    ):
        assert spell_name in events


def test_force_bolt_spends_focus_and_deals_damage(monkeypatch):
    actor = _wizard(known_spells=["force_bolt"], focus=1)
    target = DummyActor(name="enemy", object_id="enemy", position=(1, 0), hp=20)
    game = _game(actor=actor, enemies=[target])

    monkeypatch.setattr(wizard_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(wizard_events, "prompt_for_roll", lambda *_a, **_k: 7)

    result = dispatch_event("force_bolt", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 13


def test_call_of_the_grave_critical_success_applies_sickened_and_slowed(monkeypatch):
    actor = _wizard(known_spells=["call_of_the_grave"], focus=1)
    target = DummyActor(name="enemy", object_id="enemy", position=(1, 0), hp=20)
    target.ac = 10
    game = _game(actor=actor, enemies=[target])

    monkeypatch.setattr(wizard_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(wizard_events, "prompt_for_roll", lambda *_a, **_k: 20)

    result = dispatch_event("call_of_the_grave", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    sickened = [status for status in target.statuses if getattr(status, "id", None) == "sickened"]
    slowed = [status for status in target.statuses if getattr(status, "id", None) == "slowed"]
    assert len(sickened) == 1
    assert (sickened[0].data or {}).get("sickened_value") == 2
    assert len(slowed) == 1


def test_charming_words_critical_failure_adds_stunned_and_pacified(monkeypatch):
    actor = _wizard(known_spells=["charming_words"], focus=1)
    target = DummyActor(name="enemy", object_id="enemy", position=(1, 0), hp=20)
    game = _game(actor=actor, enemies=[target])

    monkeypatch.setattr(wizard_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(wizard_events, "_prompt_choice", lambda *_a, **_k: "critical_failure")

    result = dispatch_event("charming_words", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.has_status("stunned")
    assert target.has_status("charming_words_pacified")


def test_protective_ward_adds_status_and_ac_bonus_to_self_and_nearby_allies():
    actor = _wizard(known_spells=["protective_ward"], focus=1)
    ally = DummyActor(name="ally", object_id="ally", position=(1, 0), hp=20)
    game = _game(actor=actor, heroes=[actor, ally])

    result = dispatch_event("protective_ward", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert actor.has_status("protective_ward_active")
    assert any(getattr(effect, "tag", "") == "ac" and getattr(effect, "source", "") == "protective_ward" for effect in actor.bonuses)
    assert any(getattr(effect, "tag", "") == "ac" and getattr(effect, "source", "") == "protective_ward" for effect in ally.bonuses)


def test_warped_terrain_uses_chosen_actions_and_heightened_airborne(monkeypatch):
    actor = _wizard(known_spells=["warped_terrain"], focus=1)
    actor.level = 7  # focus rank 4 -> heightened clause available
    game = _game(actor=actor)

    picks = iter(["3", "yes"])
    monkeypatch.setattr(wizard_events, "_prompt_choice", lambda *_a, **_k: next(picks))
    monkeypatch.setattr(wizard_events, "pick_position_in_range", lambda *_a, **_k: (2, 2))

    result = dispatch_event("warped_terrain", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    active = [status for status in actor.statuses if getattr(status, "id", None) == "warped_terrain_active"]
    assert len(active) == 1
    data = dict(active[0].data or {})
    assert data.get("center_position") == (2, 2)
    assert data.get("radius_feet") == 15
    assert data.get("airborne") is True


def test_hand_of_the_apprentice_hits_and_deals_damage(monkeypatch):
    actor = _wizard(known_spells=["hand_of_the_apprentice"], focus=1, arcane_study="universalist")
    target = DummyActor(name="enemy", object_id="enemy", position=(3, 0), hp=20)
    target.ac = 10
    game = _game(actor=actor, enemies=[target])

    monkeypatch.setattr(wizard_events, "_pick_target", lambda *_a, **_k: target)
    rolls = iter([15, 6])  # attack, damage
    monkeypatch.setattr(wizard_events, "prompt_for_roll", lambda *_a, **_k: next(rolls))

    result = dispatch_event("hand_of_the_apprentice", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 14


def test_wizard_cannot_cast_unknown_focus_spell():
    actor = _wizard(known_spells=["force_bolt"], focus=1)
    game = _game(actor=actor)

    result = dispatch_event("call_of_the_grave", EventContext(game=game, actor=actor))

    assert result.success is False
    assert "not known" in str(result.message or "").lower()
