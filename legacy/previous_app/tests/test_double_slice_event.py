from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.attack import basic_melee_attack_event
from GameObjects.events import fighter_feat_events
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.items.weapon import create_weapon
from states.combat import Combat
from statuses import Status


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeUI:
    def __init__(self, precision_choice: str = "Pierwszy Strike"):
        self.enabled = True
        self.allow_cli_fallback = False
        self.precision_choice = precision_choice
        self.prompt_calls = 0

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        _ = choices
        self.prompt_calls += 1
        return self.precision_choice


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *args, **kwargs):
        _ = args, kwargs
        return None

    def scan_board(self, acceptable_responses=None):
        _ = acceptable_responses
        return self.choice

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return "end"


class FakeBoard:
    def __init__(self):
        self.occupants = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        _ = diagonal
        out = [
            (pos[0] + 1, pos[1]),
            (pos[0] - 1, pos[1]),
            (pos[0], pos[1] + 1),
            (pos[0], pos[1] - 1),
        ]
        if include_position:
            out.append(pos)
        return out

    def in_bounds(self, _pos):
        return True

    def remove(self, pos):
        self.occupants.pop(pos, None)


class FakeGame:
    def __init__(self, ui: FakeUI):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()
        self.ui = ui
        self.ui_log = lambda *_a, **_k: None
        self.ui_event = lambda *_a, **_k: None
        self.ui_hero = lambda *_a, **_k: None
        self.ui_active_actor = lambda *_a, **_k: None
        self.state = Combat(self)


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = [Status(id="double_slice")]
        self.bonuses = []
        self.level = 1
        self.inventory = []
        self.equipped_weapon_item_ids = []

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, status_id: str) -> bool:
        return any(getattr(s, "id", s) == status_id for s in self.statuses)

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]


class Enemy:
    def __init__(self, pos, hp=30, ac=10, resistance_per_call=0):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.resistance_per_call = int(resistance_per_call)
        self.apply_calls = 0
        self.statuses = []

    def apply_damage(self, amount, _dmg_type=""):
        self.apply_calls += 1
        dealt = max(0, int(amount) - self.resistance_per_call)
        self.hp -= dealt
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero, metadata={})


def _equip_two_weapons(hero: Hero, *, traits_first=(), traits_second=()):
    first = create_weapon("sword")
    second = create_weapon("dagger")
    assert first is not None
    assert second is not None
    if traits_first:
        first.traits = tuple(traits_first)
    if traits_second:
        second.traits = tuple(traits_second)
    hero.inventory = [first, second]
    hero.equipped_weapon_item_ids = [first.instance_id, second.instance_id]


