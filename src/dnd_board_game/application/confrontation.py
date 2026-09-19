"""Build a rules-only party confrontation from actor data and an authored scene."""
from __future__ import annotations
from dataclasses import replace

from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dnd_board_game.actors import Actor
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
from dnd_board_game.rules.confrontation import Confrontation, Participant
from dnd_board_game.rules.pooled_mana import new_mana
from dnd_board_game.rules.exploration_mana_catalog import hero_methods
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
from dnd_board_game.scenarios.confrontation import passives, validate_approaches
from .exploration_mana_flow import method_modifiers


def build(actors: tuple[Actor, ...], scene: dict, *, excluded: tuple[str, ...] = ()) -> Confrontation:
    participants = []
    options = []
    values = {}
    if 'approaches' in scene:
        validate_approaches(scene['approaches'])
        if len(scene['approaches']) < len(actors) and not any(a.get('repeatable', False) for a in scene['approaches']):
            raise ValueError('Scena wymaga odrębnego podejścia dla każdego bohatera lub opcji powtarzalnej.')
    for actor in actors:
        key = str(actor.id)
        passive_kinds = tuple((c, p['kind']) for c, p in passives(key).items())
        if 'approaches' in scene:
            own = []
            for approach in scene['approaches']:
                modifier = effective_ability_modifier(actor, approach['ability'])
                label = ABILITY_LABELS_PL[approach['ability']]
                own.append(Participant(key, actor.name, approach['name'], modifier, modifier,
                    approach['dc'], approach['die'], passive_kinds, label, ((label, modifier),),
                    approach['id'], approach['description'], tuple(approach['supports']), approach.get('repeatable', False)))
            options.append(tuple(own))
            participants.append(replace(own[0], method='Wybierz podejście', approach_id=''))
        else:
            # Completed/in-progress snapshots authored before scene approaches.
            method = next(m for m in hero_methods(key) if m.kind == scene['kind'])
            profile = scene['methods'][key]
            participants.append(Participant(key, actor.name, method.name,
                sum(m.value for m in method_modifiers(actor, method)),
                effective_ability_modifier(actor, method.ability), profile['dc'], profile['die'],
                passive_kinds, ABILITY_LABELS_PL[method.ability],
                tuple((m.label, m.value) for m in method_modifiers(actor, method))))
        values[key] = hero_profile(key)['values']
    party = tuple(participants)
    pool = new_mana(tuple(p.id for p in party), party[0].id, values=values, excluded=excluded)
    resistance = scene['resistance_per_hero'] * len(party)
    return Confrontation(party, pool, resistance, resistance,
        max(scene['minimum_pressure'], scene['pressure_per_hero'] * len(party)),
        reactions=tuple(r['kind'] for r in scene['reactions']), condition=scene['condition'],
        first_test_bonus=scene.get('first_test_bonus', 0), first_test_label=scene.get('first_test_label', ''),
        approach_options=tuple(options), approach_selection_version=3)


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
