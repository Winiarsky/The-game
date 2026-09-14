from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    CombatInteractionOption,
    CombatState,
    CombatStatus,
    SceneObject,
    apply_combat_interaction_effects,
    available_combat_interaction_options,
    available_scene_interactions,
    combat_interaction_hint_positions,
    combat_interaction_positions,
    current_actor,
    expire_invalid_combat_effects,
    scene_object_at_position,
    scene_object_by_id,
    use_turn_action,
    use_action_economy_cost,
    movement_remaining,
    replace_actor,
)
from dnd_board_game.world import BoardState, Coordinate, PathResult, movement_range


@dataclass(frozen=True, slots=True)
class PendingCombatInteraction:
    actor_id: str
    object_id: str
    object_name: str
    target_position: Coordinate
    options: tuple[CombatInteractionOption, ...]

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "object_id": self.object_id,
            "object_name": self.object_name,
            "target_position": [self.target_position.col, self.target_position.row],
            "options": [option.as_payload() for option in self.options],
        }


@dataclass(frozen=True, slots=True)
class CombatApproachInteractionPlan:
    actor_id: str
    interaction_position: Coordinate
    destination: Coordinate
    path: PathResult
    options: tuple[CombatInteractionOption, ...]

    @property
    def object_id(self) -> str:
        if not self.options:
            raise ValueError("Plan podejścia nie ma interakcji.")
        return self.options[0].object_id

    @property
    def object_name(self) -> str:
        if not self.options:
            raise ValueError("Plan podejścia nie ma interakcji.")
        return self.options[0].object_name


@dataclass(frozen=True, slots=True)
class CombatSceneInteractionTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    pending: PendingCombatInteraction | None
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    clear_movement_preview: bool = False
    clear_player_attack: bool = False


@dataclass(frozen=True, slots=True)
class CombatSceneEffectExpiration:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    expired_effects: tuple[ActiveCombatEffect, ...]


