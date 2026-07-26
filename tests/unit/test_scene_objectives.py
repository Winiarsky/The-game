from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    InitiativeEntry,
    InitiativeOrder,
    CombatStatus,
    SceneConclusionType,
    SceneObjective,
    SceneObjectiveCondition,
    SceneObjectiveStatus,
    SceneObject,
    complete_interaction_objective,
    conclude_scene,
    objective_status_after_combat,
    objective_status_after_flags,
    set_scene_flag,
    SceneFlags,
    scene_is_finished,
    scene_result,
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


def test_flag_equals_objective_completes_after_matching_scene_flag():
    objective = SceneObjective(
        "secure",
        "Zabezpiecz",
        "",
        SceneObjectiveCondition.FLAG_EQUALS,
        flag_key="crate_secured",
        flag_value=True,
    )
    flags = set_scene_flag(SceneFlags(), "crate_secured", True)

    updated = objective_status_after_flags((objective,), flags)

    assert updated[0].status == SceneObjectiveStatus.COMPLETED


def test_flag_equals_objective_waits_for_matching_flag_value():
    objective = SceneObjective(
        "secure",
        "Zabezpiecz",
        "",
        SceneObjectiveCondition.FLAG_EQUALS,
        flag_key="crate_secured",
        flag_value=True,
    )
    flags = set_scene_flag(SceneFlags(), "crate_secured", False)

    updated = objective_status_after_flags((objective,), flags)

    assert updated[0].status == SceneObjectiveStatus.ACTIVE


def test_completed_objective_can_finish_combat_while_enemies_remain() -> None:
    hero = _actor("hero", Faction.ALLY, 10)
    goblin = _actor("goblin", Faction.ENEMY, 10)
    state = start_combat((hero, goblin), _order(hero, goblin))
    objective = SceneObjective(
        "secure",
        "Zabezpiecz",
        "",
        SceneObjectiveCondition.INTERACT_WITH_OBJECT,
        status=SceneObjectiveStatus.COMPLETED,
        target_id="crate",
    )

    finished_state, result = conclude_scene(
        state,
        conclusion=SceneConclusionType.OBJECTIVE_COMPLETED,
        objectives=(objective,),
    )

    assert finished_state.status == CombatStatus.FINISHED
    assert finished_state.winner == Faction.ALLY
    assert result.conclusion == SceneConclusionType.OBJECTIVE_COMPLETED
    assert result.completed_objectives == ("secure",)


def test_party_retreat_finishes_combat_without_declaring_a_winner() -> None:
    hero = _actor("hero", Faction.ALLY, 10)
    goblin = _actor("goblin", Faction.ENEMY, 10)
    state = start_combat((hero, goblin), _order(hero, goblin))

    finished_state, result = conclude_scene(
        state,
        conclusion=SceneConclusionType.RETREAT,
    )

    assert finished_state.status == CombatStatus.FINISHED
    assert finished_state.winner is None
    assert result.conclusion == SceneConclusionType.RETREAT


def test_party_surrender_finishes_combat_with_enemy_winner() -> None:
    hero = _actor("hero", Faction.ALLY, 10)
    goblin = _actor("goblin", Faction.ENEMY, 10)
    state = start_combat((hero, goblin), _order(hero, goblin))

    finished_state, result = conclude_scene(
        state,
        conclusion=SceneConclusionType.SURRENDER,
    )

    assert finished_state.winner == Faction.ENEMY
    assert result.conclusion == SceneConclusionType.SURRENDER
    assert scene_result(finished_state, ()).conclusion == SceneConclusionType.DEFEAT
