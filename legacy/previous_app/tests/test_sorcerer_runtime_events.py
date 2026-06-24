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
from GameObjects.events.registry import dispatch_event
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status


@dataclass
class DummyActor(StatusMixin):
    name: str = "sorcerer"
    object_id: str = "sorcerer"
    class_name: str = "sorcerer"
    statuses: list = field(default_factory=list)
    bonuses: list = field(default_factory=list)
    focus_point: int = 1

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


def _game(*, ui=None):
    return SimpleNamespace(
        state=object(),
        heroes=[],
        enemies=[],
        ui=ui if ui is not None else DummyUI(),
        board=SimpleNamespace(rows=8, cols=8),
        ui_log=lambda *_a, **_k: None,
    )


def _sorcerer(
    *,
    known_rank_1: list[str],
    bloodline_rank_1: str = "magic_missile",
    signature_spells: list[str] | None = None,
) -> DummyActor:
    actor = DummyActor()
    actor.sorcerer_spell_tradition = "arcane"
    actor.sorcerer_known_cantrips = []
    actor.sorcerer_known_rank_1_spells = list(known_rank_1)
    actor.sorcerer_signature_spells = list(signature_spells or [])
    actor.spell_state = {
        "enabled": True,
        "enforce": True,
        "class_name": "sorcerer",
        "known": {
            "cantrip": [],
            "rank_1": list(known_rank_1),
        },
        "slot_total": {"rank_1": 3},
        "slot_remaining": {"rank_1": 3},
        "sorcerer_signature_spells": list(signature_spells or []),
    }
    actor.statuses = [
        Status(
            id="sorcerer",
            data={
                "sorcerer_setup": {
                    "spell_tradition": "arcane",
                    "bloodline_granted_spells": {"rank_1": bloodline_rank_1},
                }
            },
        )
    ]
    return actor


def test_retrain_sorcerer_spell_swaps_repertoire_from_ui_menu():
    actor = _sorcerer(
        known_rank_1=["magic_missile", "fear"],
        signature_spells=["fear"],
    )
    game = _game(ui=DummyUI(choices=["rank_1::fear", "grease"]))

    result = dispatch_event("retrain_sorcerer_spell", EventContext(game=game, actor=actor))

    assert result.success is True
    assert result.consumed_action is False
    assert "fear" in str(result.message or "").lower()
    assert "grease" in str(result.message or "").lower()
    rank_1 = list((getattr(actor, "spell_state", {}) or {}).get("known", {}).get("rank_1", []) or [])
    assert "grease" in rank_1
    assert "fear" not in rank_1
    assert "grease" in list(getattr(actor, "sorcerer_known_rank_1_spells", []) or [])
    assert "fear" not in list(getattr(actor, "sorcerer_known_rank_1_spells", []) or [])
    assert "grease" in list(getattr(actor, "sorcerer_signature_spells", []) or [])
    assert "fear" not in list(getattr(actor, "sorcerer_signature_spells", []) or [])


def test_retrain_sorcerer_spell_fails_when_only_bloodline_spell_is_known():
    actor = _sorcerer(known_rank_1=["magic_missile"])
    game = _game(ui=DummyUI())

    result = dispatch_event("retrain_sorcerer_spell", EventContext(game=game, actor=actor))

    assert result.success is False
    assert "no eligible repertoire spell" in str(result.message or "").lower()
