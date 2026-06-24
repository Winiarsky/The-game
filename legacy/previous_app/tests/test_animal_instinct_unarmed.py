import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401  # rejestracja eventów
from GameObjects.events.registry import dispatch_event
from GameObjects.events.base import EventContext
from GameObjects.events.attack import basic_melee_attack_event
from statuses.base import Status
from statuses.classes.barbarian.instincts.animal_instinct import (
    ANIMAL_INSTINCT_PROFILES,
    AnimalInstinctActiveStatus,
)
from statuses.rage import rage_damage_bonus


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeConn:
    def __init__(self, choice=None):
        self.choice = choice

    def set_leds(self, *args, **kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        return self.choice

    def leds_off(self):
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}

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

    def remove_status(self, status):
        self.statuses = [s for s in self.statuses if getattr(s, "id", s) != getattr(status, "id", status)]


class Enemy:
    def __init__(self, pos, hp=12, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.last_damage_type = None
        self.last_damage_amount = None

    def apply_damage(self, amount, dmg_type=""):
        self.last_damage_type = dmg_type
        self.last_damage_amount = amount
        self.hp -= amount
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


@pytest.mark.parametrize("animal_key,profile", list(ANIMAL_INSTINCT_PROFILES.items()))
def test_unarmed_attack_uses_animal_instinct_profile(monkeypatch, animal_key, profile):
    hero = Hero((0, 0))
    enemy = Enemy((1, 0), hp=20, ac=10)
    game = FakeGame()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board.occupants = {hero.position: hero, enemy.position: enemy}
    game.conn.choice = enemy.position

    hero.statuses.append(Status(id="rage"))
    hero.statuses.append(AnimalInstinctActiveStatus(profile=profile, duration=10))

    prompts = []
    rolls = iter([15, 7])  # hit, dmg

    def _prompt_for_roll(prompt, *args, **kwargs):
        prompts.append(prompt)
        return next(rolls)

    monkeypatch.setattr(basic_melee_attack_event, "prompt_for_roll", _prompt_for_roll)
    monkeypatch.setattr(basic_melee_attack_event, "refresh_flanking_statuses", lambda *_a, **_k: None)

    result = dispatch_event("unarmed", _ctx(game, hero))

    assert result.success
    assert enemy.last_damage_type == profile["damage_type"]
    expected_bonus = rage_damage_bonus(hero, is_agile=True)
    assert enemy.last_damage_amount == 7 + expected_bonus
    assert any("Obrażenia 1k10 + STR" in p for p in prompts), f"missing prompt for {animal_key}"
