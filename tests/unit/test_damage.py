import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import DamageComponentInput, DamageType, apply_damage, apply_damage_result, resolve_damage
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

    result = apply_damage_result(_actor(hp=5, temp_hp=3), damage)
    damaged = result.actor_after

    assert damaged.temp_hp == 0
    assert damaged.hp == 0
    assert damaged.is_defeated() is True
    assert result.hp_before == 5
    assert result.hp_after == 0
    assert result.temp_hp_before == 3
    assert result.temp_hp_after == 0
    assert result.absorbed_by_temp_hp == 3
    assert result.applied_to_hp == 5
    assert result.defeated is True
    assert result.defeated_by_damage is True


def test_damage_result_tracks_nonlethal_hp_change():
    damage = resolve_damage((DamageComponentInput(4, DamageType.PIERCING),))

    result = apply_damage_result(_actor(hp=10, temp_hp=2), damage)

    assert result.actor_after.hp == 8
    assert result.actor_after.temp_hp == 0
    assert result.hp_before == 10
    assert result.hp_after == 8
    assert result.absorbed_by_temp_hp == 2
    assert result.applied_to_hp == 2
    assert result.defeated is False
    assert result.defeated_by_damage is False


def test_damage_amount_cannot_be_negative():
    with pytest.raises(ValueError):
        DamageComponentInput(-1, DamageType.CUSTOM)
