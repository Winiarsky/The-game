from dataclasses import replace

import pytest

from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import ExplorationState, resolve_npc_runtime_interaction
from dnd_board_game.llm import NpcInteractionProposal, build_npc_interaction_request, validate_npc_interaction_proposal
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _request(*, selected_goal_id=None, selected_social_skill=None):
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    point = next(item for item in exploration.points if item.id == "wounded_scout")
    zone = next(item for item in exploration.zones if item.id == point.zone_id)
    return build_npc_interaction_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        zone=zone,
        point=point,
        state=state,
        player_action="Uspokajamy zwiadowcę.",
        selected_goal_id=selected_goal_id,
        selected_social_skill=selected_social_skill,
    )


def _village_request():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/village_square_mvp.json")
    )
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        merchants=exploration.merchants,
        clock_policy=exploration.clock_policy,
    )
    point = next(item for item in exploration.points if item.id == "elder_npc")
    zone = next(item for item in exploration.zones if item.id == point.zone_id)
    return build_npc_interaction_request(
        scenario_id=exploration.scenario_id,
        scenario_name=exploration.scenario_name,
        zone=zone,
        point=point,
        state=state,
        player_action="Pytamy Brena, co stało się przy strażnicy.",
        selected_goal_id="ask_watchtower_problem",
        routed_intent_id="information",
    )


def test_authored_npc_route_scopes_prompt_and_overrides_ungrounded_narration():
    request = _village_request()
    prompt = request.to_prompt_payload()

    assert [goal["id"] for goal in prompt["npc"]["goals"]] == [
        "ask_watchtower_problem"
    ]
    assert set(prompt["npc"]["policy"]["intent_permissions"]) == {"information"}
    assert prompt["grounding_contract"]["mode"] == "authored_variants"
    assert {
        variant["id"]
        for variant in prompt["grounding_contract"]["authored_response"]["variants"]
    } == {"map_and_warning", "plain_report"}
    assert "nagrod" not in " ".join(
        str(value)
        for value in prompt["npc"]["policy"]["intent_permissions"].values()
    ).lower()

    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "player_narration": "Bohater przekazuje Olanowi kilka monet.",
            "npc_response": (
                "Bren obiecuje sto sztuk złota i opowiada o niebieskim smoku."
            ),
            "success_message": "Drużyna otrzymuje nagrodę.",
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, request)

    assert validated.proposal.player_narration == (
        "Bren rozwija starą mapę i wskazuje opuszczoną strażnicę "
        "oraz prowadzący do niej trakt."
    )
    assert "gobliny" in validated.proposal.npc_response
    assert "sto sztuk złota" not in validated.proposal.npc_response
    assert "niebieskim smoku" not in validated.proposal.npc_response
    assert validated.proposal.success_message == (
        "Bren przekazuje drużynie sprawdzony trop o opuszczonej strażnicy."
    )
    assert validated.proposal.grounded_response_variant_id is None


def test_authored_npc_route_uses_only_selected_controlled_variant():
    request = _village_request()
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "grounded_response_variant_id": "plain_report",
            "player_narration": "Tekst wymyślony przez model.",
            "npc_response": "Bren obiecuje smoka i sto sztuk złota.",
            "success_message": "Nieautoryzowany sukces.",
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, request)

    assert validated.proposal.grounded_response_variant_id == "plain_report"
    assert validated.proposal.player_narration.startswith("Sołtys mówi bez ozdobników")
    assert validated.proposal.npc_response.startswith("Od kilku dni nikt stamtąd")
    assert "smoka" not in validated.proposal.npc_response
    assert validated.proposal.success_message == (
        "Bren podaje drużynie najpewniejsze informacje o zagrożeniu przy strażnicy."
    )


def test_authored_npc_route_falls_back_to_base_for_unknown_variant():
    request = _village_request()
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "grounded_response_variant_id": "invented_by_model",
            "npc_response": "Nieautoryzowany tekst.",
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, request)

    assert validated.proposal.grounded_response_variant_id is None
    assert validated.proposal.player_narration.startswith("Bren rozwija starą mapę")
    assert validated.proposal.npc_response.startswith("Od kilku dni nikt ze strażnicy")


