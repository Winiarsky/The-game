from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    CombatState,
    CombatCondition,
    ConditionSaveTiming,
    apply_condition,
    can_pay_action_economy_cost,
    current_actor,
    replace_actor,
    use_action_economy_cost,
)
from dnd_board_game.inventory import (
    consume_item_use,
    has_item_use,
    inventory_item_by_id,
)
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
    condition: CombatCondition | None
    save_ability: str | None
    save_dc: int | None
    save_timing: str | None
    action_cost: ActionEconomyCost
    charge_cost: int


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
        and action.effect_kind in {"grant_next_attack_penalty", "apply_condition"}
        and action.source_item_id
        and item is not None
        and item.available
        and has_item_use(
            actor,
            action.source_item_id,
            charge_cost=getattr(action, "charge_cost", 0),
        )
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
    item_use = consume_item_use(
        current_actor(action_use.state),
        action.source_item_id or "",
        charge_cost=getattr(action, "charge_cost", 0),
    )
    updated_state = replace_actor(action_use.state, item_use.actor)
    if action.effect_kind == "apply_condition":
        if action.condition is None:
            raise ValueError("Akcja przedmiotu nie definiuje nakładanego warunku.")
        application = apply_condition(
            updated_state.condition_states,
            target,
            action.condition,
            source_actor_id=str(actor.id),
            source_label=action.label,
            duration=EffectDuration(action.duration),
            save_ability=action.save_ability,
            save_dc=action.save_dc,
            save_timing=(
                ConditionSaveTiming(action.save_timing)
                if action.save_timing is not None
                else None
            ),
        )
        updated_state = replace(
            updated_state,
            condition_states=application.condition_states,
        )
        message = f"{actor.name} używa {action.label} na {target.name}. {application.message}"
        return CombatItemActionResolution(
            state=updated_state,
            active_effects=active_effects,
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
                ("condition", action.condition.value),
                ("applied", application.applied),
                ("charge_cost", item_use.spent),
            ),
        )
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
            ("charge_cost", item_use.spent),
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
