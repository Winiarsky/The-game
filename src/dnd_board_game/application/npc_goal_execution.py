"""Application planning for one player-selected NPC interaction goal."""

from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    CheckParticipants,
    ExplorationFlowGraph,
    ExplorationFlowRouteKind,
    ExplorationFlowTransition,
    InteractionGoal,
    NpcIntentPermission,
    NpcInteraction,
    available_interaction_goals,
    exploration_flow_for_npc,
    interaction_goal,
)

from .exploration_goal_execution import (
    resolve_goal_check_participants,
    validate_goal_participants,
)


@dataclass(frozen=True, slots=True)
class NpcGoalRoute:
    goal: InteractionGoal
    intent_id: str
    transition: ExplorationFlowTransition | None = None


@dataclass(frozen=True, slots=True)
class NpcGoalExecutionPlan:
    route: NpcGoalRoute
    permission: NpcIntentPermission
    check_participants: CheckParticipants
    participant_actor_ids: tuple[str, ...]


class NpcGoalExecutionPlanner:
    """Resolve an NPC goal through authored flow and lock its participants."""

    def available_goals(
        self,
        *,
        npc: NpcInteraction,
        flows: tuple[ExplorationFlowGraph, ...],
        flags: SceneFlags,
    ) -> tuple[InteractionGoal, ...]:
        flow = exploration_flow_for_npc(flows, npc.id)
        if flow is None:
            return available_interaction_goals(npc.goals, flags)
        goal_ids = set(flow.available_goal_ids(flags))
        return tuple(goal for goal in npc.goals if goal.id in goal_ids)

    def plan(
        self,
        *,
        npc: NpcInteraction,
        flows: tuple[ExplorationFlowGraph, ...],
        flags: SceneFlags,
        actors: tuple[Actor, ...],
        goal_id: str,
        requested_check_participants: str | None,
        requested_actor_ids: tuple[str, ...],
    ) -> NpcGoalExecutionPlan:
        route = self._route_for_goal(
            npc=npc,
            flows=flows,
            flags=flags,
            goal_id=goal_id,
        )
        if route is None:
            raise ValueError("Wybrany cel rozmowy nie jest teraz dostępny.")
        participants = resolve_goal_check_participants(
            route.goal,
            requested_check_participants,
        )
        actor_ids = validate_goal_participants(
            actors,
            requested_actor_ids,
            check_participants=participants,
        )
        permission = npc.policy.intent_permission(route.intent_id)
        if permission is None:
            raise ValueError(
                f"Cel NPC prowadzi do nieznanej intencji: {route.intent_id}."
            )
        return NpcGoalExecutionPlan(
            route=route,
            permission=permission,
            check_participants=participants,
            participant_actor_ids=actor_ids,
        )

    def _route_for_goal(
        self,
        *,
        npc: NpcInteraction,
        flows: tuple[ExplorationFlowGraph, ...],
        flags: SceneFlags,
        goal_id: str,
    ) -> NpcGoalRoute | None:
        flow = exploration_flow_for_npc(flows, npc.id)
        if flow is None:
            goal = interaction_goal(npc.goals, goal_id, flags)
            if goal is None or not goal.intent_ids:
                return None
            return NpcGoalRoute(goal=goal, intent_id=goal.intent_ids[0])
        transition = flow.transition_for_goal(goal_id, flags)
        if transition is None:
            return None
        if transition.route_kind != ExplorationFlowRouteKind.NPC_INTENT:
            raise ValueError(
                f"Cel NPC {goal_id} nie prowadzi do intencji NPC."
            )
        goal = next(
            (candidate for candidate in npc.goals if candidate.id == transition.goal_id),
            None,
        )
        if goal is None or transition.route_ref is None:
            raise ValueError(f"Flow NPC {flow.id} ma niepełną trasę {transition.id}.")
        return NpcGoalRoute(
            goal=goal,
            intent_id=transition.route_ref,
            transition=transition,
        )
