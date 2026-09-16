"""Build a rules-only party confrontation from actor data and an authored scene."""
from __future__ import annotations
from dnd_board_game.actors import Actor
from dnd_board_game.rules import ability_modifier
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
from dnd_board_game.rules.confrontation import Confrontation, Participant
from dnd_board_game.rules.pooled_mana import new_mana
from dnd_board_game.rules.exploration_mana_catalog import hero_methods
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
from dnd_board_game.scenarios.confrontation import passives
from .exploration_mana_flow import method_modifiers


def build(actors: tuple[Actor, ...], scene: dict) -> Confrontation:
    participants = []
    values = {}
    for actor in actors:
        key = str(actor.id)
        method = next(m for m in hero_methods(key) if m.kind == scene['kind'])
        profile = scene['methods'][key]
        participants.append(Participant(key, actor.name, method.name,
            sum(m.value for m in method_modifiers(actor, method)),
            ability_modifier(getattr(actor.ability_scores, method.ability)), profile['dc'], profile['die'],
            tuple((c, p['kind']) for c, p in passives(key).items()), ABILITY_LABELS_PL[method.ability],
            tuple((m.label, m.value) for m in method_modifiers(actor, method))))
        values[key] = hero_profile(key)['values']
    party = tuple(participants)
    pool = new_mana(tuple(p.id for p in party), party[0].id, values=values)
    resistance = scene['resistance_per_hero'] * len(party)
    return Confrontation(party, pool, resistance, resistance,
        max(scene['minimum_pressure'], scene['pressure_per_hero'] * len(party)),
        reactions=tuple(r['kind'] for r in scene['reactions']), condition=scene['condition'])


def prepare_lesson(state: Confrontation, lesson_id: str) -> Confrontation:
    """Conserved, explicit physical fixtures for isolated edge-case lessons."""
    from dataclasses import replace
    from dnd_board_game.rules.pooled_mana import COLORS
    pool = state.mana
    if pool.phase != 'reveal' or pool.offer or pool.pools:
        raise ValueError('Fixture wymaga świeżo przygotowanej talii.')
    if lesson_id in {'charge', 'reaction'}:
        values = pool.point_values(state.actor.id)
        high, low = max(values, key=values.get), min(values, key=values.get)
        hand = (high,) * (2 if lesson_id == 'charge' else 3)
        offer = (high, low) if lesson_id == 'charge' else ()
        pool = replace(pool, pools=((state.actor.id, hand),), offer=offer,
                       deck=(None,) * (len(pool.deck) - len(hand) - len(offer)),
                       phase='choose' if offer else 'ready', draw_due=bool(offer))
        return replace(state, mana=pool, stage='turn' if offer else 'reaction',
                       round=1 if offer else 2)
    if lesson_id == 'drain':
        # Three known cards remain; all others are physically placed in burned.
        deck = ('C', 'B', 'N')
        burned = list(c for c in COLORS for _ in range(pool.copies))
        for color in deck:
            burned.remove(color)
        return replace(state, mana=replace(pool, deck=deck, burned=tuple(burned)))
    return state
