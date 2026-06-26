from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    InitiativeEntry,
    InitiativeOrder,
    SceneObjective,
    SceneObjectiveCondition,
    SceneObjectiveStatus,
    SceneObject,
    complete_interaction_objective,
    objective_status_after_combat,
    scene_is_finished,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction, hp: int) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0 if faction == Faction.ALLY else 1, 0),
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _order(*actors: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    return InitiativeOrder(
        tuple(InitiativeEntry(actor, resolve_d20_roll(D20RollInput(request, 20 - index)), 2, index) for index, actor in enumerate(actors))
    )


def test_defeat_all_enemies_objective_completes_after_enemies_are_defeated():
    hero = _actor("hero", Faction.ALLY, 10)
    goblin = _actor("goblin", Faction.ENEMY, 10)
    state = start_combat((hero, goblin), _order(hero, goblin))
    state = replace(state, actors=(hero, replace(goblin, hp=0)))
    objective = SceneObjective("defeat", "Pokonaj przeciwników", "", SceneObjectiveCondition.DEFEAT_ALL_ENEMIES)

    updated = objective_status_after_combat(state, (objective,))

    assert updated[0].status == SceneObjectiveStatus.COMPLETED
    assert scene_is_finished(state, updated) is True


def test_interact_with_object_objective_completes_after_confirmed_interaction():
    objective = SceneObjective("secure", "Zabezpiecz", "", SceneObjectiveCondition.INTERACT_WITH_OBJECT, target_id="crate")
    scene_object = SceneObject("crate", "Skrzynia", (Coordinate(1, 0),), "Zabezpiecz", objective_id="secure")

    updated = complete_interaction_objective((objective,), scene_object)

    assert updated[0].status == SceneObjectiveStatus.COMPLETED


def test_active_objective_does_not_finish_scene_by_itself():
    hero = _actor("hero", Faction.ALLY, 10)
    goblin = _actor("goblin", Faction.ENEMY, 10)
    state = start_combat((hero, goblin), _order(hero, goblin))
    objective = SceneObjective("secure", "Zabezpiecz", "", SceneObjectiveCondition.INTERACT_WITH_OBJECT, target_id="crate")

    assert scene_is_finished(state, (objective,)) is False
