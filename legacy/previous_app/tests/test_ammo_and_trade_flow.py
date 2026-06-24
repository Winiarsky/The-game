from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext  # noqa: E402
from GameObjects.events.registry import dispatch_event  # noqa: E402
from GameObjects.items.equipment import create_equipment  # noqa: E402
from GameObjects.items.inventory import add_item, consume_ammo, count_ammo  # noqa: E402
from GameObjects.items.weapon import create_weapon  # noqa: E402
from GameObjects.NPC.base_npc import BaseNPC  # noqa: E402
from GameObjects.interactions_mixin import TradeItem  # noqa: E402
from economy import actor_total_cp, set_actor_total_cp  # noqa: E402
from hero import Hero  # noqa: E402


class _FakeEvents:
    def safe_emit_action(self, **_payload):
        return None


class _FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, _acceptable_responses=None):
        return self.choice

    def leds_off(self):
        return None


class _FakeBoard:
    def __init__(self):
        self.occupants = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def interactables_at(self, _pos):
        return []

    def is_blocked(self, _a, _b):
        return False

    def get_wall(self, _a, _b):
        return None

    def edge_interactables_between(self, _a, _b):
        return []

    def remove(self, pos):
        self.occupants.pop(pos, None)


@dataclass
class _Enemy:
    position: tuple[int, int] = (1, 0)
    hp: int = 20
    ac: int = 10

    def apply_damage(self, amount, _dmg_type="", nonlethal=False):
        _ = nonlethal
        self.hp -= int(amount or 0)
        return self.hp, self.hp <= 0


class _FakeChoiceUI:
    enabled = True
    allow_cli_fallback = False

    def __init__(self, answers: list[str]):
        self._answers = list(answers)
        self.infos: list[tuple[str, str]] = []

    def prompt_choice(self, *_args, **_kwargs):
        if not self._answers:
            return None
        return self._answers.pop(0)

    def prompt_info(self, title, *, prompt_long=None, **_kwargs):
        self.infos.append((str(title), str(prompt_long or "")))
        return "ok"


def test_ammo_stack_count_and_consume_flow():
    hero = Hero()
    arrows = create_equipment("arrows")
    assert arrows is not None
    add_item(hero, arrows)

    assert count_ammo(hero, "arrows") == 10
    ok, _ = consume_ammo(hero, "arrows", amount=3)
    assert ok is True
    assert count_ammo(hero, "arrows") == 7


def test_ranged_attack_consumes_ammo_when_tracking_enabled(monkeypatch):
    hero = Hero(position=(0, 0))
    hero.track_ammo = True
    enemy = _Enemy(position=(1, 0), hp=20, ac=10)
    bow = create_weapon("longbow")
    arrows = create_equipment("arrows")
    assert bow is not None and arrows is not None
    setattr(arrows, "ammo_count", 1)
    hero.inventory = [bow, arrows]
    hero.equipped_weapon_item_ids = [bow.instance_id]

    game = type("GameStub", (), {})()
    game.events = _FakeEvents()
    game.board = _FakeBoard()
    game.conn = _FakeConn(choice=enemy.position)
    game.ui = None
    game.ui_log = lambda *_a, **_k: None
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}

    rolls = iter([15, 5])
    monkeypatch.setattr("GameObjects.events.attack.base_attack_range_event.prompt_for_roll", lambda *_a, **_k: next(rolls))

    result = dispatch_event("attack", EventContext(game=game, actor=hero))
    assert result.success is True
    assert count_ammo(hero, "arrows") == 0
    inventory_ids = {str(getattr(item, "item_id", "") or "").strip().lower() for item in list(getattr(hero, "inventory", []) or [])}
    assert "arrows" not in inventory_ids


def test_ranged_attack_is_blocked_without_ammo_when_tracking_enabled(monkeypatch):
    hero = Hero(position=(0, 0))
    hero.track_ammo = True
    enemy = _Enemy(position=(1, 0), hp=20, ac=10)
    bow = create_weapon("longbow")
    assert bow is not None
    hero.inventory = [bow]
    hero.equipped_weapon_item_ids = [bow.instance_id]

    game = type("GameStub", (), {})()
    game.events = _FakeEvents()
    game.board = _FakeBoard()
    game.conn = _FakeConn(choice=enemy.position)
    game.ui = None
    game.ui_log = lambda *_a, **_k: None
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}

    monkeypatch.setattr("GameObjects.events.attack.base_attack_range_event.prompt_for_roll", lambda *_a, **_k: 15)

    result = dispatch_event("attack", EventContext(game=game, actor=hero))
    assert result.success is False
    assert "brak amunicji" in str(result.message or "").lower()
    assert enemy.hp == 20


def test_npc_trade_spends_money_and_adds_item_to_hero():
    ui = _FakeChoiceUI(["1", "__exit_trade__"])
    game = type("GameStub", (), {"ui": ui})()
    hero = Hero()
    set_actor_total_cp(hero, 1000)
    npc = BaseNPC(
        name="Kupiec testowy",
        inventory=[TradeItem(item_id="healer_tools", name="Narzedzia medyka", price=500, kind="equipment", stock=1)],
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    message = npc.action_trade(hero, game)

    assert "kupiono" in str(message or "").lower()
    assert actor_total_cp(hero) == 500
    inventory_ids = {str(getattr(item, "item_id", "") or "").strip().lower() for item in list(getattr(hero, "inventory", []) or [])}
    assert "healer_tools" in inventory_ids
    assert int(npc.inventory[0].stock) == 0


def test_npc_trade_blocks_purchase_when_insufficient_funds():
    ui = _FakeChoiceUI(["1", "__exit_trade__"])
    game = type("GameStub", (), {"ui": ui})()
    hero = Hero()
    set_actor_total_cp(hero, 100)
    npc = BaseNPC(
        name="Kupiec testowy",
        inventory=[TradeItem(item_id="healer_tools", name="Narzedzia medyka", price=500, kind="equipment", stock=1)],
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    message = npc.action_trade(hero, game)

    assert "koniec handlu" in str(message or "").lower()
    assert actor_total_cp(hero) == 100
    inventory_ids = {str(getattr(item, "item_id", "") or "").strip().lower() for item in list(getattr(hero, "inventory", []) or [])}
    assert "healer_tools" not in inventory_ids


def test_npc_trade_scroll_purchase_configures_spell_at_buy_time():
    ui = _FakeChoiceUI(["1", "true_strike", "__exit_trade__"])
    game = type("GameStub", (), {"ui": ui})()
    hero = Hero()
    set_actor_total_cp(hero, 500)
    npc = BaseNPC(
        name="Kupiec testowy",
        inventory=[TradeItem(item_id="scroll_common_rank1", name="Zwoj czaru 1. rangi", price=400, kind="equipment", stock=1)],
        enable_talk=False,
        enable_diplomacy=False,
        enable_pickpocket=False,
    )

    message = npc.action_trade(hero, game)

    assert "kupiono" in str(message or "").lower()
    scrolls = [
        item
        for item in list(getattr(hero, "inventory", []) or [])
        if str(getattr(item, "item_id", "") or "").strip().lower() == "scroll_common_rank1"
    ]
    assert len(scrolls) == 1
    assert str(getattr(scrolls[0], "scroll_spell_id", "") or "").strip().lower() == "true_strike"
    assert "prawdziwy cios" in str(getattr(scrolls[0], "name", "") or "").strip().lower()
    assert actor_total_cp(hero) == 100
    assert int(npc.inventory[0].stock) == 0