def test_npc_interaction_accepts_allowed_success_effect():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_stabilized", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_trusts_party", "value": True}},
            ],
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.proposal.effects_on_success[0].type == "set_flag"
    assert validated.proposal.requires_roll is True
    assert validated.proposal.ability == "charisma"
    assert validated.proposal.skill == "persuasion"
    assert validated.proposal.dc == 10
    assert validated.social_plan is not None
    assert validated.attempt_plan is not None
    assert validated.attempt_plan.available is True
    assert validated.attempt_plan.attempt_id == "scout_build_trust"


def test_npc_interaction_requires_risk_for_social_reaction_intent():
    proposal = NpcInteractionProposal.model_validate(
        {"action_type": "social", "requires_roll": False}
    )

    with pytest.raises(ValueError, match="requires request_risk"):
        validate_npc_interaction_proposal(proposal, _request())


def test_player_selected_social_skill_overrides_llm_skill() -> None:
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "requires_roll": True,
            "ability": "charisma",
            "skill": "deception",
            "dc": 20,
        }
    )

    validated = validate_npc_interaction_proposal(
        proposal,
        _request(
            selected_goal_id="calm_scout",
            selected_social_skill="intimidation",
        ),
    )

    assert validated.proposal.ability == "charisma"
    assert validated.proposal.skill == "intimidation"
    assert validated.proposal.dc == 10
    assert validated.social_plan is not None
    assert (
        _request(selected_social_skill="persuasion")
        .to_prompt_payload()["selected_social_skill"]
        == "persuasion"
    )


def test_player_selected_social_skill_is_rejected_for_non_social_route() -> None:
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "requires_roll": True,
            "ability": "wisdom",
            "skill": "medicine",
            "dc": 12,
        }
    )

    with pytest.raises(ValueError, match="only be used by a social reaction"):
        validate_npc_interaction_proposal(
            proposal,
            _request(
                selected_goal_id="help_scout",
                selected_social_skill="persuasion",
            ),
        )


def test_npc_selected_goal_rejects_unrelated_intent():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "requires_roll": True,
            "ability": "wisdom",
            "skill": "medicine",
            "dc": 12,
        }
    )

    with pytest.raises(ValueError, match="does not match selected goal"):
        validate_npc_interaction_proposal(
            proposal,
            _request(selected_goal_id="calm_scout"),
        )


def test_npc_prompt_uses_goal_narrative_style_override():
    request = _request(selected_goal_id="ask_scout")

    style = request.to_prompt_payload()["effective_narrative_style"]

    assert style["preset"] == "serious_revelation"
    assert style["humor_level"] == "none"
    assert style["irony_level"] == "none"


def test_guarded_information_prompt_omits_locked_scenario_truth_and_key_issues():
    request = _request(selected_goal_id="ask_scout")
    flags = request.state.flags
    for key in ("scout_trusts_party", "scout_stabilized", "scout_calmed"):
        flags = set_scene_flag(flags, key, True)
    request = replace(
        request,
        state=replace(request.state, flags=flags),
        routed_intent_id="information",
    )

    prompt = request.to_prompt_payload()
    serialized = str(prompt["npc"]).casefold()

    assert prompt["npc"]["gm_context"] == ""
    assert prompt["npc"]["current_state"] == ""
    assert prompt["npc"]["key_issues"] == []
    assert {
        item["id"] for item in prompt["npc"]["locked_information"]
    } == {"tower_hint", "beast_hint", "hidden_cache_hint"}
    assert "przeklęty komendant" not in serialized
    assert "commander_curse_hint" not in serialized


