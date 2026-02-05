import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bonuses import BonusEffect, BonusType, aggregate_best_by_type, compute_total_modifier
from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from combat.flanking import refresh_flanking_statuses


def test_only_best_per_type_is_used():
    effects = [
        BonusEffect(BonusType.CIRCUMSTANCE, 2, "attack_melee", source="inspiration"),
        BonusEffect(BonusType.CIRCUMSTANCE, 3, "attack_melee", source="blessing"),
        BonusEffect(BonusType.STATUS, 1, "attack_melee", source="haste"),
        BonusEffect(BonusType.STATUS, 2, "attack_melee", source="shaken", is_penalty=True),
    ]

    total = compute_total_modifier(effects, "attack_melee")
    # best circumstance +3, best status bonus +1, best status penalty -2 => 2
    assert total == 2

    agg = aggregate_best_by_type(effects, "attack_melee")
    assert agg[BonusType.CIRCUMSTANCE]["bonus"] == 3
    assert agg[BonusType.STATUS]["penalty"] == 2


def test_target_specific_bonus_applies_only_to_matching_target():
    effects = [
        BonusEffect(BonusType.CIRCUMSTANCE, 2, "attack_melee", target_id="t1"),
        BonusEffect(BonusType.CIRCUMSTANCE, 5, "attack_melee", target_id="t2"),
    ]
    assert compute_total_modifier(effects, "attack_melee", target_id="t1") == 2
    assert compute_total_modifier(effects, "attack_melee", target_id="t2") == 5
    assert compute_total_modifier(effects, "attack_melee", target_id="t3") == 0


def test_penalties_use_highest_magnitude():
    effects = [
        BonusEffect(BonusType.STATUS, 1, "ac", is_penalty=True),
        BonusEffect(BonusType.STATUS, 3, "ac", is_penalty=True),
        BonusEffect(BonusType.STATUS, 2, "ac", is_penalty=True),
    ]
    total = compute_total_modifier(effects, "ac")
    assert total == -3


def test_bonus_mixin_compute_modifier_matches_helpers():
    actor = BonusMixin()
    actor.add_bonus(BonusEffect(BonusType.CIRCUMSTANCE, 2, "stealth", source="cover"))
    actor.add_bonus(BonusEffect(BonusType.STATUS, 1, "stealth", source="spell"))
    actor.add_bonus(BonusEffect(BonusType.STATUS, 4, "stealth", source="mud", is_penalty=True))

    assert actor.compute_modifier("stealth") == -1  # 2 + 1 - 4


def test_duration_turns_ticks_and_expires():
    actor = BonusMixin()
    actor.add_bonus(BonusEffect(BonusType.CIRCUMSTANCE, 2, "ac", duration_turns=2))
    assert actor.compute_modifier("ac") == 2
    actor.tick_bonuses_turn()
    assert actor.compute_modifier("ac") == 2  # 1 tura została
    actor.tick_bonuses_turn()
    assert actor.compute_modifier("ac") == 0  # wygasł


def test_flanking_adds_only_ac_penalty_not_attack_bonus():
    class BoardStub:
        def __init__(self):
            self.width = 3
            self.height = 3

        def in_bounds(self, pos):
            x, y = pos
            return 0 <= x < self.width and 0 <= y < self.height

        def is_blocked(self, a, b):
            return False

        def edge_interactables_between(self, a, b):
            return []

        def get_neighbors(self, pos, include_position=False, diagonal=True):
            x, y = pos
            neighbors = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if not diagonal and abs(dx) + abs(dy) != 1:
                        continue
                    if not include_position and dx == 0 and dy == 0:
                        continue
                    candidate = (x + dx, y + dy)
                    if self.in_bounds(candidate):
                        neighbors.append(candidate)
            return neighbors

        def can_enter(self, pos, allow_occupied=False):
            return True

    class Actor(BonusMixin):
        def __init__(self, object_id, position):
            super().__init__()
            self.object_id = object_id
            self.position = position
            self.statuses = []
            self.flat_footed_penalty = 0

    hero = Actor("hero", (1, 1))
    enemy_left = Actor("e1", (0, 1))
    enemy_right = Actor("e2", (2, 1))

    class GameStub:
        def __init__(self):
            self.board = BoardStub()
            self.heroes = [hero]
            self.enemies = [enemy_left, enemy_right]

    game = GameStub()

    refresh_flanking_statuses(game, ac_penalty=2)

    # Hero should get only AC penalty bonus effect
    hero_penalties = [b for b in hero.bonuses if b.tag == "ac"]
    assert hero_penalties, "flanking should add AC penalty effect"
    assert all(b.is_penalty for b in hero_penalties)
    # No attack bonuses on enemies
    assert not enemy_left.bonuses
    assert not enemy_right.bonuses
from pathlib import Path
import sys
