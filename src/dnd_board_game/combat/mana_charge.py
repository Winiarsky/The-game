"""Charge-derived statuses and one-shot pick effects; no UI or I/O."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import Mapping, Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect, D20RollRequest, EffectDuration, RollModifier, RollModifierType
from dnd_board_game.rules.pooled_mana import PooledMana, charge_roll_bonus


def charge_effects(pool: PooledMana, profiles: Mapping[str, Mapping[str, object]]) -> tuple[ActiveEffect, ...]:
    effects = []
    for hero in pool.heroes:
        bonus = charge_roll_bonus(pool.points(hero))
        if bonus and pool.phase != "drain":
            effects.append(ActiveEffect(
                id=f"charge:{hero}:accuracy", actor_id=hero, kind="charge_accuracy",
                label=f"Naładowanie: +{bonus} do testów ({pool.points(hero)} pkt)",
                object_id="charge:accuracy", value=bonus,
                duration=EffectDuration.UNTIL_DECK_REFRESH))
        for color, count in Counter(pool.hand(hero)).items():
            passive = profiles[hero]['color_passives'][color]
            kind = passive['kind']
            if kind.startswith('heal'):
                continue
            value = count * passive['value']
            if passive['cap']:
                value = min(value, passive['cap'])
            effects.append(ActiveEffect(
                id=f'charge:{hero}:{color}', actor_id=hero, kind=f'charge_{kind}',
                label=f"{color} ×{count} · {passive['label']}", object_id=f'charge:{color}',
                value=value, duration=EffectDuration.UNTIL_DECK_REFRESH))
    return tuple(effects)


def picked_color(actors: tuple[Actor, ...], hero: str, passive: Mapping[str, object]) -> tuple[Actor, ...]:
    """Automatic recipient avoids a second choice on every mana pick.

    Only conscious allies benefit; ties use actor id, independent of tuple order.
    """
    from .spells import grid_distance_feet
    owner = next(a for a in actors if str(a.id) == hero)
    kind = passive['kind']
    if not kind.startswith('heal') or owner.is_unconscious() or owner.is_defeated():
        return actors
    eligible = [a for a in actors if a.faction == owner.faction and not a.is_unconscious()
                and not a.is_defeated() and grid_distance_feet(owner.position, a.position) <= 10]
    if kind == 'heal':
        eligible = [owner]
    elif kind == 'heal_weakest':
        eligible = sorted(eligible, key=lambda a: (-(a.max_hp - a.hp), str(a.id)))[:1]
    ids = {a.id for a in eligible}
    return tuple(replace(a, hp=min(a.max_hp, a.hp + int(passive['value']))) if a.id in ids else a for a in actors)


def saving_modifiers(actor: Actor, ability: str, effects: Sequence[ActiveEffect]) -> tuple[RollModifier, ...]:
    from dnd_board_game.rules.charge_rolls import uses_charge
    charge = charged_attack_request(actor, D20RollRequest(), effects).modifiers if uses_charge(actor) else ()
    return (*charge, *(RollModifier(e.label, e.value, RollModifierType.CUSTOM, e.id)
                      for e in effects if e.actor_id == str(actor.id)
                      and e.kind in {'charge_save_all', f'charge_save_{ability}'}))


def damage_bonus(actor: Actor, source: object, effects: Sequence[ActiveEffect]) -> int:
    kind = getattr(getattr(source, 'attack_kind', None), 'value', '')
    weapon = getattr(getattr(source, 'source_type', None), 'value', '') == 'weapon'
    allowed = {'charge_melee_damage'} if weapon and kind == 'melee' else {'charge_ranged_damage'} if weapon else {'charge_spell_damage'} if getattr(getattr(source, 'source_type', None), 'value', '') == 'spell' else set()
    return sum(e.value for e in effects if e.actor_id == str(actor.id) and e.kind in allowed)


def charged_attack_request(actor: Actor, request: D20RollRequest,
                           effects: Sequence[ActiveEffect]) -> D20RollRequest:
    """Replace proficiency and any previous charge snapshot, preserving other bonuses."""
    from dnd_board_game.rules.charge_rolls import uses_charge, replace_proficiency
    if not uses_charge(actor):
        return request
    bonus = max((e.value for e in effects
                 if e.actor_id == str(actor.id) and e.kind == "charge_accuracy"), default=0)
    return replace_proficiency(request, bonus)


def state_charge_bonus(state: object, actor: Actor) -> int:
    from dnd_board_game.rules.charge_rolls import uses_charge
    mana = getattr(state, "shared_mana", None)
    pool = getattr(mana, "pooled", None)
    if not uses_charge(actor) or pool is None or pool.phase == "drain":
        return 0
    return charge_roll_bonus(pool.points(str(actor.id)))


def charged_check_request(state: object, actor: Actor, request: D20RollRequest) -> D20RollRequest:
    from dnd_board_game.rules.charge_rolls import uses_charge, replace_proficiency
    return replace_proficiency(request, state_charge_bonus(state, actor)) if uses_charge(actor) else request
