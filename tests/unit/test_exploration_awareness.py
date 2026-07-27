from dataclasses import replace

from dnd_board_game.actors import skill_roll_modifiers
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationCheckPlan,
    ExplorationState,
    ExplorationTrapStatus,
    PartyCheckInput,
    detect_passive_traps,
    hide_exploration_actor,
    resolve_active_search,
    resolve_exploration_check,
    trap_state_for,
)
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.scenarios import (
    build_exploration_from_scenario,
    load_scenario,
)


def _watchtower():
    return build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )


def _state(exploration) -> ExplorationState:
    return ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        traps=exploration.traps,
    )


def test_active_search_reveals_points_and_traps_at_independent_thresholds() -> None:
    exploration = _watchtower()
    rogue = next(
        actor for actor in exploration.actors if str(actor.id) == "rogue"
    )
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    inputs = (
        PartyCheckInput(
            rogue,
            20,
            D20RollRequest(
                modifiers=skill_roll_modifiers(rogue, "perception")
            ),
        ),
    )

    result = resolve_active_search(_state(exploration), gate, inputs)

    assert result.search.party_check.winning_roll.total == 24
    assert result.search.state.exhausted_search_zones == ("gate",)
    assert [trap.id for trap in result.revealed_traps] == [
        "gate_alarm_wire"
    ]
    assert (
        trap_state_for(result.search.state, "gate_alarm_wire").status
        == ExplorationTrapStatus.REVEALED
    )


def test_passive_trap_detection_uses_highest_supplied_score() -> None:
    exploration = _watchtower()

    missed = detect_passive_traps(
        _state(exploration),
        zone_id="gate",
        perception_totals={"hero": 13, "rogue": 14},
    )
    detected = detect_passive_traps(
        _state(exploration),
        zone_id="gate",
        perception_totals={"hero": 13, "rogue": 16},
    )

    assert missed.revealed_traps == ()
    assert [trap.id for trap in detected.revealed_traps] == [
        "gate_alarm_wire"
    ]
    assert detected.detector_actor_id == "rogue"
    assert detected.detector_total == 16


def test_passive_trap_detection_can_be_scoped_to_one_distance_checked_trap() -> None:
    exploration = _watchtower()
    gate_trap = exploration.traps[0]
    distant_trap = replace(
        gate_trap,
        id="distant_alarm_wire",
        detection_distance_feet=60,
    )
    state = replace(
        _state(exploration),
        traps=(gate_trap, distant_trap),
    )

    detected = detect_passive_traps(
        state,
        zone_id="gate",
        perception_totals={"rogue": 16},
        trap_ids=(gate_trap.id,),
    )

    assert [trap.id for trap in detected.revealed_traps] == [
        gate_trap.id
    ]
    assert (
        trap_state_for(detected.state, distant_trap.id).status
        == ExplorationTrapStatus.HIDDEN
    )


def test_exploration_hide_persists_the_unopposed_stealth_total() -> None:
    exploration = _watchtower()
    rogue = next(
        actor for actor in exploration.actors if str(actor.id) == "rogue"
    )
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.LEAD_ACTOR,),
        ability="dexterity",
        skill="stealth",
        dc=10,
        lead_actor_id="rogue",
    )
    check = resolve_exploration_check(
        plan,
        (
            PartyCheckInput(
                rogue,
                12,
                D20RollRequest(
                    modifiers=skill_roll_modifiers(rogue, "stealth")
                ),
            ),
        ),
    )

    state = hide_exploration_actor(
        _state(exploration),
        rogue,
        zone_id="gate",
        check=check,
    )

    assert len(state.hidden_actor_states) == 1
    assert state.hidden_actor_states[0].actor_id == "rogue"
    assert state.hidden_actor_states[0].natural_roll == 12
    assert state.hidden_actor_states[0].stealth_total == 19
