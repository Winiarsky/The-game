"""Actor-aware pool requirements. Values and definitions are injected by callers."""
from __future__ import annotations

from typing import Mapping, Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect
from dnd_board_game.rules.pooled_mana_catalog import PoolAbility, validate_boosts
from dnd_board_game.rules.shared_mana_catalog import SharedAbility
from .session import CombatState
from .shared_mana import ManaQuote, NON_OFFENSIVE, adjacent
from .spells import grid_distance_feet


def enemy_pressure(state: CombatState, enemy: Actor, definitions: Mapping[str, Mapping[str, object]], *, hit: bool) -> tuple[CombatState, str]:
    """One eligible mana rider per enemy turn, after hit and defensive reactions."""
    from dataclasses import replace
    from dnd_board_game.rules.pooled_mana import attack_mana
    from dnd_board_game.rules.shared_mana import sync_pool
    mana = state.shared_mana
    if mana is None or mana.pooled is None or not hit or state.status.value != "active":
        return state, ""
    pool = mana.pooled
    key = str(enemy.id) + ":pressure"
    if key in pool.used or pool.phase != "ready":
        return state, ""
    entry = next((definitions[f.feature_id] for f in enemy.features if f.feature_id in definitions
                  and state.initiative_order.round_number % int(definitions[f.feature_id]["period"]) == 0), None)
    if entry is None:
        return state, ""
    pool = replace(pool, used=(*pool.used, key))
    pool = attack_mana(pool, str(entry["source"]), int(entry["count"]),
                       captor=str(enemy.id) if entry["prison"] else "")
    return replace(state, shared_mana=sync_pool(mana, pool)), str(entry["label"])


def point_modifiers(state: CombatState, actor: Actor, ability: SharedAbility,
                    targets: Sequence[Actor], effects: Sequence[ActiveEffect]) -> tuple[int, int, tuple[str, ...]]:
    pool = state.shared_mana.pooled
    hero = str(actor.id)
    bonus = surcharge = 0
    notes = []
    allies = [a for a in state.actors if a.faction == actor.faction and a.id != actor.id
              and not a.is_unconscious() and not a.is_defeated()]
    audience = any(grid_distance_feet(actor.position, a.position) <= 10 for a in allies)
    offensive = ability.id not in NON_OFFENSIVE
    if hero == "dagna" and offensive and any(a.faction == actor.faction and a.id != actor.id and not a.is_dead() and adjacent(actor, a) and 2 * a.hp < a.max_hp for a in state.actors):
        surcharge += 1
        notes.append("Nikogo nie zostawiam: spal dodatkową kartę.")
    if hero == "lorian" and len(pool.heroes) > 1 and not audience:
        surcharge += 1
        notes.append("Potrzeba publiczności: spal dodatkową kartę.")
    if hero == "nimra" and state.shared_mana.echo_spell == ability.id:
        surcharge += min(2, state.shared_mana.echo_count)
        notes.append(f"Echo: spal dodatkowe {min(2, state.shared_mana.echo_count)} karty.")
    if hero == "erynd" and offensive and any(adjacent(t, a) for t in targets for a in allies):
        surcharge += 1
        notes.append("Trauma bratobójczego strzału: spal dodatkową kartę.")
    return bonus, surcharge, tuple(notes)


def quote_pool(state: CombatState, actor: Actor, ability: SharedAbility,
               definition: PoolAbility, values: Mapping[str, int], boosts: Mapping[str, int],
               *, targets: Sequence[Actor] = (), effects: Sequence[ActiveEffect] = ()) -> ManaQuote:
    if definition.hero != str(actor.id) or ability.hero_id != str(actor.id):
        raise ValueError("Ta zdolność należy do innego bohatera.")
    pool = state.shared_mana.pooled
    if definition.free:
        if any(boosts.values()):
            raise ValueError("Darmowa zdolność nie wydaje kart na podbicia.")
        return ManaQuote((), ("Bez many; zachowujesz pulę. Normalny koszt akcji.",))
    bonus, surcharge, notes = point_modifiers(state, actor, ability, targets, effects)
    hand = pool.hand(str(actor.id))
    definition.validate(hand, values)
    validate_boosts(hand, boosts, ability.boosts, ability.boost_limit)
    total = sum(values[c] for c in hand)
    discount = sum(e.value for e in effects if e.actor_id == str(actor.id) and e.kind == "charge_burn_discount")
    cost = definition.burn + 2 * sum(boosts.values()) + surcharge
    cost = max(1, cost - discount) if cost else 0
    return ManaQuote(("*",) * cost, (f"Ładunek {total} pkt; próg {definition.minimum}. Zachowaj pulę. Po akcji spal {cost} kart z wierzchu; niedobór powoduje mana drain po wykonaniu efektu.", *notes), str(actor.id) == "nimra")
