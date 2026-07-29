from dataclasses import replace
from random import Random

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    CombatCondition,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    has_condition,
    resolve_web_save,
    start_combat,
    web_zone_contains,
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
        ability_scores=AbilityScores(dexterity=10),
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
        id="web-zone:wizard",
        actor_id="wizard",
        kind="web_zone",
        label="Sieć",
        object_id="combat_action:web",
        value=20,
        anchor_position=Coordinate(4, 4),
        source_actor_id="wizard",
        duration=EffectDuration.CONCENTRATION,
        spell_level=2,
    )


def test_web_zone_is_twenty_foot_cube_and_failed_entry_save_restrains() -> None:
    wizard = _actor("wizard", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 4))
    zone = _zone()

    assert web_zone_contains(zone, Coordinate(3, 3))
    assert web_zone_contains(zone, Coordinate(6, 6))
    assert not web_zone_contains(zone, Coordinate(2, 3))
    resolution = resolve_web_save(
        _state(wizard, enemy),
        actor_id="enemy",
        zone=zone,
        rng=Random(2),
    )

    assert resolution.saving_throw is not None
    assert resolution.saving_throw.success is False
    assert resolution.restrained is True
    assert has_condition(
        resolution.state.condition_states,
        "enemy",
        CombatCondition.RESTRAINED,
    )
    condition = resolution.state.condition_states[0]
    assert condition.save_dc == 14
    assert condition.source_spell_id == "web"
