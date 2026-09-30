"""The basket playtest shares one catalogue across cards, mats and its browser data."""
from __future__ import annotations

from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
from typing import Any

import pytest

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards.rune_baskets import (
    action_cards_content, basket_content, build_payload,
)
from dnd_board_game.scenarios.rune_basket_catalog import load_rune_basket_catalog

ROOT = Path(__file__).resolve().parents[2]


class PageContents(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))
        if tag in {'style', 'script'}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {'style', 'script'}:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.text.append(data)


@pytest.fixture(scope='module')
def catalog() -> dict[str, Any]:
    return load_rune_basket_catalog()


@pytest.fixture(scope='module')
def payload(catalog: dict[str, Any]) -> dict[str, Any]:
    return build_payload(catalog)


@pytest.fixture(scope='module')
def generator() -> Any:
    spec = importlib.util.spec_from_file_location('basket_print_generator', ROOT / 'scripts/build_rune_baskets.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_preserves_every_shared_rule_and_enriches_seven_heroes(
    catalog: dict[str, Any], payload: dict[str, Any],
) -> None:
    assert payload['categories'] == catalog['categories']
    assert payload['rules'] == catalog['rules']
    assert tuple(hero['id'] for hero in payload['heroes']) == PLAYABLE_HERO_IDS
    assert sum(len(hero['cards']) for hero in payload['heroes']) == 65
    for hero in payload['heroes']:
        for key, value in catalog['heroes'][hero['id']].items():
            assert hero[key] == value
        assert hero['hp'] > 0 and hero['ac'] > 0
        assert len(hero['abilities']) == 6
        assert hero['story'] and hero['equipment']
        assert (ROOT / 'docs/ui' / hero['portrait']).is_file()
        assert all(item['slot'] and item['quantity'] > 0 for item in hero['equipment'])


def test_each_basket_has_exact_capacity_in_both_areas_and_a_complete_d4_table(payload: dict[str, Any]) -> None:
    for hero in payload['heroes']:
        html = basket_content(hero, payload['categories'], payload['rules'])
        parser = PageContents()
        parser.feed(html)
        current: str | None = None
        slots: dict[str, dict[str, int]] = {}
        dice: dict[str, list[int]] = {}
        for _, attrs in parser.tags:
            if attrs.get('class') == 'basket-cell':
                current = str(attrs['data-category'])
                slots[current] = {'ready': 0, 'spent': 0}
                dice[current] = []
                assert int(str(attrs['data-capacity'])) == hero['capacities'][current]
            if current is not None:
                slots[current]['ready'] += 'data-ready-slot' in attrs
                slots[current]['spent'] += 'data-spent-slot' in attrs
                if 'data-d4' in attrs:
                    dice[current].append(int(str(attrs['data-d4'])))
        assert slots == {category: {'ready': amount, 'spent': amount}
                         for category, amount in hero['capacities'].items()}
        assert all(results == [1, 2, 3, 4] for results in dice.values())
        text = ' '.join(parser.text)
        for trigger in hero['regeneration']:
            assert trigger['label'] in text
        assert payload['rules']['focus_description'] in text
        assert payload['rules']['support_description'] in text


def test_action_button_and_category_are_independent_and_resonances_match(payload: dict[str, Any]) -> None:
    for hero in payload['heroes']:
        html = action_cards_content(hero, payload['categories'])
        parser = PageContents()
        parser.feed(html)
        cards = [attrs for _, attrs in parser.tags if 'data-card-id' in attrs]
        assert {str(card['data-card-id']): card['data-category'] for card in cards} == {
            card['id']: card['category'] for card in hero['cards']}
        assert len([attrs for _, attrs in parser.tags if attrs.get('class') == 'basket-action']) == 12
        for card in hero['cards']:
            assert f'data-panel-slot="{card["slot"]}"' in html
            assert card['description'] in ' '.join(parser.text)
            for resonance in card['resonances']:
                assert resonance['description'] in ' '.join(parser.text)
    brakka = next(hero for hero in payload['heroes'] if hero['id'] == 'brakka')
    reckless = next(card for card in brakka['cards'] if card['id'] == 'reckless_attack')
    assert reckless['button'] == 'Wieża'
    assert reckless['category'] == 'defense'


def test_seven_complete_sets_preserve_identity_equipment_and_six_pages(
    payload: dict[str, Any], generator: Any,
) -> None:
    for hero in payload['heroes']:
        html = generator.render_hero(hero, payload)
        parser = PageContents()
        parser.feed(html)
        text = ' '.join(parser.text)
        assert len([attrs for tag, attrs in parser.tags if tag == 'article' and 'page' in str(attrs.get('class', '')).split()]) == 6
        assert hero['flaw']['description'] in ''.join(parser.text)
        assert 'Aktualne zobowiązania' not in text
        assert 'Żetony run · własne koszyki' in text
        assert len([a for _, a in parser.tags if 'data-token-slot' in a]) == sum(hero['capacities'].values())
        assert all(story in text for _, story in hero['story'])
        printed_items = {attrs['data-id'] for _, attrs in parser.tags if attrs.get('class') == 'item'}
        assert printed_items == {item['id'] for item in hero['equipment']}
        assert not re.search(r'\b(?:nasycenie|spalanie|talia many|talii many|limit 7)\b', text, re.I)


def test_data_only_export_round_trips_the_catalogue(
    payload: dict[str, Any], generator: Any, tmp_path: Path,
) -> None:
    destination = tmp_path / 'ui' / 'data.js'
    generator.write_data(payload, destination)
    contents = destination.read_text(encoding='utf-8')
    raw = contents.split('window.RUNE_BASKET_DATA = ', 1)[1].removesuffix(';\n')
    assert json.loads(raw) == json.loads(json.dumps(payload))
    assert not list(tmp_path.rglob('*.pdf'))
