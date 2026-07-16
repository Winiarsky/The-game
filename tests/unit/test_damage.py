import pytest

from dataclasses import replace

from dnd_board_game.actors import Actor, ActorId, DamageAffinityProfile, DeathSaveState, Faction
from dnd_board_game.combat import (
    DamageAdjustment,
    DamageComponentInput,
    DamageType,
    apply_damage,
    apply_damage_result,
    resolve_damage,
)
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


@pytest.mark.parametrize(
    ("profile", "expected", "adjustment"),
    [
        (DamageAffinityProfile(resistances=(DamageType.FIRE,)), 4, DamageAdjustment.RESISTANCE),
        (DamageAffinityProfile(immunities=(DamageType.FIRE,)), 0, DamageAdjustment.IMMUNITY),
        (DamageAffinityProfile(vulnerabilities=(DamageType.FIRE,)), 18, DamageAdjustment.VULNERABILITY),
    ],
)
def test_damage_affinities_modify_each_damage_type(
    profile: DamageAffinityProfile,
    expected: int,
    adjustment: DamageAdjustment,
) -> None:
    actor = replace(_actor(hp=30), damage_affinities=profile)

    result = apply_damage_result(
        actor,
        resolve_damage((DamageComponentInput(9, DamageType.FIRE, "Płomień"),)),
    )

    assert result.damage.total_before_reduction == 9
    assert result.damage.total_applied == expected
    assert result.damage.resolved_components[0].adjustment == adjustment
    assert result.actor_after.hp == 30 - expected


def test_mixed_damage_applies_affinities_only_to_matching_components() -> None:
    actor = replace(
        _actor(hp=30),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.FIRE,)),
    )
    damage = resolve_damage(
        (
            DamageComponentInput(7, DamageType.SLASHING, "Miecz"),
            DamageComponentInput(5, DamageType.FIRE, "Płomień"),
        )
    )

    result = apply_damage_result(actor, damage)

    assert result.damage.total_before_reduction == 12
    assert result.damage.total_applied == 9
    assert [(part.damage_type, part.amount_applied) for part in result.damage.resolved_components] == [
        (DamageType.SLASHING, 7),
        (DamageType.FIRE, 2),
    ]


def test_same_type_components_are_combined_before_resistance_rounding() -> None:
    damage = resolve_damage(
        (
            DamageComponentInput(1, DamageType.FIRE, "Iskra"),
            DamageComponentInput(2, DamageType.FIRE, "Płomień"),
        ),
        DamageAffinityProfile(resistances=(DamageType.FIRE,)),
    )

    assert damage.total_before_reduction == 3
    assert damage.total_applied == 1
    assert len(damage.resolved_components) == 1


def test_immunity_takes_priority_over_other_affinities() -> None:
    profile = DamageAffinityProfile(
        resistances=(DamageType.COLD,),
        immunities=(DamageType.COLD,),
        vulnerabilities=(DamageType.COLD,),
    )

    damage = resolve_damage((DamageComponentInput(8, DamageType.COLD),), profile)

    assert damage.total_applied == 0
    assert damage.resolved_components[0].adjustment == DamageAdjustment.IMMUNITY


def _hero(hp: int = 10) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Hero",
        ac=15,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        max_hp=10,
        uses_death_saves=True,
    )


def test_damage_reducing_hero_to_zero_starts_death_saves() -> None:
    result = apply_damage_result(_hero(5), resolve_damage((DamageComponentInput(5, DamageType.SLASHING),)))

    assert result.actor_after.needs_death_save() is True
    assert result.actor_after.death_saves == DeathSaveState()
    assert result.instant_death is False


def test_massive_damage_causes_instant_death() -> None:
    result = apply_damage_result(_hero(5), resolve_damage((DamageComponentInput(15, DamageType.SLASHING),)))

    assert result.instant_death is True
    assert result.actor_after.is_dead() is True


def test_damage_at_zero_adds_one_failure_or_two_on_critical_hit() -> None:
    dying = replace(_hero(), hp=0)
    damage = resolve_damage((DamageComponentInput(1, DamageType.SLASHING),))

    normal = apply_damage_result(dying, damage)
    critical = apply_damage_result(dying, damage, critical=True)

    assert normal.actor_after.death_saves.failures == 1
    assert normal.death_save_failures_added == 1
    assert critical.actor_after.death_saves.failures == 2
    assert critical.death_save_failures_added == 2


def test_damage_breaks_stabilization_and_starts_with_one_failure() -> None:
    stable = replace(_hero(), hp=0, death_saves=DeathSaveState(stable=True))
    result = apply_damage_result(stable, resolve_damage((DamageComponentInput(1, DamageType.SLASHING),)))

    assert result.actor_after.death_saves == DeathSaveState(failures=1)
    assert result.actor_after.needs_death_save() is True
