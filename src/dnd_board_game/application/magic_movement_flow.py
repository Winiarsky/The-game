from __future__ import annotations

from dnd_board_game.combat.saving_effects import consume_saving_effects, has_wisdom_save_penalty

from dataclasses import dataclass, replace
from random import Random
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import Actor
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    CombatState,
    MagicMovementDefinition,
    MagicMovementKind,
    SceneObject,
    actor_spell_cast_validation,
    current_actor,
    forced_movement_destination,
    legal_forced_movement_targets,
    legal_teleport_positions,
    move_actor_magically,
    resolve_spell_save,
    reveal_actor,
)
from dnd_board_game.world import BoardState, Coordinate


class MagicMovementActionSpec(Protocol):
    id: str
    action_type: str
    label: str
    range_feet: int
    spell_level: int
    action_cost: ActionEconomyCost
    save_ability: str | None
    save_dc: int | None
    movement: MagicMovementDefinition | None


@dataclass(frozen=True, slots=True)
class PendingMagicMovement:
    caster_id: str
    action_id: str
    cast_level: int
    kind: MagicMovementKind
    legal_positions: tuple[Coordinate, ...] = ()
    legal_target_ids: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "caster_id": self.caster_id,
            "action_id": self.action_id,
            "cast_level": self.cast_level,
            "kind": self.kind.value,
            "legal_positions": [
                {"col": position.col, "row": position.row}
                for position in self.legal_positions
            ],
            "legal_target_ids": list(self.legal_target_ids),
        }


@dataclass(frozen=True, slots=True)
class MagicMovementTransition:
    state: CombatState
    pending: PendingMagicMovement | None
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    active_effects: tuple[ActiveCombatEffect, ...] | None = None
    moved_actor_id: str | None = None
    origin: Coordinate | None = None
    destination: Coordinate | None = None


