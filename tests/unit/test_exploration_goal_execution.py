import pytest

from dnd_board_game.application import ExplorationGoalExecutionPlanner
from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import (
    CheckParticipants,
    ExplorationState,
    build_crafting_source_registry,
    match_visible_scene_sources,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _watchtower():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )
    challenge = next(
        challenge
        for challenge in exploration.challenges
        if challenge.id == "closed_gate"
    )
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    return exploration, challenge, state


def test_planner_resolves_force_gate_as_authored_whole_party_check():
    exploration, challenge, state = _watchtower()
    planner = ExplorationGoalExecutionPlanner()

    plan = planner.plan(
        challenge=challenge,
        flows=exploration.flows,
        flags=state.flags,
        actors=exploration.actors,
        goal_id="force_entry",
        requested_check_participants=None,
        requested_actor_ids=(),
    )

    assert plan.route.transition.id == "force_gate"
    assert plan.route.resolution_option_id == "force_gate"
    assert plan.check_participants == CheckParticipants.WHOLE_PARTY
    assert plan.participant_actor_ids == ("hero", "rogue", "cleric")


def test_planner_rejects_goal_whose_graph_node_is_not_active():
    exploration, challenge, state = _watchtower()
    planner = ExplorationGoalExecutionPlanner()

    with pytest.raises(ValueError, match="nie jest dostępny"):
        planner.plan(
            challenge=challenge,
            flows=exploration.flows,
            flags=state.flags,
            actors=exploration.actors,
            goal_id="remove_bolt",
            requested_check_participants="single_actor",
            requested_actor_ids=("hero",),
        )


def test_planner_enforces_authored_tool_eligibility():
    exploration, challenge, state = _watchtower()
    planner = ExplorationGoalExecutionPlanner()

    with pytest.raises(ValueError, match="nie spełniają wymagań"):
        planner.plan(
            challenge=challenge,
            flows=exploration.flows,
            flags=state.flags,
            actors=exploration.actors,
            goal_id="open_lock",
            requested_check_participants="single_actor",
            requested_actor_ids=("hero",),
        )

    plan = planner.plan(
        challenge=challenge,
        flows=exploration.flows,
        flags=state.flags,
        actors=exploration.actors,
        goal_id="open_lock",
        requested_check_participants="single_actor",
        requested_actor_ids=("rogue",),
    )

    assert plan.participant_actor_ids == ("rogue",)


def test_planner_routes_authored_source_action_and_observation():
    exploration, challenge, state = _watchtower()
    planner = ExplorationGoalExecutionPlanner()
    flags = set_scene_flag(state.flags, "gate_lock_cleared", True)
    bolt = planner.plan(
        challenge=challenge,
        flows=exploration.flows,
        flags=flags,
        actors=exploration.actors,
        goal_id="remove_bolt",
        requested_check_participants="single_actor",
        requested_actor_ids=("hero",),
    )
    registry = build_crafting_source_registry(state, exploration.actors)
    source_matches = match_visible_scene_sources(
        registry,
        "Wciskam spróchniałą deskę przez szczelinę i podważam rygiel.",
    )

    source_execution = bolt.procedural_source_execution(
        challenge,
        source_matches,
        direct_source_use=True,
    )

    assert source_execution is not None
    assert source_execution.action.id == "pry_bolt_with_plank"
    assert source_execution.option.id == "pry_bolt_with_plank"

    survey = planner.plan(
        challenge=challenge,
        flows=exploration.flows,
        flags=state.flags,
        actors=exploration.actors,
        goal_id="look_around",
        requested_check_participants="single_actor",
        requested_actor_ids=("rogue",),
    )
    observation = survey.authored_observation(
        exploration.observations,
        "Szukam alternatywnej drogi przez mur obok bramy.",
        zone_id="gate",
        challenge_id="closed_gate",
    )

    assert observation is not None
    assert observation.id == "search_gate_alternate_route"
