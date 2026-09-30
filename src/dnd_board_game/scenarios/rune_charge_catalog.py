"""Read the v0.2 card specification without activating it in combat."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.ui.board_panel_symbols import RUNES, SYMBOLS, rune_slot

CATALOG_PATH = Path(__file__).resolve().parents[3] / 'content/print/rune_charges_v02/catalog.json'


def validate_catalog(data: dict[str, Any]) -> None:
    """Reject ambiguous card counts, prices, symbols and recovery budgets."""
    rules = data['rules']
    if data['profile'] != 'rune_charges_v02' or data['stage'] != 'cards_only':
        raise ValueError('Katalog v0.2 jest etapem kart, nie aktywacją zasad w aplikacji.')
    if rules.get('resonance_model') != 'ongoing_chain_effects':
        raise ValueError('Karty wymagają ciągłego Rezonansu z globalnym wygaszeniem premii.')
    if (rules['start_charges'], rules['max_charges'], rules['focus_die']) != (20, 20, 20):
        raise ValueError('Pierwszy test: 20/20 ładunków i Skupienie 1k20.')
    if rules['regeneration_die'] != 4 or rules['regeneration_limit'] != 'once_per_hero_per_round':
        raise ValueError('Regeneracja: wspólny limit 1k4 na bohatera na rundę.')
    runes = [r['name'] for r in data['runes']]
    if not runes or len(set(runes)) != len(runes) or runes != rules['starter_runes']:
        raise ValueError('Runy początkowe muszą być różne i mieć wspólne bonusy.')
    if any(not rune.get(key) for rune in data['runes'] for key in ('short', 'description', 'stack')):
        raise ValueError('Każda runa wymaga bonusu, pełnego opisu i zasad kumulowania.')
    if set(runes) - {name for name, _ in RUNES}:
        raise ValueError('Runa początkowa nie występuje na planszy.')
    if len(RUNES) != 20 or len(SYMBOLS) != 30 or rune_slot('Gwiazda') != rules['information_slot']:
        raise ValueError('Panel wymaga 20 run oraz osobnej Gwiazdy obok + i −.')
    if set(data['heroes']) != set(PLAYABLE_HERO_IDS):
        raise ValueError('Wymagany jest zestaw wszystkich siedmiu bohaterów.')
    order = rules['hero_rune_order']
    if len(order) != len(PLAYABLE_HERO_IDS) or set(order) != set(PLAYABLE_HERO_IDS):
        raise ValueError('Kolejność przesunięcia musi obejmować każdego bohatera raz.')
    if rules['focus_rune'] in runes:
        raise ValueError('Runa Skupienia pozostaje osobną opcją, bez bonusu Rezonansu.')
    if set(runes) != {card['rune'] for hero in data['heroes'].values() for card in hero['cards']}:
        raise ValueError('Każda runa początkowa musi mieć moc; każda moc — zdefiniowany bonus.')
    for hero_id, hero in data['heroes'].items():
        vignette = hero.get('vignette', {})
        if not all(isinstance(vignette.get(key), str) and vignette[key].strip()
                   for key in ('title', 'text')):
            raise ValueError(f'{hero_id}: brak scenki na pierwszą stronę karty.')
        count = 5 if hero_id == 'nimra' else 4
        if len(hero['cards']) != count or len({c['rune'] for c in hero['cards']}) != count:
            raise ValueError(f'{hero_id}: wymagane {count} moce pod różnymi runami.')
        offset = order.index(hero_id)
        window = runes[offset:offset + count]
        if len(window) != count or set(window) != {c['rune'] for c in hero['cards']}:
            raise ValueError(f'{hero_id}: zestaw musi być przesunięty o jedną runę.')
        if len({c['id'] for c in hero['cards']}) != count:
            raise ValueError(f'{hero_id}: powtórzony identyfikator mocy.')
        if len(hero['regeneration']) != 2 or not all(hero['regeneration']):
            raise ValueError(f'{hero_id}: podaj dwa alternatywne warunki odzysku.')
        for card in hero['cards']:
            if card['rune'] not in runes or card['budget'] not in {'S', 'A+S', 'M+S'}:
                raise ValueError(f'{hero_id}: nieprawidłowa runa lub ekonomia mocy.')
            if not 0 < card['base_cost'] < card['enhanced_cost'] <= rules['max_charges']:
                raise ValueError(f'{hero_id}: nieprawidłowy całkowity koszt trybu.')
            if card['enhanced_cost'] <= rules['regeneration_die']:
                raise ValueError(f'{hero_id}: sam odzysk może bez końca opłacać wzmocnienie.')
            if not all(card[key] for key in ('name', 'effect', 'target', 'requirements')):
                raise ValueError(f'{hero_id}: niepełny opis mocy.')


def load_rune_charge_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_catalog(data)
    return data
