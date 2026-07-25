from dnd_board_game.application import ExplorationInteractionFlowService
from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import (
    ExplorationFlowRouteKind,
    exploration_flow_for_challenge,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _watchtower():
    return build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )


def test_gate_flow_derives_parallel_active_nodes_and_initial_goals():
    exploration = _watchtower()
    flow = exploration_flow_for_challenge(exploration.flows, "closed_gate")

    assert flow is not None
    assert {node.id for node in flow.active_nodes(SceneFlags())} == {
        "gate_blocked",
        "lock_closed",
    }
    assert flow.available_goal_ids(SceneFlags()) == (
        "force_entry",
        "open_lock",
        "look_around",
    )


def test_gate_flow_reacts_to_lock_route_and_completion_flags():
    exploration = _watchtower()
    flow = exploration_flow_for_challenge(exploration.flows, "closed_gate")
    assert flow is not None

    flags = set_scene_flag(SceneFlags(), "gate_lock_cleared", True)
    flags = set_scene_flag(flags, "gate_wall_route_found", True)

    assert {node.id for node in flow.active_nodes(flags)} == {
        "gate_blocked",
        "bolt_exposed",
        "wall_route_known",
    }
    assert set(flow.available_goal_ids(flags)) == {
        "force_entry",
        "look_around",
        "remove_bolt",
        "use_wall_route",
    }

    completed = set_scene_flag(flags, "gate_passed", True)
    assert [node.id for node in flow.active_nodes(completed)] == ["gate_passed"]
    assert flow.available_transitions(completed) == ()


def test_gate_flow_routes_mechanics_observations_and_authored_sources():
    exploration = _watchtower()
    challenge = next(
        challenge
        for challenge in exploration.challenges
        if challenge.id == "closed_gate"
    )
    service = ExplorationInteractionFlowService()

    look = service.route_for_goal(
        challenge=challenge,
        flows=exploration.flows,
        goal_id="look_around",
        flags=SceneFlags(),
    )
    assert look is not None
    assert look.route_kind == ExplorationFlowRouteKind.OBSERVATION_ROUTER
    assert look.default_observation_id == "survey_gate_surroundings"
    assert "look_through_gate_gap" in look.observation_ids

    flags = set_scene_flag(SceneFlags(), "gate_lock_cleared", True)
    bolt = service.route_for_goal(
        challenge=challenge,
        flows=exploration.flows,
        goal_id="remove_bolt",
        flags=flags,
    )
    assert bolt is not None
    assert bolt.resolution_option_id == "remove_gate_bolt"
    assert [action.id for action in bolt.source_actions] == [
        "pry_bolt_with_plank"
    ]


def test_gate_flow_rejects_a_goal_whose_node_is_inactive():
    exploration = _watchtower()
    challenge = next(
        challenge
        for challenge in exploration.challenges
        if challenge.id == "closed_gate"
    )
    service = ExplorationInteractionFlowService()

    assert (
        service.route_for_goal(
            challenge=challenge,
            flows=exploration.flows,
            goal_id="remove_bolt",
            flags=SceneFlags(),
        )
        is None
    )


def test_flow_service_resolves_only_currently_active_transition_ids():
    exploration = _watchtower()
    challenge = next(
        challenge
        for challenge in exploration.challenges
        if challenge.id == "closed_gate"
    )
    service = ExplorationInteractionFlowService()

    active = service.available_routes(
        challenge=challenge,
        flows=exploration.flows,
        flags=SceneFlags(),
    )

    assert {route.transition.id for route in active if route.transition} == {
        "force_gate",
        "open_gate_lock",
        "survey_gate",
    }
    assert service.route_for_transition(
        challenge=challenge,
        flows=exploration.flows,
        transition_id="force_gate",
        flags=SceneFlags(),
    ).goal.id == "force_entry"
    assert service.route_for_transition(
        challenge=challenge,
        flows=exploration.flows,
        transition_id="remove_gate_bolt",
        flags=SceneFlags(),
    ) is None
