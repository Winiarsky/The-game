from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace

from dnd_board_game.combat import SceneFlags, scene_flag

from .models import (
    CheckAggregation,
    CheckParticipants,
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationState,
    InteractionGoal,
    InteractionMethodRule,
    NarrativeStyle,
    NpcInteraction,
    NpcKeyIssue,
)


def _normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))


def available_interaction_goals(
    goals: tuple[InteractionGoal, ...],
    flags: SceneFlags,
) -> tuple[InteractionGoal, ...]:
    return tuple(
        goal
        for goal in goals
        if all(scene_flag(flags, flag, False) for flag in goal.required_flags)
        and not any(scene_flag(flags, flag, False) for flag in goal.forbidden_flags)
    )


def interaction_goal(
    goals: tuple[InteractionGoal, ...],
    goal_id: str | None,
    flags: SceneFlags,
) -> InteractionGoal | None:
    if goal_id is None or not goal_id.strip():
        return None
    normalized_id = goal_id.strip().lower()
    return next(
        (
            goal
            for goal in available_interaction_goals(goals, flags)
            if goal.id == normalized_id
        ),
        None,
    )


def effective_narrative_style(
    instance_style: NarrativeStyle,
    goal: InteractionGoal | None,
) -> NarrativeStyle:
    if goal is not None and goal.narrative_style is not None:
        return goal.narrative_style
    return instance_style


def matched_method_rules(
    challenge: ExplorationChallenge,
    player_action: str,
    goal_id: str | None,
) -> tuple[InteractionMethodRule, ...]:
    normalized_action = _normalized_text(player_action)
    normalized_goal_id = goal_id.strip().lower() if goal_id else None
    return tuple(
        rule
        for rule in challenge.method_rules
        if (not rule.goal_ids or normalized_goal_id in rule.goal_ids)
        and any(_normalized_text(phrase) in normalized_action for phrase in rule.match_phrases)
    )


