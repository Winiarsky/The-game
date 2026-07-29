from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    DamageComponentInput,
    DamageType,
    apply_damage_result,
    resolve_actor_saving_throw,
    resolve_condition_save,
    resolve_damage,
)
from dnd_board_game.rules import (
    EffectDuration,
    SaveDamageOnSuccess,
    SavingThrowRequest,
)
from dnd_board_game.world import Coordinate


def _actor() -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=12,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(constitution=10),
    )


def _effect() -> ActiveCombatEffect:
    return ActiveCombatEffect(
        id="protection:hero",
        actor_id="hero",
        kind="protection_from_poison",
        label="Ochrona przed trucizną",
        object_id="spell:protection_from_poison",
        value=0,
        source_actor_id="cleric",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )


def test_protection_from_poison_grants_poison_damage_resistance() -> None:
    applied = apply_damage_result(
        _actor(),
        resolve_damage((DamageComponentInput(9, DamageType.POISON),)),
        active_effects=(_effect(),),
    )

    assert applied.damage.total_before_reduction == 9
    assert applied.damage.total_applied == 4
    assert applied.hp_after == 16


def test_protection_from_poison_grants_advantage_on_poison_saving_throw() -> None:
    request = SavingThrowRequest(
        ability="constitution",
        dc=12,
        source_label="Trujący obłok",
        dc_source_label="ST trucizny",
        damage_on_success=SaveDamageOnSuccess.NONE,
        effect_tags=("poison",),
    )

    result = resolve_actor_saving_throw(
        _actor(),
        request,
        natural_roll=4,
        natural_roll_2=17,
        active_effects=(_effect(),),
    )

    assert result.natural_roll == 17
    assert result.success is True


def test_protection_from_poison_grants_advantage_to_end_poisoned_condition() -> None:
    actor = _actor()
    condition = ConditionState(
        "hero",
        CombatCondition.POISONED,
        source_actor_id="enemy",
        source_label="Trucizna",
        save_ability="constitution",
        save_dc=12,
        save_timing=ConditionSaveTiming.TURN_END,
    )

    result = resolve_condition_save(
        (condition,),
        actor,
        condition,
        natural_roll=3,
        natural_roll_2=15,
        active_effects=(_effect(),),
    )

    assert result.saving_throw.natural_roll == 15
    assert result.removed is True
