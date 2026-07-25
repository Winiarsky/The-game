"""Pure, state-derived flow graphs for authored exploration scenes.

The graph orchestrates content routes. It deliberately does not resolve D&D
checks or mutate exploration state; those responsibilities stay in the
existing deterministic mechanics and effect executors.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.combat import SceneFlags, scene_flag


class ExplorationFlowRouteKind(StrEnum):
    CHALLENGE_OPTION = "challenge_option"
    OBSERVATION_ROUTER = "observation_router"


@dataclass(frozen=True, slots=True)
class ExplorationFlowCondition:
    all_flags: tuple[str, ...] = ()
    any_flags: tuple[str, ...] = ()
    no_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        flag_groups = (self.all_flags, self.any_flags, self.no_flags)
        if any(any(not flag.strip() for flag in group) for group in flag_groups):
            raise ValueError("Exploration flow conditions cannot contain empty flag ids.")
        if any(len(group) != len(set(group)) for group in flag_groups):
            raise ValueError("Exploration flow conditions cannot repeat flags in one group.")
        positive_flags = set(self.all_flags) | set(self.any_flags)
        overlap = positive_flags.intersection(self.no_flags)
        if overlap:
            raise ValueError(
                "Exploration flow conditions cannot require and forbid the same flags: "
                + ", ".join(sorted(overlap))
                + "."
            )

    def matches(self, flags: SceneFlags) -> bool:
        return (
            all(bool(scene_flag(flags, flag, False)) for flag in self.all_flags)
            and (
                not self.any_flags
                or any(bool(scene_flag(flags, flag, False)) for flag in self.any_flags)
            )
            and not any(bool(scene_flag(flags, flag, False)) for flag in self.no_flags)
        )


@dataclass(frozen=True, slots=True)
class ExplorationFlowNode:
    id: str
    label: str
    active_when: ExplorationFlowCondition = ExplorationFlowCondition()
    terminal: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip():
            raise ValueError("Exploration flow nodes require id and label.")


@dataclass(frozen=True, slots=True)
class ExplorationFlowTransition:
    id: str
    goal_id: str
    from_node_ids: tuple[str, ...]
    route_kind: ExplorationFlowRouteKind
    route_ref: str | None = None
    observation_ids: tuple[str, ...] = ()
    default_observation_id: str | None = None
    source_action_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.goal_id.strip():
            raise ValueError("Exploration flow transitions require id and goal_id.")
        if not self.from_node_ids:
            raise ValueError(f"Exploration flow transition {self.id} requires a source node.")
        if len(self.from_node_ids) != len(set(self.from_node_ids)):
            raise ValueError(f"Exploration flow transition {self.id} repeats source nodes.")
        if self.route_kind == ExplorationFlowRouteKind.CHALLENGE_OPTION and not (
            self.route_ref and self.route_ref.strip()
        ):
            raise ValueError(
                f"Exploration flow transition {self.id} requires a challenge option reference."
            )
        if self.route_kind == ExplorationFlowRouteKind.OBSERVATION_ROUTER:
            if self.route_ref is not None:
                raise ValueError(
                    f"Exploration observation transition {self.id} cannot define route_ref."
                )
            if not self.observation_ids:
                raise ValueError(
                    f"Exploration observation transition {self.id} requires observations."
                )
        if (
            self.default_observation_id is not None
            and self.default_observation_id not in self.observation_ids
        ):
            raise ValueError(
                f"Exploration flow transition {self.id} default observation must be allowed."
            )
        if len(self.observation_ids) != len(set(self.observation_ids)):
            raise ValueError(f"Exploration flow transition {self.id} repeats observations.")
        if len(self.source_action_ids) != len(set(self.source_action_ids)):
            raise ValueError(f"Exploration flow transition {self.id} repeats source actions.")


@dataclass(frozen=True, slots=True)
class ExplorationFlowGraph:
    id: str
    challenge_id: str
    nodes: tuple[ExplorationFlowNode, ...]
    transitions: tuple[ExplorationFlowTransition, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.challenge_id.strip():
            raise ValueError("Exploration flow graphs require id and challenge_id.")
        if not self.nodes:
            raise ValueError(f"Exploration flow graph {self.id} requires at least one node.")
        node_ids = tuple(node.id for node in self.nodes)
        transition_ids = tuple(transition.id for transition in self.transitions)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError(f"Exploration flow graph {self.id} repeats node ids.")
        if len(transition_ids) != len(set(transition_ids)):
            raise ValueError(f"Exploration flow graph {self.id} repeats transition ids.")
        known_nodes = set(node_ids)
        for transition in self.transitions:
            unknown = set(transition.from_node_ids) - known_nodes
            if unknown:
                raise ValueError(
                    f"Exploration flow transition {transition.id} references unknown nodes: "
                    + ", ".join(sorted(unknown))
                    + "."
                )

    def active_nodes(self, flags: SceneFlags) -> tuple[ExplorationFlowNode, ...]:
        return tuple(node for node in self.nodes if node.active_when.matches(flags))

    def available_transitions(
        self,
        flags: SceneFlags,
    ) -> tuple[ExplorationFlowTransition, ...]:
        active_node_ids = {node.id for node in self.active_nodes(flags)}
        return tuple(
            transition
            for transition in self.transitions
            if active_node_ids.intersection(transition.from_node_ids)
        )

    def transition_for_goal(
        self,
        goal_id: str | None,
        flags: SceneFlags,
    ) -> ExplorationFlowTransition | None:
        if goal_id is None:
            return None
        normalized = goal_id.strip().lower()
        matches = tuple(
            transition
            for transition in self.available_transitions(flags)
            if transition.goal_id == normalized
        )
        if len(matches) > 1:
            raise ValueError(
                f"Exploration flow graph {self.id} exposes goal {normalized} more than once."
            )
        return matches[0] if matches else None

    def available_goal_ids(self, flags: SceneFlags) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                transition.goal_id
                for transition in self.available_transitions(flags)
            )
        )


def exploration_flow_for_challenge(
    flows: tuple[ExplorationFlowGraph, ...],
    challenge_id: str,
) -> ExplorationFlowGraph | None:
    return next(
        (flow for flow in flows if flow.challenge_id == challenge_id),
        None,
    )
