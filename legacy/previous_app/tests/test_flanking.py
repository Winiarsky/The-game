import pytest

from statuses import Status
from combat.flanking import effective_ac, is_flanked, refresh_flanking_statuses


class FakeBoard:
    def __init__(self, width=5, height=5):
        self.width = width
        self.height = height
        self.blocked = set()

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def get_neighbors(self, pos, include_position=True, diagonal=True):
        x, y = pos
        offsets = (-1, 0, 1)
        result = []
        for dy in offsets:
            for dx in offsets:
                if dx == 0 and dy == 0:
                    continue
                if not diagonal and abs(dx) + abs(dy) != 1:
                    continue
                cand = (x + dx, y + dy)
                if self.in_bounds(cand):
                    result.append(cand)
        if include_position:
            result.append(pos)
        return result

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self.blocked

    def edge_interactables_between(self, a, b):
        return []

    def can_enter(self, pos, allow_occupied=False):
        return self.in_bounds(pos)


class DummyActor:
    def __init__(self, pos):
        self.position = pos
        self.statuses = []
        self.flat_footed_penalty = 0


def test_is_flanked_true_and_blocked_false():
    board = FakeBoard()
    target = (1, 1)
    threats = [DummyActor((1, 0)), DummyActor((1, 2))]
    assert is_flanked(board, target, threats) is True
    # zablokuj jedną stronę – flanka powinna zniknąć
    board.blocked.add(frozenset(((1, 1), (1, 0))))
    assert is_flanked(board, target, threats) is False


def test_refresh_flanking_sets_and_clears_status():
    board = FakeBoard()
    hero_a = DummyActor((1, 0))
    hero_b = DummyActor((1, 2))
    enemy = DummyActor((1, 1))

    class Game:
        pass

    Game.heroes = [hero_a, hero_b]
    Game.enemies = [enemy]
    Game.board = board

    refresh_flanking_statuses(Game)
    assert enemy.flat_footed_penalty == 2
    assert any(s.id == "flat_footed" for s in enemy.statuses if isinstance(s, Status))

    # przesuń bohatera, żeby zlikwidować flankę
    hero_b.position = (2, 2)
    refresh_flanking_statuses(Game)
    assert enemy.flat_footed_penalty == 0
    assert all(s.id != "flat_footed" for s in enemy.statuses if isinstance(s, Status))


def test_effective_ac_uses_flat_footed_penalty():
    actor = DummyActor((0, 0))
    actor.ac = 15
    actor.flat_footed_penalty = 2
    assert effective_ac(actor) == 13
    actor.flat_footed_penalty = 0
    actor.statuses = [Status(id="flat_footed", data={"ac_penalty": 3})]
    assert effective_ac(actor) == 12
