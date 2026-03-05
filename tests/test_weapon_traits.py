import sys
from pathlib import Path
import types

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext  # noqa: E402
from GameObjects.events.attack.basic_melee_attack_event import BasicMeleeAttackEvent  # noqa: E402
from GameObjects.events.attack.base_attack_range_event import BaseRangeAttackEvent  # noqa: E402
from GameObjects.events.attack.attack_base import AttackEventBase  # noqa: E402


class FakeEvents:
    def __init__(self):
        self.emitted = []

    def safe_emit_action(self, **payload):
        self.emitted.append(payload)


class FakeConn:
    def __init__(self, choices=None):
        self._choices = list(choices or [])

    def set_leds(self, *args, **kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        if self._choices:
            return self._choices.pop(0)
        return None

    def leds_off(self):
        return None


class FakeBoard:
    def __init__(self):
        self.occupants = {}
        self.blocked_edges = set()
        self.edge_objs = {}

    def occupant_at(self, pos):
        return self.occupants.get(pos)

    def interactables_at(self, pos):
        return []

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self.blocked_edges

    def get_wall(self, a, b):
        return None

    def edge_interactables_between(self, a, b):
        return self.edge_objs.get(frozenset((a, b)), [])

    def remove(self, pos):
        self.occupants.pop(pos, None)

    def get_neighbors(self, pos, *, include_position=False, diagonal=True):
        x, y = pos
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if diagonal:
            deltas += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        neighbors = [(x + dx, y + dy) for dx, dy in deltas]
        if include_position:
            neighbors.insert(0, pos)
        return neighbors

    def in_bounds(self, *_args, **_kwargs):
        return True


class FakeGame:
    def __init__(self, conn=None, board=None):
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.board = board or FakeBoard()
        self.conn = conn or FakeConn()
        self.ui_log = lambda *a, **k: None


class Hero:
    def __init__(self, pos=(0, 0)):
        self.position = pos
        self.statuses = []
        self.bonuses = []
        self.object_id = "hero-1"

    def remove_status(self, *_args, **_kwargs):
        return None

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def has_status(self, status_id):
        return any(getattr(item, "id", item) == status_id for item in self.statuses)


class Enemy:
    def __init__(self, pos=(1, 0), hp=30, ac=10):
        self.position = pos
        self.hp = hp
        self.ac = ac
        self.statuses = []

    def apply_damage(self, amount, dmg_type="slashing"):
        self.hp -= amount
        return self.hp, self.hp <= 0


def _ctx(game, hero):
    return EventContext(game=game, actor=hero)


def _prompt_recorder(attack_rolls, damage_rolls, recorded):
    def _prompt(*_args, **kwargs):
        if kwargs.get("layout") == "test":
            recorded.append(kwargs.get("modifiers"))
            return next(attack_rolls)
        return next(damage_rolls)

    return _prompt


def _prompt_long_recorder(attack_rolls, damage_rolls, recorded):
    def _prompt(*_args, **kwargs):
        if kwargs.get("layout") == "test":
            recorded.append(kwargs.get("prompt_long", ""))
            return next(attack_rolls)
        return next(damage_rolls)

    return _prompt


def _bonus_value(mod_grid, label_prefix, key):
    if not mod_grid:
        return None
    for entry in mod_grid.get(key, []):
        if entry.get("label", "").startswith(label_prefix):
            return entry.get("value")
    return None


def _setup_melee_game(*, hero_pos=(0, 0), enemy_positions=((1, 0),)):
    hero = Hero(hero_pos)
    enemies = [Enemy(pos) for pos in enemy_positions]
    board = FakeBoard()
    board.occupants = {hero_pos: hero}
    for enemy in enemies:
        board.occupants[enemy.position] = enemy
    conn = FakeConn([e.position for e in enemies])
    game = FakeGame(conn=conn, board=board)
    game.heroes = [hero]
    game.enemies = enemies
    return game, hero, enemies


def test_backswing_adds_bonus_after_miss(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    recorded = []
    rolls = iter([1, 1, 20, 1])  # miss, dmg (ignored), hit, dmg
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        _prompt_recorder(rolls, rolls, recorded),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class BackswingMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "backswing"]

    event = BackswingMelee()
    event.run(_ctx(game, hero))
    event.run(_ctx(game, hero))

    assert _bonus_value(recorded[1], "backswing", "bonCirc") == 1


def test_sweep_adds_bonus_after_different_target(monkeypatch):
    game, hero, _enemies = _setup_melee_game(enemy_positions=((1, 0), (0, 1)))
    recorded = []
    rolls = iter([1, 1, 20, 1])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        _prompt_recorder(rolls, rolls, recorded),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class SweepMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "sweep"]

    event = SweepMelee()
    event.run(_ctx(game, hero))
    event.run(_ctx(game, hero))

    assert _bonus_value(recorded[1], "sweep", "bonCirc") == 1


