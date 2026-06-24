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

    def scan_board(self, _positions=None):
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


@dataclass
class Hero:
    object_id: str = "hero-thief"
    position: tuple[int, int] | None = (0, 0)
    statuses: list[Status] = field(default_factory=lambda: [Status(id="rogue")])
    bonuses: list = field(default_factory=list)
    class_name: str = "rogue"
    rogue_racket: str = "thief"

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]


@dataclass
class Enemy:
    object_id: str = "enemy-thief"
    position: tuple[int, int] | None = (1, 0)
    ac: int = 10
    hp: int = 20
    statuses: list[Status] = field(default_factory=list)
    bonuses: list = field(default_factory=list)

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def apply_damage(self, amount, _dtype=""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


class ThiefFinesseAttack(BasicMeleeAttackEvent):
    weapon_label = "thief finesse blade"
    damage_prompt = "1k4 + STR"
    action_id_base = "thief_finesse_attack"
    damage_type = DamageType.PIERCING.value
    default_tags = ["attack_melee", "finesse"]


def test_thief_racket_replaces_strength_with_dexterity_in_damage_prompt(monkeypatch):
    hero = Hero()
    enemy = Enemy()
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    prompts: list[str] = []
    rolls = iter([20, 4])  # trafienie + obrażenia

    def _prompt(prompt, *_a, **_k):
        prompts.append(str(prompt))
        return next(rolls)

    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", _prompt)
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses", lambda *_a, **_k: None)

    result = ThiefFinesseAttack().run(EventContext(game=game, actor=hero))

    assert result.success is True
    assert any("Obrażenia 1k4 + DEX" in text for text in prompts)
    assert not any("Obrażenia 1k4 + STR" in text for text in prompts)

