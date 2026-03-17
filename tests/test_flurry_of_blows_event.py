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
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.items.weapon import create_weapon
from states.combat import Combat
from statuses.base import Status


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeUI:
    enabled = False
    allow_cli_fallback = False


class FakeConn:
    def __init__(self, choices: list[tuple[int, int]]):
        self.choices = list(choices)

    def set_leds(self, *args, **kwargs):
        _ = args, kwargs
        return None

    def scan_board(self, acceptable_responses=None):
        _ = acceptable_responses
        if self.choices:
            return self.choices.pop(0)
        return None

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
    def __init__(self, conn):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = conn
        self.ui = FakeUI()
        self.ui_log = lambda *_a, **_k: None
        self.ui_event = lambda *_a, **_k: None
        self.ui_hero = lambda *_a, **_k: None
        self.ui_active_actor = lambda *_a, **_k: None
        self.state = Combat(self)


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = [Status(id="flurry_of_blows")]
        self.bonuses = []

    def has_status(self, status_id: str) -> bool:
        return any(getattr(s, "id", s) == status_id for s in self.statuses)

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]


class Enemy:
    def __init__(self, pos, hp=40, ac=10, resistance_per_call=0):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.resistance_per_call = int(resistance_per_call)
        self.apply_calls = 0

    def apply_damage(self, amount, _dmg_type=""):
        self.apply_calls += 1
        dealt = max(0, int(amount) - self.resistance_per_call)
        self.hp -= dealt
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def test_flurry_merges_damage_when_both_hits_same_target(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((1, 0), hp=40, ac=10, resistance_per_call=5)
    game = FakeGame(conn=FakeConn([enemy.position, enemy.position]))
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}

    rolls = iter([15, 10, 15, 8])
    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("flurry_of_blows", _ctx(game, hero))

    assert result.success is True
    assert enemy.hp == 27
    assert enemy.apply_calls == 1


def test_flurry_of_blows_uses_equipped_monk_weapon_with_monastic_weaponry(monkeypatch):
    hero = Hero((0, 0))
    hero.statuses.append(Status(id="monastic_weaponry"))
    hero.level = 1
    hero.str_mod = 3
    hero.weapon_proficiency_ranks = {"simple": "trained", "martial": "untrained", "unarmed": "trained"}

    bo_staff = create_weapon("bo_staff")
    assert bo_staff is not None
    hero.inventory = [bo_staff]
    hero.equipped_weapon_item_ids = [bo_staff.instance_id]

    enemy = Enemy((1, 0), hp=40, ac=10, resistance_per_call=0)
    game = FakeGame(conn=FakeConn([enemy.position, enemy.position]))
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}

    prompts: list[str] = []

    def _fake_prompt(*args, **kwargs):
        prompt = kwargs.get("prompt")
        if prompt is None and args:
            prompt = args[0]
        prompts.append(str(prompt or ""))
        text = str(prompt or "").lower()
        if "obra" in text:
            return 8
        return 15

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", _fake_prompt)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("flurry_of_blows", _ctx(game, hero))

    assert result.success is True
    attack_payload = dict(getattr(game.state, "attack_state", {}).get(hero, {}) or {})
    weapon_counts = dict(attack_payload.get("weapon_counts") or {})
    assert int(weapon_counts.get("attack_bo_staff", 0) or 0) == 2