def apply_goal_resolution_profile(
    option: ExplorationChallengeOption,
    *,
    challenge: ExplorationChallenge,
    selected_goal_id: str | None,
    resolution_option_id: str | None = None,
    selected_check_participants: CheckParticipants | None = None,
    player_action: str,
    state: ExplorationState,
    minimum_dc: int = 5,
) -> ExplorationChallengeOption:
    """Bind an LLM-proposed check to the authored outcome profile for its goal."""
    goal = next(
        (
            candidate
            for candidate in challenge.goals
            if selected_goal_id is not None
            and candidate.id == selected_goal_id
            and (
                resolution_option_id is not None
                or candidate.resolution_option_id is not None
            )
        ),
        None,
    )
    if goal is None and selected_goal_id is None:
        option_tags = set(option.tags)
        candidates = [
            candidate
            for candidate in challenge.goals
            if candidate.resolution_option_id is not None
            and option_tags.intersection(candidate.suggested_tags)
        ]
        if candidates:
            profiles_by_id = {candidate.id: candidate for candidate in challenge.options}

            def goal_match_score(candidate: InteractionGoal) -> tuple[int, int]:
                profile = profiles_by_id.get(candidate.resolution_option_id or "")
                return (
                    len(option_tags.intersection(candidate.suggested_tags)),
                    len(option_tags.intersection(profile.tags)) if profile is not None else 0,
                )

            goal = max(
                candidates,
                key=goal_match_score,
            )
    if goal is None:
        return option
    profile_id = resolution_option_id or goal.resolution_option_id
    if profile_id is None:
        return option
    profile = next(
        (
            candidate
            for candidate in challenge.options
            if candidate.id == profile_id
        ),
        None,
    )
    if profile is None:
        raise ValueError(
            f"Cel {goal.id} wskazuje nieistniejący profil rozstrzygnięcia "
            f"{profile_id}."
        )
    blocked_flags = tuple(
        flag
        for flag in profile.unavailable_if_flags
        if bool(scene_flag(state.flags, flag, False))
    )
    if blocked_flags:
        raise ValueError(
            profile.unavailable_message
            or f"To działanie zostało już wykonane: {', '.join(blocked_flags)}."
        )
    dc_modifier = sum(
        modifier
        for flag, modifier in profile.dc_modifiers_if_flags
        if bool(scene_flag(state.flags, flag, False))
    )
    method_rules = matched_method_rules(challenge, player_action, selected_goal_id)
    method_noise_delta = sum(rule.noise_delta for rule in method_rules)
    success_noise_overrides = tuple(
        rule.success_noise_override
        for rule in method_rules
        if rule.success_noise_override is not None
    )

    def adjusted_noise(value: int, *, success: bool = False) -> int:
        if success and success_noise_overrides:
            return min(success_noise_overrides)
        return max(0, value + method_noise_delta)

    mechanics_are_authored = resolution_option_id is not None
    grounded_base = profile if mechanics_are_authored else option
    authored_check = profile.ability_check if mechanics_are_authored else option.ability_check
    return replace(
        grounded_base,
        id=profile.id,
        label=option.label,
        description=option.description,
        check_participants=(
            selected_check_participants or goal.check_participants
            if selected_goal_id is not None
            else option.check_participants
        ),
        check_aggregation=(
            CheckAggregation.MAJORITY
            if selected_goal_id is not None
            and (selected_check_participants or goal.check_participants)
            == CheckParticipants.WHOLE_PARTY
            else CheckAggregation.LEAD_RESULT
            if selected_goal_id is not None
            else option.check_aggregation
        ),
        ability_check=replace(
            authored_check,
            dc=max(minimum_dc, authored_check.dc + dc_modifier),
        ),
        progress_on_success=profile.progress_on_success,
        progress_on_failure=profile.progress_on_failure,
        success_message=profile.success_message,
        critical_success_message=profile.critical_success_message,
        failure_message=profile.failure_message,
        critical_failure_message=profile.critical_failure_message,
        tags=tuple(dict.fromkeys((*option.tags, *profile.tags))),
        roll_mode=option.roll_mode,
        situational_modifiers=option.situational_modifiers,
        improvised_tool=option.improvised_tool,
        consequence_targets=option.consequence_targets,
        requires_item_ids=tuple(
            dict.fromkeys((*profile.requires_item_ids, *option.requires_item_ids))
        ),
        requires_spell_ids=tuple(
            dict.fromkeys((*profile.requires_spell_ids, *option.requires_spell_ids))
        ),
        mechanic_id=option.mechanic_id or profile.mechanic_id,
        unavailable_if_flags=profile.unavailable_if_flags,
        unavailable_message=profile.unavailable_message,
        dc_modifiers_if_flags=profile.dc_modifiers_if_flags,
        critical_success_flags=profile.critical_success_flags,
        success_flags=profile.success_flags,
        failure_flags=profile.failure_flags,
        critical_failure_flags=profile.critical_failure_flags,
        success_noise=adjusted_noise(profile.success_noise, success=True),
        failure_noise=adjusted_noise(profile.failure_noise),
        critical_failure_noise=adjusted_noise(profile.critical_failure_noise),
        quiet_success_margin=profile.quiet_success_margin,
        quiet_on_natural_20=profile.quiet_on_natural_20,
        success_complication=profile.success_complication,
        failure_complication=profile.failure_complication,
        critical_failure_complication=profile.critical_failure_complication,
        hazards=profile.hazards,
    )


@dataclass(frozen=True, slots=True)
class NpcKeyIssueMatch:
    issue: NpcKeyIssue
    matched_phrase: str


def match_npc_key_issue(
    npc: NpcInteraction,
    player_action: str,
    flags: SceneFlags,
    goal_id: str | None = None,
) -> NpcKeyIssueMatch | None:
    normalized_action = _normalized_text(player_action)
    normalized_goal_id = goal_id.strip().lower() if goal_id else None
    for issue in npc.key_issues:
        if issue.goal_ids and normalized_goal_id not in issue.goal_ids:
            continue
        if not issue.repeatable and any(
            scene_flag(flags, flag, False) for flag in issue.consumed_if_flags
        ):
            continue
        for phrase in issue.match_phrases:
            if _normalized_text(phrase) in normalized_action:
                return NpcKeyIssueMatch(issue=issue, matched_phrase=phrase)
    return None
