from __future__ import annotations

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
from GameObjects.events.magic.level_1st import events as rank1_events
from GameObjects.events.magic.level_1st.events import HarmEvent, HealEvent
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status


class Actor(StatusMixin):
    def __init__(self, *, name: str, position: tuple[int, int], hp: int = 20):
        super().__init__()
        self.name = name
        self.position = position
        self.hp = int(hp)

    def apply_damage(self, amount: int, _damage_type: str = ""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0

    def heal(self, amount: int):
        self.hp += int(amount)
        return self.hp


class FakeConn:
    def __init__(self, choice):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return self.choice

    def leds_off(self):
        return None


class FakeUI:
    enabled = True

    def prompt_choice(self, _prompt, choices=None, **_kwargs):
        if choices:
            return choices[0]
        return "single"


def test_heal_with_holy_castigation_still_heals_non_undead(monkeypatch):
    caster = Actor(name="Cleric", position=(0, 0))
    caster.statuses = [Status(id="healing_hands"), Status(id="holy_castigation")]
    fiend = Actor(name="Fiend", position=(1, 0), hp=15)
    fiend.tags = ["fiend"]

    prompt_calls = []

    def _roll(*_args, **kwargs):
        prompt_calls.append(kwargs)
        return 6

    monkeypatch.setattr(rank1_events, "prompt_for_roll", _roll)

    game = SimpleNamespace(
        state=object(),
        heroes=[caster],
        enemies=[fiend],
        conn=FakeConn(fiend.position),
        ui=FakeUI(),
        ui_log=lambda *_a, **_k: None,
    )
    result = HealEvent().run(EventContext(game=game, actor=caster))

    assert result.success is True
    assert fiend.hp == 21
    assert any("d10" in str((item.get("prompt_long") or "")).lower() for item in prompt_calls)


def test_harm_with_harming_hands_heals_undead_target(monkeypatch):
    caster = Actor(name="Cleric", position=(0, 0))
    caster.statuses = [Status(id="harming_hands")]
    undead = Actor(name="Undead", position=(1, 0), hp=8)
    undead.tags = ["undead"]

    prompt_calls = []

    def _roll(*_args, **kwargs):
        prompt_calls.append(kwargs)
        return 5

    monkeypatch.setattr(rank1_events, "prompt_for_roll", _roll)

    game = SimpleNamespace(
        state=object(),
        heroes=[caster],
        enemies=[undead],
        conn=FakeConn(undead.position),
        ui=FakeUI(),
        ui_log=lambda *_a, **_k: None,
    )
    result = HarmEvent().run(EventContext(game=game, actor=caster))

    assert result.success is True
    assert undead.hp == 13
    assert any("d10" in str((item.get("prompt_long") or "")).lower() for item in prompt_calls)
