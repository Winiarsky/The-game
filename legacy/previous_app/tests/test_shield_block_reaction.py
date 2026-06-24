from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bonuses import BonusEffect, BonusType
from combat.reactions.dispatcher import dispatch_reactions
from GameObjects.interactions_mixin import BonusMixin, ReactiveMixin, StatusMixin
from GameObjects.items.shield import StandardShield
from states.combat import Combat
from statuses.general.shield_block import SHIELD_BLOCK_STATUS


class DummyUI:
    def __init__(self, answers: list[str] | None = None):
        self.answers = list(answers or [])
        self.enabled = True
        self.allow_cli_fallback = False
        self.prompt_calls = 0

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        self.prompt_calls += 1
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        return positions[0] if positions else None

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return "end"


class DummyHero(StatusMixin, BonusMixin, ReactiveMixin):
    def __init__(self, *, name: str, object_id: str, position: tuple[int, int], wounds: int = 0):
        super().__init__()
        self.name = name
        self.object_id = object_id
        self.position = position
        self.wounds = wounds
        self.bonuses = []
        self.reactions = []
        self.reactions_left = 1
        self.reactions_max = 1

    def __hash__(self):
        return id(self)

    def heal(self, amount: int) -> int:
        self.wounds = max(0, int(self.wounds) - max(0, int(amount)))
        return self.wounds


class DummyEnemy(ReactiveMixin):
    def __init__(self, *, name: str, object_id: str, position: tuple[int, int]):
        super().__init__()
        self.name = name
        self.object_id = object_id
        self.position = position
        self.hp = 20
        self.reactions = []
        self.reactions_left = 1
        self.reactions_max = 1

    def __hash__(self):
        return id(self)


def _raise_shield(hero: DummyHero) -> None:
    hero.add_bonus(
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag="ac",
            source="raise_shield:round1",
            label="tarcza w górze",
            duration_turns=1,
        )
    )


def _build_game(hero: DummyHero, enemy: DummyEnemy, *, ui_answers: list[str] | None = None):
    logs: list[str] = []
    game = type("Game", (), {})()
    game.ui = DummyUI(ui_answers or ["tak"])
    game.conn = DummyConn()
    game.heroes = [hero]
    game.enemies = [enemy]
    game.board = type("Board", (), {})()
    game.ui_log = lambda msg: logs.append(str(msg))
    game.ui_event = lambda *_a, **_k: None
    game.ui_hero = lambda *_a, **_k: None
    game.ui_active_actor = lambda *_a, **_k: None
    game._logs = logs

    combat = Combat(game)
    game.state = combat
    combat.base_order = [hero, enemy]
    combat.round_queue = [hero, enemy]
    combat.base_initiative[hero] = 12
    combat.base_initiative[enemy] = 10
    return game, combat


def test_shield_block_reduces_damage_and_damages_shield():
    hero = DummyHero(name="Hero", object_id="hero-1", position=(0, 0), wounds=12)
    hero.add_status(SHIELD_BLOCK_STATUS)
    hero.equipped_shield = StandardShield()
    _raise_shield(hero)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1))
    game, combat = _build_game(hero, enemy)

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": hero,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 12,
            "damage_type": "slashing",
        },
    )

    assert hero.wounds == 7
    assert hero.equipped_shield.current_hp == 13
    assert hero.reactions_left == 0
    assert combat.out_of_turn_actions_used.get(hero, 0) == 1


def test_shield_block_logs_destruction_when_shield_breaks():
    hero = DummyHero(name="Hero", object_id="hero-1", position=(0, 0), wounds=50)
    hero.add_status(SHIELD_BLOCK_STATUS)
    hero.equipped_shield = StandardShield()
    _raise_shield(hero)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1))
    game, _combat = _build_game(hero, enemy)

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": hero,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 50,
            "damage_type": "slashing",
        },
    )

    assert hero.equipped_shield.is_destroyed is True
    assert any("zniszczona" in line.lower() for line in game._logs)


def test_shield_block_does_not_trigger_with_broken_shield():
    hero = DummyHero(name="Hero", object_id="hero-1", position=(0, 0), wounds=12)
    hero.add_status(SHIELD_BLOCK_STATUS)
    hero.equipped_shield = StandardShield(current_hp=10)
    _raise_shield(hero)
    enemy = DummyEnemy(name="Enemy", object_id="enemy-1", position=(0, 1))
    game, _combat = _build_game(hero, enemy, ui_answers=["tak"])

    dispatch_reactions(
        game,
        {
            "actor": enemy,
            "target": hero,
            "action_id": "enemy_attack_melee",
            "action_tags": ["attack_melee"],
            "damage": 12,
            "damage_type": "slashing",
        },
    )

    assert hero.wounds == 12
    assert hero.equipped_shield.current_hp == 10
    assert game.ui.prompt_calls == 0
