from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board_grid import BoardGrid
from GameObjects.Enemies.goblin_commando import GoblinCommando
from GameObjects.Enemies.goblin_dog import GoblinDog
from GameObjects.Enemies.goblin_warrior import GoblinWarrior
from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.enemy.enemy_move_event import _goal_positions_from_metadata
from GameObjects.events.enemy.enemy_strike_event import EnemyStrikeEvent
from GameObjects.events.enemy.goblin_dog_scratch_event import GoblinDogScratchEvent
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses import Status
from states.combat import Combat

commando_ai = importlib.import_module("GameObjects.Enemies.behaviors.goblin_commando_raider")
dog_ai = importlib.import_module("GameObjects.Enemies.behaviors.goblin_dog_hunter")
warrior_ai = importlib.import_module("GameObjects.Enemies.behaviors.goblin_warrior_pack")


@dataclass
class DummyHero:
    name: str
    object_id: str
    ac: int
    hp: int
    max_hp: int
    position: tuple[int, int] | None = None
    will_bonus: int = 0
    reflex_bonus: int = 0
    statuses: list = field(default_factory=list)
    bonuses: list = field(default_factory=list)

    def set_position(self, pos):
        self.position = pos

    def has_status(self, status_id: str) -> bool:
        return any(str(getattr(item, "id", item) or "").strip().lower() == status_id for item in self.statuses)

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status_id: str):
        before = len(self.statuses)
        self.statuses = [
            item
            for item in self.statuses
            if str(getattr(item, "id", item) or "").strip().lower() != str(status_id or "").strip().lower()
        ]
        return before != len(self.statuses)

    def add_bonus(self, effect):
        self.bonuses.append(effect)

    def remove_bonuses_with_prefix(self, prefix: str):
        self.bonuses = [item for item in self.bonuses if not str(getattr(item, "source", "") or "").startswith(prefix)]

    def current_hp(self):
        return self.hp

    def apply_damage(self, amount, _damage_type):
        self.hp = max(0, self.hp - int(amount))
        return self.hp, self.hp <= 0

    def hp_ratio(self):
        return max(0.0, min(1.0, float(self.hp) / float(max(1, self.max_hp))))


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        return positions[0]

    def leds_off(self):
        return None

    def read_card(self, *_args, **_kwargs):
        return "ACCEPT"


class DummyWoundsHero(StatusMixin):
    def __init__(self, *, name: str, object_id: str, ac: int, max_hp: int, wounds: int, position=None):
        super().__init__()
        self.name = name
        self.object_id = object_id
        self.ac = ac
        self.max_hp = max_hp
        self.wounds = wounds
        self.position = position
        self.bonuses = []

    def set_position(self, pos):
        self.position = pos


def build_game(board: BoardGrid, heroes: list[DummyHero], enemies: list[object]):
    game = SimpleNamespace(
        board=board,
        heroes=heroes,
        enemies=enemies,
        conn=DummyConn(),
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        ui_hero=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
    )
    game.events = SimpleNamespace(safe_emit_action=lambda **_kwargs: None)
    game.state = Combat(game)
    return game


def place_all(board: BoardGrid, actors: list[object]):
    for actor in actors:
        if getattr(actor, "position", None) is None:
            continue
        board.place(actor, actor.position)


def test_goblin_warrior_pack_scores_flank_position_highest():
    board = BoardGrid(rows=7, cols=7)
    hero = DummyHero(name="Cedric", object_id="hero-1", ac=17, hp=20, max_hp=20, position=(3, 3))
    ally = GoblinCommando(position=(3, 2))
    warrior = GoblinWarrior(position=(1, 3))
    place_all(board, [hero, ally, warrior])
    game = build_game(board, [hero], [ally, warrior])

    melee_weapon = warrior_ai.best_weapon(warrior, weapon_id="dogslicer", ranged=False)
    flank_score = warrior_ai._score_pack_position(warrior, game, hero, (3, 4), melee_weapon)
    side_score = warrior_ai._score_pack_position(warrior, game, hero, (2, 3), melee_weapon)
    backline_score = warrior_ai._score_pack_position(warrior, game, hero, (1, 3), melee_weapon)

    assert flank_score > side_score
    assert flank_score > backline_score


def test_goblin_warrior_when_alone_prefers_shortbow():
    board = BoardGrid(rows=7, cols=7)
    hero = DummyHero(name="Cedric", object_id="hero-1", ac=17, hp=20, max_hp=20, position=(5, 3))
    warrior = GoblinWarrior(position=(1, 3))
    place_all(board, [hero, warrior])
    game = build_game(board, [hero], [warrior])

    calls = []

    def fake_dispatch(name, ctx):
        calls.append((name, dict(ctx.metadata or {})))
        return EventResult(success=True, consumed_action=True)

    original_dispatch = warrior_ai.dispatch_event
    warrior_ai.dispatch_event = fake_dispatch
    try:
        used = warrior_ai.goblin_warrior_pack(warrior, game, combat_state=game.state, actions_left=1)
    finally:
        warrior_ai.dispatch_event = original_dispatch

    assert used == 1
    assert calls == [("enemy_strike", {"forced_target": hero, "weapon_id": "shortbow"})]


def test_goblin_commando_opens_with_demoralize_then_trip():
    board = BoardGrid(rows=7, cols=7)
    hero = DummyHero(name="Cedric", object_id="hero-1", ac=17, hp=20, max_hp=20, will_bonus=5, reflex_bonus=6, position=(3, 3))
    ally = GoblinWarrior(position=(4, 3))
    commando = GoblinCommando(position=(2, 3))
    place_all(board, [hero, ally, commando])
    game = build_game(board, [hero], [ally, commando])

    calls = []

    def fake_dispatch(name, ctx):
        calls.append(name)
        if name == "enemy_trip":
            hero.add_status(SimpleNamespace(id="prone"))
        return EventResult(success=True, consumed_action=True)

    original_dispatch = commando_ai.dispatch_event
    commando_ai.dispatch_event = fake_dispatch
    try:
        used = commando_ai.goblin_commando_raider(commando, game, combat_state=game.state, actions_left=3)
    finally:
        commando_ai.dispatch_event = original_dispatch

    assert used == 3
    assert calls[0] == "demoralize"
    assert "enemy_trip" in calls
    assert calls[-1] == "enemy_strike"