class CombatSceneInteractionFlowService:
    """Coordinate combat scene interactions and position-bound effects."""

    def select(
        self,
        *,
        state: CombatState,
        scene_objects: tuple[SceneObject, ...],
        position: Coordinate,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatSceneInteractionTransition:
        actor = _active_hero(state)
        options = available_combat_interaction_options(
            scene_objects,
            state,
            actor,
            position,
        )
        if not options:
            raise ValueError("To pole nie ma teraz dostępnej interakcji.")
        scene_object = scene_object_at_position(scene_objects, position)
        assert scene_object is not None
        pending = PendingCombatInteraction(
            actor_id=str(actor.id),
            object_id=scene_object.id,
            object_name=scene_object.name,
            target_position=position,
            options=options,
        )
        option_labels = ", ".join(option.label for option in options)
        return CombatSceneInteractionTransition(
            state=state,
            active_effects=active_effects,
            pending=pending,
            board_message=(
                f"Wybrano interakcję z obiektem: {scene_object.name}. "
                f"Wybierz w UI: {option_labels}."
            ),
            message_title="Interakcja",
            message_body=(
                f"{actor.name} wybiera {scene_object.name}. "
                f"Dostępne opcje: {option_labels}."
            ),
            event_type="ui_combat_interaction_selected",
            event_payload=(
                ("actor_id", str(actor.id)),
                ("object_id", scene_object.id),
                ("position", [position.col, position.row]),
                ("options", [option.id for option in options]),
            ),
            clear_movement_preview=True,
            clear_player_attack=True,
        )

    def confirm(
        self,
        *,
        state: CombatState,
        scene_objects: tuple[SceneObject, ...],
        active_effects: tuple[ActiveCombatEffect, ...],
        pending: PendingCombatInteraction,
        interaction_id: str,
        rng: Random,
    ) -> CombatSceneInteractionTransition:
        actor = _active_hero(state)
        if str(actor.id) != pending.actor_id:
            raise ValueError("Oczekująca interakcja nie należy do aktywnego aktora.")
        option = next(
            (candidate for candidate in pending.options if candidate.id == interaction_id),
            None,
        )
        if option is None:
            raise ValueError("Nieznana opcja interakcji.")
        action_result = use_action_economy_cost(state, option.action_cost)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        scene_object = scene_object_by_id(scene_objects, option.object_id)
        if scene_object is None:
            raise ValueError("Obiekt interakcji nie istnieje w aktywnym encounterze.")
        interaction = next(
            (
                candidate
                for candidate in available_scene_interactions(scene_object)
                if candidate.id == option.id
            ),
            None,
        )
        if interaction is None:
            raise ValueError("Interakcja nie istnieje w aktywnym encounterze.")
        applied = apply_combat_interaction_effects(
            state=action_result.state,
            actor=actor,
            scene_object=scene_object,
            interaction=interaction,
            target_position=option.target_position,
            active_effects=active_effects,
            rng=rng,
        )
        message = f"{actor.name}: {applied.message}"
        return CombatSceneInteractionTransition(
            state=applied.state,
            active_effects=applied.active_effects,
            pending=None,
            board_message=message,
            message_title="Interakcja",
            message_body=message,
            event_type="ui_combat_interaction_confirmed",
            event_payload=(
                ("actor_id", str(actor.id)),
                ("object_id", scene_object.id),
                ("interaction_id", option.id),
                ("message", message),
                (
                    "saving_throw",
                    (
                        applied.saving_throw.as_payload()
                        if applied.saving_throw is not None
                        else None
                    ),
                ),
            ),
            clear_movement_preview=True,
        )

    def cancel(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        pending: PendingCombatInteraction,
    ) -> CombatSceneInteractionTransition:
        return CombatSceneInteractionTransition(
            state=state,
            active_effects=active_effects,
            pending=None,
            board_message=(
                "Anulowano interakcję. "
                "Kliknij Skanuj planszę, żeby wybrać ruch, cel albo obiekt."
            ),
            message_title="Interakcja",
            message_body="Anulowano wybór interakcji.",
            event_type="ui_combat_interaction_cancelled",
            event_payload=(
                ("actor_id", pending.actor_id),
                ("object_id", pending.object_id),
            ),
        )

    def options(
        self,
        *,
        state: CombatState,
        scene_objects: tuple[SceneObject, ...],
        actor: Actor,
        position: Coordinate,
    ) -> tuple[CombatInteractionOption, ...]:
        if state.status != CombatStatus.ACTIVE or actor.faction != Faction.ALLY:
            return ()
        return available_combat_interaction_options(
            scene_objects,
            state,
            actor,
            position,
        )

    def plan_approach(
        self,
        *,
        state: CombatState,
        board: BoardState,
        scene_objects: tuple[SceneObject, ...],
        actor: Actor,
        position: Coordinate,
    ) -> CombatApproachInteractionPlan | None:
        if state.status != CombatStatus.ACTIVE or actor.faction != Faction.ALLY:
            return None
        scene_object = scene_object_at_position(scene_objects, position)
        if scene_object is None or not available_scene_interactions(scene_object):
            return None

        remaining = movement_remaining(state, actor)
        movement_actor = replace(actor, speed_feet=remaining)
        reachable = movement_range(board, movement_actor, state.actors)
        # The range already contains shortest paths to every reachable tile.
        # Re-running find_path for each candidate repeats the whole search.
        for destination in sorted(
            reachable.reachable_tiles,
            key=lambda tile: (reachable.costs_by_tile[tile], tile.col, tile.row),
        ):
            moved_actor = replace(actor, position=destination)
            moved_state = replace_actor(state, moved_actor)
            options = available_combat_interaction_options(
                scene_objects,
                moved_state,
                moved_actor,
                position,
            )
            if not options:
                continue
            return CombatApproachInteractionPlan(
                actor_id=str(actor.id),
                interaction_position=position,
                destination=destination,
                path=PathResult(
                    reachable.origin, destination, reachable.paths_by_tile[destination],
                    reachable.costs_by_tile[destination], True,
                ),
                options=options,
            )
        return None

    def positions(
        self,
        *,
        state: CombatState,
        scene_objects: tuple[SceneObject, ...],
        actor: Actor,
    ) -> tuple[Coordinate, ...]:
        return combat_interaction_positions(scene_objects, state, actor)

    def hint_positions(
        self,
        *,
        state: CombatState,
        scene_objects: tuple[SceneObject, ...],
        actor: Actor,
        reachable_tiles: frozenset[Coordinate],
    ) -> tuple[Coordinate, ...]:
        return combat_interaction_hint_positions(
            scene_objects,
            state,
            actor,
            reachable_tiles,
        )

    def expire_invalid_effects(
        self,
        *,
        state: CombatState,
        scene_objects: tuple[SceneObject, ...],
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatSceneEffectExpiration:
        updated_state, updated_effects = expire_invalid_combat_effects(
            state,
            scene_objects,
            active_effects,
        )
        remaining_ids = {effect.id for effect in updated_effects}
        expired = tuple(
            effect for effect in active_effects if effect.id not in remaining_ids
        )
        return CombatSceneEffectExpiration(updated_state, updated_effects, expired)


def _active_hero(state: CombatState) -> Actor:
    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Walka nie jest aktywna.")
    actor = current_actor(state)
    if actor.faction != Faction.ALLY:
        raise ValueError("To nie jest tura bohatera.")
    return actor
