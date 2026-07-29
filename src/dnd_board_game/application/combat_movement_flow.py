from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    CombatState,
    CombatStatus,
    SceneObject,
    current_actor,
    grid_distance_feet,
    grappled_actor_ids,
    movement_remaining,
    opportunity_attackers_for_movement,
    path_with_condition_cost,
    refresh_hidden_after_movement,
    use_movement,
)
from dnd_board_game.world import (
    DIFFICULT_TERRAIN,
    BoardState,
    Coordinate,
    PathResult,
    find_path,
)


@dataclass(frozen=True, slots=True)
class CombatMovementPreview:
    actor_id: str
    destination: Coordinate
    path: PathResult
    board_message: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class CombatMovementSubmission:
    state: CombatState
    actor_id: str
    destination: Coordinate
    path: PathResult
    movement_remaining_feet: int
    requires_opportunity_confirmation: bool
    threat_actor_ids: tuple[str, ...]
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class CombatMovementFlowService:
    """Plan and apply deterministic player movement during combat."""

    def preview(
        self,
        *,
        state: CombatState,
        board: BoardState,
        destination: Coordinate,
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> CombatMovementPreview:
        actor, path = self._plan_path(
            state=state,
            board=board,
            destination=destination,
            active_effects=active_effects,
            invalid_path_message="Nie można dojść do wskazanego pola.",
        )
        dragged = _dragged_actor_for_path(state, actor, path)
        dragged_message = (
            f" Po ruchu przestaw {dragged.name} na {path.path[-2].as_tuple()}."
            if dragged is not None
            else ""
        )
        return CombatMovementPreview(
            actor_id=str(actor.id),
            destination=destination,
            path=path,
            board_message=(
                f"Wybrano ścieżkę ruchu {actor.name} -> {destination.as_tuple()} "
                f"({path.cost_feet} ft). Kliknij to pole ponownie, żeby zatwierdzić."
                f"{dragged_message}"
            ),
            event_type="ui_combat_movement_previewed",
            event_payload=(
                *_movement_event_payload(actor, destination, path),
                *(_dragged_event_payload(dragged, path) if dragged is not None else ()),
            ),
        )

    def submit(
        self,
        *,
        state: CombatState,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        destination: Coordinate,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> CombatMovementSubmission:
        actor, path = self._plan_path(
            state=state,
            board=board,
            destination=destination,
            active_effects=active_effects,
            invalid_path_message="Nie można wykonać ruchu na wybrane pole.",
        )
        threats = opportunity_attackers_for_movement(
            state,
            actor,
            actor.position,
            destination,
            attack_sources_by_actor,
            active_effects,
        )
        if threats:
            threat_actor_ids = tuple(str(threat.attacker.id) for threat in threats)
            threat_names = ", ".join(threat.attacker.name for threat in threats)
            return CombatMovementSubmission(
                state=state,
                actor_id=str(actor.id),
                destination=destination,
                path=path,
                movement_remaining_feet=movement_remaining(
                    state,
                    actor,
                    active_effects,
                ),
                requires_opportunity_confirmation=True,
                threat_actor_ids=threat_actor_ids,
                board_message=(
                    f"Ten ruch prowokuje atak okazyjny: {threat_names}. "
                    "Potwierdź Enterem albo przyciskiem."
                ),
                message_title="Atak okazyjny",
                message_body=(
                    f"{actor.name} opuszcza zasięg wroga. Zagrożenia: {threat_names}. "
                    "Potwierdź ruch, żeby rozstrzygnąć reakcje."
                ),
                event_type="ui_combat_opportunity_movement_pending",
                event_payload=(
                    ("actor_id", str(actor.id)),
                    ("destination", [destination.col, destination.row]),
                    ("threat_actor_ids", list(threat_actor_ids)),
                ),
            )

        dragged = _dragged_actor_for_path(state, actor, path)
        movement = use_movement(state, actor, path, active_effects)
        if not movement.accepted:
            raise ValueError(movement.message)
        moved_actor = current_actor(movement.state)
        hidden = refresh_hidden_after_movement(
            board,
            moved_actor,
            movement.state.actors,
            movement.state.hidden_states,
            scene_objects,
        )
        updated_state = replace(movement.state, hidden_states=hidden.hidden_states)
        return CombatMovementSubmission(
            state=updated_state,
            actor_id=str(actor.id),
            destination=destination,
            path=path,
            movement_remaining_feet=movement.movement_remaining_feet,
            requires_opportunity_confirmation=False,
            threat_actor_ids=(),
            board_message="",
            message_title="Ruch",
            message_body=movement.message,
            event_type="ui_combat_player_moved",
            event_payload=(
                *_movement_event_payload(actor, destination, path),
                *(_dragged_event_payload(dragged, path) if dragged is not None else ()),
                ("movement_remaining_feet", movement.movement_remaining_feet),
                ("revealed_to_actor_ids", list(hidden.revealed_to_actor_ids)),
            ),
        )

    @staticmethod
    def _plan_path(
        *,
        state: CombatState,
        board: BoardState,
        destination: Coordinate,
        invalid_path_message: str,
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> tuple[Actor, PathResult]:
        if state.status != CombatStatus.ACTIVE:
            raise ValueError("Walka nie jest aktywna.")
        actor = current_actor(state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        movement_actor = replace(
            actor,
            speed_feet=movement_remaining(state, actor, active_effects),
        )
        movement_board = _board_with_spell_zone_terrain(
            board,
            active_effects,
        )
        path = find_path(
            movement_board,
            movement_actor,
            state.actors,
            destination,
        )
        path = path_with_condition_cost(
            path,
            state.condition_states,
            str(actor.id),
            movement_budget_feet=movement_remaining(
                state,
                actor,
                active_effects,
            ),
        )
        if not path.valid:
            raise ValueError(invalid_path_message)
        return actor, path


def _board_with_spell_zone_terrain(
    board: BoardState,
    active_effects: tuple[ActiveCombatEffect, ...],
) -> BoardState:
    zones = tuple(
        effect
        for effect in active_effects
        if effect.kind in {
            "spike_growth_zone",
            "web_zone",
            "entangle_zone",
            "grease_zone",
        }
        and effect.anchor_position is not None
    )
    if not zones:
        return board
    overlaid = BoardState(
        dimensions=board.dimensions,
        terrain_by_tile=dict(board.terrain_by_tile),
        walls=set(board.walls),
        doors=dict(board.doors),
    )
    for row in range(board.dimensions.rows):
        for col in range(board.dimensions.cols):
            position = Coordinate(col, row)
            if overlaid.terrain_at(position).blocks_movement:
                continue
            if any(_position_in_difficult_zone(position, zone) for zone in zones):
                overlaid.set_terrain(position, DIFFICULT_TERRAIN)
    return overlaid


def _position_in_difficult_zone(
    position: Coordinate,
    zone: ActiveCombatEffect,
) -> bool:
    assert zone.anchor_position is not None
    if zone.kind in {"web_zone", "entangle_zone", "grease_zone"}:
        side = max(1, zone.value // 5)
        before = (side - 1) // 2
        after = side - before - 1
        return (
            zone.anchor_position.col - before
            <= position.col
            <= zone.anchor_position.col + after
            and zone.anchor_position.row - before
            <= position.row
            <= zone.anchor_position.row + after
        )
    return grid_distance_feet(position, zone.anchor_position) <= zone.value


def _movement_event_payload(
    actor: Actor,
    destination: Coordinate,
    path: PathResult,
) -> tuple[tuple[str, object], ...]:
    return (
        ("actor_id", str(actor.id)),
        ("destination", [destination.col, destination.row]),
        ("path", [[position.col, position.row] for position in path.path]),
        ("cost_feet", path.cost_feet),
    )


def _dragged_actor_for_path(
    state: CombatState,
    actor: Actor,
    path: PathResult,
) -> Actor | None:
    if len(path.path) < 2:
        return None
    dragged_ids = grappled_actor_ids(state.condition_states, str(actor.id))
    if not dragged_ids:
        return None
    return next(
        (candidate for candidate in state.actors if str(candidate.id) == dragged_ids[0]),
        None,
    )


def _dragged_event_payload(
    dragged: Actor,
    path: PathResult,
) -> tuple[tuple[str, object], ...]:
    destination = path.path[-2]
    return (
        ("dragged_actor_id", str(dragged.id)),
        ("dragged_destination", [destination.col, destination.row]),
    )
