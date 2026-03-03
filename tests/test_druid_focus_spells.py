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

from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event, list_events
from GameObjects.events.magic.focus_spells.druid import order_spell_events as druid_events
from GameObjects.items.inventory import ensure_actor_inventory
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status


@dataclass
class DummyHero(StatusMixin):
    name: str = "Hero"
    position: tuple[int, int] | None = None
    hp: int = 20

    def __post_init__(self):
        self.bonuses = []

    def apply_damage(self, amount: int, _damage_type: str = ""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0

    def heal(self, amount: int):
        self.hp += int(amount)


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return None

    def leds_off(self):
        return None


def _druid(*, order: str, order_spell: str, focus: int = 1, known_extra: list[str] | None = None) -> DummyHero:
    actor = DummyHero(name="Druid", position=(0, 0), hp=20)
    actor.class_name = "druid"
    actor.focus_point = int(focus)
    actor.statuses.append(
        Status(
            id="druid",
            data={
                "druid_setup": {
                    "order": order,
                    "order_spell": order_spell,
                }
            },
        )
    )
    actor.druid_order_spells = [order_spell] + list(known_extra or [])
    return actor


def _game(*, actor, enemies=None, heroes=None):
    return SimpleNamespace(
        state=object(),
        heroes=list(heroes or [actor]),
        enemies=list(enemies or []),
        conn=DummyConn(),
        ui=None,
        board=None,
        ui_log=lambda *_a, **_k: None,
    )


def test_druid_focus_spells_are_registered():
    events = list_events()
    for name in ("goodberry", "heal_animal", "tempest_surge", "wild_morph", "wild_shape"):
        assert name in events


def test_goodberry_creates_items_and_spends_focus(monkeypatch):
    actor = _druid(order="leaf", order_spell="goodberry", focus=2)
    game = _game(actor=actor)

    result = dispatch_event("goodberry", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 1
    inventory = ensure_actor_inventory(actor)
    goodberries = [item for item in inventory if str(getattr(item, "item_id", "")).lower() == "goodberry"]
    assert len(goodberries) == 1


def test_heal_animal_heals_animal_target(monkeypatch):
    actor = _druid(order="animal", order_spell="heal_animal", focus=1)
    target = DummyHero(name="Wolf", position=(1, 0), hp=7)
    target.tags = ["animal"]
    game = _game(actor=actor, heroes=[actor, target])

    monkeypatch.setattr(druid_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(druid_events, "_prompt_choice", lambda *_a, **_k: "ranged")
    roll_values = iter([11])  # healing
    monkeypatch.setattr(druid_events, "prompt_for_roll", lambda *_a, **_k: next(roll_values))

    result = dispatch_event("heal_animal", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 18


def test_tempest_surge_failure_applies_clumsy_and_persistent(monkeypatch):
    actor = _druid(order="storm", order_spell="tempest_surge", focus=1)
    target = DummyHero(name="Enemy", position=(1, 0), hp=18)
    game = _game(actor=actor, enemies=[target])

    monkeypatch.setattr(druid_events, "_pick_target", lambda *_a, **_k: target)
    monkeypatch.setattr(druid_events, "_prompt_choice", lambda *_a, **_k: "failure")
    roll_values = iter([10])  # base damage
    monkeypatch.setattr(druid_events, "prompt_for_roll", lambda *_a, **_k: next(roll_values))

    result = dispatch_event("tempest_surge", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 8
    assert any(getattr(status, "id", None) == "clumsy" for status in target.statuses)
    assert any(getattr(status, "id", None) == "persistent_damage" for status in target.statuses)


def test_wild_morph_adds_active_claws_status(monkeypatch):
    actor = _druid(order="wild", order_spell="wild_morph", focus=1)
    actor.statuses.append(Status(id="wild_shape"))
    game = _game(actor=actor)

    monkeypatch.setattr(druid_events, "_prompt_choice", lambda *_a, **_k: "wild_claws")
    monkeypatch.setattr(druid_events, "prompt_for_roll", lambda *_a, **_k: 1)

    result = dispatch_event("wild_morph", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    active = [s for s in actor.statuses if getattr(s, "id", None) == "wild_morph_active"]
    assert len(active) == 1
    assert (active[0].data or {}).get("effect") == "wild_claws"


def test_wild_shape_adds_active_form_and_spends_focus(monkeypatch):
    actor = _druid(order="wild", order_spell="wild_morph", focus=1)
    actor.statuses.append(Status(id="wild_shape"))  # feat grants the focus spell
    game = _game(actor=actor)

    monkeypatch.setattr(druid_events, "_prompt_choice", lambda *_a, **_k: "pest_form:cat")
    monkeypatch.setattr(druid_events, "prompt_for_roll", lambda *_a, **_k: 1)

    result = dispatch_event("wild_shape", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    active = [s for s in actor.statuses if getattr(s, "id", None) == "wild_shape_active"]
    assert len(active) == 1
    assert (active[0].data or {}).get("form") == "cat"


def test_druid_cannot_cast_unknown_focus_spell():
    actor = _druid(order="leaf", order_spell="goodberry", focus=1)
    target = DummyHero(name="Wolf", position=(1, 0), hp=7)
    target.tags = ["animal"]
    game = _game(actor=actor, heroes=[actor, target])

    result = dispatch_event("heal_animal", EventContext(game=game, actor=actor))

    assert result.success is False
    assert "not known" in str(result.message or "").lower()
