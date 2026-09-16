"""Labeled ability text shared by character cards on screen and on paper."""
from __future__ import annotations

from dnd_board_game.rules.shared_mana_catalog import shared_ability
from dnd_board_game.scenarios.pooled_mana_catalog import load_catalog, pool_ability

ACTION_LABELS = {'A': 'Akcja główna', 'D': 'Akcja dodatkowa', 'R': 'Reakcja', 'MOD': 'Modyfikacja opisanego działania'}
COLOR_LABELS = {'C': 'czerwona', 'B': 'biała', 'Z': 'zielona', 'F': 'czarna', 'N': 'niebieska'}


def ability_sections(hero_id: str, ability_id: str) -> tuple[tuple[str, str], ...]:
    ability = shared_ability(hero_id, ability_id)
    if ability is None:
        raise ValueError('Nieznana zdolność postaci.')
    cost = pool_ability(ability_id, hero_id)
    profile = load_catalog()['abilities'][ability_id]
    requirement = f'Co najmniej {cost.minimum} pkt. Pula zostaje po użyciu.' if cost.minimum else '0 pkt — dostępna bez naładowania.'
    if cost.required:
        requirement += ' W puli: ' + ', '.join(f'{n} × {COLOR_LABELS[c]}' for c, n in cost.required) + '.'
    burning = ('0 kart.' if cost.burn == 0 else f'{cost.burn} karta z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.'
               if cost.burn == 1 else f'{cost.burn} kart z wierzchu wspólnej talii po efekcie, także przy niepowodzeniu.')
    effect = profile.get('description', ability.description)
    if ability_id == 'spiritual_weapon':
        effect = effect.replace('D + biała', 'akcja dodatkowa, bez spalania')
    duration = {'O': 'Działa do mana draina; wskazane warunki mogą zakończyć wcześniej.',
                'T': 'Działa do początku następnej tury postaci, która użyła zdolności, lub do wcześniejszego wykorzystania.'}.get(ability.duration, '')
    if duration:
        effect += ' ' + duration
    sections = [('Ładunek', requirement), ('Akcja', ACTION_LABELS[ability.timing]), ('Spalanie', burning), ('Efekt', effect)]
    if ability.boosts:
        boosts = []
        for boost in ability.boosts:
            # Colour identifies the rune, not an extra colour requirement.
            label = boost.label.split(': ', 1)[-1]
            boosts.append(f'{label}. Maks. {boost.maximum} razy.')
        maximum = min(ability.boost_limit, sum(b.maximum for b in ability.boosts))
        sections.append(('Podbicia', ' '.join(boosts) + f' Każde: +2 spalone karty. Łącznie maks. {maximum}. Kolor runy nie wymaga tego koloru w puli ani w spaleniu.'))
    return tuple(sections)
