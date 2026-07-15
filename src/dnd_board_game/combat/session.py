from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.world import PathResult

from .action_economy import ActionUse, consume_action
from .initiative import InitiativeEntry, InitiativeOrder


class CombatStatus(StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class TurnActionState:
    action_use: ActionUse = ActionUse.ACTION_AVAILABLE
    bonus_action_use: ActionUse = ActionUse.ACTION_AVAILABLE
    reaction_available: bool = True
    movement_used_feet: int = 0
    extra_movement_feet: int = 0


@dataclass(frozen=True, slots=True)
class TurnActionUseResult:
    state: CombatState
    accepted: bool
    message: str


@dataclass(frozen=True, slots=True)
class TurnMovementUseResult:
    state: CombatState
    accepted: bool
    message: str
    movement_remaining_feet: int


@dataclass(frozen=True, slots=True)
class CombatState:
    actors: tuple[Actor, ...]
    initiative_order: InitiativeOrder
    turn_action: TurnActionState = TurnActionState()
    status: CombatStatus = CombatStatus.ACTIVE
    winner: Faction | None = None
    spent_reaction_actor_ids: frozenset[ActorId] = frozenset()

    @property
    def round_number(self) -> int:
        return self.initiative_order.round_number


def start_combat(
    actors: tuple[Actor, ...],
    initiative_order: InitiativeOrder,
) -> CombatState:
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
        replace(state, turn_action=replace(state.turn_action, action_use=action_use)),
        True,
        "Akcja została zużyta.",
    )


def use_bonus_action(state: CombatState) -> TurnActionUseResult:
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    try:
        bonus_action_use = consume_action(state.turn_action.bonus_action_use)
    except ValueError:
        return TurnActionUseResult(state, False, "Akcja bonusowa w tej turze została już zużyta.")
    return TurnActionUseResult(
        replace(state, turn_action=replace(state.turn_action, bonus_action_use=bonus_action_use)),
        True,
        "Akcja bonusowa została zużyta.",
    )


def use_reaction(state: CombatState) -> TurnActionUseResult:
    return use_actor_reaction(state, current_actor(state))


def reaction_available_for(state: CombatState, actor: Actor) -> bool:
    return state.status == CombatStatus.ACTIVE and actor.id not in state.spent_reaction_actor_ids


def use_actor_reaction(state: CombatState, actor: Actor) -> TurnActionUseResult:
    if state.status != CombatStatus.ACTIVE:
        return TurnActionUseResult(state, False, "Walka nie jest aktywna.")
    if not reaction_available_for(state, actor):
        return TurnActionUseResult(state, False, "Reakcja w tej rundzie została już zużyta.")
    spent = frozenset((*state.spent_reaction_actor_ids, actor.id))
    turn_action = state.turn_action
    if actor.id == current_actor(state).id:
        turn_action = replace(turn_action, reaction_available=False)
    return TurnActionUseResult(
        replace(state, spent_reaction_actor_ids=spent, turn_action=turn_action),
        True,
        "Reakcja została zużyta.",
    )


def movement_remaining(state: CombatState, actor: Actor) -> int:
    return max(0, actor.speed_feet + state.turn_action.extra_movement_feet - state.turn_action.movement_used_feet)


def use_dash(state: CombatState, actor: Actor) -> TurnActionUseResult:
    if actor.id != current_actor(state).id:
        return TurnActionUseResult(state, False, "To nie jest tura tego aktora.")
    action_result = use_turn_action(state)
    if not action_result.accepted:
        return action_result
    updated = replace(
        action_result.state,
        turn_action=replace(
            action_result.state.turn_action,
            extra_movement_feet=action_result.state.turn_action.extra_movement_feet + actor.speed_feet,
        ),
    )
    return TurnActionUseResult(updated, True, f"Dash: {actor.name} dostaje dodatkowe {actor.speed_feet} feet ruchu w tej turze.")


def use_movement(state: CombatState, actor: Actor, path: PathResult) -> TurnMovementUseResult:
    remaining = movement_remaining(state, actor)
    if state.status != CombatStatus.ACTIVE:
        return TurnMovementUseResult(state, False, "Walka nie jest aktywna.", remaining)
    if actor.id != current_actor(state).id:
        return TurnMovementUseResult(state, False, "To nie jest tura tego aktora.", remaining)
    if not path.valid:
        return TurnMovementUseResult(state, False, "Nie można wykonać ruchu na wybrane pole.", remaining)
    if path.cost_feet > remaining:
        return TurnMovementUseResult(
            state,
            False,
            f"Za mało ruchu. Koszt: {path.cost_feet} feet, pozostało: {remaining} feet.",
            remaining,
        )
    updated_actor = replace(actor, position=path.destination)
    updated_state = replace_actor(state, updated_actor)
    movement_used = state.turn_action.movement_used_feet + path.cost_feet
    updated_state = replace(updated_state, turn_action=replace(updated_state.turn_action, movement_used_feet=movement_used))
    updated_remaining = movement_remaining(updated_state, updated_actor)
    return TurnMovementUseResult(
        updated_state,
        True,
        f"Ruch wykonany na {path.destination.as_tuple()}. Pozostało ruchu: {updated_remaining} feet.",
        updated_remaining,
    )


def finish_turn(state: CombatState) -> CombatState:
    finished_state = _with_finished_status(state)
    if finished_state.status != CombatStatus.ACTIVE:
        return finished_state
    order = _sync_order_actor_states(finished_state.initiative_order, finished_state.actors).advance_turn(skip_defeated=True)
    next_actor = actor_by_id(finished_state, order.current_actor.id)
    spent = frozenset(actor_id for actor_id in finished_state.spent_reaction_actor_ids if actor_id != next_actor.id)
    return replace(
        finished_state,
        initiative_order=order,
        spent_reaction_actor_ids=spent,
        turn_action=TurnActionState(reaction_available=next_actor.id not in spent),
    )


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
