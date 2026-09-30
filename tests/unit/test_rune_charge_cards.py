"""The new card edition is complete, consistent and separate from live rules."""
from copy import deepcopy
from dataclasses import replace
from html.parser import HTMLParser
from html import escape
import importlib.util
from pathlib import Path
from typing import Any

import pytest

from dnd_board_game.scenarios.rune_charge_catalog import load_rune_charge_catalog, validate_catalog
from dnd_board_game.ui.board_panel_symbols import RUNES, SYMBOLS, rune_slot


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


@pytest.fixture(scope='module')
def generator() -> Any:
    path = Path(__file__).resolve().parents[2] / 'scripts/build_rune_charges.py'
    spec = importlib.util.spec_from_file_location('charge_generator', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('hero', ['garran','brakka','mira','dagna','lorian','nimra','erynd'])
def test_every_printed_power_has_one_button_both_prices_and_shared_rune_bonus(hero: str, generator: Any) -> None:
    data = load_rune_charge_catalog()
    sheet = generator.render_hero(hero, data)
    parsed = Page()
    parsed.feed(sheet)
    assert len([a for tag,a in parsed.tags if tag == 'article' and 'page' in a.get('class','').split()]) == 5
    assert not any('data-charge' in a for _, a in parsed.tags)
    assert 'charge-track' not in sheet
    first_page = sheet.split('</article>', 1)[0]
    assert data['heroes'][hero]['passive']['description'] in first_page
    assert '<h2>Odzysk klasowy</h2>' in first_page
    assert '<span class="recovery-die">1k4</span>' in first_page
    assert 'Skupienie' not in first_page.split('<div class="charge-personal">', 1)[1]
    assert 'Wspólny limit:' not in sheet
    assert 'Przy pełnej puli możesz pominąć odzysk' not in sheet
    assert 'Cel osobisty' not in first_page
    assert escape(data['heroes'][hero]['vignette']['text']) in first_page
    assert all(t in first_page for t in data['heroes'][hero]['regeneration'])
    assert '01 / 05' in first_page
    for number in range(2, 6):
        assert f'0{number} / 05' in sheet
    assert 'Wzm. +' not in sheet
    assert 'Zwykły atak nie otrzymuje bonusów paczki.' not in sheet
    assert 'Twoja tura i obsługa' not in sheet
    second_page = sheet.split('</article>')[1]
    assert 'landscape' not in second_page
    assert second_page.count('class="goal-slot"') == 1
    assert second_page.count('class="goal-track"') == 1
    assert second_page.count('class="goal-step"') == 5
    assert second_page.count('class="charge-slot"') == len(data['heroes'][hero]['cards']) + 1
    assert 'Rezonans ·' not in second_page
    assert 'biegłość +' not in sheet
    printed = {a['data-card-id']: a for _,a in parsed.tags if 'data-card-id' in a}
    cards = data['heroes'][hero]['cards']
    assert len(cards) == (5 if hero == 'nimra' else 4)
    assert set(printed) == {c['id'] for c in cards} | {'focus'}
    assert len({c['rune'] for c in cards}) == len(cards)
    for card in cards:
        assert printed[card['id']]['data-rune'] == card['rune']
        assert f'data-panel-slot="{rune_slot(card["rune"])}"' in sheet
        assert f'Podst. {card["base_cost"]} / Wzm. {card["enhanced_cost"]}' in sheet
        bonus = next(r['short'] for r in data['runes'] if r['name'] == card['rune'])
        assert bonus in sheet
        assert f'aria-label="Rezonans: {card["rune"]}"' in sheet
        assert card['name'] in sheet
    for rune in data['runes']:
        assert rune['description'] in sheet
    legend = [a['data-legend-rune'] for _, a in parsed.tags if 'data-legend-rune' in a]
    assert len(legend) == len(set(legend)) == 10
    assert set(legend) == set(data['rules']['starter_runes'])
    assert 'koszyk' not in sheet.lower()
    assert data['heroes'][hero]['passive']['description'] in sheet
    assert all(t in sheet for t in data['heroes'][hero]['regeneration'])


def test_garran_revision_keeps_healing_and_prints_charge_and_status_rules(generator: Any) -> None:
    data = load_rune_charge_catalog()
    hero = data['heroes']['garran']
    assert 'stan Żywa osłona: +1 KP' in hero['passive']['description']
    assert hero['regeneration'][1] == 'Przeciwnik chybił atakiem w ciebie.'
    cards = {card['id']: card for card in hero['cards']}
    assert 'regroup' not in cards
    assert cards['bastion_charge']['budget'] == 'M+S'
    assert '1k6 obrażeń magicznych' in cards['breaking_strike']['effect']
    assert 'odległości 1 od celu' in cards['shield_bash']['effect']
    assert cards['second_wind']['effect'] == (
        'Odzyskaj 1k10 + poziom własnych PW, do maksimum. Nie przywraca utraconej akcji ani reakcji.')
    sheet = generator.render_hero('garran', data)
    assert 'ST 10 + Siła + liczba przebytych pól' in sheet
    assert 'Powalony' in sheet
    assert 'dystansowe −2' in sheet
    assert 'Ścieżka przysięgi' not in sheet


@pytest.mark.parametrize('key', ['title', 'text'])
def test_catalog_requires_a_complete_character_scene(key: str) -> None:
    data = deepcopy(load_rune_charge_catalog())
    data['heroes']['garran']['vignette'][key] = ''
    with pytest.raises(ValueError, match='scenki'):
        validate_catalog(data)


@pytest.mark.parametrize('change', ['too_many_powers','same_button','bad_price','recharge_pays_enhancement','missing_hero'])
def test_catalog_rejects_ambiguous_or_self_sustaining_card_sets(change: str) -> None:
    data = deepcopy(load_rune_charge_catalog())
    cards = data['heroes']['garran']['cards']
    if change == 'too_many_powers':
        cards.append(deepcopy(cards[0]))
    elif change == 'same_button':
        cards[1]['rune'] = cards[0]['rune']
    elif change == 'bad_price':
        cards[0]['enhanced_cost'] = cards[0]['base_cost']
    elif change == 'recharge_pays_enhancement':
        cards[0]['base_cost'] = 2
        cards[0]['enhanced_cost'] = data['rules']['regeneration_die']
    else:
        del data['heroes']['mira']
    with pytest.raises(ValueError):
        validate_catalog(data)


def test_information_moved_without_moving_any_other_control_or_old_rune() -> None:
    assert len(SYMBOLS) == 30 and len(RUNES) == 20
    assert [name for name,_ in SYMBOLS[24:]] == ['Iskra','Gwiazda','Zwiększ','Zmniejsz','Zatwierdź','Wróć']
    assert [name for name,_ in SYMBOLS[5:24]] == [
        'Rozwidlenie','Wieża','Klepsydra','Trójząb','Brama','Romb','Hak','Błysk','Oko',
        'Schody','Korona','Węzeł','Grot','Kotwica','Spirala','Kielich','Most','Fala','Klucz']


def test_heroes_share_overlapping_windows_instead_of_identical_rune_sets() -> None:
    data = load_rune_charge_catalog()
    expected = {
        'garran': {'Wieża', 'Grot', 'Schody', 'Błysk'},
        'brakka': {'Grot', 'Schody', 'Błysk', 'Hak'},
        'mira': {'Schody', 'Błysk', 'Hak', 'Oko'},
        'dagna': {'Błysk', 'Hak', 'Oko', 'Kielich'},
        'lorian': {'Hak', 'Oko', 'Kielich', 'Węzeł'},
        'nimra': {'Oko', 'Kielich', 'Węzeł', 'Fala', 'Klepsydra'},
        'erynd': {'Kielich', 'Węzeł', 'Fala', 'Klepsydra'},
    }
    assert {key: {c['rune'] for c in h['cards']} for key, h in data['heroes'].items()} == expected
    assert {r['name'] for r in data['runes']} == set.union(*expected.values())
    assert len({r['stack'] for r in data['runes']}) == 10


def test_legacy_power_only_resonance_cannot_generate_current_cards() -> None:
    data = deepcopy(load_rune_charge_catalog())
    data['rules']['resonance_model'] = 'power_only_packet'
    with pytest.raises(ValueError, match='ciągłego Rezonansu'):
        validate_catalog(data)


@pytest.mark.parametrize('hero,ability', [
    ('garran', 'Siła'), ('brakka', 'Siła'), ('dagna', 'Mądrość'),
    ('lorian', 'Charyzma'), ('nimra', 'Inteligencja'),
])
def test_printed_save_dc_keeps_formula_when_hero_abilities_change(
    hero: str, ability: str, generator: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = load_rune_charge_catalog()
    assert f'ST 10 + {ability}' in generator.render_hero(hero, data)
    original = generator.build_print_hero
    def advanced_hero(*args: Any, **kwargs: Any) -> Any:
        model = original(*args, **kwargs)
        return replace(model, abilities=tuple((name, 24, 7) for name, _, _ in model.abilities))
    monkeypatch.setattr(generator, 'build_print_hero', advanced_hero)
    sheet = generator.render_hero(hero, data)
    assert f'ST 10 + {ability}' in sheet
    assert 'ST 14' not in sheet and 'ST 17' not in sheet


def test_renderer_uses_configured_dc_base_without_mutating_catalog(generator: Any) -> None:
    data = deepcopy(load_rune_charge_catalog())
    data['rules']['save_dc_base'] = 11
    before = deepcopy(data)
    assert 'ST 11 + Inteligencja' in generator.render_hero('nimra', data)
    assert data == before


@pytest.mark.parametrize('change', [
    'missing_bonus', 'duplicate_bonus', 'empty_bonus', 'empty_stacking',
    'wrong_window', 'duplicate_hero_order', 'focus_as_power', 'unknown_board_rune',
])
def test_catalog_rejects_incomplete_or_conflicting_resonance_assignments(change: str) -> None:
    data = deepcopy(load_rune_charge_catalog())
    if change == 'missing_bonus':
        data['runes'].pop()
    elif change == 'duplicate_bonus':
        data['runes'].append(deepcopy(data['runes'][0]))
        data['rules']['starter_runes'].append(data['runes'][0]['name'])
    elif change == 'empty_bonus':
        data['runes'][-1]['description'] = ''
    elif change == 'empty_stacking':
        del data['runes'][-1]['stack']
    elif change == 'wrong_window':
        data['heroes']['garran']['cards'][0]['rune'] = 'Hak'
        data['heroes']['brakka']['cards'][3]['rune'] = 'Wieża'
    elif change == 'duplicate_hero_order':
        data['rules']['hero_rune_order'][-1] = 'nimra'
    else:
        replacement = 'Spirala' if change == 'focus_as_power' else 'Nieznana'
        data['runes'][0]['name'] = replacement
        data['rules']['starter_runes'][0] = replacement
        data['heroes']['garran']['cards'][0]['rune'] = replacement
    with pytest.raises(ValueError):
        validate_catalog(data)
