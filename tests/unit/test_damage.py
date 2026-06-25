import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import DamageComponentInput, DamageType, apply_damage, resolve_damage
from dnd_board_game.world import Coordinate


def _actor(hp: int = 10, temp_hp: int = 0) -> Actor:
    return Actor(
        id=ActorId("goblin"),
        name="Goblin",
        ac=13,
        hp=hp,
        temp_hp=temp_hp,
        speed_feet=30,
        position=Coordinate(1, 0),
        faction=Faction.ENEMY,
    )


def test_damage_reduces_hp_and_sums_components():
    damage = resolve_damage(
        (
            DamageComponentInput(4, DamageType.SLASHING, "Miecz"),
            DamageComponentInput(2, DamageType.FIRE, "Ogień"),
        )
    )

    damaged = apply_damage(_actor(hp=10), damage)

    assert damage.total_before_reduction == 6
    assert damaged.hp == 4


def test_temp_hp_absorbs_damage_before_hp_and_hp_does_not_go_below_zero():
    damage = resolve_damage((DamageComponentInput(12, DamageType.SLASHING),))

    damaged = apply_damage(_actor(hp=5, temp_hp=3), damage)

    assert damaged.temp_hp == 0
    assert damaged.hp == 0
    assert damaged.is_defeated() is True


def test_damage_amount_cannot_be_negative():
    with pytest.raises(ValueError):
        DamageComponentInput(-1, DamageType.CUSTOM)
