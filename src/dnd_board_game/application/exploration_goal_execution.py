"""Application planning for one player-selected exploration goal."""

from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    CheckParticipants,
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationFlowGraph,
    ExplorationObservation,
    InteractionGoal,
    InteractionParticipantMode,
    InteractionSourceAction,
    SceneSourceMatch,
    actors_matching_challenge_option,
    match_exploration_observation,
)

from .exploration_interaction_flow import (
    ExplorationGoalRoute,
    ExplorationInteractionFlowService,
)


@dataclass(frozen=True, slots=True)
class ProceduralSourceExecution:
    action: InteractionSourceAction
    source_match: SceneSourceMatch
    option: ExplorationChallengeOption


@dataclass(frozen=True, slots=True)
class ExplorationGoalExecutionPlan:
    route: ExplorationGoalRoute
    check_participants: CheckParticipants
    participant_actor_ids: tuple[str, ...]

    def procedural_source_execution(
        self,
        challenge: ExplorationChallenge,
        source_matches: tuple[SceneSourceMatch, ...],
        *,
        direct_source_use: bool,
    ) -> ProceduralSourceExecution | None:
        if not direct_source_use:
            return None
        matched = next(
            (
                (action, source_match)
                for action in self.route.source_actions
                for source_match in source_matches
                if source_match.source.reference_id == action.source_ref
            ),
            None,
        )
        if matched is None:
            return None
        action, source_match = matched
        option = next(
            (
                candidate
                for candidate in challenge.options
                if candidate.id == action.option_id
            ),
            None,
        )
        if option is None:
            raise ValueError(
                f"Akcja źródła {action.id} wskazuje nieistniejącą opcję."
            )
        return ProceduralSourceExecution(
            action=action,
            source_match=source_match,
            option=option,
        )

    def authored_observation(
        self,
        observations: tuple[ExplorationObservation, ...],
        player_action: str,
        *,
        zone_id: str,
        challenge_id: str,
    ) -> ExplorationObservation | None:
        return match_exploration_observation(
            observations,
            player_action,
            zone_id=zone_id,
            challenge_id=challenge_id,
            allowed_observation_ids=self.route.observation_ids,
        )


class ExplorationGoalExecutionPlanner:
    """Resolve a visible goal, participant policy and its authored route."""

    def __init__(
        self,
        route_service: ExplorationInteractionFlowService | None = None,
    ) -> None:
        self.route_service = route_service or ExplorationInteractionFlowService()

    def plan(
        self,
        *,
        challenge: ExplorationChallenge,
        flows: tuple[ExplorationFlowGraph, ...],
        flags: SceneFlags,
        actors: tuple[Actor, ...],
        goal_id: str,
        requested_check_participants: str | None,
        requested_actor_ids: tuple[str, ...],
    ) -> ExplorationGoalExecutionPlan:
        route = self.route_service.route_for_goal(
            challenge=challenge,
            flows=flows,
            goal_id=goal_id,
            flags=flags,
        )
        if route is None:
            raise ValueError("Wybrany cel nie jest dostępny w tej interakcji.")
        participants = resolve_goal_check_participants(
            route.goal,
            requested_check_participants,
        )
        profile = next(
            (
                option
                for option in challenge.options
                if option.id == route.resolution_option_id
            ),
            None,
        )
        eligible_actor_ids = (
            {
                str(actor.id)
                for actor in actors_matching_challenge_option(actors, profile)
                if actor.faction == Faction.ALLY
            }
            if profile is not None
            else None
        )
        actor_ids = validate_goal_participants(
            actors,
            requested_actor_ids,
            check_participants=participants,
            eligible_actor_ids=eligible_actor_ids,
        )
        return ExplorationGoalExecutionPlan(
            route=route,
            check_participants=participants,
            participant_actor_ids=actor_ids,
        )

    def legacy_authored_observation(
        self,
        observations: tuple[ExplorationObservation, ...],
        player_action: str,
        *,
        zone_id: str,
        challenge_id: str,
    ) -> ExplorationObservation | None:
        """Compatibility route for explicit slash actions without a goal card."""

        return match_exploration_observation(
            observations,
            player_action,
            zone_id=zone_id,
            challenge_id=challenge_id,
        )


def resolve_goal_check_participants(
    goal: InteractionGoal,
    requested: str | None,
) -> CheckParticipants:
    if goal.participant_mode == InteractionParticipantMode.MUST:
        if (
            requested is not None
            and CheckParticipants(requested) != goal.check_participants
        ):
            raise ValueError("Ten kafelek wymusza inny typ testu.")
        return goal.check_participants
    if requested is None:
        raise ValueError("Najpierw wybierz typ testu dla tego kafelka.")
    selected = CheckParticipants(requested)
    if selected not in goal.participant_options:
        raise ValueError("Wybrany typ testu nie jest dozwolony dla tego kafelka.")
    return selected


def validate_goal_participants(
    actors: tuple[Actor, ...],
    requested_actor_ids: tuple[str, ...],
    *,
    check_participants: CheckParticipants,
    eligible_actor_ids: set[str] | None = None,
) -> tuple[str, ...]:
    ally_ids = tuple(str(actor.id) for actor in actors if actor.faction == Faction.ALLY)
    requested = tuple(
        dict.fromkeys(
            actor_id.strip()
            for actor_id in requested_actor_ids
            if actor_id.strip()
        )
    )
    if len(requested) != len(requested_actor_ids):
        raise ValueError("Każdą postać można wskazać tylko raz.")
    if any(actor_id not in ally_ids for actor_id in requested):
        raise ValueError("Wybrano postać, która nie należy do drużyny.")

    if check_participants == CheckParticipants.NO_ACTOR:
        if requested:
            raise ValueError("Ta decyzja nie jest przypisana do konkretnej postaci.")
        selected = ()
    elif check_participants == CheckParticipants.WHOLE_PARTY:
        if requested:
            raise ValueError("W teście grupowym rzuca automatycznie cała drużyna.")
        selected = ally_ids
    elif check_participants == CheckParticipants.SINGLE_ACTOR:
        if len(requested) != 1:
            raise ValueError("Ten test wykonuje dokładnie jedna wybrana postać.")
        selected = requested
    elif check_participants == CheckParticipants.LEAD_WITH_HELP:
        if len(requested) not in {1, 2}:
            raise ValueError(
                "Wybierz głównego wykonawcę oraz opcjonalnie jednego pomocnika."
            )
        selected = requested
    else:
        raise ValueError("Kafelek ma nieobsługiwany model uczestników.")

    if (
        eligible_actor_ids is not None
        and check_participants
        not in {CheckParticipants.NO_ACTOR, CheckParticipants.WHOLE_PARTY}
    ):
        incapable = tuple(
            actor_id
            for actor_id in selected
            if actor_id not in eligible_actor_ids
        )
        if incapable:
            names = ", ".join(
                actor.name
                for actor in actors
                if str(actor.id) in set(incapable)
            )
            raise ValueError(
                f"Te postacie nie spełniają wymagań tego sposobu: {names}."
            )
    return selected
