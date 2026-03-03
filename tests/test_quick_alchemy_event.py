from types import SimpleNamespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import GameObjects.events.all_events  # noqa: F401

from GameObjects.events.base import EventContext
from GameObjects.events.elixirs.juggernaut_mutagen_event import JuggernautMutagenEvent
from GameObjects.events.quick_alchemy_event import QuickAlchemyEvent
from GameObjects.items.inventory import (
    add_alchemical_item,
    has_ready_alchemical_item,
    transfer_item,
)
from board_grid import BoardGrid
from hero import Hero
from states.combat import Combat
from statuses import Status
from statuses.classes.alchemist.alchemsit import ALCHEMSIT_STATUS


class FakeConn:
    def __init__(self, card_responses):
        self._card_responses = list(card_responses)
        self.read_calls = 0

    def read_card(self, *_args, **_kwargs):
        self.read_calls += 1
        if not self._card_responses:
            return ""
        return self._card_responses.pop(0)

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        if positions:
            return positions[0]
        return None

    def leds_off(self):
        return None


class DummyUI:
    enabled = True

    def __init__(self):
        self.info_calls = []

    def prompt_info(self, title, *, prompt_long=None, **_kwargs):
        self.info_calls.append((title, prompt_long))
        return "ok"


def _make_game(hero, conn):
    game = SimpleNamespace(
        heroes=[hero],
        enemies=[],
        conn=conn,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
    )
    game.state = Combat(game)
    return game


def test_quick_alchemy_requires_feat_status():
    hero = Hero(position=(0, 0))
    conn = FakeConn(["alchemists_fire"])
    game = _make_game(hero, conn)

    result = QuickAlchemyEvent().run(EventContext(game=game, actor=hero))
    assert result.success is False
    assert result.consumed_action is False
    assert "wymaga feata" in (result.message or "")


def test_alchemist_status_grants_quick_alchemy_feat():
    grants = list((ALCHEMSIT_STATUS.data or {}).get("grants_statuses") or [])
    grant_ids = [getattr(item, "id", str(item)) for item in grants]
    assert "alchemist_research_field" in grant_ids
    assert "quick_alchemy_allow" in grant_ids
    assert "advanced_alchemy" in grant_ids


def test_quick_alchemy_reprompts_invalid_then_creates_item(monkeypatch):
    hero = Hero(position=(0, 0))
    hero.add_status(Status(id="quick_alchemy_allow"))
    conn = FakeConn(["attack", "alchemists_fire"])
    game = _make_game(hero, conn)

    ui = DummyUI()
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    result = QuickAlchemyEvent().run(EventContext(game=game, actor=hero))

    assert result.success is True
    assert result.consumed_action is True
    assert result.actions_spent == 1
    assert conn.read_calls == 2
    assert "alchemists fire" in (result.message or "").lower()
    assert has_ready_alchemical_item(hero, "alchemists_fire") is False

    alchemical_items = [item for item in getattr(hero, "inventory", []) if getattr(item, "event_name", "") == "alchemists_fire"]
    assert len(alchemical_items) == 1
    assert int(getattr(alchemical_items[0], "preparation_counter", -1)) == 1


def test_quick_alchemy_end_cancels_without_cost():
    hero = Hero(position=(0, 0))
    hero.add_status(Status(id="quick_alchemy_allow"))
    conn = FakeConn(["end"])
    game = _make_game(hero, conn)

    result = QuickAlchemyEvent().run(EventContext(game=game, actor=hero))

    assert result.success is False
    assert result.consumed_action is False
    assert "anulowane" in (result.message or "").lower()
    assert not any(getattr(item, "event_name", None) for item in getattr(hero, "inventory", []) or [])


def test_quick_alchemy_item_becomes_ready_after_end_of_turn():
    hero = Hero(position=(0, 0))
    hero.add_status(Status(id="quick_alchemy_allow"))
    conn = FakeConn(["alchemists_fire"])
    game = _make_game(hero, conn)
    combat = game.state

    combat.base_order = [hero]
    combat.round_queue = [hero]
    combat.initiative_order = [hero]
    combat._initiatives_ready = True

    result = QuickAlchemyEvent().run(EventContext(game=game, actor=hero))
    assert result.success is True
    assert has_ready_alchemical_item(hero, "alchemists_fire") is False

    combat._advance_turn()

    assert has_ready_alchemical_item(hero, "alchemists_fire") is True


def test_alchemist_can_transfer_mutagen_and_other_hero_can_drink_it(monkeypatch):
    alchemist = Hero()
    drinker = Hero()

    event_name = "juggernaut_mutagen"
    add_alchemical_item(alchemist, event_name=event_name, preparation_counter=0)
    assert has_ready_alchemical_item(alchemist, event_name) is True

    item = next(item for item in (getattr(alchemist, "inventory", []) or []) if getattr(item, "event_name", "") == event_name)
    ok, _msg = transfer_item(alchemist, drinker, item)
    assert ok is True
    assert has_ready_alchemical_item(alchemist, event_name) is False
    assert has_ready_alchemical_item(drinker, event_name) is True

    board = BoardGrid(rows=3, cols=3)
    board.place(drinker, (1, 1))
    conn = FakeConn([])
    game = SimpleNamespace(
        board=board,
        heroes=[alchemist, drinker],
        enemies=[],
        conn=conn,
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
    )
    game.state = Combat(game)

    event = JuggernautMutagenEvent()
    monkeypatch.setattr(event, "_prompt_level", lambda: "lesser")

    result = event.run(EventContext(game=game, actor=drinker))
    assert result.success is True
    assert drinker.has_status("juggernaut_mutagen")
    assert drinker.has_status("juggernaut_mutagen_penalty")
    assert has_ready_alchemical_item(drinker, event_name) is False
