from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    CombatState,
    CombatStatus,
    current_actor,
    movement_remaining,
    opportunity_attackers_for_movement,
    use_movement,
)
from dnd_board_game.world import BoardState, Coordinate, PathResult, find_path


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
    ) -> CombatMovementPreview:
        actor, path = self._plan_path(
            state=state,
            board=board,
            destination=destination,
            invalid_path_message="Nie można dojść do wskazanego pola.",
        )
        return CombatMovementPreview(
            actor_id=str(actor.id),
            destination=destination,
            path=path,
            board_message=(
                f"Wybrano ścieżkę ruchu {actor.name} -> {destination.as_tuple()} "
                f"({path.cost_feet} ft). Kliknij to pole ponownie, żeby zatwierdzić."
            ),
            event_type="ui_combat_movement_previewed",
            event_payload=_movement_event_payload(actor, destination, path),
        )

    def submit(
        self,
        *,
        state: CombatState,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        destination: Coordinate,
    ) -> CombatMovementSubmission:
        actor, path = self._plan_path(
            state=state,
            board=board,
            destination=destination,
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
                movement_remaining_feet=movement_remaining(state, actor),
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

        movement = use_movement(state, actor, path)
        if not movement.accepted:
            raise ValueError(movement.message)
        return CombatMovementSubmission(
            state=movement.state,
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
                ("movement_remaining_feet", movement.movement_remaining_feet),
            ),
        )

    @staticmethod
    def _plan_path(
        *,
        state: CombatState,
        board: BoardState,
        destination: Coordinate,
        invalid_path_message: str,
    ) -> tuple[Actor, PathResult]:
        if state.status != CombatStatus.ACTIVE:
            raise ValueError("Walka nie jest aktywna.")
        actor = current_actor(state)
        if actor.faction != Faction.ALLY:
            raise ValueError("To nie jest tura bohatera.")
        movement_actor = replace(actor, speed_feet=movement_remaining(state, actor))
        path = find_path(board, movement_actor, state.actors, destination)
        if not path.valid:
            raise ValueError(invalid_path_message)
        return actor, path


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
