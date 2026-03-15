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

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.magic.magic_event import MagicEvent
from GameObjects.events.registry import dispatch_event, register_event
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status


@register_event
class _WizardTestRank1Spell(MagicEvent):
    name = "wizard_test_rank1_spell"
    actions_cost = 2
    spell_tags = ["rank1", "arcane", "evocation"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="wizard test spell cast")


@register_event
class _WizardTestRank2Spell(MagicEvent):
    name = "wizard_test_rank2_spell"
    actions_cost = 2
    spell_tags = ["rank2", "arcane", "evocation"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="wizard test rank2 spell cast")


@dataclass
class DummyActor(StatusMixin):
    name: str = "wizard"
    object_id: str = "wizard"
    class_name: str = "wizard"
    focus_point: int = 0
    statuses: list = field(default_factory=list)
    bonuses: list = field(default_factory=list)

    def __hash__(self):
        return id(self)

    def add_bonus(self, effect):
        self.bonuses.append(effect)


class DummyUI:
    def __init__(self, choices: list[str] | None = None):
        self.enabled = True
        self.allow_cli_fallback = False
        self._choices = list(choices or [])

    def prompt_choice(self, _prompt, choices=None, **_kwargs):
        if self._choices:
            return self._choices.pop(0)
        if choices:
            return choices[0]
        return None


class DummyConn:
    def __init__(self, cards: list[str] | None = None):
        self._cards = list(cards or [])

    def read_card(self, _prompt: str = "", acceptable_responses: list[str] | None = None):
        if self._cards:
            candidate = str(self._cards.pop(0)).strip().lower()
        elif acceptable_responses:
            candidate = str(acceptable_responses[0]).strip().lower()
        else:
            candidate = ""
        if acceptable_responses and candidate not in acceptable_responses:
            return acceptable_responses[0]
        return candidate

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return None

    def leds_off(self):
        return None


def _game(*, ui=None, conn=None):
    return SimpleNamespace(
        state=object(),
        heroes=[],
        enemies=[],
        ui=ui if ui is not None else DummyUI(),
        conn=conn if conn is not None else DummyConn(),
        board=SimpleNamespace(rows=8, cols=8),
        ui_log=lambda *_a, **_k: None,
    )


def _wizard(
    *,
    arcane_study: str = "evocation",
    drain_action: str = "drain_bonded_item",
    focus: int = 0,
    thesis: str | None = None,
) -> DummyActor:
    actor = DummyActor()
    actor.focus_point = int(focus)
    setup = {
        "arcane_study": arcane_study,
        "drain_action": drain_action,
    }
    if thesis:
        setup["thesis"] = thesis
    actor.statuses = [
        Status(
            id="wizard",
            data={
                "wizard_setup": setup
            },
        )
    ]
    return actor


def test_magic_resolver_records_wizard_cast_registry():
    actor = _wizard()
    game = _game()

    result = dispatch_event("wizard_test_rank1_spell", EventContext(game=game, actor=actor))

    assert result.success is True
    registry = list(getattr(actor, "wizard_cast_spells_registry", []) or [])
    assert len(registry) == 1
    assert registry[0].get("spell_id") == "wizard_test_rank1_spell"
    assert registry[0].get("rank") == 1
    assert registry[0].get("is_focus") is False
    assert registry[0].get("is_cantrip") is False


def test_drain_bonded_item_casts_selected_spell_after_card_scan():
    actor = _wizard(arcane_study="evocation", drain_action="drain_bonded_item")
    actor.wizard_cast_spells_registry = [
        {"spell_id": "wizard_test_rank1_spell", "rank": 1, "is_focus": False, "is_cantrip": False}
    ]
    game = _game(ui=DummyUI(), conn=DummyConn(cards=["wizard_test_rank1_spell"]))

    result = dispatch_event("drain_bonded_item", EventContext(game=game, actor=actor))

    assert result.success is True
    assert result.consumed_action is True
    assert result.actions_spent == 2
    usage = dict(getattr(actor, "wizard_drain_usage", {}) or {})
    assert usage.get("all") == 1

    second = dispatch_event("drain_bonded_item", EventContext(game=game, actor=actor))
    assert second.success is False
    assert "no eligible" in str(second.message or "").lower()


