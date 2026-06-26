from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor
from dnd_board_game.world import BoardState, Coordinate, MovementRangeResult, PathResult, find_path, movement_range

from .action_economy import ActionUse
from .attack_flow import AttackSource, legal_melee_targets
from .scene import SceneObject, available_scene_interactions, visible_scene_objects
from .session import CombatState, TurnMovementUseResult, movement_remaining, use_movement
from .session import use_turn_action
from .targets import CombatTarget


class TurnPromptMode(StrEnum):
    IDLE = "idle"
    ACTOR_OPTIONS_PREVIEW = "actor_options_preview"
    TILE_OPTIONS_PREVIEW = "tile_options_preview"
    MOVEMENT_PREVIEW = "movement_preview"
    ATTACK_PREVIEW = "attack_preview"
    INTERACTION_PREVIEW = "interaction_preview"
    INVALID = "invalid"
    RESOLVED = "resolved"


class TileOptionKind(StrEnum):
    ATTACK = "attack"
    INTERACTION = "interaction"


@dataclass(frozen=True, slots=True)
class TileOption:
    kind: TileOptionKind
    label: str
    message: str
    attack_target: CombatTarget | None = None
    attack_source: AttackSource | None = None
    interaction_object: SceneObject | None = None


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
    tile_options: tuple[TileOption, ...] = ()
    selected_tile_option_index: int = 0
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
    end_turn_requested: bool = False


def preview_turn_intent(
    board: BoardState,
    state: CombatState,
    actor: Actor,
    attack_source: AttackSource,
    clicked_position: Coordinate,
    interactables: tuple[SceneObject, ...] = (),
    selected_tile_option_index: int = 0,
) -> TurnIntentPreview:
    remaining = movement_remaining(state, actor)
    action_available = state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    if actor.is_defeated():
        return _invalid(actor, clicked_position, remaining, action_available, "Pokonany aktor nie może działać.")
    if not board.in_bounds(clicked_position):
        return _invalid(actor, clicked_position, remaining, action_available, "Kliknięte pole jest poza planszą.")
    if clicked_position == actor.position:
        return TurnIntentPreview(
            mode=TurnPromptMode.ACTOR_OPTIONS_PREVIEW,
            actor=actor,
            clicked_position=clicked_position,
            message=(
                f"Opcje aktora: {actor.name}. Dostępna opcja: zakończ turę. "
                "Kliknij to pole ponownie, aby zakończyć turę."
            ),
            movement_remaining_feet=remaining,
            action_available=action_available,
        )

    if action_available:
        tile_options = _tile_options_for_position(board, state, actor, attack_source, clicked_position, interactables)
        if len(tile_options) == 1:
            option = tile_options[0]
            return _preview_from_tile_option(actor, clicked_position, remaining, action_available, option)
        if len(tile_options) > 1:
            selected_index = selected_tile_option_index % len(tile_options)
            option = tile_options[selected_index]
            return TurnIntentPreview(
                mode=TurnPromptMode.TILE_OPTIONS_PREVIEW,
                actor=actor,
                clicked_position=clicked_position,
                message=(
                    f"Na tym polu jest kilka opcji. Wybrano: {option.label}. "
                    "Kliknij to pole ponownie, aby przełączyć opcję. Naciśnij Enter, aby potwierdzić."
                ),
                attack_target=option.attack_target,
                attack_source=option.attack_source,
                interaction_object=option.interaction_object,
                tile_options=tile_options,
                selected_tile_option_index=selected_index,
                movement_remaining_feet=remaining,
                action_available=action_available,
            )

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

    return _invalid(
        actor,
        clicked_position,
        remaining,
        action_available,
        "To pole nie jest teraz legalnym celem ataku ani legalnym polem ruchu.",
    )