class MagicMovementFlowService:
    """Resolve teleport and save-based forced movement spells."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()

    def prepare(
        self,
        *,
        board: BoardState,
        state: CombatState,
        action: MagicMovementActionSpec,
        cast_level: int | None = None,
        scene_objects: tuple[SceneObject, ...] = (),
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> MagicMovementTransition:
        caster = current_actor(state)
        definition = _movement_definition(action)
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=cast_level,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        positions: tuple[Coordinate, ...] = ()
        target_ids: tuple[str, ...] = ()
        if definition.kind == MagicMovementKind.TELEPORT:
            positions = legal_teleport_positions(
                board,
                state,
                caster,
                distance_feet=definition.distance_feet,
                scene_objects=scene_objects,
            )
            if not positions:
                raise ValueError("Brak legalnego pola teleportacji.")
            instruction = "Wybierz podświetlone pole teleportacji."
        else:
            targets = legal_forced_movement_targets(
                board,
                state,
                caster,
                kind=definition.kind,
                range_feet=action.range_feet,
                distance_feet=definition.distance_feet,
                scene_objects=scene_objects,
            )
            target_ids = tuple(str(target.id) for target in targets)
            if not target_ids:
                raise ValueError("Brak legalnego celu wymuszonego ruchu.")
            instruction = "Wybierz podświetlony cel czaru."
        pending = PendingMagicMovement(
            caster_id=str(caster.id),
            action_id=action.id,
            cast_level=validation.cast_level,
            kind=definition.kind,
            legal_positions=positions,
            legal_target_ids=target_ids,
        )
        return MagicMovementTransition(
            state=state,
            pending=pending,
            message_title="Magiczny ruch",
            message_body=f"{caster.name} przygotowuje {action.label}. {instruction}",
            event_type="ui_combat_magic_movement_started",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", validation.cast_level),
                ("kind", definition.kind.value),
            ),
        )

    def confirm(
        self,
        *,
        board: BoardState,
        state: CombatState,
        action: MagicMovementActionSpec,
        pending: PendingMagicMovement,
        rng: Random,
        position: Coordinate | None = None,
        target_id: str | None = None,
        scene_objects: tuple[SceneObject, ...] = (),
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> MagicMovementTransition:
        caster = current_actor(state)
        definition = _movement_definition(action)
        if (
            str(caster.id) != pending.caster_id
            or action.id != pending.action_id
            or definition.kind != pending.kind
        ):
            raise ValueError("Oczekujący magiczny ruch nie należy do aktywnego aktora.")
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=pending.cast_level,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        if definition.kind == MagicMovementKind.TELEPORT:
            return self._confirm_teleport(
                board=board,
                state=state,
                caster=caster,
                action=action,
                pending=pending,
                position=position,
                scene_objects=scene_objects,
            )
        return self._confirm_forced_movement(
            board=board,
            state=state,
            caster=caster,
            action=action,
            pending=pending,
            target_id=target_id,
            rng=rng,
            scene_objects=scene_objects,
            active_effects=active_effects,
        )

    def cancel(
        self,
        *,
        state: CombatState,
        pending: PendingMagicMovement,
    ) -> MagicMovementTransition:
        return MagicMovementTransition(
            state=state,
            pending=None,
            message_title="Magiczny ruch",
            message_body="Anulowano czar. Akcja i slot nie zostały zużyte.",
            event_type="ui_combat_magic_movement_cancelled",
            event_payload=(
                ("caster_id", pending.caster_id),
                ("spell_id", pending.action_id),
            ),
        )

    def _confirm_teleport(
        self,
        *,
        board: BoardState,
        state: CombatState,
        caster: Actor,
        action: MagicMovementActionSpec,
        pending: PendingMagicMovement,
        position: Coordinate | None,
        scene_objects: tuple[SceneObject, ...],
    ) -> MagicMovementTransition:
        assert action.movement is not None
        legal = legal_teleport_positions(
            board,
            state,
            caster,
            distance_feet=action.movement.distance_feet,
            scene_objects=scene_objects,
        )
        if position is None or position not in pending.legal_positions or position not in legal:
            raise ValueError("Wybrane pole nie jest legalnym celem teleportacji.")
        resource = self._consume(state, caster, action, pending.cast_level)
        caster_after = _actor_by_id(resource.state, str(caster.id))
        updated = move_actor_magically(resource.state, caster_after, position)
        updated = replace(
            updated,
            hidden_states=reveal_actor(updated.hidden_states, str(caster.id)),
        )
        message = (
            f"{caster.name} rzuca {action.label} i teleportuje się z "
            f"{caster.position.as_tuple()} na {position.as_tuple()}."
        )
        return MagicMovementTransition(
            state=updated,
            pending=None,
            message_title="Teleportacja",
            message_body=message,
            event_type="ui_combat_teleport_confirmed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", pending.cast_level),
                ("origin", list(caster.position.as_tuple())),
                ("destination", list(position.as_tuple())),
            ),
            moved_actor_id=str(caster.id),
            origin=caster.position,
            destination=position,
        )

    def _confirm_forced_movement(
        self,
        *,
        board: BoardState,
        state: CombatState,
        caster: Actor,
        action: MagicMovementActionSpec,
        pending: PendingMagicMovement,
        target_id: str | None,
        rng: Random,
        scene_objects: tuple[SceneObject, ...],
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> MagicMovementTransition:
        assert action.movement is not None
        legal_targets = legal_forced_movement_targets(
            board,
            state,
            caster,
            kind=action.movement.kind,
            range_feet=action.range_feet,
            distance_feet=action.movement.distance_feet,
            scene_objects=scene_objects,
        )
        legal_ids = {str(target.id) for target in legal_targets}
        if (
            target_id is None
            or target_id not in pending.legal_target_ids
            or target_id not in legal_ids
        ):
            raise ValueError("Wybrany aktor nie jest legalnym celem tego czaru.")
        target = _actor_by_id(state, target_id)
        resource = self._consume(state, caster, action, pending.cast_level)
        target_after = _actor_by_id(resource.state, target_id)
        save_dc = action.save_dc or caster.spell_save_dc
        save = resolve_spell_save(
            target_after,
            ability=action.save_ability or "strength",
            dc=save_dc,
            natural_roll=rng.randint(1, 20),
            natural_roll_2=rng.randint(1, 20) if has_wisdom_save_penalty(str(target_after.id), action.save_ability or "strength", active_effects) else None,
            active_effects=active_effects,
            condition_states=resource.state.condition_states,
            combat_actors=resource.state.actors,
        )
        destination = target_after.position
        updated = resource.state
        if not save.success:
            destination = forced_movement_destination(
                board,
                resource.state,
                caster,
                target_after,
                kind=action.movement.kind,
                distance_feet=action.movement.distance_feet,
                scene_objects=scene_objects,
            )
            updated = move_actor_magically(updated, target_after, destination)
        updated = replace(
            updated,
            hidden_states=reveal_actor(updated.hidden_states, str(caster.id)),
        )
        verb = "odpycha" if action.movement.kind == MagicMovementKind.PUSH else "przyciąga"
        outcome = (
            f"{target.name} utrzymuje pozycję"
            if save.success
            else f"{target.name} trafia na {destination.as_tuple()}"
        )
        message = (
            f"{caster.name} rzuca {action.label}: {verb} cel do "
            f"{action.movement.distance_feet} ft. Save {save.total}/{save_dc}: {outcome}."
        )
        return MagicMovementTransition(
            state=updated,
            pending=None,
            message_title="Wymuszony ruch",
            message_body=message,
            active_effects=consume_saving_effects(active_effects, save),
            event_type="ui_combat_forced_movement_confirmed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("target_id", target_id),
                ("spell_id", action.id),
                ("cast_level", pending.cast_level),
                ("kind", action.movement.kind.value),
                ("save", save.as_payload()),
                ("origin", list(target.position.as_tuple())),
                ("destination", list(destination.as_tuple())),
            ),
            moved_actor_id=(target_id if destination != target.position else None),
            origin=target.position,
            destination=destination,
        )

    def _consume(
        self,
        state: CombatState,
        caster: Actor,
        action: MagicMovementActionSpec,
        cast_level: int,
    ):
        return self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=cast_level,
            action_cost=action.action_cost,
        )


def _movement_definition(
    action: MagicMovementActionSpec,
) -> MagicMovementDefinition:
    if action.action_type != "spell_movement" or action.movement is None:
        raise ValueError("Ta akcja nie jest czarem przemieszczającym.")
    return action.movement


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    return next(
        actor for actor in state.actors if str(actor.id) == actor_id
    )
