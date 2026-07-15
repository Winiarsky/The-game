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


def _state(*, noise: int, tags: tuple[str, ...] = (), spotted: bool = False) -> ExplorationState:
    attempt = ExplorationChallengeAttempt(
        challenge_id="closed_gate",
        option_id="freeform",
        approach_label="Podejście graczy",
        approach_tags=tags,
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
    if spotted:
        flags = set_scene_flag(flags, "gate_goblins_spotted", True)
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
    result = resolve_encounter_opening(_state(noise=2), _policy())

    assert result.rule_id == "quiet_entry"
    assert result.outcome == EncounterOpeningOutcome.PARTY_SURPRISES_ENEMIES


def test_noise_without_reconnaissance_lets_enemies_surprise_party() -> None:
    result = resolve_encounter_opening(_state(noise=3), _policy())

    assert result.rule_id == "alerted_without_reconnaissance"
    assert result.outcome == EncounterOpeningOutcome.ENEMIES_SURPRISE_PARTY


def test_reconnaissance_prevents_enemy_surprise_despite_noise() -> None:
    result = resolve_encounter_opening(_state(noise=3, spotted=True), _policy())

    assert result.rule_id == "alerted_after_reconnaissance"
    assert result.outcome == EncounterOpeningOutcome.NO_SURPRISE


def test_forced_breach_takes_priority_over_noise_ambush() -> None:
    result = resolve_encounter_opening(_state(noise=5, tags=("heavy_force",)), _policy())

    assert result.rule_id == "forced_breach"
    assert result.outcome == EncounterOpeningOutcome.NO_SURPRISE
