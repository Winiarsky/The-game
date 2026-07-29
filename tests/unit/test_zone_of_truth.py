from random import Random

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    actor_is_bound_to_truth,
    resolve_zone_of_truth_save,
    start_combat,
    zone_of_truth_contains,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(charisma=10),
        spell_save_dc=14,
    )


def _state(*actors: Actor) -> CombatState:
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)),
                0,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(actors, order)


def _zone() -> ActiveCombatEffect:
    return ActiveCombatEffect(
        id="truth-zone:cleric",
        actor_id="cleric",
        kind="zone_of_truth_zone",
        label="Strefa prawdy",
        object_id="combat_action:zone_of_truth",
        value=15,
        anchor_position=Coordinate(4, 4),
        source_actor_id="cleric",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )


def test_zone_of_truth_repeats_save_until_failure_then_tracks_known_result() -> None:
    cleric = _actor("cleric", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 4))
    state = _state(cleric, enemy)
    zone = _zone()

    assert zone_of_truth_contains(zone, enemy.position)
    success = resolve_zone_of_truth_save(
        state,
        (zone,),
        actor_id="enemy",
        zone=zone,
        rng=Random(5),
    )
    assert success.saving_throw is not None
    assert success.saving_throw.success is True
    assert success.bound is False
    failure = resolve_zone_of_truth_save(
        state,
        success.active_effects,
        actor_id="enemy",
        zone=zone,
        rng=Random(2),
    )
    assert failure.saving_throw is not None
    assert failure.saving_throw.success is False
    assert failure.bound is True
    assert actor_is_bound_to_truth("enemy", zone.id, failure.active_effects)
    no_repeat = resolve_zone_of_truth_save(
        state,
        failure.active_effects,
        actor_id="enemy",
        zone=zone,
        rng=Random(5),
    )
    assert no_repeat.saving_throw is None
    assert no_repeat.bound is True
