"""Garran may intercept a declared single attack before its roll."""
from __future__ import annotations
from dataclasses import replace
from typing import TYPE_CHECKING
from dnd_board_game.combat.session import reaction_available_for, use_actor_reaction
from dnd_board_game.combat.shared_mana import adjacent
from dnd_board_game.combat.physical_mana import effect
from dnd_board_game.rules import apply_active_effect
from dnd_board_game.rules.shared_mana import ManaPhase, finish_mana_action

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def offer_guard(session: ExplorationUiSession) -> bool:
    state = session.combat_state
    intent = session.pending_enemy_turn_intent
    if state.shared_mana is None or state.shared_mana.phase != ManaPhase.READY or intent is None or intent.target is None:
        return False
    if any(e.kind == 'shared_guard_offered' and e.actor_id == str(intent.enemy.id) for e in session.active_combat_effects):
        return False
    protector = next((a for a in state.actors if str(a.id) == 'garran'), None)
    target = next((a for a in state.actors if str(a.id) == intent.target.id), None)
    encounter = session._active_encounter()
    source = next((s for s in encounter.attack_source_options_by_actor.get(intent.enemy.id, ()) if s.id == intent.source_id), encounter.attack_sources_by_actor.get(intent.enemy.id))
    if protector is None or target is None or source is None or source.area is not None or source.save_ability is not None or protector.is_unconscious() or not reaction_available_for(state, protector) or target.faction != protector.faction or not adjacent(protector, target):
        return False
    if state.shared_mana.runes is not None:
        from dnd_board_game.combat.runes import quote_runes
        try:
            quote_runes(state, protector, "garran_guard_companion", {})
        except ValueError:
            return False
    from .shared_mana import gate_payment
    if not gate_payment(session, 'garran_guard_companion', 'resolve_shared_guard', {}, actor_id='garran'):
        return False
    session.active_combat_effects = apply_active_effect(session.active_combat_effects, effect(str(intent.enemy.id), 'shared_guard_offered', 'Osłona towarzysza została zaoferowana')).active_effects
    session.board_message = f'{target.name} jest celem pojedynczego ataku. Garran może przejąć atak: odłóż koszt i zatwierdź albo naciśnij powrót.'
    return True


def resolve_guard(session: ExplorationUiSession, *, reduction_roll: int | None = None) -> dict[str, object]:
    state = session.combat_state
    intent = session.pending_enemy_turn_intent
    if intent is None or intent.target is None or state.shared_mana.pending_ability != 'garran_guard_companion':
        raise ValueError('Nie ma opłaconej Osłony towarzysza.')
    boosts = dict(state.shared_mana.pending_boosts)
    sides = 6 if boosts.get("reduce_d6") else 4 if boosts.get("reduce_d4") else 0
    if state.shared_mana.runes is not None and sides:
        if reduction_roll is None:
            from .shared_mana import ManaDeclaration
            session.shared_mana_declaration = ManaDeclaration("garran_guard_companion", "garran", "resolve_shared_guard", boosts=boosts, stage="effect_roll")
            session._sync_board_leds()
            return session.state_payload()
        if type(reduction_roll) is not int or not 1 <= reduction_roll <= sides:
            raise ValueError(f"Podaj naturalny k{sides} redukcji obrażeń.")
    protector = next(a for a in state.actors if str(a.id) == 'garran')
    use = use_actor_reaction(state, protector)
    if not use.accepted:
        raise ValueError(use.message)
    guard = replace(effect(intent.target.id, 'garran_guard_companion', 'Osłona towarzysza'), source_actor_id='garran', target_actor_id=intent.target.id, value=reduction_roll or 0)
    session.active_combat_effects = apply_active_effect(session.active_combat_effects, guard).active_effects
    mana = finish_mana_action(state.shared_mana, revision=state.shared_mana.revision)
    # A last card may request refresh only after the interrupted attack is complete.
    if mana.phase == ManaPhase.REFRESH:
        mana = replace(mana, phase=ManaPhase.READY)
    session.combat_state = replace(use.state, shared_mana=mana)
    # Keep the paid reaction when the pre-payment enemy plan is resumed.
    session.pending_enemy_turn_intent = replace(intent, state=replace(intent.state,
        shared_mana=mana, spent_reaction_actor_ids=use.state.spent_reaction_actor_ids))
    session.resolve_enemy_turn()
    from .training_tutorial import record_ability
    result = session.pending_enemy_turn_result or session.pending_enemy_turn_ack_result
    if result is not None and result.target is not None and result.target.id == 'garran':
        record_ability(session, 'garran_guard_companion', 'garran')
    return session.state_payload()
