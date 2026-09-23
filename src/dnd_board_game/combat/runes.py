"""Rune-card payments and independent special-action budgets."""
from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence
from dnd_board_game.actors import Actor
from dnd_board_game.rules.runes import plan_card_payment, spend_runes
from dnd_board_game.scenarios.rune_catalog import RuneCard, rune_card
from .action_economy import ActionUse
from .session import CombatState, current_actor, reaction_available_for


def uses_runes(actor: Actor) -> bool:
    return any(f.feature_id == "rune_resource_v01" for f in actor.features)


def rune_resolution(state: CombatState) -> bool:
    mana = state.shared_mana
    return bool(mana and mana.runes and mana.phase.value == "resolving" and mana.pending_actor == str(current_actor(state).id))


def require_budget(state: CombatState, actor: Actor, card: RuneCard, boosts: Mapping[str, int] | None = None) -> None:
    budget = card.budget_for(boosts or {})
    if state.status.value != "active" or actor.is_defeated():
        raise ValueError("Bohater nie może teraz użyć mocy.")
    from .conditions import condition_blocks_actions
    if budget != "R" and condition_blocks_actions(state.condition_states, str(actor.id)):
        raise ValueError("Stan postaci blokuje akcje specjalne.")
    if budget == "R":
        if not reaction_available_for(state, actor):
            raise ValueError("Reakcja została już wykorzystana.")
        return
    if actor.id != current_actor(state).id:
        raise ValueError("To nie jest tura tej postaci.")
    from .session import shared_bonus_action_limit
    if state.turn_action.rune_special_used and state.turn_action.shared_bonus_actions_used >= shared_bonus_action_limit(state, actor):
        raise ValueError("Akcja specjalna w tej turze została już wykorzystana.")
    if "A" in budget and state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
        raise ValueError("Ta moc wymaga niewykorzystanego ataku lub przedmiotu.")
    if "M" in budget and (state.turn_action.movement_used_feet or state.turn_action.movement_action_used):
        raise ValueError("Ta moc wymaga całego niewykorzystanego ruchu.")


def quote_runes(state: CombatState, actor: Actor, ability_id: str, boosts: Mapping[str, int],
                selected_wildcards: Sequence[str] | None = None, *, targets: Sequence[Actor] = ()) -> tuple[str, ...]:
    if ability_id.startswith("basic_attack:"):
        return ()
    card = rune_card(str(actor.id), ability_id)
    if card is None or state.shared_mana is None or state.shared_mana.runes is None:
        raise ValueError("Nieznana karta mocy runicznej.")
    require_budget(state, actor, card, boosts)
    pool = state.shared_mana.runes
    if card.once and (str(actor.id), ability_id) in pool.used_once:
        raise ValueError("Ta moc została już użyta w tej walce.")
    payment = plan_card_payment(pool.hand(str(actor.id)), rune_requirements(state, actor, ability_id, boosts, targets=targets), selected_wildcards)
    if ability_id == "mana_tuning" and (len(pool.hand(str(actor.id))) <= len(payment) or not pool.deck):
        raise ValueError("Strojenie wymaga dodatkowej runy do wymiany oraz niepustej talii.")
    if ability_id == "mana_recovery" and (not pool.discard or len(pool.hand(str(actor.id))) - len(payment) >= 7):
        raise ValueError("Odzysk wymaga run na stosie przed zapłatą i miejsca na ręce.")
    return payment


def rune_requirements(state: CombatState, actor: Actor, ability_id: str,
                       boosts: Mapping[str, int], *, targets: Sequence[Actor] = ()) -> tuple[str, ...]:
    from .rune_flaws import rune_flaw_cost
    card = rune_card(str(actor.id), ability_id)
    pool = state.shared_mana.runes
    free = card.free_first and (str(actor.id), ability_id + ":free") not in pool.used_once
    return card.payment(boosts, free_base=free) + ("*",) * rune_flaw_cost(state, actor, ability_id, targets).count


def commit_budget(state: CombatState, actor: Actor, card: RuneCard, boosts: Mapping[str, int] | None = None) -> CombatState:
    require_budget(state, actor, card, boosts)
    budget = card.budget_for(boosts or {})
    if budget == "R":
        # Existing reaction resolver consumes the reaction on resolution.
        return state
    turn = state.turn_action
    return replace(state, turn_action=replace(turn, rune_special_used=True,
        shared_bonus_actions_used=turn.shared_bonus_actions_used + 1,
        action_use=ActionUse.ACTION_USED if "A" in budget else turn.action_use,
        movement_action_used=True if "M" in budget else turn.movement_action_used,
        attack_action_active=False, attacks_used=0, attacks_maximum=0))
