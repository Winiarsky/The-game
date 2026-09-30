"""Validated costs and cooperative resonance, independent of presentation."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Mapping, Sequence
from dnd_board_game.actors import Actor
from dnd_board_game.rules.rune_baskets import RuneBaskets, category_of, spend_tokens
from dnd_board_game.rules.shared_mana import ManaPhase, sync_runes
from dnd_board_game.scenarios.rune_catalog import rune_card
from .session import CombatState, reaction_available_for, use_actor_reaction


def helpers(state: CombatState, actor: Actor, rune: str) -> tuple[Actor, ...]:
    pool = state.shared_mana.runes
    return tuple(a for a in state.actors if a.id != actor.id and a.faction == actor.faction
        and not a.is_unconscious() and not a.is_defeated() and reaction_available_for(state, a)
        and max(abs(a.position.col-actor.position.col), abs(a.position.row-actor.position.row)) <= 3
        and rune in pool.hand(str(a.id)))


def quote(state: CombatState, actor: Actor, ability_id: str, boosts: Mapping[str, int],
          selected: Sequence[str] | None = None, *, targets: Sequence[Actor] = (), helper_id: str = "") -> tuple[str, ...]:
    from .runes import require_budget
    from .rune_flaws import rune_flaw_cost
    pool = state.shared_mana.runes
    card = rune_card(str(actor.id), ability_id, pool=pool)
    if not isinstance(pool, RuneBaskets) or card is None:
        raise ValueError("Nieznana moc koszyków run.")
    require_budget(state, actor, card, boosts)
    if card.once and (str(actor.id), ability_id) in pool.used_once:
        raise ValueError("Ta moc została już użyta w walce.")
    requirements = card.payment(boosts)
    resonance = requirements[1] if len(requirements) > 1 else ""
    hand = list(pool.hand(str(actor.id)))
    surcharge = rune_flaw_cost(state, actor, ability_id, targets).count
    if selected is not None:
        own = tuple(selected)
        expected = 1 + surcharge + bool(resonance and not helper_id)
        if len(own) != expected or Counter(own) - Counter(hand) or category_of(own[0]) != card.category:
            raise ValueError("Wybierz własną runę kategorii mocy i opłać wymagane dopłaty.")
        if resonance and not helper_id and own[-1] != resonance:
            raise ValueError("Rezonans wymaga wskazanego symbolu.")
        if helper_id and (not resonance or helper_id not in {str(a.id) for a in helpers(state, actor, resonance)}):
            raise ValueError("Pomocnik musi mieć runę, reakcję i znajdować się w promieniu 3 pól.")
        return own
    base = next((r for r in hand if category_of(r) == card.category), None)
    if base is None:
        raise ValueError("Brak własnego żetonu kategorii tej mocy. Pomocnik nie opłaca podstawy.")
    hand.remove(base)
    own = [base]
    if resonance:
        if resonance in hand:
            hand.remove(resonance)
            own.append(resonance)
        elif not helpers(state, actor, resonance):
            raise ValueError("Brak runy Rezonansu i dostępnego pomocnika w promieniu 3 pól.")
    if len(hand) < surcharge:
        raise ValueError("Brakuje własnych run na dopłatę skazy.")
    return (base, *hand[:surcharge], *own[1:])


def commit(state: CombatState, actor: Actor, ability_id: str, boosts: Mapping[str, int],
           selected: Sequence[str], *, targets: Sequence[Actor] = (), helper_id: str = "") -> CombatState:
    from .runes import commit_budget
    mana = state.shared_mana
    if mana.phase != ManaPhase.READY:
        raise ValueError("Moc została już opłacona albo trwa inna operacja.")
    own = quote(state, actor, ability_id, boosts, selected, targets=targets, helper_id=helper_id)
    if ability_id == "counterattack_command" and helper_id in {str(a.id) for a in targets}:
        raise ValueError("Uczestnik Kontrataku potrzebuje reakcji na rozkaz; wybierz innego pomocnika.")
    from .rune_flaws import rune_flaw_cost
    surcharge = rune_flaw_cost(state, actor, ability_id, targets).count
    card = rune_card(str(actor.id), ability_id, pool=mana.runes)
    payments = {str(actor.id): own}
    if helper_id:
        payments[helper_id] = card.payment(boosts)[1:]
        helper = next(a for a in state.actors if str(a.id) == helper_id)
        used = use_actor_reaction(state, helper)
        if not used.accepted:
            raise ValueError(used.message)
        state = used.state
    pool = spend_tokens(mana.runes, payments, once=(str(actor.id), ability_id) if card.once else None)
    paid = replace(sync_runes(mana, pool), phase=ManaPhase.RESOLVING, pending_actor=str(actor.id),
        pending_ability=ability_id, pending_boosts=tuple(boosts.items()), rune_payment=own,
        rune_flaw_paid=bool(surcharge), rune_ally_actor="", rune_ally_payment="",
        echo_spell=ability_id if actor.id == 'nimra' else mana.echo_spell,
        echo_count=min(2, mana.echo_count+1) if actor.id == 'nimra' and mana.echo_spell == ability_id else 1 if actor.id == 'nimra' else mana.echo_count,
        technique_movement={"unstoppable":20,"blade_dance":15}.get(ability_id,0), attack_targets=())
    return replace(commit_budget(state, actor, card, boosts), shared_mana=paid)
