import pytest

from dnd_board_game.application import ScenarioContinuationFlowService
from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import ScenarioContinuation
from dnd_board_game.exploration import (
    ContinuationNavigationResult,
    ContinuationOutcomeKind,
    ContinuationSummaryItem,
    ScenarioContinuationOutcome,
)


def _continuation() -> ScenarioContinuation:
    return ScenarioContinuation(
        id="depart",
        label="Wyrusz",
        description="Drużyna rusza dalej.",
        departure_zone_id="road",
        target_scenario_id="watchtower",
        target_scenario_path="watchtower.json",
        available_if_flags=("quest_accepted", "ready"),
        departure_summary=(
            ContinuationSummaryItem("Stały cel wyprawy."),
            ContinuationSummaryItem("Poznany sekretny skrót.", "knows_shortcut"),
        ),
    )


def _branched_continuation() -> ScenarioContinuation:
    return ScenarioContinuation(
        id="depart",
        label="Wyrusz",
        description="Drużyna rusza dalej.",
        departure_zone_id="road",
        target_scenario_id="watchtower",
        target_scenario_path="watchtower.json",
        propagate_flags=("alerted",),
        outcomes=(
            ScenarioContinuationOutcome(
                id="lost",
                kind=ContinuationOutcomeKind.FAIL_FORWARD,
                label="Zgubiona droga",
                navigation_result=ContinuationNavigationResult.FAILURE,
                target_effects=(
                    {
                        "type": "set_flag",
                        "parameters": {"key": "route_lost", "value": True},
                    },
                ),
            ),
            ScenarioContinuationOutcome(
                id="alerted",
                kind=ContinuationOutcomeKind.PARTIAL_SUCCESS,
                label="Alarm",
                required_flags=("alerted",),
            ),
            ScenarioContinuationOutcome(
                id="clean",
                kind=ContinuationOutcomeKind.SUCCESS,
                label="Czyste wejście",
            ),
        ),
    )


def test_continuation_requires_authored_flags_and_departure_zone():
    service = ScenarioContinuationFlowService()
    flags = set_scene_flag(SceneFlags(), "quest_accepted", True)

    payload = service.availability_payload(
        _continuation(),
        flags=flags,
        current_zone_id="market",
    )

    assert payload is not None
    assert payload["available"] is False
    assert payload["missing_flags"] == ["ready"]
    assert payload["requires_departure_zone"] is True
    assert payload["departure_summary"] == [
        {"label": "Stały cel wyprawy.", "known": True},
        {"label": "Poznany sekretny skrót.", "known": False},
    ]

    with pytest.raises(ValueError, match="nie jest jeszcze gotowa"):
        service.plan(
            _continuation(),
            source_scenario_id="village",
            flags=flags,
            current_zone_id="market",
        )


def test_continuation_plan_is_available_only_at_authored_exit():
    service = ScenarioContinuationFlowService()
    flags = set_scene_flag(
        set_scene_flag(SceneFlags(), "quest_accepted", True),
        "ready",
        True,
    )

    with pytest.raises(ValueError, match="lokacji wyjścia"):
        service.plan(
            _continuation(),
            source_scenario_id="village",
            flags=flags,
            current_zone_id="market",
        )

    plan = service.plan(
        _continuation(),
        source_scenario_id="village",
        flags=flags,
        current_zone_id="road",
    )

    assert plan.as_payload()["available"] is True
    assert plan.source_scenario_id == "village"
    assert plan.continuation.target_scenario_id == "watchtower"


def test_continuation_outcome_selects_fail_forward_and_exports_target_effects():
    service = ScenarioContinuationFlowService()
    flags = set_scene_flag(SceneFlags(), "alerted", True)
    continuation = _branched_continuation()
    plan = service.plan(
        continuation,
        source_scenario_id="village",
        flags=flags,
        current_zone_id="road",
    )

    resolution = service.resolve_outcome(
        plan,
        flags=flags,
        navigation_succeeded=False,
    )

    assert resolution.outcome.id == "lost"
    assert resolution.outcome.kind == ContinuationOutcomeKind.FAIL_FORWARD
    assert resolution.propagated_flags == (("alerted", True),)
    assert resolution.target_effects == (
        {
            "type": "set_flag",
            "parameters": {"key": "alerted", "value": True},
        },
        {
            "type": "set_flag",
            "parameters": {"key": "route_lost", "value": True},
        },
    )


def test_continuation_outcome_uses_ordered_flag_branch_then_default():
    service = ScenarioContinuationFlowService()
    continuation = _branched_continuation()
    plan = service.plan(
        continuation,
        source_scenario_id="village",
        flags=SceneFlags(),
        current_zone_id="road",
    )

    clean = service.resolve_outcome(
        plan,
        flags=SceneFlags(),
        navigation_succeeded=True,
    )
    alerted_flags = set_scene_flag(SceneFlags(), "alerted", True)
    alerted = service.resolve_outcome(
        plan,
        flags=alerted_flags,
        navigation_succeeded=True,
    )

    assert clean.outcome.id == "clean"
    assert alerted.outcome.id == "alerted"


def test_continuation_outcomes_require_one_final_unconditional_fallback():
    conditional = ScenarioContinuationOutcome(
        id="alerted",
        kind=ContinuationOutcomeKind.PARTIAL_SUCCESS,
        label="Alarm",
        required_flags=("alerted",),
    )

    with pytest.raises(ValueError, match="one final default outcome"):
        ScenarioContinuation(
            id="depart",
            label="Wyrusz",
            description="Drużyna rusza dalej.",
            departure_zone_id="road",
            target_scenario_id="watchtower",
            target_scenario_path="watchtower.json",
            outcomes=(conditional,),
        )


def test_campaign_threads_propagate_without_repeating_scenario_configuration():
    service = ScenarioContinuationFlowService()
    flags = set_scene_flag(SceneFlags(), 'campaign_delayed_rewards_v1', '{"bell":"pending"}')
    flags = set_scene_flag(flags, 'campaign_mission_zero_case', '{"debt":"garran"}')
    from dnd_board_game.application.party_ethos import apply_choice, KEY, read
    flags = apply_choice(flags, 'mission:force', 'ruthlessness')
    flags = set_scene_flag(flags, 'local_only', True)
    plan = service.plan(_branched_continuation(), source_scenario_id='misja_0_dzwon', flags=flags, current_zone_id='road')
    result = service.resolve_outcome(plan, flags=flags, navigation_succeeded=True)
    carried = dict(result.propagated_flags)
    assert set(carried) == {'campaign_delayed_rewards_v1', 'campaign_mission_zero_case', KEY}
    restored = set_scene_flag(SceneFlags(), KEY, carried[KEY])
    assert read(restored).position == 4
    assert apply_choice(restored, 'mission:force', 'ruthlessness') == restored
    assert carried['campaign_mission_zero_case'] == '{"debt":"garran"}'
