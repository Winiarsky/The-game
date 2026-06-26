from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor
from dnd_board_game.world import BoardState, Coordinate, MovementRangeResult, PathResult, find_path, movement_range

from .action_economy import ActionUse
from .attack_flow import AttackSource, legal_melee_targets
from .scene import SceneObject, visible_scene_objects
from .session import CombatState, TurnMovementUseResult, movement_remaining, use_movement
from .session import use_turn_action
from .targets import CombatTarget


class TurnPromptMode(StrEnum):
    IDLE = "idle"
    MOVEMENT_PREVIEW = "movement_preview"
    ATTACK_PREVIEW = "attack_preview"
    INTERACTION_PREVIEW = "interaction_preview"
    INVALID = "invalid"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class TurnIntentPreview:
    mode: TurnPromptMode
    actor: Actor
    clicked_position: Coordinate
    message: str
    movement_range: MovementRangeResult | None = None
    movement_path: PathResult | None = None
    attack_target: CombatTarget | None = None
    attack_source: AttackSource | None = None
    interaction_object: SceneObject | None = None
    movement_remaining_feet: int = 0
    action_available: bool = False


@dataclass(frozen=True, slots=True)
class TurnIntentConfirmation:
    state: CombatState
    accepted: bool
    mode: TurnPromptMode
    message: str
    movement_result: TurnMovementUseResult | None = None
    attack_target: CombatTarget | None = None
    attack_source: AttackSource | None = None
    interaction_object: SceneObject | None = None


def preview_turn_intent(
    board: BoardState,
    state: CombatState,
    actor: Actor,
    attack_source: AttackSource,
    clicked_position: Coordinate,
    interactables: tuple[SceneObject, ...] = (),
) -> TurnIntentPreview:
    remaining = movement_remaining(state, actor)
    action_available = state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    if actor.is_defeated():
        return _invalid(actor, clicked_position, remaining, action_available, "Pokonany aktor nie może działać.")
    if not board.in_bounds(clicked_position):
        return _invalid(actor, clicked_position, remaining, action_available, "Kliknięte pole jest poza planszą.")

    legal_targets = legal_melee_targets(board, actor, state.actors) if action_available else ()
    for target in legal_targets:
        if target.position == clicked_position:
            return TurnIntentPreview(
                mode=TurnPromptMode.ATTACK_PREVIEW,
                actor=actor,
                clicked_position=clicked_position,
                message=(
                    f"Wybrano cel: {target.name}. Dostępna akcja: Atak {attack_source.name}. "
                    "Rzuć po potwierdzeniu. Kliknij to pole ponownie, aby potwierdzić atak."
                ),
                attack_target=target,
                attack_source=attack_source,
                movement_remaining_feet=remaining,
                action_available=action_available,
            )

    if action_available:
        for scene_object in visible_scene_objects(interactables):
            if clicked_position in scene_object.positions:
                if not _is_adjacent(actor.position, scene_object.primary_position):
                    return _invalid(
                        actor,
                        clicked_position,
                        remaining,
                        action_available,
                        f"{scene_object.name} jest poza zasięgiem interakcji. Podejdź bliżej.",
                    )
                return TurnIntentPreview(
                    mode=TurnPromptMode.INTERACTION_PREVIEW,
                    actor=actor,
                    clicked_position=clicked_position,
                    message=(
                        f"Wybrano obiekt: {scene_object.name}. Dostępna akcja: {scene_object.interaction_label}. "
                        "Kliknij to pole ponownie, aby potwierdzić interakcję."
                    ),
                    interaction_object=scene_object,
                    movement_remaining_feet=remaining,
                    action_available=action_available,
                )

    if remaining <= 0:
        return _invalid(actor, clicked_position, remaining, action_available, "Nie masz już ruchu w tej turze.")

    movement_actor = replace(actor, speed_feet=remaining)
    movement_result = movement_range(board, movement_actor, state.actors)
    path = find_path(board, movement_actor, state.actors, clicked_position)
    if path.valid:
        after_move = remaining - path.cost_feet
        return TurnIntentPreview(
            mode=TurnPromptMode.MOVEMENT_PREVIEW,
            actor=actor,
            clicked_position=clicked_position,
            message=(
                f"Wybrano ruch na {clicked_position.as_tuple()}. Koszt: {path.cost_feet} feet. "
                f"Pozostanie: {after_move} feet. Kliknij to pole ponownie, aby potwierdzić ruch."
            ),
            movement_range=movement_result,
            movement_path=path,
            movement_remaining_feet=remaining,
            action_available=action_available,
        )

    if clicked_position == actor.position:
        return _invalid(actor, clicked_position, remaining, action_available, "To jest aktualne pole aktywnego aktora.")
    return _invalid(
        actor,
        clicked_position,
        remaining,
        action_available,
        "To pole nie jest teraz legalnym celem ataku ani legalnym polem ruchu.",
    )


def confirm_turn_intent(state: CombatState, preview: TurnIntentPreview) -> TurnIntentConfirmation:
    if preview.mode == TurnPromptMode.MOVEMENT_PREVIEW and preview.movement_path is not None:
        current = _actor_from_state(state, preview.actor)
        result = use_movement(state, current, preview.movement_path)
        return TurnIntentConfirmation(
            state=result.state,
            accepted=result.accepted,
            mode=TurnPromptMode.RESOLVED if result.accepted else TurnPromptMode.INVALID,
            message=result.message,
            movement_result=result,
        )
    if preview.mode == TurnPromptMode.ATTACK_PREVIEW and preview.attack_target is not None and preview.attack_source is not None:
        return TurnIntentConfirmation(
            state=state,
            accepted=True,
            mode=TurnPromptMode.RESOLVED,
            message=f"Potwierdzono atak na {preview.attack_target.name}.",
            attack_target=preview.attack_target,
            attack_source=preview.attack_source,
        )
    if preview.mode == TurnPromptMode.INTERACTION_PREVIEW and preview.interaction_object is not None:
        action_result = use_turn_action(state)
        return TurnIntentConfirmation(
            state=action_result.state,
            accepted=action_result.accepted,
            mode=TurnPromptMode.RESOLVED if action_result.accepted else TurnPromptMode.INVALID,
            message=(
                f"Potwierdzono interakcję: {preview.interaction_object.interaction_label}."
                if action_result.accepted
                else action_result.message
            ),
            interaction_object=preview.interaction_object if action_result.accepted else None,
        )
    return TurnIntentConfirmation(state, False, TurnPromptMode.INVALID, preview.message)


def _invalid(
    actor: Actor,
    clicked_position: Coordinate,
    remaining: int,
    action_available: bool,
    message: str,
) -> TurnIntentPreview:
    return TurnIntentPreview(
        mode=TurnPromptMode.INVALID,
        actor=actor,
        clicked_position=clicked_position,
        message=message,
        movement_remaining_feet=remaining,
        action_available=action_available,
    )


def _actor_from_state(state: CombatState, actor: Actor) -> Actor:
    for candidate in state.actors:
        if candidate.id == actor.id:
            return candidate
    raise ValueError(f"Unknown actor: {actor.id}.")


def _is_adjacent(a: Coordinate, b: Coordinate) -> bool:
    dc = abs(a.col - b.col)
    dr = abs(a.row - b.row)
    return max(dc, dr) == 1 and (dc != 0 or dr != 0)
