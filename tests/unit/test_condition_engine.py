from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    add_condition,
    apply_condition,
    attack_source_with_prone,
    condition_roll_request,
    effective_movement_speed,
    expire_condition_states,
    resolve_condition_save,
)
from dnd_board_game.rules import (
    D20RollRequest,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    RollMode,
)
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, position: Coordinate = Coordinate(0, 0)) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=Faction.ALLY if actor_id == "hero" else Faction.ENEMY,
        ability_scores=AbilityScores(dexterity=14, constitution=12),
    )


def _attack_source() -> AttackSource:
    return AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
    )


def test_poisoned_disadvantages_attacks_and_ability_checks() -> None:
    hero = _actor("hero")
    enemy = _actor("enemy", Coordinate(1, 0))
    states = (ConditionState("hero", CombatCondition.POISONED),)

    source = attack_source_with_prone(_attack_source(), states, hero, enemy)
    check = condition_roll_request(
        D20RollRequest(),
        states,
        hero,
        ability_check=True,
    )

    assert source.attack_roll_request.mode == RollMode.DISADVANTAGE
    assert check.mode == RollMode.DISADVANTAGE
    assert any("Zatruty" in modifier.label for modifier in check.modifiers)


def test_restrained_blocks_speed_and_changes_attacks_and_dexterity_saves() -> None:
    hero = _actor("hero")
    enemy = _actor("enemy", Coordinate(1, 0))
    states = (ConditionState("enemy", CombatCondition.RESTRAINED),)

    source = attack_source_with_prone(_attack_source(), states, hero, enemy)
    save = condition_roll_request(
        D20RollRequest(),
        states,
        enemy,
        saving_throw_ability="dexterity",
    )

    assert effective_movement_speed(enemy, states) == 0
    assert source.attack_roll_request.mode == RollMode.ADVANTAGE
    assert save.mode == RollMode.DISADVANTAGE


def test_advantage_against_restrained_target_cancels_poisoned_attacker_disadvantage() -> None:
    hero = _actor("hero")
    enemy = _actor("enemy", Coordinate(1, 0))
    states = (
        ConditionState("hero", CombatCondition.POISONED),
        ConditionState("enemy", CombatCondition.RESTRAINED),
    )

    source = attack_source_with_prone(_attack_source(), states, hero, enemy)

    assert source.attack_roll_request.mode == RollMode.NORMAL


def test_condition_immunity_rejects_application_without_mutating_state() -> None:
    guardian = replace(_actor("enemy"), condition_immunities=("poisoned",))

    result = apply_condition((), guardian, CombatCondition.POISONED)

    assert result.applied is False
    assert result.condition_states == ()
    assert "odporność" in result.message


def test_condition_save_uses_condition_roll_mode_and_removes_on_success() -> None:
    hero = _actor("hero")
    restrained = ConditionState(
        "hero",
        CombatCondition.RESTRAINED,
        source_label="Lepka ciecz",
        save_ability="dexterity",
        save_dc=12,
        save_timing=ConditionSaveTiming.TURN_END,
    )

    failed = resolve_condition_save(
        (restrained,),
        hero,
        restrained,
        natural_roll=18,
        natural_roll_2=2,
    )
    succeeded = resolve_condition_save(
        (restrained,),
        hero,
        restrained,
        natural_roll=18,
        natural_roll_2=15,
    )

    assert failed.saving_throw.natural_roll == 2
    assert failed.removed is False
    assert succeeded.removed is True
    assert succeeded.condition_states == ()


def test_condition_duration_expires_on_matching_turn_boundary() -> None:
    condition = ConditionState(
        "hero",
        CombatCondition.POISONED,
        duration=EffectDuration.UNTIL_TURN_END,
        expiration_actor_id="hero",
    )

    unchanged, early = expire_condition_states(
        (condition,),
        EffectEvent(EffectEventType.TURN_END, actor_id="enemy"),
    )
    remaining, expired = expire_condition_states(
        unchanged,
        EffectEvent(EffectEventType.TURN_END, actor_id="hero"),
    )

    assert early == ()
    assert remaining == ()
    assert expired == (condition,)


def test_reapplying_condition_refreshes_its_save_contract() -> None:
    original = ConditionState(
        "hero",
        CombatCondition.POISONED,
        source_actor_id="enemy",
        save_ability="constitution",
        save_dc=10,
        save_timing=ConditionSaveTiming.TURN_END,
    )

    updated = add_condition(
        (original,),
        "hero",
        CombatCondition.POISONED,
        source_actor_id="enemy",
        source_label="Silniejsza trucizna",
        save_ability="constitution",
        save_dc=15,
        save_timing=ConditionSaveTiming.TURN_END,
    )

    assert len(updated) == 1
    assert updated[0].source_label == "Silniejsza trucizna"
    assert updated[0].save_dc == 15