def test_revealed_information_replaces_generated_spoilers_with_authored_facts():
    request = _request(selected_goal_id="ask_scout")
    flags = request.state.flags
    for key in ("scout_trusts_party", "scout_stabilized", "scout_calmed"):
        flags = set_scene_flag(flags, key, True)
    request = replace(
        request,
        state=replace(request.state, flags=flags),
        routed_intent_id="information",
    )
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "request_risk": "no_risk",
            "player_narration": "Na zbroi błyska znak dawnego komendanta.",
            "npc_response": (
                "Bestia jest przeklętym komendantem w starej zbroi."
            ),
            "requires_roll": True,
            "skill": "persuasion",
            "revealed_information_ids": ["tower_hint", "beast_hint"],
        }
    )

    validated = validate_npc_interaction_proposal(proposal, request).proposal

    assert "przeklętym komendantem" not in validated.npc_response
    assert "starej zbroi" not in validated.npc_response
    assert "sowią głową" in validated.npc_response
    assert "wieży obserwacyjnej" in validated.npc_response
    assert validated.success_message == "NPC przekazuje dostępne informacje."


def test_npc_interaction_marks_too_risky_request_as_refusal_without_roll():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "significant_risk",
            "requires_roll": True,
            "ability": "charisma",
            "skill": "persuasion",
            "dc": 15,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.social_plan is not None
    assert validated.social_plan.possible is False
    assert validated.proposal.requires_roll is False
    assert validated.proposal.dc is None


def test_npc_interaction_returns_natural_retry_block_instead_of_validation_error():
    request = _request()
    first = resolve_npc_runtime_interaction(
        request.state,
        npc_id="wounded_scout",
        intent="social",
        success=False,
        summary="Zwiadowca nadal nie ufa drużynie.",
        attempt_id="scout_build_trust",
    )
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(
        proposal,
        replace(request, state=first.state),
    )

    assert validated.attempt_plan is not None
    assert validated.attempt_plan.available is False
    assert "Najpierw pokażcie czynami" in validated.attempt_plan.blocked_reason


def test_npc_interaction_rejects_effect_flag_outside_policy():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "dragon_summoned", "value": True}},
            ],
        }
    )

    with pytest.raises(ValueError, match="effect flag is not allowed"):
        validate_npc_interaction_proposal(proposal, _request())


def test_npc_interaction_locked_intent_can_be_unlocked_by_success_effect():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "request_risk": "no_risk",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_stabilized", "value": True}},
                {"type": "set_flag", "parameters": {"key": "scout_trusts_party", "value": True}},
            ],
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.proposal.action_type == "information"


def test_npc_interaction_uses_content_check_and_outcomes_for_structured_target():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "scout_reports",
            "quantity": 1,
            "requires_roll": False,
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.action_plan is not None
    assert validated.action_plan.target.label == "Torba z meldunkami"
    assert validated.proposal.requires_roll is True
    assert validated.proposal.ability == "dexterity"
    assert validated.proposal.skill == "sleight_of_hand"
    assert validated.proposal.dc == 14


def test_npc_interaction_rejects_unknown_structured_target():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "imaginary_gold",
            "requires_roll": True,
            "ability": "dexterity",
            "skill": "sleight_of_hand",
            "dc": 10,
        }
    )

    with pytest.raises(ValueError, match="has no target"):
        validate_npc_interaction_proposal(proposal, _request())


def test_npc_interaction_rejects_llm_effects_for_structured_target():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "scout_reports",
            "requires_roll": True,
            "ability": "dexterity",
            "skill": "sleight_of_hand",
            "dc": 10,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_dead", "value": True}},
            ],
        }
    )

    with pytest.raises(ValueError, match="cannot define LLM-owned outcomes"):
        validate_npc_interaction_proposal(proposal, _request())


def test_structured_intimidation_uses_authored_check_and_content_outcomes():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "intimidation",
            "request_risk": "minor_risk",
            "target_id": "scout_information",
            "requires_roll": False,
            "skill": "intimidation",
        }
    )

    validated = validate_npc_interaction_proposal(proposal, _request())

    assert validated.social_plan is None
    assert validated.action_plan is not None
    assert validated.action_plan.target.reward_label == "Trop o bestii"
    assert validated.attempt_plan is not None
    assert validated.attempt_plan.max_attempts == 1
    assert validated.proposal.requires_roll is True
    assert validated.proposal.ability == "charisma"
    assert validated.proposal.skill == "intimidation"
    assert validated.proposal.dc == 18