def test_drain_bonded_item_blocks_when_familiar_drain_is_configured():
    actor = _wizard(arcane_study="universalist", drain_action="drain_familiar")
    actor.wizard_cast_spells_registry = [
        {"spell_id": "wizard_test_rank1_spell", "rank": 1, "is_focus": False, "is_cantrip": False}
    ]
    game = _game()

    result = dispatch_event("drain_bonded_item", EventContext(game=game, actor=actor))

    assert result.success is False
    assert "drain_familiar" in str(result.message or "")


def test_drain_familiar_universalist_works_once_per_rank():
    actor = _wizard(arcane_study="universalist", drain_action="drain_familiar")
    actor.wizard_cast_spells_registry = [
        {"spell_id": "wizard_test_rank1_spell", "rank": 1, "is_focus": False, "is_cantrip": False},
        {"spell_id": "wizard_test_rank2_spell", "rank": 2, "is_focus": False, "is_cantrip": False},
    ]
    game = _game(ui=DummyUI(), conn=DummyConn(cards=["wizard_test_rank1_spell", "wizard_test_rank2_spell"]))

    first = dispatch_event("drain_familiar", EventContext(game=game, actor=actor))
    second = dispatch_event("drain_familiar", EventContext(game=game, actor=actor))
    third = dispatch_event("drain_familiar", EventContext(game=game, actor=actor))

    assert first.success is True
    assert second.success is True
    assert third.success is False
    usage = dict(getattr(actor, "wizard_drain_usage", {}) or {})
    assert usage.get("rank:1") == 1
    assert usage.get("rank:2") == 1


def test_drain_bonded_item_recasts_without_prepared_copy_or_slot():
    actor = _wizard(arcane_study="evocation", drain_action="drain_bonded_item")
    actor.wizard_cast_spells_registry = [
        {"spell_id": "wizard_test_rank1_spell", "rank": 1, "is_focus": False, "is_cantrip": False}
    ]
    actor.spell_state = {
        "enabled": True,
        "enforce": True,
        "class_name": "wizard",
        "known": {"rank_1": ["wizard_test_rank1_spell"]},
        "prepared_today": {"rank_1": [], "cantrip": []},
        "slot_total": {"rank_1": 0},
        "slot_remaining": {"rank_1": 0},
        "prepared_counts": {"rank_1": {}},
        "consumed_counts": {"rank_1": {}},
    }
    game = _game(ui=DummyUI(), conn=DummyConn(cards=["wizard_test_rank1_spell"]))

    result = dispatch_event("drain_bonded_item", EventContext(game=game, actor=actor))

    assert result.success is True
    state = dict(getattr(actor, "spell_state", {}) or {})
    assert int((state.get("slot_remaining", {}) or {}).get("rank_1", 0) or 0) == 0
    consumed_rank1 = dict((state.get("consumed_counts", {}) or {}).get("rank_1", {}) or {})
    assert int(consumed_rank1.get("wizard_test_rank1_spell", 0) or 0) == 0


def test_refocus_restores_wizard_focus_point_up_to_pool_limit():
    actor = _wizard(focus=0)
    actor.focus_pool_max = 2
    game = _game()

    first = dispatch_event("refocus", EventContext(game=game, actor=actor))
    second = dispatch_event("refocus", EventContext(game=game, actor=actor))
    third = dispatch_event("refocus", EventContext(game=game, actor=actor))

    assert first.success is True
    assert first.consumed_action is False
    assert second.success is True
    assert third.success is False
    assert getattr(actor, "focus_point", 0) == 2


