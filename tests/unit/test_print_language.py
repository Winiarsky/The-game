"""Editorial rendering checks: safe emphasis and complete common player aid."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

from dnd_board_game.physical_cards.print_language import keyword_text

ROOT = Path(__file__).resolve().parents[2]
COPY = ROOT / 'content/print/characters/mats_v2'


def test_keyword_emphasis_handles_inflection_and_longest_phrase() -> None:
    result = keyword_text('Wpływu nie dodaj do wpływowego tekstu. Pula many.', ['wpływu', 'many', 'pula many'])
    assert result == '<strong class="keyword">Wpływu</strong> nie dodaj do wpływowego tekstu. <strong class="keyword">Pula many</strong>.'


def test_keyword_emphasis_escapes_content_and_literal_terms() -> None:
    result = keyword_text('<img onerror="oops"> mod. SIŁ + KP & KP2', ['mod. SIŁ', 'KP'])
    assert '<img' not in result
    assert '&lt;img onerror=&quot;oops&quot;&gt;' in result
    assert '<strong class="keyword">mod. SIŁ</strong>' in result
    assert '&amp; KP2' in result
    assert keyword_text('<none>', []) == '&lt;none&gt;'


def test_all_character_mats_have_mechanical_emphasis(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    mats = importlib.import_module('build_hero_mats')
    copy = json.loads((COPY / 'copy.json').read_text())
    for hid in mats.PLAYABLE_HERO_IDS:
        hero = mats.build_print_hero(hid)
        own = {**copy['heroes'][hid], 'exploration_copy': copy['exploration_passives']}
        actions = mats.actions_page(hero, own)
        mana = mats.mana_page(hero, own)
        assert actions.count('class="action"') == len(hero.cards)
        assert mana.count('class="passive-block ') == 10
        assert '<strong class="keyword">' in actions
        assert '<strong class="keyword">' in mana
        assert 'Własna flanka' not in actions
        assert 'Ognisko' not in mats.equipment_page(hero)
        assert not any(code in actions for code in ('(T)', '(O)', 'obrona KON', 'remis broni'))


def test_player_aid_explains_each_mode_and_is_generated(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    mats = importlib.import_module('build_hero_mats')
    pages = json.loads((COPY / 'player_aid.json').read_text())
    assert [p['id'] for p in pages] == ['01_podstawy','02_walka','03_rozmowy','04_obiekty']
    for page in pages:
        html = mats.player_aid_page(page)
        assert page['title'] in html
        assert '<strong class="keyword">' in html
        for section in page['sections']:
            assert section['title'] in html
    assert 'zwiększy premię do +3' in json.dumps(pages, ensure_ascii=False)
    assert 'nie dodaje nowych powiązań' in json.dumps(pages, ensure_ascii=False)
    assert 'postęp 3 + 4 + 1 = 8' in json.dumps(pages, ensure_ascii=False)
