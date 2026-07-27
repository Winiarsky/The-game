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


def _village_elder():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/village_square_mvp.json")
    )
    point = next(point for point in exploration.points if point.id == "elder_npc")
    assert point.npc_interaction is not None
    return exploration, point.npc_interaction


def _village_keeper():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/village_square_mvp.json")
    )
    point = next(point for point in exploration.points if point.id == "tavern_keeper")
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


def test_village_elder_flow_hides_negotiation_after_quest_hook_or_refusal():
    exploration, npc = _village_elder()
    planner = NpcGoalExecutionPlanner()

    initial = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=SceneFlags(),
    )
    informed = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=set_scene_flag(SceneFlags(), "quest_hook_found", True),
    )
    accepted = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=set_scene_flag(
            set_scene_flag(SceneFlags(), "quest_hook_found", True),
            "quest_accepted",
            True,
        ),
    )
    closed = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=set_scene_flag(SceneFlags(), "elder_refuses_party", True),
    )

    assert {goal.id for goal in initial} == {
        "ask_watchtower_problem",
        "negotiate_advance",
    }
    assert [goal.id for goal in informed] == [
        "ask_watchtower_problem",
        "accept_watchtower_quest",
    ]
    assert [goal.id for goal in accepted] == [
        "ask_watchtower_problem",
        "confirm_watchtower_departure",
    ]
    assert closed == ()


def test_village_elder_flow_locks_negotiation_to_social_intent():
    exploration, npc = _village_elder()

    plan = NpcGoalExecutionPlanner().plan(
        npc=npc,
        flows=exploration.flows,
        flags=SceneFlags(),
        actors=exploration.actors,
        goal_id="negotiate_advance",
        requested_check_participants="lead_with_help",
        requested_actor_ids=("rogue", "hero"),
    )

    assert plan.route.transition is not None
    assert plan.route.transition.id == "negotiate_bren_advance"
    assert plan.route.intent_id == "social"
    assert plan.check_participants == CheckParticipants.LEAD_WITH_HELP
    assert plan.participant_actor_ids == ("rogue", "hero")


def test_village_keeper_flow_hides_consumed_rumor_but_keeps_conversation():
    exploration, npc = _village_keeper()
    planner = NpcGoalExecutionPlanner()

    initial = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=SceneFlags(),
    )
    informed = planner.available_goals(
        npc=npc,
        flows=exploration.flows,
        flags=set_scene_flag(SceneFlags(), "tavern_rumor_heard", True),
    )

    assert {goal.id for goal in initial} == {
        "ask_watchtower_rumors",
        "chat_with_keeper",
    }
    assert [goal.id for goal in informed] == ["chat_with_keeper"]


def test_village_keeper_flow_locks_rumor_to_authored_information_route():
    exploration, npc = _village_keeper()

    plan = NpcGoalExecutionPlanner().plan(
        npc=npc,
        flows=exploration.flows,
        flags=SceneFlags(),
        actors=exploration.actors,
        goal_id="ask_watchtower_rumors",
        requested_check_participants="single_actor",
        requested_actor_ids=("rogue",),
    )

    assert plan.route.transition is not None
    assert plan.route.transition.id == "ask_olan_about_watchtower"
    assert plan.route.intent_id == "information"
    assert plan.check_participants == CheckParticipants.SINGLE_ACTOR
    assert plan.participant_actor_ids == ("rogue",)
    assert plan.permission.effects_on_success == (
        {
            "type": "set_flag",
            "parameters": {"key": "tavern_rumor_heard", "value": True},
        },
        {
            "type": "set_flag",
            "parameters": {"key": "quest_hook_found", "value": True},
        },
    )
