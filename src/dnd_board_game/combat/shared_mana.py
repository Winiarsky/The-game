"""Actor-aware shared-mana quotes and deck-cycle effect boundaries."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect, AdditionalEffectExpiration, EffectDuration, EffectEvent, EffectEventType, expire_active_effects
from dnd_board_game.rules.shared_mana import SharedMana
from dnd_board_game.rules.shared_mana_catalog import SharedAbility
from dnd_board_game.rules.shared_mana_catalog import shared_ability
from .session import CombatState
from .spells import grid_distance_feet


NON_OFFENSIVE = frozenset({
    "second_wind", "defensive_stance", "garran_guard_companion", "garran_shield_wall", "garran_rally",
    "iron_bastion", "rage", "reckless_attack", "acceleration", "hard_as_rock", "hide", "instinctive_dodge",
    "feint", "smoke_screen", "bless", "lesser_restoration", "caring_gesture", "healing_word", "divine_care_aura",
    "preserve_life", "mana_inspiration", "mana_tuning", "cutting_words", "mana_recovery", "mana_great_tuning",
    "victory_hymn", "misty_step", "shield", "hunters_mark", "cunning_action", "aim",
})

RIDER_LIFETIMES = {"guiding_bolt": "T", "nimra_mind_break": "T", "deafening_roar": "T", "unstoppable": "T", "blade_mistress": "O"}


def adjacent(first: Actor, second: Actor) -> bool:
    return first.id != second.id and max(abs(first.position.col-second.position.col), abs(first.position.row-second.position.row)) <= 1


@dataclass(frozen=True, slots=True)
class ManaQuote:
    cards: tuple[str, ...]
    reminders: tuple[str, ...]
    echo: bool = False


def quote_ability(state: CombatState, actor: Actor, ability: SharedAbility,
                  boosts: Mapping[str, int], *, targets: Sequence[Actor] = (),
                  effects: Sequence[ActiveEffect] = (), substitution: bool = False) -> ManaQuote:
    if ability.hero_id != str(actor.id):
        raise ValueError("Ta zdolność należy do innego bohatera.")
    mana = state.shared_mana or SharedMana()
    surcharge = 0
    reminders: list[str] = []
    if str(actor.id) == "dagna" and ability.id not in NON_OFFENSIVE:
        wounded = [a for a in state.actors if a.faction == actor.faction and not a.is_dead()
                   and adjacent(actor, a) and 2*a.hp < a.max_hp]
        if wounded:
            surcharge += 1
            reminders.append("Nikogo nie zostawiam: sąsiad ma mniej niż połowę PW (" + ", ".join(a.name for a in wounded) + "). Dopłać 1 dowolną manę.")
    echo = str(actor.id) == "nimra" and ability.timing in {"A", "D"}
    if echo and mana.echo_spell == ability.id:
        surcharge += mana.echo_count
        reminders.append(f"Echo: użycie {mana.echo_count+1}. z rzędu, dopłać {mana.echo_count} dowolnych kart.")
    if str(actor.id) == "lorian" and not ability.id.startswith("basic_attack:") and len([a for a in state.actors if a.faction == actor.faction and a.id in {"garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"}]) > 1:
        audience = any(a.id != actor.id and a.faction == actor.faction and not a.is_unconscious() and not a.is_defeated() and grid_distance_feet(actor.position, a.position) <= 10 for a in state.actors)
        used = any(e.actor_id == str(actor.id) and e.kind == "shared_audience_paid" for e in effects)
        if not audience and not used:
            surcharge += 1
            reminders.append("Potrzeba publiczności: brak przytomnego sojusznika w 10 ft. Dopłać 1 dowolną manę.")
    if str(actor.id) == "erynd" and ((ability.id.startswith("basic_attack:") and any(bow in ability.id for bow in ("longbow", "shortbow"))) or ability.id in {"disrupting_arrow", "anchoring_arrow", "exposing_arrow", "double_shot", "arrow_rain"}):
        used = any(e.actor_id == str(actor.id) and e.kind == "shared_friendly_fire_paid" for e in effects)
        if not used and any(adjacent(target, ally) for target in targets for ally in state.actors if ally.id != actor.id and ally.faction == actor.faction and ally.id in {"garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"} and not ally.is_unconscious() and not ally.is_defeated()):
            surcharge += 1
            reminders.append("Trauma bratobójczego strzału: bohater stoi przy celu. Dopłać 1 dowolną manę.")
    if substitution:
        option = substitution_option(state, actor, ability, targets, effects)
        if option is None:
            raise ValueError("Zamiana koloru nie jest dostępna przy tej deklaracji.")
        index, color, label = option
        cost = list(ability.cost)
        cost[index] = color
        ability = replace(ability, cost="".join(cost))
        reminders.append(label + ". Zużywa pasyw raz we własnej turze.")
    return ManaQuote(ability.payment(boosts, surcharge), tuple(reminders), echo)


def expire_deck_effects(state: CombatState, effects: tuple[ActiveEffect, ...]) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    """Use the ordinary effect lifecycle, including concentration-bound O effects."""
    result = expire_active_effects(effects, EffectEvent(EffectEventType.DECK_REFRESHED))
    expired_spells = {(e.source_actor_id, e.source.id) for e in result.expired_effects if e.source is not None}
    conditions = tuple(c for c in state.condition_states if c.duration != EffectDuration.UNTIL_DECK_REFRESH
                       and not (c.duration == EffectDuration.CONCENTRATION and (c.source_actor_id, c.source_spell_id) in expired_spells))
    hidden = state.hidden_states
    if any(e.kind == "shared_hidden" for e in result.expired_effects):
        ids = {e.actor_id for e in result.expired_effects if e.kind == "shared_hidden"}
        hidden = tuple(h for h in hidden if h.actor_id not in ids)
    from .summoning import remove_summons
    state, _ = remove_summons(state, spell_id="spiritual_weapon")
    from dnd_board_game.actors.mana_passives import reset_mana_passives
    return replace(state, condition_states=conditions, hidden_states=hidden,
                   actors=tuple(reset_mana_passives(a) for a in state.actors)), tuple(
                       e for e in result.active_effects if e.kind != 'saturation_reaction_damage')


def synchronize_shared_effects(state: CombatState, effects: tuple[ActiveEffect, ...]) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    """Apply catalogue lifetimes to authored effects, retaining early expiry."""
    if state.shared_mana is None:
        return state, effects
    deck_duration = EffectDuration.UNTIL_DECK_REFRESH
    if state.shared_mana.pooled is not None:
        from .mana_charge import charge_effects
        from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
        pool = state.shared_mana.pooled
        if not pool.values:
            from dnd_board_game.rules.pooled_mana import COLORS
            from dnd_board_game.rules.shared_mana import sync_pool
            pool = replace(pool, catalog_version=2, values=tuple((h, tuple(hero_profile(h)["values"][c] for c in COLORS)) for h in pool.heroes))
            state = replace(state, shared_mana=sync_pool(state.shared_mana, pool))
        profiles = {h: hero_profile(h) for h in pool.heroes}
        retired_markers = {'sneak_attack_used', 'first_blood_used', 'field_medic_step_used',
                           'shared_nimble_used', 'shared_momentum_used'}
        effects = tuple(e for e in effects if not (e.actor_id in profiles and e.kind in retired_markers))
        from dnd_board_game.actors.mana_passives import apply_color_features
        state = replace(state, actors=tuple(
            apply_color_features(a, pool.hand(str(a.id)) if pool.phase not in {'setup', 'drain'} else (),
                                 profiles[str(a.id)]['color_passives'])
            if str(a.id) in profiles else a for a in state.actors))
        effects = tuple(e for e in effects if not e.kind.startswith("charge_")) + charge_effects(pool, profiles, state.actors)
    from .shared_mana_features import synchronize_bastion
    effects = synchronize_bastion(state.actors, effects)
    normalized = []
    for effect in effects:
        owner = effect.source_actor_id or effect.actor_id
        candidates = (effect.source.id if effect.source else "", effect.object_id.partition(":")[2])
        ability = next((a for key in candidates if (a := shared_ability(owner, key))), None)
        bookkeeping = (effect.kind.endswith(("_used", "_paid", "_pending"))
                       or effect.kind in {"mira_attack_prepared", "movement_speed_cap", "disengage_until_turn_end", "rage_activity", "mana_series_source", "mana_attack_series", "rage_duration"}
                       or effect.kind.startswith(("nimra_echo_", "mana_ordinary_")))
        lifetime = (ability.duration or RIDER_LIFETIMES.get(ability.id, "")) if ability else ""
        if ability is not None and lifetime and not bookkeeping:
            duration = deck_duration if lifetime == "O" else EffectDuration.UNTIL_TURN_START
            early = {EffectDuration.UNTIL_NEXT_ATTACK, EffectDuration.WHILE_AT_POSITION}
            extra = tuple(e for e in effect.additional_expirations if e.duration in {*early, EffectDuration.CONCENTRATION})
            if effect.duration in early and not any(e.duration == effect.duration for e in extra):
                extra += (AdditionalEffectExpiration(effect.duration, actor_id=effect.expiration_actor_id or effect.actor_id,
                    target_actor_id=None if effect.kind in {"lorian_mocked_attack", "erynd_disrupted"} else effect.target_actor_id),)
            concentrated = effect.duration == EffectDuration.CONCENTRATION or any(e.duration == EffectDuration.CONCENTRATION for e in extra)
            if concentrated:
                extra = tuple(e for e in extra if e.duration not in {EffectDuration.CONCENTRATION, duration})
                extra += (AdditionalEffectExpiration(duration, actor_id=owner),)
                duration = EffectDuration.CONCENTRATION
            effect = replace(effect, duration=duration, remaining_rounds=None,
                             expiration_actor_id=owner, additional_expirations=extra)
        normalized.append(effect)
    from .physical_mana import effect as marker
    hidden_ids = {str(h.actor_id) for h in state.hidden_states if h.hidden_from_actor_ids}
    normalized = [e for e in normalized if e.kind != "shared_hidden" or e.actor_id in hidden_ids]
    for actor in state.actors:
        if str(actor.id) == "mira" and str(actor.id) in hidden_ids and not any(e.kind == "shared_hidden" and e.actor_id == str(actor.id) for e in normalized):
            normalized.append(marker(str(actor.id), "shared_hidden", "Ukrycie · utrudnienie obron i testów reakcji", duration=deck_duration))
    conditions = []
    for condition in state.condition_states:
        ability = shared_ability(condition.source_actor_id or "", condition.source_spell_id or "")
        lifetime = (ability.duration or RIDER_LIFETIMES.get(ability.id, "")) if ability else ""
        if ability is not None and lifetime and condition.duration != EffectDuration.CONCENTRATION:
            condition = replace(condition,
                duration=deck_duration if lifetime == "O" and ability.id != "nimra_sticky_matrix" else EffectDuration.UNTIL_TURN_START,
                expiration_actor_id=condition.source_actor_id, expiration_event_count=1)
        conditions.append(condition)
    sources = tuple(sorted({e.source_actor_id or e.actor_id for e in normalized if e.kind == "victory_hymn"}))
    state = replace(state, condition_states=tuple(conditions), shared_mana=replace(state.shared_mana, hymn_sources=sources, bastion_sources=tuple(sorted({e.source_actor_id for e in normalized if e.kind == "iron_bastion"}))))
    from .session import current_actor, shared_bonus_action_limit
    from .action_economy import ActionUse
    limit = shared_bonus_action_limit(state, current_actor(state))
    state = replace(state, turn_action=replace(state.turn_action,
        bonus_action_use=ActionUse.ACTION_AVAILABLE if state.turn_action.shared_bonus_actions_used < limit else ActionUse.ACTION_USED))
    return state, tuple(normalized)


def paid_flaw_markers(actor_id: str, quote: ManaQuote, effects: tuple[ActiveEffect, ...]) -> tuple[ActiveEffect, ...]:
    from dnd_board_game.rules import apply_active_effect
    from .physical_mana import effect
    for prefix, kind in (("Potrzeba publiczności:", "shared_audience_paid"), ("Trauma bratobójczego", "shared_friendly_fire_paid"), ("Za tarczą:", "shared_substitution_used"), ("Uczeń Życia:", "shared_substitution_used"), ("Alchemia barw:", "shared_substitution_used")):
        if any(text.startswith(prefix) for text in quote.reminders):
            marker = replace(effect(actor_id, kind, "Skaza opłacona", duration=EffectDuration.UNTIL_TURN_START), source_actor_id=actor_id, expiration_actor_id=actor_id)
            effects = apply_active_effect(effects, marker).active_effects
    return effects


def substitution_option(state: CombatState, actor: Actor, ability: SharedAbility,
                        targets: Sequence[Actor], effects: Sequence[ActiveEffect]) -> tuple[int, str, str] | None:
    from .session import current_actor
    if current_actor(state).id != actor.id or ability.category in {'ultimate', 'item'} or any(e.actor_id == str(actor.id) and e.kind == 'shared_substitution_used' for e in effects):
        return None
    if str(actor.id) == 'garran' and ability.id in {'defensive_stance', 'garran_shield_wall', 'garran_guard_companion'} and 'B' in ability.cost:
        if any(a.faction == actor.faction and adjacent(actor, a) and str(a.id) in {'brakka', 'mira', 'dagna', 'lorian', 'nimra', 'erynd'} and not a.is_unconscious() and not a.is_defeated() for a in state.actors):
            return ability.cost.index('B'), 'N', 'Za tarczą: niebieska zamiast białej w koszcie bazowym'
    if str(actor.id) == 'dagna' and ability.id == 'healing_word' and any(a.id != actor.id and a.faction == actor.faction for a in targets):
        return ability.cost.index('B'), 'Z', 'Uczeń Życia: zielona zamiast białej w koszcie bazowym'
    if str(actor.id) == 'nimra':
        index = next((i for i, color in enumerate(ability.cost) if color not in {'N', '*'}), None)
        if index is not None:
            return index, 'N', 'Alchemia barw: niebieska zamiast wymaganego koloru bazowego'
    return None
