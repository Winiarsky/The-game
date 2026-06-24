from types import SimpleNamespace

import pytest

from combat.damage_utils import apply_splash_damage
from damage_types import DamageType


class BoardStub:
    def __init__(self, width=5, height=5):
        self.width = width
        self.height = height
        self.removed = []

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        if not self.in_bounds(pos):
            return []
        x, y = pos
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if not diagonal and abs(dx) + abs(dy) != 1:
                    continue
                candidate = (x + dx, y + dy)
                if self.in_bounds(candidate):
                    neighbors.append(candidate)
        if include_position:
            neighbors.append(pos)
        return neighbors

    def remove(self, pos):
        self.removed.append(pos)


class DummyUnit:
    def __init__(self, pos, hp=10, name="unit", object_id=None):
        self.position = pos
        self.hp = hp
        self.name = name
        self.object_id = object_id or name

    def apply_damage(self, amount, _damage_type):
        self.hp -= amount
        return self.hp, self.hp <= 0


def test_apply_splash_damage_hits_enemy_and_hero(monkeypatch):
    class DummyUI:
        def __init__(self):
            self.messages = []

        def prompt_info(self, _title, *, prompt_long=None, **_kwargs):
            self.messages.append(prompt_long)
            return "ok"

    dummy_ui = DummyUI()
    monkeypatch.setattr("combat.damage_utils.get_ui_client", lambda: dummy_ui)

    board = BoardStub()
    hero_adj = DummyUnit((0, 1), name="Hero", object_id="hero-1")
    enemy_adj = DummyUnit((1, 1), hp=5, name="Enemy", object_id="enemy-1")
    game = SimpleNamespace(
        board=board,
        heroes=[hero_adj],
        enemies=[enemy_adj],
    )

    res = apply_splash_damage(
        game,
        center_pos=(0, 0),
        amount=2,
        damage_type=DamageType.ACID.value,
        info_title="Splash",
        source="test",
    )

    assert hero_adj in res["heroes"]
    assert enemy_adj in res["enemies"]
    assert enemy_adj.hp == 3
    assert any("2" in (msg or "") for msg in dummy_ui.messages)


def test_apply_splash_damage_defeats_and_removes_enemy():
    board = BoardStub()
    enemy_adj = DummyUnit((1, 1), hp=2, name="Enemy", object_id="enemy-1")
    game = SimpleNamespace(
        board=board,
        heroes=[],
        enemies=[enemy_adj],
    )

    res = apply_splash_damage(
        game,
        center_pos=(0, 0),
        amount=3,
        damage_type=DamageType.ACID.value,
    )

    assert enemy_adj in res["defeated"]
    assert enemy_adj not in game.enemies
    assert (1, 1) in board.removed


def test_apply_splash_damage_respects_exclude():
    board = BoardStub()
    enemy_adj = DummyUnit((1, 1), hp=5, name="Enemy", object_id="enemy-1")
    hero_adj = DummyUnit((0, 1), name="Hero", object_id="hero-1")
    game = SimpleNamespace(
        board=board,
        heroes=[hero_adj],
        enemies=[enemy_adj],
    )

    res = apply_splash_damage(
        game,
        center_pos=(0, 0),
        amount=2,
        damage_type=DamageType.ACID.value,
        exclude=enemy_adj,
    )

    assert enemy_adj not in res["enemies"]
    assert enemy_adj.hp == 5
    assert hero_adj in res["heroes"]


@pytest.mark.parametrize("center_pos", [None, (99, 99)])
def test_apply_splash_damage_no_neighbors(center_pos):
    board = BoardStub()
    enemy_adj = DummyUnit((1, 1), hp=5, name="Enemy", object_id="enemy-1")
    game = SimpleNamespace(
        board=board,
        heroes=[],
        enemies=[enemy_adj],
    )

    res = apply_splash_damage(
        game,
        center_pos=center_pos,
        amount=2,
        damage_type=DamageType.ACID.value,
    )

    assert res["heroes"] == []
    assert res["enemies"] == []
    assert res["defeated"] == []
