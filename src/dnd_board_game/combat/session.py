from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, ActorId, Faction

from .action_economy import ActionUse, consume_action
from .initiative import InitiativeEntry, InitiativeOrder


class CombatStatus(StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class TurnActionState:
    action_use: ActionUse = ActionUse.ACTION_AVAILABLE


@dataclass(frozen=True, slots=True)
class TurnActionUseResult:
    state: CombatState
    accepted: bool
    message: str


@dataclass(frozen=True, slots=True)
class CombatState:
    actors: tuple[Actor, ...]
    initiative_order: InitiativeOrder
    turn_action: TurnActionState = TurnActionState()
    status: CombatStatus = CombatStatus.ACTIVE
    winner: Faction | None = None

    @property
    def round_number(self) -> int:
        return self.initiative_order.round_number


def start_combat(actors: tuple[Actor, ...], initiative_order: InitiativeOrder) -> CombatState:
    if not actors:
        raise ValueError("Cannot start combat without actors.")
    state = CombatState(actors=actors, initiative_order=_sync_order_actor_states(initiative_order, actors))
    return _with_finished_status(state)


def current_actor(state: CombatState) -> Actor:
    current_id = state.initiative_order.current_actor.id
    return actor_by_id(state, current_id)


def actor_by_id(state: CombatState, actor_id: ActorId) -> Actor:
    for actor in state.actors:
        if actor.id == actor_id:
            return actor
    raise ValueError(f"Unknown combat actor: {actor_id}.")


def replace_actor(state: CombatState, updated_actor: Actor) -> CombatState:
    actors = tuple(updated_actor if actor.id == updated_actor.id else actor for actor in state.actors)
    if all(actor.id != updated_actor.id for actor in state.actors):
        raise ValueError(f"Unknown combat actor: {updated_actor.id}.")
    synced = replace(state, actors=actors, initiative_order=_sync_order_actor_states(state.initiative_order, actors))
    return _with_finished_status(synced)


def use_turn_action(state: CombatState) -> TurnActionUseResult:
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    try:
        action_use = consume_action(state.turn_action.action_use)
    except ValueError:
        return TurnActionUseResult(state, False, "Akcja w tej turze została już zużyta.")
    return TurnActionUseResult(
        replace(state, turn_action=TurnActionState(action_use)),
        True,
        "Akcja została zużyta.",
    )


def finish_turn(state: CombatState) -> CombatState:
    finished_state = _with_finished_status(state)
    if finished_state.status != CombatStatus.ACTIVE:
        return finished_state
    order = _sync_order_actor_states(finished_state.initiative_order, finished_state.actors).advance_turn(skip_defeated=True)
    return replace(finished_state, initiative_order=order, turn_action=TurnActionState())


def stop_combat(state: CombatState) -> CombatState:
    return replace(state, status=CombatStatus.STOPPED)


def combat_is_finished(state: CombatState) -> bool:
    return combat_winner(state) is not None


def combat_winner(state: CombatState) -> Faction | None:
    allies_alive = any(actor.faction == Faction.ALLY and not actor.is_defeated() for actor in state.actors)
    enemies_alive = any(actor.faction == Faction.ENEMY and not actor.is_defeated() for actor in state.actors)
    if allies_alive and not enemies_alive:
        return Faction.ALLY
    if enemies_alive and not allies_alive:
        return Faction.ENEMY
    return None


def _with_finished_status(state: CombatState) -> CombatState:
    winner = combat_winner(state)
    if winner is None:
        return state
    return replace(state, status=CombatStatus.FINISHED, winner=winner)


def _sync_order_actor_states(order: InitiativeOrder, actors: tuple[Actor, ...]) -> InitiativeOrder:
    actor_map = {actor.id: actor for actor in actors}
    entries: list[InitiativeEntry] = []
    for entry in order.entries:
        actor = actor_map.get(entry.actor.id, entry.actor)
        entries.append(replace(entry, actor=actor))
    return InitiativeOrder(tuple(entries), order.current_index, order.round_number)
