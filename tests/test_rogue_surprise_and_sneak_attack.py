from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from damage_types import DamageType
from GameObjects.events.attack.basic_melee_attack_event import BasicMeleeAttackEvent
from GameObjects.events.base import EventContext
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

    def get_neighbors(self, pos, *, include_position=False, diagonal=True):
        _ = diagonal
        x, y = pos
        out = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        if include_position:
            out.append(pos)
        return out

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


class FinesseMeleeAttackEvent(BasicMeleeAttackEvent):
    weapon_label = "test finesse weapon"
    damage_prompt = "1k6"
    action_id_base = "test_finesse_attack"
    damage_type = DamageType.PIERCING.value
    default_tags = ["attack_melee", "agile", "finesse"]


@dataclass
class Hero:
    object_id: str = "hero-1"
    position: tuple[int, int] | None = (0, 0)
    statuses: list[Status] = field(default_factory=list)
    bonuses: list = field(default_factory=list)
    level: int = 1
    class_name: str = "rogue"

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
    hp: int = 20
    ac: int = 15
    statuses: list[Status] = field(default_factory=list)
    bonuses: list = field(default_factory=list)

    def has_status(self, status_id: str) -> bool:
        return any(getattr(s, "id", s) == status_id for s in self.statuses)

    def add_bonus(self, effect):
        self.bonuses.append(effect)

    def apply_damage(self, amount, _dmg_type=""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


def test_surprise_attack_makes_unacted_target_off_guard_and_enables_sneak_attack(monkeypatch):
    hero = Hero(
        statuses=[
            Status(id="rogue"),
            Status(id="sneak_attack"),
            Status(id="surprise_attack"),
        ]
    )
    enemy = Enemy()

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position
    game.state.round_index = 1
    game.state.round_queue = [hero, enemy]

    prompts: list[str] = []
    rolls = iter([13, 5, 4])

    def _prompt(*args, **_kwargs):
        prompts.append(str(args[0]) if args else "")
        return next(rolls)

    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", _prompt)
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses", lambda *_a, **_k: None)

    result = FinesseMeleeAttackEvent().run(EventContext(game=game, actor=hero))

    assert result.success is True
    assert bool((result.data or {}).get("hit", False)) is True
    assert enemy.hp == 11
    assert any("Sneak Attack:" in prompt for prompt in prompts)


def test_surprise_attack_does_not_apply_after_target_acted(monkeypatch):
    hero = Hero(
        statuses=[
            Status(id="rogue"),
            Status(id="sneak_attack"),
            Status(id="surprise_attack"),
        ]
    )
    enemy = Enemy()

    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position
    game.state.round_index = 1
    game.state.round_queue = [hero]  # enemy już działał w tej rundzie

    prompts: list[str] = []
    rolls = iter([13])

    def _prompt(*args, **_kwargs):
        prompts.append(str(args[0]) if args else "")
        return next(rolls)

    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", _prompt)
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses", lambda *_a, **_k: None)

    result = FinesseMeleeAttackEvent().run(EventContext(game=game, actor=hero))

    assert result.success is True
    assert bool((result.data or {}).get("hit", True)) is False
    assert enemy.hp == 20
    assert not any("Sneak Attack:" in prompt for prompt in prompts)

