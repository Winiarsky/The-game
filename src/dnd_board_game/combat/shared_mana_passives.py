"""Once-per-turn hit passives for the shared market heroes."""
from __future__ import annotations
from dataclasses import replace
from dnd_board_game.rules import ActiveEffect, EffectDuration, apply_active_effect
from .session import CombatState, current_actor, replace_actor
from .physical_mana import effect, is_basic_weapon
from .attack_flow import AttackSource


def apply_hit_passive(state: CombatState, effects: tuple[ActiveEffect, ...], source: AttackSource) -> tuple[CombatState, tuple[ActiveEffect, ...], bool]:
    actor = current_actor(state)
    if state.shared_mana is None or str(actor.id) != state.shared_mana.turn_actor:
        return state, effects, False
    key = 'shared_momentum_used' if str(actor.id) == 'brakka' else 'shared_nimble_used'
    if any(e.actor_id == str(actor.id) and e.kind == key for e in effects):
        return state, effects, False
    nimble = str(actor.id) == 'mira' and any('knife' in (value or '') or 'dagger' in (value or '') for value in (source.source_item_id, source.proficiency_id))
    momentum = str(actor.id) == 'brakka' and is_basic_weapon(actor, source) and any(e.actor_id == str(actor.id) and e.kind == 'rage' for e in effects)
    if not (nimble or momentum):
        return state, effects, False
    marker = replace(effect(str(actor.id), key, 'Pasyw wykorzystany', duration=EffectDuration.UNTIL_TURN_START), expiration_actor_id=str(actor.id))
    effects = apply_active_effect(effects, marker).active_effects
    if momentum and actor.temp_hp < 2:
        effects = tuple(e for e in effects if not (e.actor_id == str(actor.id) and e.kind == "temporary_hit_points"))
        state = replace_actor(state, replace(actor, temp_hp=2))
        marker = replace(effect(str(actor.id), 'temporary_hit_points', 'Bitewny rozpęd: 2 tymczasowe PW', 2, EffectDuration.UNTIL_TURN_START), expiration_actor_id=str(actor.id))
        effects = apply_active_effect(effects, marker).active_effects
    return state, effects, nimble
