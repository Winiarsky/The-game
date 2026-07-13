from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import CombatSceneInteractionFlowService
from dnd_board_game.combat import (
    ActionUse,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    SceneInteraction,
    SceneInteractionCondition,
    SceneInteractionEffect,
    SceneObject,
    replace_actor,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    ac: int = 12,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=ac,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(),
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
    return start_combat(tuple(actors), order)


def _cart() -> SceneObject:
    return SceneObject(
        id="cart",
        name="Wóz",
        positions=(Coordinate(1, 0),),
        interaction_label="Użyj wozu",
        interactions=(
            SceneInteraction(
                id="take_cover",
                label="Otrzymaj osłonę",
                conditions=(
                    SceneInteractionCondition("action_available"),
                    SceneInteractionCondition("actor_adjacent_to_object"),
                ),
                effects=(
                    SceneInteractionEffect(
                        "grant_ac_bonus_until_move",
                        (("value", 2), ("label", "Osłona: wóz")),
                    ),
                ),
            ),
        ),
    )


def test_scene_interaction_selection_returns_pending_options_and_event() -> None:
    service = CombatSceneInteractionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 5))
    state = _state(hero, enemy)

    transition = service.select(
        state=state,
        scene_objects=(_cart(),),
        position=Coordinate(1, 0),
        active_effects=(),
    )

    assert transition.pending is not None
    assert transition.pending.object_id == "cart"
    assert [option.id for option in transition.pending.options] == ["take_cover"]
    assert transition.event_type == "ui_combat_interaction_selected"
    assert transition.clear_player_attack is True


def test_scene_interaction_confirmation_spends_action_and_applies_cover() -> None:
    service = CombatSceneInteractionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), ac=14)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 5))
    state = _state(hero, enemy)
    selected = service.select(
        state=state,
        scene_objects=(_cart(),),
        position=Coordinate(1, 0),
        active_effects=(),
    )
    assert selected.pending is not None

    confirmed = service.confirm(
        state=state,
        scene_objects=(_cart(),),
        active_effects=(),
        pending=selected.pending,
        interaction_id="take_cover",
        rng=Random(1),
    )

    protected = next(actor for actor in confirmed.state.actors if actor.id == hero.id)
    assert protected.ac == 16
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED
    assert confirmed.active_effects[0].kind == "grant_ac_bonus_until_move"
    assert confirmed.pending is None
    assert confirmed.event_type == "ui_combat_interaction_confirmed"


def test_invalid_position_effect_expiration_restores_actor_state() -> None:
    service = CombatSceneInteractionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), ac=14)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 5))
    state = _state(hero, enemy)
    selected = service.select(
        state=state,
        scene_objects=(_cart(),),
        position=Coordinate(1, 0),
        active_effects=(),
    )
    assert selected.pending is not None
    confirmed = service.confirm(
        state=state,
        scene_objects=(_cart(),),
        active_effects=(),
        pending=selected.pending,
        interaction_id="take_cover",
        rng=Random(1),
    )
    protected = next(actor for actor in confirmed.state.actors if actor.id == hero.id)
    moved_state = replace_actor(
        confirmed.state,
        replace(protected, position=Coordinate(0, 1)),
    )

    expired = service.expire_invalid_effects(
        state=moved_state,
        scene_objects=(_cart(),),
        active_effects=confirmed.active_effects,
    )

    restored = next(actor for actor in expired.state.actors if actor.id == hero.id)
    assert restored.ac == 14
    assert expired.active_effects == ()
    assert expired.expired_effects == confirmed.active_effects


def test_cancel_and_invalid_selection_preserve_combat_state() -> None:
    service = CombatSceneInteractionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 5))
    state = _state(hero, enemy)
    selected = service.select(
        state=state,
        scene_objects=(_cart(),),
        position=Coordinate(1, 0),
        active_effects=(),
    )
    assert selected.pending is not None

    cancelled = service.cancel(
        state=state,
        active_effects=(),
        pending=selected.pending,
    )

    assert cancelled.state is state
    assert cancelled.pending is None
    with pytest.raises(ValueError, match="dostępnej interakcji"):
        service.select(
            state=state,
            scene_objects=(_cart(),),
            position=Coordinate(4, 4),
            active_effects=(),
        )
