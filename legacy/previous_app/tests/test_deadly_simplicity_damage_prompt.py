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
from statuses import Status


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        if self.choice is not None:
            return self.choice
        if acceptable_responses:
            return acceptable_responses[0]
        return None

    def leds_off(self):
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}
        self.blocked_edges = set()

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        del diagonal
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
    def __init__(self):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = FakeBoard()
        self.conn = FakeConn()
        self.ui_log = lambda *_a, **_k: None


class Hero:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]


class Enemy:
    def __init__(self, pos, hp=12, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac

    def apply_damage(self, amount, _dmg_type=""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def test_deadly_simplicity_upgrades_unarmed_from_d4_to_d6(monkeypatch):
    hero = Hero((0, 0))
    hero.add_status(
        Status(
            id="cleric",
            data={
                "cleric_setup": {
                    "favored_weapon": "unarmed",
                    "favored_weapon_group": "unarmed",
                }
            },
        )
    )
    hero.add_status(Status(id="deadly_simplicity"))

    enemy = Enemy((1, 0), hp=10, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    prompts = []
    rolls = iter([20, 5])

    def _prompt(prompt, *_args, **_kwargs):
        prompts.append(str(prompt))
        return next(rolls)

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", _prompt)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("unarmed", _ctx(game, hero))

    assert result.success
    assert any("Obrażenia 1k6 + STR" in text for text in prompts)