def test_forceful_adds_damage_on_second_attack(monkeypatch):
    game, hero, enemies = _setup_melee_game()
    rolls = iter([20, 5, 20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class ForcefulMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "forceful"]
        damage_prompt = "1k6 + STR"

    event = ForcefulMelee()
    event.run(_ctx(game, hero))
    first = game.events.emitted[-1]["damage_components"][0][1]
    event.run(_ctx(game, hero))
    second = game.events.emitted[-1]["damage_components"][0][1]

    assert second == first + 1


def test_twin_adds_damage_when_alternating_weapons(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    rolls = iter([20, 5, 20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class TwinSwordA(BasicMeleeAttackEvent):
        action_id_base = "attack_twin_a"
        default_tags = ["attack_melee", "sword", "twin"]
        damage_prompt = "1k6 + STR"

    class TwinSwordB(BasicMeleeAttackEvent):
        action_id_base = "attack_twin_b"
        default_tags = ["attack_melee", "sword", "twin"]
        damage_prompt = "1k6 + STR"

    a = TwinSwordA()
    b = TwinSwordB()
    a.run(_ctx(game, hero))
    first = game.events.emitted[-1]["damage_components"][0][1]
    b.run(_ctx(game, hero))
    second = game.events.emitted[-1]["damage_components"][0][1]

    assert second == first + 1


def test_backstabber_adds_precision_vs_flat_footed(monkeypatch):
    game, hero, enemies = _setup_melee_game()
    enemies[0].statuses = ["flat_footed"]
    rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class BackstabMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "backstabber"]
        damage_prompt = "1k6 + STR"

    event = BackstabMelee()
    event.run(_ctx(game, hero))
    dmg = game.events.emitted[-1]["damage_components"][0][1]
    assert dmg == 6


def test_deadly_adds_extra_damage_on_crit(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    rolls = iter([20, 5, 3])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class DeadlyMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "deadly:d8"]
        damage_prompt = "1k6 + STR"

    event = DeadlyMelee()
    event.run(_ctx(game, hero))
    total = game.events.emitted[-1]["damage"]
    assert total == 8


def test_versatile_selects_alternate_damage_type(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )
    monkeypatch.setattr(AttackEventBase, "_prompt_choice", lambda *_a, **_k: "slashing")

    class VersatileMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "versatile:s"]
        damage_type = "piercing"

    event = VersatileMelee()
    event.run(_ctx(game, hero))
    dtype = game.events.emitted[-1]["damage_components"][0][0]
    assert dtype == "slashing"


def test_reach_allows_attack_at_distance(monkeypatch):
    game, hero, _enemies = _setup_melee_game(enemy_positions=((2, 0),))
    rolls = iter([20, 1])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class ReachMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "reach"]

    event = ReachMelee()
    result = event.run(_ctx(game, hero))
    assert result.success


def test_volley_adds_penalty_within_min_range(monkeypatch):
    hero = Hero((0, 0))
    enemy = Enemy((3, 0), ac=10)
    board = FakeBoard()
    board.occupants = {hero.position: hero, enemy.position: enemy}
    conn = FakeConn([enemy.position])
    game = FakeGame(conn=conn, board=board)
    game.heroes = [hero]
    game.enemies = [enemy]

    recorded = []
    rolls = iter([20, 1])
    monkeypatch.setattr(
        "GameObjects.events.attack.base_attack_range_event.prompt_for_roll",
        _prompt_recorder(rolls, rolls, recorded),
    )

    class VolleyRange(BaseRangeAttackEvent):
        default_tags = ["attack_ranged", "ranged_attack", "volley:30"]
        range_increment_ft = 60

    event = VolleyRange()
    event.run(_ctx(game, hero))

    assert _bonus_value(recorded[0], "volley 30ft", "penCirc") == 2


def test_finesse_prompt_in_attack(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    recorded = []
    rolls = iter([20, 1])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        _prompt_long_recorder(rolls, rolls, recorded),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class FinesseMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "finesse"]

    event = FinesseMelee()
    event.run(_ctx(game, hero))

    assert recorded
    assert "Finesse: możesz użyć ZR zamiast SI do premii ataku." in recorded[0]


def test_fatal_adds_extra_damage_on_crit(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    rolls = iter([20, 5, 4])  # attack, base damage, fatal extra
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class FatalMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "fatal:d12"]
        damage_prompt = "1k8 + STR"

    event = FatalMelee()
    event.run(_ctx(game, hero))
    total = game.events.emitted[-1]["damage"]
    assert total == 9


def test_modular_selects_requested_damage_type(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )
    monkeypatch.setattr(AttackEventBase, "_prompt_choice", lambda *_a, **_k: "bludgeoning")

    class ModularMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "modular:b,p"]
        damage_type = "slashing"

    event = ModularMelee()
    event.run(_ctx(game, hero))
    dtype = game.events.emitted[-1]["damage_components"][0][0]
    assert dtype == "bludgeoning"


