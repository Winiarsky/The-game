from __future__ import annotations

from dnd_board_game.combat import scene_flag
from dnd_board_game.exploration import (
    EncounterOpeningPolicy,
    EncounterOpeningResolution,
    EncounterOpeningRule,
    ExplorationState,
    challenge_state_for,
)


def resolve_encounter_opening(
    state: ExplorationState,
    policy: EncounterOpeningPolicy,
) -> EncounterOpeningResolution:
    """Resolve an authored encounter-opening policy from persisted exploration state."""

    challenge_state = challenge_state_for(state, policy.challenge_id)
    completion_tags = (
        challenge_state.attempts[-1].approach_tags
        if challenge_state.completed and challenge_state.attempts
        else ()
    )
    for rule in policy.rules:
        if _matches(rule, state, challenge_state.noise, completion_tags):
            return EncounterOpeningResolution(
                rule_id=rule.id,
                outcome=rule.outcome,
                title=rule.title,
                narration=rule.narration,
                noise=challenge_state.noise,
                completion_tags=completion_tags,
            )
    return EncounterOpeningResolution(
        rule_id="default",
        outcome=policy.default_outcome,
        title=policy.default_title,
        narration=policy.default_narration,
        noise=challenge_state.noise,
        completion_tags=completion_tags,
    )


def _matches(
    rule: EncounterOpeningRule,
    state: ExplorationState,
    noise: int,
    completion_tags: tuple[str, ...],
) -> bool:
    if rule.min_noise is not None and noise < rule.min_noise:
        return False
    if rule.max_noise is not None and noise > rule.max_noise:
        return False
    if any(not bool(scene_flag(state.flags, flag, False)) for flag in rule.required_flags):
        return False
    if any(bool(scene_flag(state.flags, flag, False)) for flag in rule.forbidden_flags):
        return False
    if rule.completion_any_tags and not set(rule.completion_any_tags).intersection(completion_tags):
        return False
    return True
