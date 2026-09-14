"""Two ordered participants act inside Garran's paid command, without new turns."""
from __future__ import annotations
from dataclasses import asdict, replace
import json
from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect, EffectDuration, apply_active_effect
from .action_economy import ActionUse
from .initiative import InitiativeEntry
from .session import CombatState, TurnActionState, current_actor, use_turn_action, use_actor_reaction, reaction_available_for
from .spells import grid_distance_feet
from .physical_mana import effect


def validate_command_target(state: CombatState, target_id: str) -> Actor:
    owner = current_actor(state)
    target = next((a for a in state.actors if str(a.id) == target_id), None)
    if target is None or target.id == owner.id or target.faction != owner.faction or target.is_unconscious() or target.is_defeated() or grid_distance_feet(owner.position, target.position) > 15 or not reaction_available_for(state, target):
        raise ValueError('Wybierz przytomnego sojusznika w 15 ft z dostępną reakcją.')
    return target


def _movement(effects: tuple[ActiveEffect, ...], actor_id: str) -> tuple[ActiveEffect, ...]:
    for kind, value in (('movement_speed_cap', 10), ('disengage_until_turn_end', 0)):
        effects = apply_active_effect(effects, replace(effect(actor_id, kind, 'Rozkaz: ruch do 10 ft bez ataków okazyjnych', value),
            id=f'shared_command:{actor_id}:{kind}', object_id='shared_command')).active_effects
    return effects


def start_command(state: CombatState, effects: tuple[ActiveEffect, ...], target_id: str) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    target = validate_command_target(state, target_id)
    spent = use_turn_action(state)
    if not spent.accepted:
        raise ValueError(spent.message)
    owner = current_actor(state)
    marker = replace(effect(str(owner.id), 'shared_command_owner', 'Rozkaz: Kontratak!', duration=EffectDuration.UNTIL_ENCOUNTER_END),
        object_id=json.dumps(asdict(spent.state.turn_action)), target_actor_id=str(target.id))
    effects = apply_active_effect(effects, marker).active_effects
    state = replace(spent.state, shared_mana=replace(state.shared_mana, command_step=1, command_ally=str(target.id), command_stage='movement', command_skipped=False),
        turn_action=TurnActionState(bonus_action_use=ActionUse.ACTION_USED, shared_bonus_actions_used=2, reaction_available=False,
            object_interaction_available=False, weapon_change_available=False))
    return state, _movement(effects, str(owner.id))


def advance_command(state: CombatState, effects: tuple[ActiveEffect, ...]) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    marker = next(e for e in effects if e.kind == 'shared_command_owner')
    effects = tuple(e for e in effects if e.object_id != 'shared_command')
    if state.shared_mana.command_step == 1 and state.status.value == "active":
        ally = next(a for a in state.actors if str(a.id) == marker.target_actor_id)
        reaction = use_actor_reaction(state, ally)
        if reaction.accepted and not ally.is_unconscious() and not ally.is_defeated():
            state = reaction.state
            owner_entry = state.initiative_order.current_entry
            entry = InitiativeEntry(ally, owner_entry.roll, owner_entry.dexterity_modifier,
                1 + max(e.stable_order for e in state.initiative_order.entries))
            entries = list(state.initiative_order.entries)
            index = state.initiative_order.current_index + 1
            entries.insert(index, entry)
            state = replace(state, initiative_order=replace(state.initiative_order, entries=tuple(entries), current_index=index),
                shared_mana=replace(state.shared_mana, command_step=2, command_stage='movement'),
                turn_action=TurnActionState(bonus_action_use=ActionUse.ACTION_USED, shared_bonus_actions_used=2, reaction_available=False,
                    object_interaction_available=False, weapon_change_available=False))
            return state, _movement(effects, str(ally.id))
    entries = list(state.initiative_order.entries)
    if state.shared_mana.command_step == 2:
        entries.pop(state.initiative_order.current_index)
    index = next(i for i, e in enumerate(entries) if str(e.actor.id) == marker.actor_id)
    raw = json.loads(marker.object_id)
    raw['action_use'] = ActionUse(raw['action_use'])
    raw['bonus_action_use'] = ActionUse(raw['bonus_action_use'])
    state = replace(state, initiative_order=replace(state.initiative_order, entries=tuple(entries), current_index=index),
        turn_action=TurnActionState(**raw), shared_mana=replace(state.shared_mana, command_step=0, command_ally='', command_stage=''))
    return state, tuple(e for e in effects if e.id != marker.id)
