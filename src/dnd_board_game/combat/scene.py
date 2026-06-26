from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Faction
from dnd_board_game.hardware import LedFeedback, LedFrame, LedRole
from dnd_board_game.world import Coordinate

from .session import CombatState, combat_winner
from .setup import SetupVisibility


class SceneObjectiveCondition(StrEnum):
    DEFEAT_ALL_ENEMIES = "defeat_all_enemies"
    INTERACT_WITH_OBJECT = "interact_with_object"


class SceneObjectiveStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SceneObjective:
    id: str
    name: str
    description: str
    condition: SceneObjectiveCondition
    status: SceneObjectiveStatus = SceneObjectiveStatus.ACTIVE
    target_id: str | None = None


@dataclass(frozen=True, slots=True)
class SceneObject:
    id: str
    name: str
    positions: tuple[Coordinate, ...]
    interaction_label: str
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    objective_id: str | None = None
    description: str = ""

    @property
    def primary_position(self) -> Coordinate:
        if not self.positions:
            raise ValueError(f"Scene object {self.id} has no positions.")
        return self.positions[0]


@dataclass(frozen=True, slots=True)
class SceneResult:
    finished: bool
    message: str
    winner: Faction | None = None
    completed_objectives: tuple[str, ...] = ()


def scene_setup_led_feedback(start_zones: tuple[tuple[Coordinate, ...], ...]) -> LedFeedback:
    positions = tuple(sorted({position for zone in start_zones for position in zone}))
    if not positions:
        return LedFeedback()
    return LedFeedback((LedFrame(positions, (0, 220, 255), LedRole.ALLY),))


def visible_scene_objects(objects: tuple[SceneObject, ...]) -> tuple[SceneObject, ...]:
    return tuple(obj for obj in objects if obj.visibility == SetupVisibility.VISIBLE and obj.positions)


def complete_interaction_objective(
    objectives: tuple[SceneObjective, ...],
    scene_object: SceneObject,
) -> tuple[SceneObjective, ...]:
    updated: list[SceneObjective] = []
    for objective in objectives:
        if (
            objective.status == SceneObjectiveStatus.ACTIVE
            and objective.condition == SceneObjectiveCondition.INTERACT_WITH_OBJECT
            and (objective.target_id == scene_object.id or objective.id == scene_object.objective_id)
        ):
            updated.append(replace(objective, status=SceneObjectiveStatus.COMPLETED))
            continue
        updated.append(objective)
    return tuple(updated)


def objective_status_after_combat(state: CombatState, objectives: tuple[SceneObjective, ...]) -> tuple[SceneObjective, ...]:
    if combat_winner(state) != Faction.ALLY:
        return objectives
    updated: list[SceneObjective] = []
    for objective in objectives:
        if (
            objective.status == SceneObjectiveStatus.ACTIVE
            and objective.condition == SceneObjectiveCondition.DEFEAT_ALL_ENEMIES
        ):
            updated.append(replace(objective, status=SceneObjectiveStatus.COMPLETED))
            continue
        updated.append(objective)
    return tuple(updated)


def scene_is_finished(state: CombatState, objectives: tuple[SceneObjective, ...]) -> bool:
    if objectives and all(objective.status == SceneObjectiveStatus.COMPLETED for objective in objectives):
        return True
    return combat_winner(state) is not None


def scene_result(state: CombatState, objectives: tuple[SceneObjective, ...]) -> SceneResult:
    completed = tuple(objective.id for objective in objectives if objective.status == SceneObjectiveStatus.COMPLETED)
    if objectives and all(objective.status == SceneObjectiveStatus.COMPLETED for objective in objectives):
        return SceneResult(True, "Scena zakończona. Cel sceny został osiągnięty.", Faction.ALLY, completed)
    winner = combat_winner(state)
    if winner == Faction.ALLY:
        return SceneResult(True, "Scena zakończona. Bohaterowie zwyciężyli.", winner, completed)
    if winner == Faction.ENEMY:
        return SceneResult(True, "Scena zakończona. Bohaterowie zostali pokonani.", winner, completed)
    return SceneResult(False, "Scena trwa.", None, completed)
