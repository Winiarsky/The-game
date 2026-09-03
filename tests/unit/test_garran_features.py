from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    RecoveryPeriod,
)
from dnd_board_game.combat import (
    ActionUse,
    CombatCondition,
    InitiativeEntry,
    InitiativeOrder,
    combat_armor_class,
    effective_movement_speed,
    redirect_guarded_single_target,
    resolve_action_surge,
    resolve_garran_command_halt,
    resolve_garran_defensive_stance,
    resolve_garran_guard_companion,
    resolve_garran_rally,
    resolve_garran_shield_wall,
    resolve_actor_saving_throw,
    resolve_shield_bash,
    start_combat,
    synchronize_garran_effects,
    use_turn_action,
)
from dnd_board_game.combat.conditions import ConditionState
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectEvent,
    EffectEventType,
    SavingThrowRequest,
    expire_active_effects,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, Coordinate


def _actor(
    actor_id: str,
    position: Coordinate,
    *,
    faction: Faction = Faction.ALLY,
    features: tuple[str, ...] = (),
    strength: int = 10,
    hp: int = 20,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=14,
        hp=hp,
        max_hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(strength=strength, wisdom=10),
        resource_pools=(
            ActorResourcePool(
                "tactics_uses",
                "Taktyka",
                4,
                4,
                RecoveryPeriod.LONG_REST,
            ),
        ) if actor_id == "garran" else (),
        features=tuple(
            FeatureGrant(item, item, FeatureSourceKind.SCENARIO, "test")
            for item in features
        ),
        uses_death_saves=faction == Faction.ALLY,
    )


def _state(*actors: Actor):
    request = D20RollRequest()
    entries = tuple(
        InitiativeEntry(
            actor,
            resolve_d20_roll(D20RollInput(request, 20 - index)),
            0,
            index,
        )
        for index, actor in enumerate(actors)
    )
    return start_combat(tuple(actors), InitiativeOrder(entries))


def test_defensive_stance_spends_whole_movement_and_grants_two_ac() -> None:
    garran = _actor(
        "garran",
        Coordinate(1, 1),
        features=("defensive_stance",),
        strength=18,
    )
    state = _state(garran, _actor("enemy", Coordinate(3, 1), faction=Faction.ENEMY))

    result = resolve_garran_defensive_stance(state, ())

    assert result.state.turn_action.movement_action_used is True
    assert result.state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert combat_armor_class(garran, result.active_effects) == combat_armor_class(garran) + 2
    moved = expire_active_effects(
        result.active_effects,
        EffectEvent(
            EffectEventType.ACTOR_MOVED,
            actor_id="garran",
            position=Coordinate(2, 1),
        ),
    )
    assert moved.active_effects == ()


def test_shield_bash_tie_deals_nothing_and_win_deals_damage_even_if_push_blocked() -> None:
    board = BoardState()
    garran = _actor("garran", Coordinate(1, 1), features=("shield_bash",), strength=18)
    enemy = _actor("enemy", Coordinate(2, 1), faction=Faction.ENEMY, strength=18)
    blocker = _actor("blocker", Coordinate(3, 1), faction=Faction.ENEMY)

    tied = resolve_shield_bash(
        _state(garran, enemy, blocker),
        board=board,
        target_id="enemy",
        attacker_roll=10,
        defender_roll=10,
        damage_roll=4,
    )
    won = resolve_shield_bash(
        _state(garran, enemy, blocker),
        board=board,
        target_id="enemy",
        attacker_roll=20,
        defender_roll=1,
        damage_roll=4,
    )

    assert tied.succeeded is False and tied.target_after.hp == enemy.hp
    assert won.succeeded is True
    assert won.target_after.hp == enemy.hp - 8
    assert won.push_destination is None
    assert won.target_after.position == enemy.position
    assert dict(won.state.damage_received_by_actor)["enemy"] == 8


def test_command_halt_handles_critical_failure_and_critical_success() -> None:
    garran = _actor(
        "garran",
        Coordinate(1, 1),
        features=("garran_command_halt",),
        strength=18,
    )
    enemy = _actor("enemy", Coordinate(5, 1), faction=Faction.ENEMY)

    failed = resolve_garran_command_halt(
        _state(garran, enemy), (), target_id="enemy", natural_roll=1
    )
    critical = resolve_garran_command_halt(
        _state(garran, enemy), (), target_id="enemy", natural_roll=20
    )

    assert failed.outcome == "critical_failure"
    assert effective_movement_speed(enemy, (), failed.active_effects) == 0
    assert {effect.kind for effect in failed.active_effects} >= {
        "garran_command_no_movement",
        "garran_command_attack_penalty",
    }
    assert critical.outcome == "critical_success"
    assert critical.active_effects == ()


