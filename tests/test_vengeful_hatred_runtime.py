from types import SimpleNamespace

from hero import Hero
from GameObjects.Enemies.enemy_types import EnemyType
from statuses.race.dwarf.feats.vengeful_hatred import (
    VengefulHatredStatus,
    grant_vengeful_hatred_revenge,
    tick_vengeful_hatred_rounds,
    vengeful_hatred_damage_bonus,
)


def test_vengeful_hatred_scales_with_weapon_dice():
    hero = Hero()
    hero.add_status(VengefulHatredStatus(EnemyType.ORC))
    target = SimpleNamespace(enemy_type=EnemyType.ORC, object_id="orc-1")

    assert vengeful_hatred_damage_bonus(hero, target, weapon_dice=1) == 1
    assert vengeful_hatred_damage_bonus(hero, target, weapon_dice=3) == 3


def test_vengeful_hatred_revenge_target_lasts_for_rounds():
    hero = Hero()
    hero.add_status(VengefulHatredStatus(EnemyType.ORC))

    attacker = SimpleNamespace(enemy_type=EnemyType.HUMAN, object_id="attacker-1")
    assert grant_vengeful_hatred_revenge(hero, attacker, rounds=2)
    assert vengeful_hatred_damage_bonus(hero, attacker, weapon_dice=2) == 2

    tick_vengeful_hatred_rounds(hero)
    assert vengeful_hatred_damage_bonus(hero, attacker, weapon_dice=1) == 1
    tick_vengeful_hatred_rounds(hero)
    assert vengeful_hatred_damage_bonus(hero, attacker, weapon_dice=1) == 0