def test_propulsive_adds_half_strength_to_ranged_damage(monkeypatch):
    hero = Hero((0, 0))
    hero.str_mod = 4
    enemy = Enemy((2, 0), ac=10)
    board = FakeBoard()
    board.occupants = {hero.position: hero, enemy.position: enemy}
    conn = FakeConn([enemy.position])
    game = FakeGame(conn=conn, board=board)
    game.heroes = [hero]
    game.enemies = [enemy]

    rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.base_attack_range_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )

    class PropulsiveRange(BaseRangeAttackEvent):
        default_tags = ["attack_ranged", "ranged_attack", "propulsive"]
        damage_prompt = "1k6"
        range_increment_ft = 60

    event = PropulsiveRange()
    event.run(_ctx(game, hero))
    dmg = game.events.emitted[-1]["damage_components"][0][1]
    assert dmg == 7


def test_nonlethal_sets_nonlethal_payload(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    rolls = iter([20, 5])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class NonlethalMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "nonlethal"]

    event = NonlethalMelee()
    event.run(_ctx(game, hero))
    assert bool(game.events.emitted[-1].get("nonlethal", False)) is True


def test_two_hand_updates_damage_prompt_when_chosen(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    captured_damage_prompts = []

    def _prompt(*args, **kwargs):
        if kwargs.get("layout") == "test":
            return 20
        captured_damage_prompts.append(str(args[0] if args else ""))
        return 5

    monkeypatch.setattr("GameObjects.events.attack.attack_base.AttackEventBase._prompt_choice", lambda *_a, **_k: "tak")
    monkeypatch.setattr("GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll", _prompt)
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class TwoHandMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "two_hand:d10"]
        damage_prompt = "1k8 + STR"

    event = TwoHandMelee()
    event.run(_ctx(game, hero))

    assert captured_damage_prompts
    assert "1k10" in captured_damage_prompts[0]


def test_concealing_grants_concealed_status_after_attack(monkeypatch):
    game, hero, _enemies = _setup_melee_game()
    rolls = iter([20, 1])
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.prompt_for_roll",
        lambda *_, **__: next(rolls),
    )
    monkeypatch.setattr(
        "GameObjects.events.attack.basic_melee_attack_event.refresh_flanking_statuses",
        lambda *_: None,
    )

    class ConcealingMelee(BasicMeleeAttackEvent):
        default_tags = ["attack_melee", "concealing"]

    event = ConcealingMelee()
    event.run(_ctx(game, hero))

    assert hero.has_status("concealed")
