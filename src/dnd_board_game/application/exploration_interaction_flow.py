"""Application-facing routing for authored exploration flow graphs."""

from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    ExplorationChallenge,
    ExplorationFlowGraph,
    ExplorationFlowRouteKind,
    ExplorationFlowTransition,
    InteractionGoal,
    InteractionSourceAction,
    available_interaction_goals,
    exploration_flow_for_challenge,
    interaction_goal,
)


@dataclass(frozen=True, slots=True)
class ExplorationGoalRoute:
    goal: InteractionGoal
    transition: ExplorationFlowTransition | None = None

    @property
    def route_kind(self) -> ExplorationFlowRouteKind:
        if self.transition is not None:
            return self.transition.route_kind
        return (
            ExplorationFlowRouteKind.OBSERVATION_ROUTER
            if self.goal.observation_ids
            else ExplorationFlowRouteKind.CHALLENGE_OPTION
        )

    @property
    def resolution_option_id(self) -> str | None:
        if self.transition is not None:
            return self.transition.route_ref
        return self.goal.resolution_option_id

    @property
    def observation_ids(self) -> tuple[str, ...]:
        if self.transition is not None:
            return self.transition.observation_ids
        return self.goal.observation_ids

    @property
    def default_observation_id(self) -> str | None:
        if self.transition is not None:
            return self.transition.default_observation_id
        return self.goal.default_observation_id

    @property
    def source_actions(self) -> tuple[InteractionSourceAction, ...]:
        if self.transition is None:
            return self.goal.source_actions
        allowed_ids = set(self.transition.source_action_ids)
        return tuple(
            action
            for action in self.goal.source_actions
            if action.id in allowed_ids
        )


class ExplorationInteractionFlowService:
    """Resolve player-facing goals through a flow graph when one is authored."""

    def available_goals(
        self,
        *,
        challenge: ExplorationChallenge,
        flows: tuple[ExplorationFlowGraph, ...],
        flags: SceneFlags,
    ) -> tuple[InteractionGoal, ...]:
        flow = exploration_flow_for_challenge(flows, challenge.id)
        if flow is None:
            return available_interaction_goals(challenge.goals, flags)
        goal_ids = set(flow.available_goal_ids(flags))
        return tuple(goal for goal in challenge.goals if goal.id in goal_ids)

    def route_for_goal(
        self,
        *,
        challenge: ExplorationChallenge,
        flows: tuple[ExplorationFlowGraph, ...],
        goal_id: str | None,
        flags: SceneFlags,
    ) -> ExplorationGoalRoute | None:
        if goal_id is None or not goal_id.strip():
            return None
        flow = exploration_flow_for_challenge(flows, challenge.id)
        if flow is None:
            goal = interaction_goal(challenge.goals, goal_id, flags)
            return ExplorationGoalRoute(goal=goal) if goal is not None else None
        transition = flow.transition_for_goal(goal_id, flags)
        if transition is None:
            return None
        goal = next(
            (candidate for candidate in challenge.goals if candidate.id == transition.goal_id),
            None,
        )
        if goal is None:
            raise ValueError(
                f"Flow {flow.id} routes an unknown goal: {transition.goal_id}."
            )
        return ExplorationGoalRoute(goal=goal, transition=transition)

    def available_routes(
        self,
        *,
        challenge: ExplorationChallenge,
        flows: tuple[ExplorationFlowGraph, ...],
        flags: SceneFlags,
    ) -> tuple[ExplorationGoalRoute, ...]:
        """Return the exact routes a freeform declaration may enter right now."""

        return tuple(
            route
            for goal in self.available_goals(
                challenge=challenge,
                flows=flows,
                flags=flags,
            )
            for route in (
                self.route_for_goal(
                    challenge=challenge,
                    flows=flows,
                    goal_id=goal.id,
                    flags=flags,
                ),
            )
            if route is not None
        )

    def route_for_transition(
        self,
        *,
        challenge: ExplorationChallenge,
        flows: tuple[ExplorationFlowGraph, ...],
        transition_id: str,
        flags: SceneFlags,
    ) -> ExplorationGoalRoute | None:
        """Resolve only an active transition; stale or invented ids stay blocked."""

        return next(
            (
                route
                for route in self.available_routes(
                    challenge=challenge,
                    flows=flows,
                    flags=flags,
                )
                if route.transition is not None
                and route.transition.id == transition_id
            ),
            None,
        )
