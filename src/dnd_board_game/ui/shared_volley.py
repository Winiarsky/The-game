"""Physical attack roll for the ranger's shared-roll area volley."""
from __future__ import annotations
from dnd_board_game.rules.charge_rolls import uses_charge
from dataclasses import replace
from typing import TYPE_CHECKING, Mapping
from dnd_board_game.combat.session import current_actor, use_turn_action, replace_actor
from dnd_board_game.combat.shared_volley import resolve_volley, volley_bonuses, volley_source, volley_damage_specs
from dnd_board_game.combat.damage import damage_components_from_totals, resolve_damage, apply_damage_result
from dnd_board_game.application.player_area_healing_flow import PlayerAreaSpellTransition

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def confirm_volley(session: ExplorationUiSession) -> dict[str, object]:
    pending = session.pending_area_spell
    if pending is None or pending.source_id != 'arrow_rain' or pending.stage != 'confirm_area':
        raise ValueError('Najpierw wybierz obszar Deszczu strzał.')
    if not pending.target_ids:
        raise ValueError('Wybierz obszar z przynajmniej jednym dostępnym wrogiem.')
    action = use_turn_action(session.combat_state)
    if not action.accepted:
        raise ValueError(action.message)
    from dnd_board_game.application.player_combat_action_flow import _consume_attack_ammunition
    actor = current_actor(action.state)
    source = session._attack_source_by_id(actor, pending.source_id)
    session.combat_state = _consume_attack_ammunition(action.state, str(actor.id), source)
    session.pending_area_spell = replace(pending, stage='attack_roll')
    session.board_message = 'Deszcz strzał: rzuć wspólny k20. Wynik porównamy z KP każdego wroga osobno.'
    session._sync_board_leds()
    return session.state_payload()


def submit_volley_roll(session: ExplorationUiSession, natural_roll: int, natural_roll_2: int | None = None) -> dict[str, object]:
    pending = session.pending_area_spell
    if pending is None or pending.source_id != 'arrow_rain' or pending.stage != 'attack_roll':
        raise ValueError('Brak wspólnego rzutu Deszczu strzał.')
    state = session.combat_state
    actor = current_actor(state)
    source = session._attack_source_by_id(actor, pending.source_id, pending.cast_level)
    source = volley_source(actor, source, session.active_combat_effects)
    total, hits = resolve_volley(source, tuple(a for a in state.actors if str(a.id) in pending.target_ids),
        {key: position.cover_bonus for key, position in pending.target_positioning}, session.active_combat_effects,
        natural_roll=natural_roll, natural_roll_2=natural_roll_2)
    session.pending_area_spell = replace(pending, stage='damage_roll' if any(h.hit for h in hits) else 'volley_miss', volley_total=total, volley_hits=hits)
    from dnd_board_game.rules import EffectEvent, EffectEventType
    session._apply_combat_trigger_events((EffectEvent(EffectEventType.ATTACK_RESOLVED, actor_id=str(actor.id)),))
    session._sync_board_leds()
    return session.state_payload()


def apply_volley_damage(session: ExplorationUiSession, component_totals: Mapping[str, int] | None) -> dict[str, object]:
    pending = session.pending_area_spell
    if pending is None or pending.source_id != 'arrow_rain' or pending.stage not in {'damage_roll', 'volley_miss'}:
        raise ValueError('Najpierw rozstrzygnij test Deszczu strzał.')
    state = session.combat_state
    actor = current_actor(state)
    source = session._attack_source_by_id(actor, pending.source_id, pending.cast_level)
    hits = tuple(h for h in pending.volley_hits if h.hit)
    bonuses = volley_bonuses(state, source, hits, session.active_combat_effects)
    specs = volley_damage_specs(source, bonuses)
    components = damage_components_from_totals(specs, component_totals or {}) if hits else ()
    damages = []
    for hit in hits:
        target = next(a for a in state.actors if str(a.id) == hit.actor_id)
        own_components = tuple(value for spec, value in zip(specs, components) if spec.id not in {c.id for c, _ in bonuses} or any(c.id == spec.id and target_id == hit.actor_id for c, target_id in bonuses))
        applied = apply_damage_result(target, resolve_damage(own_components, target.damage_affinities))
        state = replace_actor(state, applied.actor_after)
        damages.append(applied)
    from dnd_board_game.combat.physical_mana import effect
    from dnd_board_game.rules import apply_active_effect
    from dnd_board_game.combat.erynd_features import commit_first_blood_hit
    for component, _ in bonuses:
        if component.id == "first_blood" and not uses_charge(actor):
            session.active_combat_effects = commit_first_blood_hit(session.active_combat_effects, str(actor.id))
        elif component.id != 'first_blood':
            session.active_combat_effects = apply_active_effect(session.active_combat_effects, effect(str(actor.id), "mana_hunters_mark_used", "Znak wykorzystany", 1)).active_effects
    state = replace(state, hidden_states=tuple(h for h in state.hidden_states if h.actor_id != str(actor.id)))
    names = {str(a.id): a.name for a in state.actors}
    summary = '; '.join(f'{names[h.actor_id]}: {pending.volley_total} przeciw KP {h.armor_class}, ' + ('trafienie' if h.hit else 'pudło') for h in pending.volley_hits)
    return session._apply_player_area_spell_transition(PlayerAreaSpellTransition(state=state, pending=None,
        board_message=summary, message_title='Deszcz strzał', message_body=summary,
        event_type='shared_volley_resolved', event_payload=(('attack_total', pending.volley_total), ('hit_ids', [h.actor_id for h in hits])), applied_damages=tuple(damages)))