def test_shield_wall_tracks_adjacency_and_does_not_buff_garran() -> None:
    garran = _actor(
        "garran",
        Coordinate(1, 1),
        features=("garran_shield_wall",),
        strength=18,
    )
    ally = _actor("ally", Coordinate(2, 1))
    state = _state(garran, ally, _actor("enemy", Coordinate(5, 1), faction=Faction.ENEMY))

    result = resolve_garran_shield_wall(state, ())
    assert combat_armor_class(ally, result.active_effects) == combat_armor_class(ally) + 2
    assert combat_armor_class(garran, result.active_effects) == combat_armor_class(garran)

    moved = replace(ally, position=Coordinate(4, 1))
    synchronized = synchronize_garran_effects(
        (garran, moved, state.actors[2]), result.active_effects
    )
    assert combat_armor_class(moved, synchronized) == combat_armor_class(moved)


def test_rally_ignores_deafened_ally_and_guard_redirects_once() -> None:
    garran = _actor(
        "garran",
        Coordinate(1, 1),
        features=("garran_rally", "garran_guard_companion"),
        strength=18,
    )
    ally = _actor("ally", Coordinate(2, 1))
    deaf = _actor("deaf", Coordinate(1, 2))
    enemy = _actor("enemy", Coordinate(5, 1), faction=Faction.ENEMY)
    state = replace(
        _state(garran, ally, deaf, enemy),
        condition_states=(
            ConditionState("ally", CombatCondition.FRIGHTENED),
            ConditionState("deaf", CombatCondition.FRIGHTENED),
            ConditionState("deaf", CombatCondition.DEAFENED),
        ),
    )

    rally = resolve_garran_rally(state, ())
    assert not any(
        item.actor_id == "ally" and item.condition == CombatCondition.FRIGHTENED
        for item in rally.state.condition_states
    )
    assert any(
        item.actor_id == "deaf" and item.condition == CombatCondition.FRIGHTENED
        for item in rally.state.condition_states
    )
    assert {effect.actor_id for effect in rally.active_effects} == {"garran", "ally"}
    ally_save = resolve_actor_saving_throw(
        ally,
        SavingThrowRequest(ability="wisdom", dc=12, source_label="test"),
        natural_roll=3,
        natural_roll_2=17,
        active_effects=rally.active_effects,
    )
    assert ally_save.natural_roll == 17

    fresh = _state(garran, ally, enemy)
    guard = resolve_garran_guard_companion(
        fresh, (), target_id="ally"
    )
    redirected = redirect_guarded_single_target(
        guard.state, guard.active_effects, "ally"
    )
    second = redirect_guarded_single_target(
        guard.state, redirected.active_effects, "ally"
    )
    assert redirected.redirected is True and str(redirected.target.id) == "garran"
    assert second.redirected is False and str(second.target.id) == "ally"


def test_movement_technique_cannot_be_used_after_voluntary_movement() -> None:
    garran = _actor("garran", Coordinate(1, 1), features=("defensive_stance",))
    base = _state(garran, _actor("enemy", Coordinate(3, 1), faction=Faction.ENEMY))
    state = replace(base, turn_action=replace(base.turn_action, movement_used_feet=5))

    with pytest.raises(ValueError, match="przed dobrowolnym ruchem"):
        resolve_garran_defensive_stance(state, ())


def test_action_surge_requires_a_free_bonus_action() -> None:
    garran = _actor("garran", Coordinate(1, 1), features=("action_surge",))
    garran = replace(
        garran,
        resource_pools=(
            *garran.resource_pools,
            ActorResourcePool(
                "action_surge_uses",
                "Zryw akcji",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    base = _state(garran, _actor("enemy", Coordinate(3, 1), faction=Faction.ENEMY))
    after_action = use_turn_action(base).state
    no_bonus = replace(
        after_action,
        turn_action=replace(
            after_action.turn_action,
            bonus_action_use=ActionUse.ACTION_USED,
        ),
    )

    with pytest.raises(ValueError, match="bonus"):
        resolve_action_surge(no_bonus)
