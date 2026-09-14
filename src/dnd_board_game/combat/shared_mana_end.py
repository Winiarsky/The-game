"""Apply end-of-turn effects once, before asking players to refill the market."""
from dataclasses import replace
from dnd_board_game.rules import ActiveEffect, EffectEvent, EffectEventType
from .session import CombatState, current_actor
from .scene_interactions import expire_combat_effects
from .conditions import expire_condition_states
from .triggers import resolve_combat_triggers, TriggerActivation


def prepare_shared_turn_end(state: CombatState, effects: tuple[ActiveEffect, ...]) -> tuple[CombatState, tuple[ActiveEffect, ...], tuple[ActiveEffect, ...], tuple[TriggerActivation, ...]]:
    if state.shared_mana.end_effects_applied:
        return state, effects, (), ()
    actor = current_actor(state)
    event = EffectEvent(EffectEventType.TURN_END, actor_id=str(actor.id))
    trigger = resolve_combat_triggers(state, event)
    state, effects, expired = expire_combat_effects(trigger.state, effects, event)
    conditions, _ = expire_condition_states(state.condition_states, event)
    return replace(state, condition_states=conditions, shared_mana=replace(state.shared_mana, end_effects_applied=True)), effects, expired, trigger.activations
