import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.events.attack import basic_melee_attack_event
from GameObjects.events.attack import base_attack_range_event


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeConn:
    def __init__(self, *, board_choice=None):
        self.board_choice = board_choice

    def set_leds(self, *args, **kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        if self.board_choice is not None:
            return self.board_choice
        if acceptable_responses:
            return acceptable_responses[0]
        return None

    def leds_off(self):
        return None


class DummyUI:
    def __init__(self, choices=None):
        self.enabled = True
        self.allow_cli_fallback = False
        self.choices = list(choices or [])

    def prompt_choice(self, _prompt, choices=None, **_kwargs):
        if self.choices:
            return self.choices.pop(0)
        if choices:
            return choices[0]
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}
        self.blocked_edges = set()

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        del diagonal
        neighbors = [
            (pos[0] + 1, pos[1]),
            (pos[0] - 1, pos[1]),
            (pos[0], pos[1] + 1),
            (pos[0], pos[1] - 1),
        ]
        if include_position:
            neighbors.append(pos)
        return neighbors

    def in_bounds(self, _pos):
        return True

    def interactables_at(self, _pos):
        return []

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self.blocked_edges

    def get_wall(self, _a, _b):
        return None

    def edge_interactables_between(self, _a, _b):
        return []

    def remove(self, pos):
        self.occupants.pop(pos, None)


class FakeGame:
    def __init__(self, *, conn, ui=None):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = conn
        self.ui = ui if ui is not None else DummyUI()
        self.ui_log = lambda *_a, **_k: None


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []
        self.weapon_loadout = ["sword", "longbow", "unarmed"]
        self.active_weapon = "sword"

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, status_id):
        return any(getattr(item, "id", item) == status_id for item in self.statuses)


class Enemy:
    def __init__(self, pos, hp=12, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.last_damage_type = None

    def apply_damage(self, amount, dmg_type=""):
        self.last_damage_type = dmg_type
        self.hp -= amount
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def test_swap_weapon_changes_active_weapon_from_scanned_card():
    hero = Hero((0, 0))
    game = FakeGame(conn=FakeConn(), ui=DummyUI(["longbow"]))
    game.heroes = [hero]

    result = dispatch_event("swap_weapon", _ctx(game, hero))

    assert result.success
    assert result.consumed_action
    assert hero.active_weapon == "longbow"


def test_swap_weapon_rejects_weapon_outside_hero_loadout():
    hero = Hero((0, 0))
    hero.weapon_loadout = ["sword", "unarmed"]
    hero.active_weapon = "sword"
    game = FakeGame(conn=FakeConn(), ui=DummyUI(["longbow"]))
    game.heroes = [hero]

    result = dispatch_event("swap_weapon", _ctx(game, hero))

    assert not result.success
    assert not result.consumed_action
    assert hero.active_weapon == "sword"


def test_attack_uses_current_active_weapon_sword(monkeypatch):
    hero = Hero((0, 0))
    hero.active_weapon = "sword"
    enemy = Enemy((1, 0), hp=10, ac=10)
    game = FakeGame(conn=FakeConn(board_choice=enemy.position))
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}

    rolls = iter([20, 5])  # hit, damage
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_, **__: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("attack", _ctx(game, hero))

    assert result.success
    assert enemy.hp == 5
    assert any(str(ev.get("action_id", "")).startswith("attack_sword") for ev in game.events.emitted)


def test_attack_after_swap_weapon_uses_longbow(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((2, 0), hp=11, ac=10)
    game = FakeGame(conn=FakeConn(board_choice=enemy.position), ui=DummyUI(["longbow"]))
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}

    swap_result = dispatch_event("swap_weapon", _ctx(game, hero))
    assert swap_result.success
    assert hero.active_weapon == "longbow"

    rolls = iter([15, 4])  # hit, damage
    monkeypatch.setattr(base_attack_range_event, "prompt_for_roll", lambda *_, **__: next(rolls))

    result = dispatch_event("attack", _ctx(game, hero))

    assert result.success
    assert enemy.hp == 7
    assert hero.has_status("range_attacker")