def test_goblin_dog_focuses_wounded_lone_target():
    board = BoardGrid(rows=9, cols=9)
    hero_front = DummyHero(name="Tank", object_id="hero-1", ac=18, hp=20, max_hp=20, position=(3, 1))
    hero_support = DummyHero(name="Support", object_id="hero-2", ac=16, hp=20, max_hp=20, position=(3, 2))
    hero_weak = DummyHero(name="Archer", object_id="hero-3", ac=16, hp=4, max_hp=20, position=(7, 1))
    dog = GoblinDog(position=(1, 1))
    place_all(board, [hero_front, hero_support, hero_weak, dog])
    game = build_game(board, [hero_front, hero_support, hero_weak], [dog])

    target = dog_ai._focus_target(dog, game)

    assert target is hero_weak


def test_downed_hero_is_excluded_from_enemy_target_selection():
    board = BoardGrid(rows=7, cols=7)
    freya = DummyWoundsHero(name="Freya", object_id="hero-f", ac=16, max_hp=20, wounds=20, position=(4, 3))
    freya.add_status(Status(id="unconscious", label="Unconscious"))
    freya.add_status(Status(id="dying_2", label="Dying 2", data={"value": 2}))
    cedric = DummyHero(name="Cedric", object_id="hero-c", ac=17, hp=20, max_hp=20, position=(5, 3))
    dog = GoblinDog(position=(2, 3))
    place_all(board, [freya, cedric, dog])
    game = build_game(board, [freya, cedric], [dog])

    target = dog_ai._focus_target(dog, game)

    assert target is cedric


def test_enemy_strike_cancels_when_forced_target_is_downed():
    board = BoardGrid(rows=5, cols=5)
    freya = DummyWoundsHero(name="Freya", object_id="hero-f", ac=15, max_hp=20, wounds=20, position=(2, 2))
    freya.add_status(Status(id="unconscious", label="Unconscious"))
    freya.add_status(Status(id="dying_3", label="Dying 3", data={"value": 3}))
    dog = GoblinDog(position=(2, 1))
    place_all(board, [freya, dog])
    game = build_game(board, [freya], [dog])

    result = EnemyStrikeEvent().run(
        EventContext(game=game, actor=dog, metadata={"forced_target": freya, "weapon_id": "jaws"})
    )

    assert result.success is False
    assert result.consumed_action is False
    assert result.message == "Strike: brak celu."


def test_goblin_dog_retreat_scoring_prefers_farther_square():
    board = BoardGrid(rows=7, cols=7)
    hero = DummyHero(name="Cedric", object_id="hero-1", ac=17, hp=20, max_hp=20, position=(3, 3))
    dog = GoblinDog(position=(3, 4), hp=6, max_hp=17)
    place_all(board, [hero, dog])
    game = build_game(board, [hero], [dog])

    current_score = dog_ai._score_retreat_position(dog, game, (3, 4))
    far_score = dog_ai._score_retreat_position(dog, game, (2, 6))

    assert far_score > current_score


def test_enemy_strike_with_goblin_dog_jaws_applies_goblin_pox(monkeypatch):
    board = BoardGrid(rows=5, cols=5)
    hero = DummyHero(name="Cedric", object_id="hero-1", ac=15, hp=20, max_hp=20, position=(2, 2))
    dog = GoblinDog(position=(2, 1))
    place_all(board, [hero, dog])
    game = build_game(board, [hero], [dog])

    rolls = iter([15, 4])
    monkeypatch.setattr("random.randint", lambda *_args, **_kwargs: next(rolls))

    result = EnemyStrikeEvent().run(
        EventContext(game=game, actor=dog, metadata={"forced_target": hero, "weapon_id": "jaws"})
    )

    assert result.success is True
    assert any(getattr(status, "source", None) == "goblin_pox" for status in hero.statuses)


def test_goblin_dog_scratch_applies_pox_to_all_adjacent_heroes():
    board = BoardGrid(rows=5, cols=5)
    hero_a = DummyHero(name="Cedric", object_id="hero-1", ac=15, hp=20, max_hp=20, position=(2, 2))
    hero_b = DummyHero(name="Mira", object_id="hero-2", ac=15, hp=20, max_hp=20, position=(3, 2))
    dog = GoblinDog(position=(2, 1))
    place_all(board, [hero_a, hero_b, dog])
    game = build_game(board, [hero_a, hero_b], [dog])

    result = GoblinDogScratchEvent().run(EventContext(game=game, actor=dog))

    assert result.success is True
    assert any(getattr(status, "source", None) == "goblin_pox" for status in hero_a.statuses)
    assert any(getattr(status, "source", None) == "goblin_pox" for status in hero_b.statuses)


def test_enemy_move_metadata_normalizes_tactical_goal_position():
    board = BoardGrid(rows=5, cols=5)
    hero = DummyHero(name="Cedric", object_id="hero-1", ac=15, hp=20, max_hp=20, position=(4, 4))
    warrior = GoblinWarrior(position=(0, 0))
    place_all(board, [hero, warrior])
    game = build_game(board, [hero], [warrior])

    goals = _goal_positions_from_metadata(game, warrior, {"goal_position": (2, 0)})

    assert goals == [(2, 0)]