def test_refocus_restores_focus_for_non_wizard_with_focus_pool():
    actor = DummyActor(class_name="champion", focus_point=0)
    actor.focus_pool_max = 1
    game = _game()

    first = dispatch_event("refocus", EventContext(game=game, actor=actor))
    second = dispatch_event("refocus", EventContext(game=game, actor=actor))

    assert first.success is True
    assert first.consumed_action is False
    assert second.success is False
    assert getattr(actor, "focus_point", 0) == 1


def test_wizard_spell_substitution_swaps_one_uncast_prepared_copy():
    actor = _wizard(thesis="spell_substitution")
    actor.spell_state = {
        "enabled": True,
        "enforce": True,
        "class_name": "wizard",
        "known": {"rank_1": ["wizard_test_rank1_spell", "fear"]},
        "prepared_today": {"rank_1": ["wizard_test_rank1_spell", "wizard_test_rank1_spell"], "cantrip": []},
        "slot_total": {"rank_1": 2},
        "slot_remaining": {"rank_1": 1},
        "prepared_counts": {"rank_1": {"wizard_test_rank1_spell": 2}},
        "consumed_counts": {"rank_1": {"wizard_test_rank1_spell": 1}},
    }
    game = _game(ui=DummyUI(choices=["1", "1"]))

    result = dispatch_event("wizard_spell_substitution", EventContext(game=game, actor=actor))

    assert result.success is True
    assert result.consumed_action is False
    assert "10 minut" in str(result.message or "").lower()
    state = dict(getattr(actor, "spell_state", {}) or {})
    prepared_counts = dict((state.get("prepared_counts", {}) or {}).get("rank_1", {}) or {})
    assert int(prepared_counts.get("wizard_test_rank1_spell", 0) or 0) == 1
    assert int(prepared_counts.get("fear", 0) or 0) == 1
    consumed_counts = dict((state.get("consumed_counts", {}) or {}).get("rank_1", {}) or {})
    assert int(consumed_counts.get("wizard_test_rank1_spell", 0) or 0) == 1


def test_wizard_spell_substitution_requires_thesis():
    actor = _wizard(thesis="spell_blending")
    actor.spell_state = {
        "enabled": True,
        "enforce": True,
        "class_name": "wizard",
        "known": {"rank_1": ["wizard_test_rank1_spell", "fear"]},
        "prepared_today": {"rank_1": ["wizard_test_rank1_spell"], "cantrip": []},
        "slot_total": {"rank_1": 1},
        "slot_remaining": {"rank_1": 1},
        "prepared_counts": {"rank_1": {"wizard_test_rank1_spell": 1}},
        "consumed_counts": {"rank_1": {}},
    }
    game = _game(ui=DummyUI(choices=["1", "1"]))

    result = dispatch_event("wizard_spell_substitution", EventContext(game=game, actor=actor))

    assert result.success is False
    assert "requires thesis" in str(result.message or "").lower()


def test_wizard_spell_substitution_is_limited_to_once_per_scenario():
    actor = _wizard(thesis="spell_substitution")
    actor.object_id = "wizard-1"
    actor.spell_state = {
        "enabled": True,
        "enforce": True,
        "class_name": "wizard",
        "known": {"rank_1": ["wizard_test_rank1_spell", "fear"]},
        "prepared_today": {"rank_1": ["wizard_test_rank1_spell", "wizard_test_rank1_spell", "wizard_test_rank1_spell"], "cantrip": []},
        "slot_total": {"rank_1": 3},
        "slot_remaining": {"rank_1": 3},
        "prepared_counts": {"rank_1": {"wizard_test_rank1_spell": 3}},
        "consumed_counts": {"rank_1": {}},
    }
    game = _game(ui=DummyUI(choices=["1", "1"]))

    first = dispatch_event("wizard_spell_substitution", EventContext(game=game, actor=actor))
    second = dispatch_event("wizard_spell_substitution", EventContext(game=game, actor=actor))

    assert first.success is True
    assert second.success is False
    assert "once per scenario" in str(second.message or "").lower()
