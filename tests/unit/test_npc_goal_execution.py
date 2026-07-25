import pytest

from dnd_board_game.application import NpcGoalExecutionPlanner
from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import CheckParticipants
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _watchtower_npc():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )
    point = next(
        point for point in exploration.points if point.id == "wounded_scout"
    )
    assert point.npc_interaction is not None
    return exploration, point.npc_interaction


def test_npc_flow_hides_information_goal_until_scout_trusts_party():
    exploration, npc = _watchtower_npc()
    planner = NpcGoalExecutionPlanner()

    initial = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=SceneFlags(),
    )
    trusted = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=set_scene_flag(SceneFlags(), "scout_trusts_party", True),
    )

    assert {goal.id for goal in initial} == {
        "calm_scout",
        "help_scout",
        "pressure_scout",
    }
    assert {goal.id for goal in trusted} == {
        "help_scout",
        "ask_scout",
        "pressure_scout",
    }


def test_npc_planner_locks_authored_intent_and_selected_participants():
    exploration, npc = _watchtower_npc()

    plan = NpcGoalExecutionPlanner().plan(
        npc=npc,
        flows=exploration.flows,
        flags=SceneFlags(),
        actors=exploration.actors,
        goal_id="calm_scout",
        requested_check_participants="lead_with_help",
        requested_actor_ids=("cleric", "hero"),
    )

    assert plan.route.transition is not None
    assert plan.route.transition.id == "calm_wounded_scout"
    assert plan.route.intent_id == "social"
    assert plan.check_participants == CheckParticipants.LEAD_WITH_HELP
    assert plan.participant_actor_ids == ("cleric", "hero")


def test_npc_planner_rejects_inactive_goal():
    exploration, npc = _watchtower_npc()

    with pytest.raises(ValueError, match="nie jest teraz dostępny"):
        NpcGoalExecutionPlanner().plan(
            npc=npc,
            flows=exploration.flows,
            flags=SceneFlags(),
            actors=exploration.actors,
            goal_id="ask_scout",
            requested_check_participants="single_actor",
            requested_actor_ids=("rogue",),
        )