def test_double_slice_merges_damage_and_applies_resistance_once(monkeypatch):
    ui = FakeUI()
    hero = Hero((0, 0))
    _equip_two_weapons(hero)
    enemy = Enemy((1, 0), hp=40, ac=10, resistance_per_call=5)
    game = FakeGame(ui)
    game.heroes = [hero]
    game.enemies = [enemy]
    game.state.base_order = [hero, enemy]
    game.state.round_queue = [hero, enemy]
    game.state.base_initiative[hero] = 15
    game.state.base_initiative[enemy] = 10
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([15, 10, 15, 8])  # atk1 hit, dmg1=10, atk2 hit, dmg2=8
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)
    monkeypatch.setattr(fighter_feat_events, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("double_slice", _ctx(game, hero))

    assert result.success is True
    # Double Slice łączy obrażenia i rozlicza je jednorazowo:
    # (10 + 8) - 5 = 13 obrażeń.
    assert enemy.hp == 27
    assert enemy.apply_calls == 1
    assert (result.data or {}).get("damage_components") == [("slashing", 10), ("piercing", 8)]


def test_double_slice_precision_choice_uses_ui_prompt(monkeypatch):
    ui = FakeUI(precision_choice="Drugi Strike")
    hero = Hero((0, 0))
    # Obie bronie z backstabber, żeby wymusić prompt precision.
    _equip_two_weapons(hero, traits_first=("backstabber",), traits_second=("backstabber",))
    enemy = Enemy((1, 0), hp=40, ac=10, resistance_per_call=0)
    enemy.statuses = [Status(id="flat_footed")]
    game = FakeGame(ui)
    game.heroes = [hero]
    game.enemies = [enemy]
    game.state.base_order = [hero, enemy]
    game.state.round_queue = [hero, enemy]
    game.state.base_initiative[hero] = 15
    game.state.base_initiative[enemy] = 10
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([15, 6, 15, 6])  # oba hity, baza 6 + 6
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)
    monkeypatch.setattr(fighter_feat_events, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("double_slice", _ctx(game, hero))

    assert result.success is True
    # Precision (+1) tylko na drugim Striku: 6 + (6+1) = 13
    assert enemy.hp == 27
    assert ui.prompt_calls == 1
    assert (result.data or {}).get("precision_choice") == "second"


def test_double_slice_non_agile_offhand_uses_status_penalty_and_counts_two_attacks(monkeypatch):
    ui = FakeUI()
    hero = Hero((0, 0))
    _equip_two_weapons(hero)
    # Dagger zwykle jest agile; usuwamy trait, żeby sprawdzić karę -2 status.
    hero.inventory[1].traits = tuple(t for t in (hero.inventory[1].traits or ()) if str(t).strip().lower() != "agile")
    enemy = Enemy((1, 0), hp=40, ac=30, resistance_per_call=0)
    game = FakeGame(ui)
    game.heroes = [hero]
    game.enemies = [enemy]
    game.state.base_order = [hero, enemy]
    game.state.round_queue = [hero, enemy]
    game.state.base_initiative[hero] = 15
    game.state.base_initiative[enemy] = 10
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    captured_modifiers = []

    def _prompt(*args, **kwargs):
        prompt = str(args[0] if args else "")
        if prompt.startswith("Atak "):
            captured_modifiers.append(dict(kwargs.get("modifiers") or {}))
        return 10

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", _prompt)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)
    monkeypatch.setattr(fighter_feat_events, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("double_slice", _ctx(game, hero))
    assert result.success is True
    assert len(captured_modifiers) >= 2

    second_attack_mods = captured_modifiers[1]
    assert any(int(item.get("value", 0) or 0) == 2 for item in (second_attack_mods.get("penStat") or []))
    assert not any(int(item.get("value", 0) or 0) == 2 for item in (second_attack_mods.get("penCirc") or []))

    attack_state = dict(game.state.attack_state.get(hero, {}) or {})
    assert int(attack_state.get("attacks_this_turn", 0) or 0) == 2

    dispatch_event("sword", _ctx(game, hero))
    assert len(captured_modifiers) >= 3
    third_attack_mods = captured_modifiers[2]
    assert any(int(item.get("value", 0) or 0) == 10 for item in (third_attack_mods.get("penCirc") or []))


def test_double_slice_agile_offhand_has_no_extra_penalty(monkeypatch):
    ui = FakeUI()
    hero = Hero((0, 0))
    _equip_two_weapons(hero)  # second weapon (dagger) ma agile
    enemy = Enemy((1, 0), hp=40, ac=30, resistance_per_call=0)
    game = FakeGame(ui)
    game.heroes = [hero]
    game.enemies = [enemy]
    game.state.base_order = [hero, enemy]
    game.state.round_queue = [hero, enemy]
    game.state.base_initiative[hero] = 15
    game.state.base_initiative[enemy] = 10
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    captured_modifiers = []

    def _prompt(*args, **kwargs):
        prompt = str(args[0] if args else "")
        if prompt.startswith("Atak "):
            captured_modifiers.append(dict(kwargs.get("modifiers") or {}))
        return 10

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", _prompt)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)
    monkeypatch.setattr(fighter_feat_events, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("double_slice", _ctx(game, hero))
    assert result.success is True
    assert len(captured_modifiers) >= 2

    second_attack_mods = captured_modifiers[1]
    assert not any(int(item.get("value", 0) or 0) == 2 for item in (second_attack_mods.get("penStat") or []))
    assert not any(int(item.get("value", 0) or 0) == 2 for item in (second_attack_mods.get("penCirc") or []))
