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
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.items.weapon import create_weapon
from states.combat import Combat
from statuses.base import Status


class FakeEvents:
    def safe_emit_action(self, **_payload):
        return None


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, _acceptable_responses=None):
        return self.choice

    def leds_off(self):
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        _ = diagonal
        out = [(pos[0] + 1, pos[1]), (pos[0] - 1, pos[1]), (pos[0], pos[1] + 1), (pos[0], pos[1] - 1)]
        if include_position:
            out.append(pos)
        return out

    def in_bounds(self, _pos):
        return True

    def interactables_at(self, _pos):
        return []

    def is_blocked(self, _a, _b):
        return False

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
        self.ui_event = lambda *_a, **_k: None
        self.ui_hero = lambda *_a, **_k: None
        self.ui_active_actor = lambda *_a, **_k: None
        self.state = Combat(self)


@dataclass
class Hero:
    object_id: str = "hero-1"
    position: tuple[int, int] | None = (0, 0)
    statuses: list[Status] = field(default_factory=list)
    bonuses: list = field(default_factory=list)
    inventory: list[object] = field(default_factory=list)
    equipped_weapon_item_ids: list[str] = field(default_factory=list)

    def has_status(self, status_id: str) -> bool:
        return any(getattr(s, "id", s) == status_id for s in self.statuses)

    def add_status(self, status):
        self.statuses.append(status)

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != sid]


@dataclass
class Enemy:
    object_id: str = "enemy-1"
    position: tuple[int, int] | None = (1, 0)
    hp: int = 40
    ac: int = 10
    apply_calls: int = 0

    def apply_damage(self, amount, _dmg_type=""):
        self.apply_calls += 1
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


def test_hunted_shot_merges_damage_when_both_shots_hit(monkeypatch):
    hero = Hero()
    enemy = Enemy(hp=40)

    bow = create_weapon("longbow")
    assert bow is not None
    hero.inventory = [bow]
    hero.equipped_weapon_item_ids = [bow.instance_id]

    hero.statuses.extend(
        [
            Status(id="hunted_shot"),
            Status(id="ranger", data={"ranger_setup": {"hunted_prey_target_id": enemy.object_id}}),
        ]
    )

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([15, 6, 15, 8])
    monkeypatch.setattr("GameObjects.events.attack.base_attack_range_event.prompt_for_roll", lambda *_a, **_k: next(rolls))

    result = dispatch_event("hunted_shot", EventContext(game=game, actor=hero))

    assert result.success is True
    assert enemy.hp == 26
    assert enemy.apply_calls == 1


def test_twin_takedown_merges_damage_when_both_hits(monkeypatch):
    hero = Hero()
    enemy = Enemy(hp=40)

    sword = create_weapon("sword")
    dagger = create_weapon("dagger")
    assert sword is not None and dagger is not None
    hero.inventory = [sword, dagger]
    hero.equipped_weapon_item_ids = [sword.instance_id, dagger.instance_id]

    hero.statuses.extend(
        [
            Status(id="twin_takedown"),
            Status(id="ranger", data={"ranger_setup": {"hunted_prey_target_id": enemy.object_id}}),
        ]
    )

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    rolls = iter([15, 7, 15, 5])
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", lambda *_a, **_k: next(rolls))
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses", lambda *_a, **_k: None)
    monkeypatch.setattr("GameObjects.events.ranger_feat_events.refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("twin_takedown", EventContext(game=game, actor=hero))

    assert result.success is True
    assert enemy.hp == 28
    assert enemy.apply_calls == 2
