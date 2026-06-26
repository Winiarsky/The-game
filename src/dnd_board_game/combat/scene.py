from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Faction
from dnd_board_game.hardware import LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    RollModifier,
    resolve_ability_check,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate

from .session import CombatState, combat_winner
from .setup import SetupVisibility


class SceneObjectiveCondition(StrEnum):
    DEFEAT_ALL_ENEMIES = "defeat_all_enemies"
    INTERACT_WITH_OBJECT = "interact_with_object"
    FLAG_EQUALS = "flag_equals"


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
    flag_key: str | None = None
    flag_value: object = True


@dataclass(frozen=True, slots=True)
class SceneFlags:
    values: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class SceneAbilityCheck:
    ability: str
    dc: int
    skill: str | None = None
    modifiers: tuple[RollModifier, ...] = ()


@dataclass(frozen=True, slots=True)
class SceneInteraction:
    id: str
    label: str
    description: str = ""
    ability_check: SceneAbilityCheck | None = None
    success_flag: str | None = None
    failure_flag: str | None = None
    success_message: str = ""
    failure_message: str = ""


@dataclass(frozen=True, slots=True)
class SceneInteractionResult:
    interaction: SceneInteraction
    success: bool
    message: str
    flag_key: str | None = None
    flag_value: object = True
    roll: D20RollResult | None = None
    dc: int | None = None


@dataclass(frozen=True, slots=True)
class SceneObject:
    id: str
    name: str
    positions: tuple[Coordinate, ...]
    interaction_label: str
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    objective_id: str | None = None
    description: str = ""
    interactions: tuple[SceneInteraction, ...] = ()

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


def scene_flag(flags: SceneFlags, key: str, default: object = None) -> object:
    for candidate_key, value in flags.values:
        if candidate_key == key:
            return value
    return default


def set_scene_flag(flags: SceneFlags, key: str, value: object) -> SceneFlags:
    if not key:
        raise ValueError("Scene flag key cannot be empty.")
    values = {candidate_key: candidate_value for candidate_key, candidate_value in flags.values}
    values[key] = value
    return SceneFlags(tuple(sorted(values.items())))


def default_scene_interaction(scene_object: SceneObject) -> SceneInteraction:
    return SceneInteraction(
        id=f"interact_{scene_object.id}",
        label=scene_object.interaction_label,
        description=scene_object.description,
    )


def available_scene_interactions(scene_object: SceneObject) -> tuple[SceneInteraction, ...]:
    if scene_object.interactions:
        return scene_object.interactions
    return (default_scene_interaction(scene_object),)


def resolve_scene_interaction(
    interaction: SceneInteraction,
    *,
    natural_roll: int | None = None,
) -> SceneInteractionResult:
    if interaction.ability_check is None:
        return SceneInteractionResult(
            interaction=interaction,
            success=True,
            message=interaction.success_message or f"Interakcja zakończona: {interaction.label}.",
            flag_key=interaction.success_flag,
        )

    if natural_roll is None:
        raise ValueError(f"Interaction {interaction.id} requires a natural d20 roll.")
    request = D20RollRequest(modifiers=interaction.ability_check.modifiers)
    roll = resolve_d20_roll(D20RollInput(request=request, natural_roll=natural_roll))
    check = resolve_ability_check(roll, interaction.ability_check.dc)
    if check.success:
        return SceneInteractionResult(
            interaction=interaction,
            success=True,
            message=interaction.success_message or "Test cechy zakończony sukcesem.",
            flag_key=interaction.success_flag,
            roll=roll,
            dc=interaction.ability_check.dc,
        )
    return SceneInteractionResult(
        interaction=interaction,
        success=False,
        message=interaction.failure_message or "Test cechy zakończony porażką.",
        flag_key=interaction.failure_flag,
        roll=roll,
        dc=interaction.ability_check.dc,
    )


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


def objective_status_after_flags(
    objectives: tuple[SceneObjective, ...],
    flags: SceneFlags,
) -> tuple[SceneObjective, ...]:
    updated: list[SceneObjective] = []
    for objective in objectives:
        if (
            objective.status == SceneObjectiveStatus.ACTIVE
            and objective.condition == SceneObjectiveCondition.FLAG_EQUALS
            and objective.flag_key is not None
            and scene_flag(flags, objective.flag_key) == objective.flag_value
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