def confirm_turn_intent(state: CombatState, preview: TurnIntentPreview) -> TurnIntentConfirmation:
    if preview.mode == TurnPromptMode.ACTOR_OPTIONS_PREVIEW:
        return TurnIntentConfirmation(
            state=state,
            accepted=True,
            mode=TurnPromptMode.RESOLVED,
            message=f"{preview.actor.name} kończy turę.",
            end_turn_requested=True,
        )
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
    if preview.mode == TurnPromptMode.TILE_OPTIONS_PREVIEW:
        option = preview.tile_options[preview.selected_tile_option_index]
        if option.kind == TileOptionKind.ATTACK and option.attack_target is not None and option.attack_source is not None:
            return TurnIntentConfirmation(
                state=state,
                accepted=True,
                mode=TurnPromptMode.RESOLVED,
                message=f"Potwierdzono: {option.label}.",
                attack_target=option.attack_target,
                attack_source=option.attack_source,
            )
        if option.kind == TileOptionKind.INTERACTION and option.interaction_object is not None:
            return _confirm_interaction_option(state, option.interaction_object)
    if preview.mode == TurnPromptMode.INTERACTION_PREVIEW and preview.interaction_object is not None:
        return _confirm_interaction_option(state, preview.interaction_object)
    return TurnIntentConfirmation(state, False, TurnPromptMode.INVALID, preview.message)


def _confirm_interaction_option(state: CombatState, scene_object: SceneObject) -> TurnIntentConfirmation:
    action_result = use_turn_action(state)
    return TurnIntentConfirmation(
        state=action_result.state,
        accepted=action_result.accepted,
        mode=TurnPromptMode.RESOLVED if action_result.accepted else TurnPromptMode.INVALID,
        message=(
            f"Potwierdzono interakcję: {scene_object.interaction_label}."
            if action_result.accepted
            else action_result.message
        ),
        interaction_object=scene_object if action_result.accepted else None,
    )


def _tile_options_for_position(
    board: BoardState,
    state: CombatState,
    actor: Actor,
    attack_source: AttackSource,
    clicked_position: Coordinate,
    interactables: tuple[SceneObject, ...],
) -> tuple[TileOption, ...]:
    options: list[TileOption] = []
    legal_targets = legal_melee_targets(board, actor, state.actors)
    target_on_tile = next((target for target in legal_targets if target.position == clicked_position), None)
    if target_on_tile is not None:
        options.append(
            TileOption(
                kind=TileOptionKind.ATTACK,
                label=f"Atak na {target_on_tile.name}",
                message=(
                    f"Wybrano cel: {target_on_tile.name}. Dostępna akcja: Atak {attack_source.name}. "
                    "Rzuć po potwierdzeniu."
                ),
                attack_target=target_on_tile,
                attack_source=attack_source,
            )
        )

    has_enemy_on_tile = any(
        other.position == clicked_position
        and other.id != actor.id
        and other.faction != actor.faction
        and not other.is_defeated()
        for other in state.actors
    )
    for scene_object in visible_scene_objects(interactables):
        if clicked_position not in scene_object.positions:
            continue
        if has_enemy_on_tile and not scene_object.allow_interaction_when_occupied_by_enemy:
            continue
        if not _is_adjacent(actor.position, scene_object.primary_position):
            continue
        interactions = available_scene_interactions(scene_object)
        interaction_label = interactions[0].label if interactions else scene_object.interaction_label
        options.append(
            TileOption(
                kind=TileOptionKind.INTERACTION,
                label=f"Interakcja: {interaction_label}",
                message=f"Wybrano obiekt: {scene_object.name}. Dostępna akcja: {interaction_label}.",
                interaction_object=scene_object,
            )
        )
    return tuple(options)


def _preview_from_tile_option(
    actor: Actor,
    clicked_position: Coordinate,
    remaining: int,
    action_available: bool,
    option: TileOption,
) -> TurnIntentPreview:
    if option.kind == TileOptionKind.ATTACK:
        return TurnIntentPreview(
            mode=TurnPromptMode.ATTACK_PREVIEW,
            actor=actor,
            clicked_position=clicked_position,
            message=f"{option.message} Kliknij to pole ponownie, aby potwierdzić atak.",
            attack_target=option.attack_target,
            attack_source=option.attack_source,
            movement_remaining_feet=remaining,
            action_available=action_available,
        )
    return TurnIntentPreview(
        mode=TurnPromptMode.INTERACTION_PREVIEW,
        actor=actor,
        clicked_position=clicked_position,
        message=f"{option.message} Kliknij to pole ponownie, aby potwierdzić interakcję.",
        interaction_object=option.interaction_object,
        movement_remaining_feet=remaining,
        action_available=action_available,
    )


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
