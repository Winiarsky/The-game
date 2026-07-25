from dnd_board_game.application import resolve_encounter_opening
from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import (
    EncounterOpeningOutcome,
    ExplorationChallengeAttempt,
    ExplorationChallengeState,
    ExplorationState,
    PartyPosition,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _policy():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )
    trigger = next(item for item in exploration.encounter_triggers if item.id == "gate_open_skirmish")
    assert trigger.opening_policy is not None
    return trigger.opening_policy


def _state(
    *,
    noise: int,
    critical_breach: bool = False,
    wall_bypass: bool = False,
    ambush_prepared: bool = False,
) -> ExplorationState:
    attempt = ExplorationChallengeAttempt(
        challenge_id="closed_gate",
        option_id="freeform",
        approach_label="Podejście graczy",
        approach_tags=(),
        resource_id=None,
        natural_roll=15,
        total=15,
        success=True,
        critical_failure=False,
        progress_added=3,
        noise_added=noise,
        complications_added=(),
    )
    flags = SceneFlags()
    if critical_breach:
        flags = set_scene_flag(flags, "gate_critical_breach", True)
    if wall_bypass:
        flags = set_scene_flag(flags, "gate_wall_bypass_surprise", True)
    if ambush_prepared:
        flags = set_scene_flag(flags, "gate_goblin_ambush_prepared", True)
    return ExplorationState(
        zones=(),
        points=(),
        party_position=PartyPosition("gate"),
        flags=flags,
        challenge_states=(
            ExplorationChallengeState(
                challenge_id="closed_gate",
                current_progress=3,
                noise=noise,
                completed=True,
                attempts=(attempt,),
            ),
        ),
    )


def test_quiet_entry_surprises_enemies() -> None:
    result = resolve_encounter_opening(_state(noise=0), _policy())

    assert result.rule_id == "quiet_entry"
    assert result.outcome == EncounterOpeningOutcome.PARTY_SURPRISES_ENEMIES


def test_full_alert_lets_enemies_surprise_party() -> None:
    result = resolve_encounter_opening(_state(noise=3), _policy())

    assert result.rule_id == "ambush_prepared_by_alert"
    assert result.outcome == EncounterOpeningOutcome.ENEMIES_SURPRISE_PARTY


def test_partial_alert_has_no_surprise() -> None:
    result = resolve_encounter_opening(_state(noise=2), _policy())

    assert result.rule_id == "default"
    assert result.outcome == EncounterOpeningOutcome.NO_SURPRISE


def test_critical_breach_surprises_enemies_when_alert_is_low() -> None:
    result = resolve_encounter_opening(_state(noise=0, critical_breach=True), _policy())

    assert result.rule_id == "critical_breach"
    assert result.outcome == EncounterOpeningOutcome.PARTY_SURPRISES_ENEMIES


def test_discovered_wall_route_surprises_enemies_when_entry_stays_quiet() -> None:
    result = resolve_encounter_opening(_state(noise=1, wall_bypass=True), _policy())

    assert result.rule_id == "hidden_wall_entry"
    assert result.outcome == EncounterOpeningOutcome.PARTY_SURPRISES_ENEMIES


def test_prepared_ambush_takes_priority_over_quiet_final_attempt() -> None:
    result = resolve_encounter_opening(_state(noise=0, ambush_prepared=True), _policy())

    assert result.rule_id == "ambush_prepared_by_failure"
    assert result.outcome == EncounterOpeningOutcome.ENEMIES_SURPRISE_PARTY
