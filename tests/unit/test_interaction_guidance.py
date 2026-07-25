from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import (
    interaction_goal,
    effective_narrative_style,
    match_npc_key_issue,
    matched_method_rules,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _watchtower():
    return build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )


def test_watchtower_exposes_hybrid_goals_for_gate_and_scout():
    exploration = _watchtower()
    gate = next(item for item in exploration.challenges if item.id == "closed_gate")
    scout = next(item for item in exploration.points if item.id == "wounded_scout")

    assert [goal.id for goal in gate.goals] == [
        "force_entry",
        "use_wall_route",
        "open_lock",
        "look_around",
        "remove_bolt",
    ]
    assert {goal.id: goal.resolution_option_id for goal in gate.goals} == {
        "force_entry": "force_gate",
        "use_wall_route": "find_way_around",
        "open_lock": "lockpick_gate",
        "look_around": None,
        "remove_bolt": "remove_gate_bolt",
    }
    assert scout.npc_interaction is not None
    assert [goal.id for goal in scout.npc_interaction.goals][-1] == "custom_scout"


def test_every_gate_goal_has_a_distinct_tile_image():
    exploration = _watchtower()
    gate = next(item for item in exploration.challenges if item.id == "closed_gate")

    images = [goal.image for goal in gate.goals]

    assert all(images)
    assert len(set(images)) == len(images)


def test_quiet_method_rule_is_grounded_in_player_wording():
    exploration = _watchtower()
    gate = next(item for item in exploration.challenges if item.id == "closed_gate")

    rules = matched_method_rules(
        gate,
        "Zakładamy linę i przechodzimy po cichu.",
        "force_entry",
    )

    assert [rule.id for rule in rules] == ["quiet_tradeoff"]
    assert rules[0].modifier == -1
    assert rules[0].noise_delta == -1
    assert rules[0].success_noise_override == 0


def test_scout_reports_issue_triggers_once_for_grounded_promise():
    exploration = _watchtower()
    scout = next(item for item in exploration.points if item.id == "wounded_scout")
    assert scout.npc_interaction is not None

    matched = match_npc_key_issue(
        scout.npc_interaction,
        "Daję słowo, że dostarczymy meldunki.",
        SceneFlags(),
        "calm_scout",
    )

    assert matched is not None
    assert matched.issue.id == "reports_must_survive"

    consumed_flags = set_scene_flag(SceneFlags(), "scout_trusts_party", True)
    assert (
        match_npc_key_issue(
            scout.npc_interaction,
            "Dostarczymy meldunki.",
            consumed_flags,
            "calm_scout",
        )
        is None
    )


def test_unknown_or_unavailable_goal_is_not_resolved():
    exploration = _watchtower()
    gate = next(item for item in exploration.challenges if item.id == "closed_gate")

    assert interaction_goal(gate.goals, "nie_ma", SceneFlags()) is None


def test_goal_narrative_style_overrides_heroic_instance_profile():
    exploration = _watchtower()
    gate = next(item for item in exploration.challenges if item.id == "closed_gate")
    force = interaction_goal(gate.goals, "force_entry", SceneFlags())
    inspect = interaction_goal(gate.goals, "look_around", SceneFlags())

    assert force is not None
    assert inspect is not None
    assert gate.narrative_style.preset == "heroic_dnd"
    assert effective_narrative_style(gate.narrative_style, force).preset == "heroic_charge"
    serious = effective_narrative_style(gate.narrative_style, inspect)
    assert serious.preset == "tense_discovery"
    assert serious.humor_level == "none"
    assert serious.irony_level == "none"


def test_gate_goals_follow_lock_and_discovery_flags():
    exploration = _watchtower()
    gate = next(item for item in exploration.challenges if item.id == "closed_gate")

    initial_ids = {
        goal.id
        for goal in gate.goals
        if interaction_goal(gate.goals, goal.id, SceneFlags()) is not None
    }
    assert "open_lock" in initial_ids
    assert "remove_bolt" not in initial_ids
    assert "use_wall_route" not in initial_ids

    flags = set_scene_flag(SceneFlags(), "gate_lock_cleared", True)
    assert interaction_goal(gate.goals, "open_lock", flags) is None
    bolt = interaction_goal(gate.goals, "remove_bolt", flags)
    assert bolt is not None
    assert bolt.image == "assets/gate_bolt.webp"
    assert bolt.source_actions[0].source_ref == "gate_rotten_planks"
    assert bolt.source_actions[0].option_id == "pry_bolt_with_plank"

    flags = set_scene_flag(flags, "gate_wall_route_found", True)
    assert interaction_goal(gate.goals, "use_wall_route", flags) is not None


def test_scout_information_goal_uses_serious_revelation_profile():
    exploration = _watchtower()
    scout = next(item for item in exploration.points if item.id == "wounded_scout")
    assert scout.npc_interaction is not None
    goal = interaction_goal(
        scout.npc_interaction.goals,
        "ask_scout",
        SceneFlags(),
    )

    style = effective_narrative_style(scout.npc_interaction.narrative_style, goal)

    assert style.preset == "serious_revelation"
    assert style.humor_level == "none"
