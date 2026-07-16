from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    CombatState,
    can_pay_action_economy_cost,
    current_actor,
    replace_actor,
    use_action_economy_cost,
)
from dnd_board_game.inventory import consume_inventory_item, inventory_item_by_id
from dnd_board_game.rules import (
    EffectDuration,
    EffectSource,
    EffectSourceType,
    apply_active_effect,
)


class TargetedItemActionSpec(Protocol):
    id: str
    label: str
    action_type: str
    value: int
    duration: str
    target_faction: str
    source_item_id: str | None
    range_feet: int
    effect_kind: str | None
    action_cost: ActionEconomyCost


@dataclass(frozen=True, slots=True)
class CombatItemActionResolution:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    actor_id: str
    target_id: str
    action_id: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


def targeted_item_action_is_legal(
    state: CombatState,
    action: TargetedItemActionSpec,
    target: Actor,
) -> bool:
    actor = current_actor(state)
    item = inventory_item_by_id(actor, action.source_item_id or "")
    return bool(
        action.action_type == "targeted_item_effect"
        and action.effect_kind in {"grant_next_attack_penalty"}
        and action.source_item_id
        and item is not None
        and item.available
        and _target_matches(actor, target, action.target_faction)
        and _distance_feet(actor, target) <= action.range_feet
        and can_pay_action_economy_cost(state, _action_cost(action))
    )


def resolve_targeted_item_action(
    *,
    state: CombatState,
    active_effects: tuple[ActiveCombatEffect, ...],
    action: TargetedItemActionSpec,
    target_id: str,
) -> CombatItemActionResolution:
    actor = current_actor(state)
    target = _actor_by_id(state, target_id)
    if actor.faction != Faction.ALLY or actor.is_defeated():
        raise ValueError("To nie jest aktywna tura bohatera.")
    if not targeted_item_action_is_legal(state, action, target):
        raise ValueError("Ta akcja przedmiotu nie jest legalna dla wybranego celu.")
    action_use = use_action_economy_cost(state, _action_cost(action))
    if not action_use.accepted:
        raise ValueError(action_use.message)
    consumed_actor = consume_inventory_item(current_actor(action_use.state), action.source_item_id or "")
    updated_state = replace_actor(action_use.state, consumed_actor)
    duration = EffectDuration(action.duration)
    effect = ActiveCombatEffect(
        id=f"item_effect:{actor.id}:{target.id}:{action.id}:{state.round_number}",
        actor_id=str(target.id),
        kind=action.effect_kind or "",
        label=action.label,
        object_id=f"item_action:{action.id}",
        value=action.value,
        source_actor_id=str(actor.id),
        target_actor_id=str(target.id),
        source=EffectSource(EffectSourceType.ITEM, action.source_item_id or action.id, action.label),
        duration=duration,
        stacking_key=f"item_action:{action.id}:{target.id}",
    )
    applied = apply_active_effect(active_effects, effect)
    message = (
        f"{actor.name} używa {action.label} na {target.name}. "
        f"Efekt: {action.value:+d} do następnego ataku celu."
    )
    return CombatItemActionResolution(
        state=updated_state,
        active_effects=applied.active_effects,
        actor_id=str(actor.id),
        target_id=str(target.id),
        action_id=action.id,
        message_title="Przedmiot",
        message_body=message,
        event_type="ui_combat_targeted_item_used",
        event_payload=(
            ("actor_id", str(actor.id)),
            ("target_id", str(target.id)),
            ("action_id", action.id),
            ("source_item_id", action.source_item_id or ""),
            ("effect_kind", action.effect_kind or ""),
            ("value", action.value),
        ),
    )


def _target_matches(actor: Actor, target: Actor, target_faction: str) -> bool:
    if target.is_defeated():
        return False
    if target_faction == "self":
        return target.id == actor.id
    if target_faction == "ally":
        return target.faction == actor.faction
    if target_faction in {"enemy", "hostile"}:
        return target.faction not in {actor.faction, Faction.NEUTRAL}
    if target_faction in {"any", "creature"}:
        return True
    return False


def _action_cost(action: TargetedItemActionSpec) -> ActionEconomyCost:
    return ActionEconomyCost(getattr(action, "action_cost", ActionEconomyCost.ACTION))


def _distance_feet(actor: Actor, target: Actor) -> int:
    return max(
        abs(actor.position.col - target.position.col),
        abs(actor.position.row - target.position.row),
    ) * 5


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor
