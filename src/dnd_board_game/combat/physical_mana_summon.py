"""A paid weapon activation temporarily controls the summon within its owner's turn."""
from dataclasses import asdict, replace
import json

from dnd_board_game.actors import Actor
from dnd_board_game.actors.resources import uses_physical_mana
from dnd_board_game.rules import ActiveEffect, EffectDuration, apply_active_effect
from .action_economy import ActionUse
from .initiative import InitiativeEntry
from .session import CombatState, TurnActionState, current_actor, use_bonus_action
from .physical_mana import effect


def available_weapon(state: CombatState) -> Actor | None:
    owner = current_actor(state)
    if not uses_physical_mana(owner) or owner.is_defeated() or owner.is_unconscious():
        return None
    ids = {s.actor_id for s in state.summoned_creatures if s.owner_actor_id == owner.id and s.spell_id == 'spiritual_weapon'}
    return next((a for a in state.actors if a.id in ids and not a.is_defeated()), None)


def activate_weapon(state: CombatState, effects: tuple[ActiveEffect, ...], *, on_cast: bool = False
                    ) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    owner = current_actor(state)
    weapon = available_weapon(state)
    if weapon is None or any(e.kind == 'mana_weapon_control' for e in effects):
        raise ValueError('Brak duchowej broni możliwej do aktywowania.')
    if not on_cast:
        spent = use_bonus_action(state)
        if not spent.accepted:
            raise ValueError(spent.message)
        state = spent.state
    marker = replace(effect(str(owner.id), 'mana_weapon_control', 'Sterowanie duchową bronią',
                            duration=EffectDuration.UNTIL_ENCOUNTER_END),
                     target_actor_id=str(weapon.id), object_id=json.dumps(asdict(state.turn_action)))
    effects = apply_active_effect(effects, marker).active_effects
    owner_entry = state.initiative_order.current_entry
    entry = InitiativeEntry(weapon, owner_entry.roll, owner_entry.dexterity_modifier,
                            1 + max(e.stable_order for e in state.initiative_order.entries))
    entries = list(state.initiative_order.entries)
    index = state.initiative_order.current_index + 1
    entries.insert(index, entry)
    state = replace(state, initiative_order=replace(state.initiative_order, entries=tuple(entries), current_index=index),
                    turn_action=TurnActionState(bonus_action_use=ActionUse.ACTION_USED, reaction_available=False,
                                               object_interaction_available=False, weapon_change_available=False))
    return state, effects


def finish_weapon_activation(state: CombatState, effects: tuple[ActiveEffect, ...]
                             ) -> tuple[CombatState, tuple[ActiveEffect, ...]] | None:
    weapon = current_actor(state)
    marker = next((e for e in effects if e.kind == 'mana_weapon_control' and e.target_actor_id == str(weapon.id)), None)
    if marker is None:
        return None
    raw = json.loads(marker.object_id)
    raw['action_use'] = ActionUse(raw['action_use'])
    raw['bonus_action_use'] = ActionUse(raw['bonus_action_use'])
    entries = tuple(e for e in state.initiative_order.entries if e.actor.id != weapon.id)
    index = next(i for i,e in enumerate(entries) if str(e.actor.id) == marker.actor_id)
    restored = replace(state, initiative_order=replace(state.initiative_order, entries=entries, current_index=index),
                       turn_action=TurnActionState(**raw))
    return restored, tuple(e for e in effects if e.id != marker.id)
